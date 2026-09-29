#!/usr/bin/env python3
"""spectool - lint and export Markdown requirement specifications.

Part of the spec-specialist skill. Python 3.8+, standard library only.

Usage:
  spectool.py lint   SPEC [--notes NOTES] [--format text|json] [--min-severity info|warn|error]
  spectool.py export SPEC [--csv PATH] [--html PATH] [--out-dir DIR] [--only csv|html]
                          [--no-bom] [--delimiter CHAR] [--cell-format text|html]
  spectool.py refs   SPEC [--kind all|req|info|heading]
  spectool.py tbx    SPEC [--notes NOTES]

Spec format (details in references/spec-template.md):
  * optional front matter between '---' lines (simple "key: value" YAML subset);
  * Markdown headings without manual numbers (numbers are computed);
  * 'INFO:' items - non-binding context; may span paragraphs, lists and tables;
  * 'REQ:' items - one sentence with one "shall", followed by "- Attribute: value"
    bullets (Rationale, Verification, Source, ...). No IDs: Polarion assigns them.

Rule codes: Rn = INCOSE Guide to Writing Requirements v3.1 rule n; ISO-x = clause x
of ISO/IEC/IEEE 29148:2018; NRM-x = section x of the INCOSE Needs and Requirements
Manual. Lint findings are heuristics: a human (or Claude) confirms each one.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


class SpecError(Exception):
    """Unrecoverable problem with the spec file (bad front matter, unreadable file)."""


# --------------------------------------------------------------------------- model

@dataclass
class Item:
    kind: str                       # heading | info | req | loose
    text: str
    line: int
    level: int = 0                  # heading level (1 = '#')
    attrs: Dict[str, str] = field(default_factory=dict)
    attr_lines: Dict[str, int] = field(default_factory=dict)
    number: str = ""                # heading number, e.g. "3.1"
    section: str = "0"              # number of the enclosing heading
    section_title: str = ""
    ordinal: int = 0                # position of the REQ/INFO/TEXT item within its section

    @property
    def ref(self) -> str:
        if self.kind == "heading":
            return "§" + self.number
        label = {"req": "REQ", "info": "INFO", "loose": "TEXT"}[self.kind]
        return "§%s %s %d" % (self.section, label, self.ordinal)

    def attr(self, name: str) -> Optional[str]:
        """Case-insensitive attribute lookup."""
        for key, value in self.attrs.items():
            if key.lower() == name.lower():
                return value
        return None


@dataclass
class Spec:
    meta: Dict[str, object]
    items: List[Item]
    path: str = ""

    def of(self, kind: str) -> List[Item]:
        return [it for it in self.items if it.kind == kind]


DEFAULT_META: Dict[str, object] = {
    "verification_methods": ["Test", "Analysis", "Inspection", "Demonstration"],
    "required_attributes": ["Rationale", "Verification"],
    "csv_columns": ["Type", "Level", "Title", "Description", "Rationale", "Verification", "Source"],
    "csv_delimiter": ",",
    "type_names": {"heading": "Heading", "info": "Information", "req": "Requirement"},
}


# --------------------------------------------------------------------- front matter

def _strip_yaml_comment(value: str) -> str:
    quote = None
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1] in " \t"):
            return value[:i].rstrip()
    return value


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _split_top(text: str) -> List[str]:
    parts, buf, depth, quote = [], [], 0, None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _value(raw: str) -> object:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [_scalar(x) for x in _split_top(raw[1:-1])]
    if raw.startswith("{") and raw.endswith("}"):
        out: Dict[str, str] = {}
        for part in _split_top(raw[1:-1]):
            key, _, val = part.partition(":")
            out[_scalar(key)] = _scalar(val)
        return out
    return _scalar(raw)


def parse_front_matter(lines: Sequence[str]) -> Tuple[Dict[str, object], int]:
    """Parse the YAML subset used by specs. Returns (meta, index of first body line)."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta: Dict[str, object] = {}
    key: Optional[str] = None
    for i in range(1, len(lines)):
        raw = lines[i].rstrip()
        if raw.strip() == "---":
            return meta, i + 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", raw)
        if item and key is not None:
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(_scalar(_strip_yaml_comment(item.group(1))))  # type: ignore[union-attr]
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", raw)
        if not pair:
            raise SpecError("front matter line %d cannot be parsed: %r" % (i + 1, raw))
        key = pair.group(1)
        value = _strip_yaml_comment(pair.group(2))
        meta[key] = _value(value) if value.strip() else []
    raise SpecError("front matter is not closed with '---'")


# ---------------------------------------------------------------------------- parser

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
MARKER_RE = re.compile(r"^(INFO|REQ):[ \t]?(.*)$")
ATTR_RE = re.compile(r"^\s*[-*]\s+([A-Za-z][A-Za-z0-9 _/-]{0,40}?)\s*:\s*(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _blank_comments(text: str) -> str:
    """Remove HTML comments but keep line numbering."""
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def parse_spec(text: str, path: str = "") -> Spec:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("﻿"):
        text = text[1:]
    lines = text.split("\n")
    raw_meta, start = parse_front_matter(lines)
    meta = dict(DEFAULT_META)
    meta.update(raw_meta)
    if isinstance(raw_meta.get("type_names"), dict):
        names = dict(DEFAULT_META["type_names"])  # type: ignore[arg-type]
        names.update(raw_meta["type_names"])  # type: ignore[arg-type]
        meta["type_names"] = names

    body = _blank_comments("\n".join(lines[start:])).split("\n")
    items: List[Item] = []
    cur: Optional[Item] = None
    last_attr: Optional[str] = None
    in_fence = False

    def close() -> None:
        nonlocal cur, last_attr
        if cur is not None:
            if cur.kind == "req":
                cur.text = " ".join(cur.text.split())
            else:
                cur.text = cur.text.strip("\n").rstrip()
            if cur.kind != "loose" or cur.text.strip():
                items.append(cur)
        cur, last_attr = None, None

    def open_loose(lineno: int) -> None:
        nonlocal cur
        close()
        cur = Item("loose", "", lineno)

    for idx, raw in enumerate(body):
        lineno = start + idx + 1
        line = raw.rstrip()
        if in_fence or FENCE_RE.match(line):
            if FENCE_RE.match(line):
                in_fence = not in_fence
            if cur is None or cur.kind == "req":
                open_loose(lineno)
            cur.text += raw + "\n"  # type: ignore[union-attr]
            continue
        heading = HEADING_RE.match(line)
        if heading:
            close()
            items.append(Item("heading", heading.group(2).strip(), lineno, level=len(heading.group(1))))
            continue
        marker = MARKER_RE.match(line)
        if marker:
            close()
            kind = marker.group(1).lower()
            cur = Item(kind, marker.group(2) + ("" if kind == "req" else "\n"), lineno)
            continue
        if cur is not None and cur.kind == "req":
            if not line.strip():
                close()
                continue
            attr = ATTR_RE.match(line)
            if attr:
                last_attr = attr.group(1).strip()
                cur.attrs[last_attr] = attr.group(2).strip()
                cur.attr_lines[last_attr] = lineno
                continue
            if last_attr is not None and raw[:1] in (" ", "\t"):
                cur.attrs[last_attr] = (cur.attrs[last_attr] + " " + line.strip()).strip()
                continue
            if last_attr is None:
                cur.text += " " + line.strip()   # hard-wrapped statement
                continue
            open_loose(lineno)
            cur.text += raw + "\n"  # type: ignore[union-attr]
            continue
        if cur is not None:
            cur.text += raw + "\n"
            continue
        if line.strip():
            open_loose(lineno)
            cur.text += raw + "\n"  # type: ignore[union-attr]
    close()
    _number(items)
    return Spec(meta=meta, items=items, path=path)


def _number(items: List[Item]) -> None:
    counters = [0] * 7
    section, title = "0", ""
    ordinals: Dict[str, int] = {}
    for it in items:
        if it.kind == "heading":
            counters[it.level] += 1
            for k in range(it.level + 1, 7):
                counters[k] = 0
            it.number = ".".join(str(counters[k]) for k in range(1, it.level + 1))
            section, title = it.number, it.text
            ordinals = {}
        else:
            ordinals[it.kind] = ordinals.get(it.kind, 0) + 1
            it.ordinal = ordinals[it.kind]
            it.section, it.section_title = section, title


def load_spec(path: str) -> Spec:
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return parse_spec(fh.read(), path=str(path))
    except OSError as exc:
        raise SpecError(str(exc)) from exc


def default_notes_path(spec_path: str) -> str:
    base = spec_path[:-3] if spec_path.lower().endswith(".md") else spec_path
    return base + ".notes.md"


# ------------------------------------------------------------------------ word lists
# Sources: GtWR v3.1 rule examples, ISO/IEC/IEEE 29148 5.2.7, NRM 4.3.5.1.2.
# Lists are deliberately short and editable; each hit is a prompt for judgment.

VAGUE = [
    "allowable", "several", "many", "a lot of", "a few", "almost always", "very nearly",
    "nearly", "about", "close to", "almost", "approximate", "approximately", "ancillary",
    "relevant", "routine", "common", "generic", "significant", "significantly", "flexible",
    "expandable", "typical", "typically", "sufficient", "sufficiently", "adequate",
    "adequately", "appropriate", "appropriately", "efficient", "efficiently", "effective",
    "effectively", "proficient", "reasonable", "reasonably", "customary", "usually",
    "normally", "best", "most", "user friendly", "user-friendly", "easy to use",
    "easy-to-use", "cost effective", "cost-effective", "minimal", "better than",
    "higher quality", "high quality", "robust", "affordable", "some", "suitable",
    "properly", "correctly",
]
VAGUE_LOWER_ONLY = ["safe", "safely", "secure", "securely"]   # capitalised = defined term
ESCAPE = [
    "so far as is possible", "as far as possible", "as little as possible", "where possible",
    "as much as possible", "if it should prove necessary", "if necessary",
    "to the extent necessary", "as appropriate", "as required", "to the extent practical",
    "if practicable", "if possible", "as applicable", "where applicable", "when necessary",
    "when needed", "if needed",
]
OPEN_ENDED = [
    "including but not limited to", "but not limited to", "not limited to", "etc.", "etc",
    "and so on", "as a minimum", "provide support", "among others", "and the like",
]
SUPERFLUOUS = [
    "be able to", "be capable of", "be designed to", "have the capability to",
    "have the ability to", "be possible to",
]
NEGATIONS = ["not", "cannot", "nor"]                          # lower case; NOT is logical
COMBINATORS = [
    "and", "or", "then", "unless", "but", "as well as", "but also", "however", "whether",
    "meanwhile", "whereas", "on the other hand", "otherwise",
]
PURPOSE = [
    "in order to", "so that", "so as to", "thus allowing", "thereby", "for the purpose of",
    "with the aim of",
]
PRONOUNS = ["it", "its", "this", "these", "those", "they", "them", "their", "he", "she", "his", "her", "him"]
ABSOLUTES = ["all", "every", "always", "never", "100%", "100 %"]
UNIVERSALS = ["any", "both", "whichever", "whatever"]
UNMEASURED = [
    "prompt", "promptly", "fast", "faster", "quick", "quickly", "maximum", "minimum",
    "maximize", "minimize", "maximise", "minimise", "optimum", "optimal", "optimize",
    "optimise", "nominal", "high speed", "high-speed", "low latency", "low-latency",
    "high throughput", "high-throughput", "medium-sized", "best practices",
    "as fast as possible", "as soon as possible", "real-time", "real time", "rapid",
    "rapidly", "slow", "large", "small",
]
TEMPORAL = [
    "eventually", "instantaneous", "instantaneously", "simultaneous", "simultaneously",
    "immediately", "soon", "at last", "earliest", "latest", "subsequently", "later",
]
TEMPORAL_UNQUANTIFIED = ["until", "before", "after", "as soon as", "once", "when finished"]
INTERFACE = ["interface", "interfaces", "interfacing", "interfaced"]
EXAMPLES = ["e.g.", "i.e.", "such as", "for example", "for instance"]
WEAK_VERBS = ["support", "supports", "process", "handle", "track", "manage", "flag"]
INFO_HIDDEN = [
    "shall", "must", "should", "required", "requires", "require", "mandatory", "need to",
    "needs to", "has to", "have to",
]

UNIT_WORDS = {
    "s", "ms", "us", "µs", "ns", "ps", "sec", "second", "seconds", "millisecond",
    "milliseconds", "microsecond", "microseconds", "nanosecond", "nanoseconds", "hz", "khz",
    "mhz", "ghz", "bit", "bits", "byte", "bytes", "b", "kb", "kib", "mb", "mib", "gb",
    "kbit", "mbit", "gbit", "kbps", "mbps", "gbps", "cycle", "cycles", "clock", "clocks",
    "block", "blocks", "word", "words", "beat", "beats", "transfer", "transfers", "w", "mw",
    "uw", "µw", "v", "mv", "a", "ma", "ua", "°c", "c", "k", "mm", "um", "µm", "nm", "mm2",
    "um2", "gate", "gates", "ge", "kge", "percent", "%", "ppm", "lsb", "lsbs",
}
STOP_AFTER_NUMBER = {
    "after", "before", "of", "to", "from", "in", "on", "at", "by", "for", "with", "within",
    "and", "or", "than", "when", "while", "if", "the", "a", "an", "is", "are", "per", "that",
    "which", "unless", "until",
}
SKIP_BEFORE_NUMBER = {
    "to", "is", "are", "=", "of", "equals", "equal", "section", "sections", "§", "table",
    "figure", "fig", "clause", "annex", "appendix", "fips", "sp", "rfc", "iso", "iec",
    "ieee", "version", "v", "rev", "revision", "issue", "part", "bit", "byte", "level",
    "step", "index", "channel", "slot", "register", "field", "value", "amba", "release",
    "edition", "chapter", "item", "row", "column", "state", "mode",
}


def _phrase_re(phrases: Sequence[str], case_sensitive: bool = False) -> "re.Pattern[str]":
    parts = [re.escape(p).replace(r"\ ", r"\s+") for p in sorted(phrases, key=len, reverse=True)]
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(r"(?<![\w-])(?:" + "|".join(parts) + r")(?![\w-])", flags)


WORD_RULES = [
    ("ISO-5.2.4.must", "ERROR", ["must"], False,
     '"{w}" is not the agreed requirement keyword; use "shall" (ISO 29148 5.2.4).'),
    ("ISO-5.2.4.will", "WARN", ["will"], False,
     '"will" states a fact or intent, not a requirement; use "shall" or move the text to an INFO item (ISO 5.2.4).'),
    ("ISO-5.2.4.goal", "WARN", ["should", "may"], False,
     '"{w}" marks a goal or an allowance, which is not binding (ISO 5.2.4); confirm the intent.'),
    ("R7", "WARN", VAGUE, False,
     'vague term "{w}"; replace with a measurable value or a defined term (GtWR R7, ISO 5.2.7).'),
    ("R7", "WARN", VAGUE_LOWER_ONLY, True,
     'vague term "{w}"; state the security or safety property to verify (GtWR R7, NRM 4.3.5.1.2).'),
    ("R8", "WARN", ESCAPE, False,
     'escape clause "{w}" makes the requirement optional (GtWR R8, ISO 5.2.7).'),
    ("R9", "WARN", OPEN_ENDED, False,
     'open-ended "{w}"; list each case as its own requirement (GtWR R9).'),
    ("R10", "WARN", SUPERFLUOUS, False,
     'superfluous "{w}"; state the action directly ("shall <verb>") (GtWR R10, ISO 5.2.4).'),
    ("R16", "WARN", NEGATIONS, True,
     'negative statement "{w}"; state the positive, verifiable behavior (GtWR R16, ISO 5.2.4).'),
    ("R19", "WARN", COMBINATORS, True,
     'combinator "{w}"; check the requirement is singular; write logical conditions as [X AND Y] (GtWR R19, R15).'),
    ("R20", "WARN", PURPOSE, False,
     'purpose phrase "{w}"; move the reason to the Rationale attribute (GtWR R20).'),
    ("R24", "WARN", PRONOUNS, False,
     'pronoun "{w}"; repeat the noun (GtWR R24, ISO 5.2.7).'),
    ("R26", "WARN", ABSOLUTES, False,
     'absolute "{w}"; use "each" with an explicit set, or a verifiable limit (GtWR R26, R32).'),
    ("R32", "WARN", UNIVERSALS, False,
     'universal quantifier "{w}"; use "each" (GtWR R32).'),
    ("R34", "WARN", UNMEASURED, False,
     'unmeasured "{w}"; give a measurable target with units (GtWR R34).'),
    ("R35", "WARN", TEMPORAL, False,
     'indefinite timing "{w}"; state the time limit with units (GtWR R35).'),
    ("NRM-6.2.3.interface", "WARN", INTERFACE, False,
     '"{w}" in a requirement; state the specific interaction (verb + object) and point to its definition (NRM 6.2.3.2).'),
    ("R21.example", "WARN", EXAMPLES, False,
     '"{w}" introduces examples inside a requirement; move them to Rationale or an INFO item (GtWR R9, R21).'),
]
COMPILED_RULES = [(code, sev, _phrase_re(words, cs), msg) for code, sev, words, cs, msg in WORD_RULES]
TEMPORAL_UNQ_RE = _phrase_re(TEMPORAL_UNQUANTIFIED)
INFO_HIDDEN_RE = _phrase_re(INFO_HIDDEN)
SHALL_RE = re.compile(r"\bshall\b", re.IGNORECASE)
WEAK_VERB_RE = re.compile(r"\bshall\s+(?:not\s+)?(" + "|".join(WEAK_VERBS) + r")\b", re.IGNORECASE)
PASSIVE_RE = re.compile(
    r"\bshall\s+(?:not\s+)?be\s+(\w+(?:ed|en)|set|reset|sent|read|written|kept|held|put|built|done|made|shown|given|taken)\b",
    re.IGNORECASE)
ANDOR_RE = re.compile(r"\band\s*/\s*or\b", re.IGNORECASE)
TBX_RE = re.compile(r"\b(TBD|TBR|TBC|TBS)-(\d+)\b")
BARE_TBX_RE = re.compile(r"\b(TBD|TBR|TBC|TBS)\b(?!-\d)")
TBR_BRACKET_RE = re.compile(r"\[[^\]\[]*\b(?:TBR|TBC)-\d+\]")
TBX_HIGHLIGHT_RE = re.compile(r"\[[^\]\[]*\b(?:TBR|TBC)-\d+\]|\b(?:TBD|TBR|TBC|TBS)-\d+\b")
DEC_RE = re.compile(r"\bDEC-\d+\b")
QUANTIFIED_TIME_RE = re.compile(
    r"(?:\d[\d.,]*|TBXVALUE)\s*(?:-\s*)?(?:[A-Za-z_]+\s+)?"
    r"(?:cycles?|clocks?|ns|µs|us|ms|s|sec|seconds?|milliseconds?|microseconds?|nanoseconds?)\b")
TERM_RE = re.compile(r"`([^`]+)`|(?<![\w`])([A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]*)(?![\w`])")
SENTENCE_BREAK_RE = re.compile(r"[.!?](?=\s+\S)")
ABBREVIATIONS_RE = re.compile(r"\b(?:e\.g\.|i\.e\.|etc\.|cf\.|vs\.|approx\.|fig\.|no\.|sec\.|rev\.|ver\.)", re.IGNORECASE)


def _clean(text: str) -> str:
    """Remove text that must not trigger word rules: code spans, link targets, TBX values."""
    text = re.sub(r"`[^`]*`", " CODE ", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = TBR_BRACKET_RE.sub(" TBXVALUE ", text)
    text = TBX_RE.sub(" TBXVALUE ", text)
    text = re.sub(r"\b(?:most|least)\s+significant\b", " SIGNIFICANCE ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bat\s+(?:most|least)\b", " BOUND ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbetween\s+(\S+)\s+and\s+(\S+)", r"between \1 RANGE \2", text)
    # "If <condition>, then the <entity> shall ..." is a GtWR R1 pattern, not a combinator.
    text = re.sub(r"^(\s*If\b[^,]*,)\s*then\b", r"\1", text, flags=re.IGNORECASE)
    return text


def _last_word(text: str) -> str:
    words = re.findall(r"[§=]|[A-Za-z][\w-]*", text)
    return words[-1].lower() if words else ""


def _unitless_numbers(clean: str) -> List[str]:
    hits = []
    for m in re.finditer(r"(?<![\w.\-])(\d+(?:\.\d+)?)(?![\w])", clean):
        after = clean[m.end():]
        if after[:1] in ("-", "%", "‰") or after.lstrip()[:1] in ("%",):
            continue
        if _last_word(clean[:m.start()]) in SKIP_BEFORE_NUMBER:
            continue
        nxt = re.findall(r"[A-Za-zµ°%][\w°µ]*", after)[:2]
        if not nxt or nxt[0].lower() in STOP_AFTER_NUMBER:
            hits.append(m.group(1))
    return hits


def _oblique_hits(clean: str) -> List[str]:
    hits = []
    for m in re.finditer(r"(\S*?)([A-Za-z0-9µ°]*)/([A-Za-z0-9µ°]*)(\S*)", clean):
        left, right = m.group(2).lower(), m.group(3).lower()
        token = m.group(0)
        if "+/-" in token or token.startswith(("http", "./", "../")):
            continue
        if left in UNIT_WORDS or right in UNIT_WORDS or right == "s":
            continue
        hits.append(token.strip(".,;:"))
    return hits


def _parentheses_hits(clean: str) -> List[str]:
    hits = []
    for m in re.finditer(r"\([^()]*\)|\[[^\[\]]*\]", clean):
        inner = m.group(0)
        if inner.startswith("[") and re.search(r"\b(?:AND|OR|XOR|NOT)\b", inner):
            continue   # logical-condition convention (GtWR R15)
        hits.append(inner)
    return hits


def _sentence_breaks(clean: str) -> int:
    text = ABBREVIATIONS_RE.sub("ABBR", clean)
    text = re.sub(r"(\d)\.(\d)", r"\1\2", text)
    return len(SENTENCE_BREAK_RE.findall(text.strip()))


# ------------------------------------------------------------------------------ lint

@dataclass
class Finding:
    severity: str
    code: str
    ref: str
    line: int
    message: str

    def as_dict(self) -> Dict[str, object]:
        return {"severity": self.severity, "code": self.code, "ref": self.ref,
                "line": self.line, "message": self.message}


SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


def _as_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def _defined_vocabulary(spec: Spec) -> set:
    words = set()
    for it in spec.items:
        if it.kind in ("info", "heading"):
            words.update(re.findall(r"[A-Za-z0-9_]+", it.text))
    return words


def lint(spec: Spec, notes_text: Optional[str] = None) -> List[Finding]:
    out: List[Finding] = []

    def add(sev: str, code: str, it: Item, msg: str, line: Optional[int] = None) -> None:
        out.append(Finding(sev, code, it.ref, line or it.line, msg))

    ip = str(spec.meta.get("ip", "")).strip()
    methods = {m.lower() for m in _as_list(spec.meta.get("verification_methods"))}
    required = _as_list(spec.meta.get("required_attributes"))
    vocabulary = _defined_vocabulary(spec)
    seen: Dict[str, Item] = {}
    used_tbx: Dict[str, Item] = {}
    decisions: Dict[str, Item] = {}
    prev_level = 0

    for it in spec.items:
        if it.kind == "heading":
            if re.match(r"^\d+(\.\d+)*\.?\s", it.text):
                add("WARN", "STRUCT.heading-number", it,
                    "heading carries a manual number; numbers are computed, remove it.")
            if prev_level and it.level > prev_level + 1:
                add("WARN", "STRUCT.heading-skip", it, "heading level skips from %d to %d." % (prev_level, it.level))
            prev_level = it.level
        elif it.kind == "loose":
            add("WARN", "STRUCT.loose-text", it,
                "text outside an INFO/REQ item; mark it 'INFO:' (context) or 'REQ:' (binding).")
        elif it.kind == "info":
            hits = sorted({m.group(0).lower() for m in INFO_HIDDEN_RE.finditer(_clean(it.text))})
            if hits:
                add("WARN", "INFO.hidden-req", it,
                    "INFO item uses %s; binding content belongs in a REQ item, INFO must not add or relax requirements (ISO 5.2.4, 9.6.20)."
                    % ", ".join('"%s"' % h for h in hits))

        for m in TBX_RE.finditer(it.text + " " + " ".join(it.attrs.values())):
            used_tbx.setdefault(m.group(0), it)
        for value in [it.text] + list(it.attrs.values()):
            for m in BARE_TBX_RE.finditer(value):
                add("WARN", "TBX.untracked", it,
                    '"%s" without a number; use %s-nn and log it in the notes file (NRM 14.2.4).' % (m.group(1), m.group(1)))
        for m in re.finditer(r"\b(?:TBR|TBC)-\d+\b", it.text):
            if not any(m.start() > b.start() and m.end() <= b.end() for b in TBR_BRACKET_RE.finditer(it.text)):
                add("WARN", "TBX.tbr-format", it,
                    '%s should follow a tentative value inside brackets, e.g. "[<value> %s]" (NRM 14.2.4).' % (m.group(0), m.group(0)))

        if it.kind != "req":
            continue

        stmt = it.text
        if not stmt.strip():
            add("ERROR", "STRUCT.empty-req", it, "REQ item has no statement.")
            continue
        clean = _clean(stmt)
        nshall = len(SHALL_RE.findall(clean))
        if nshall == 0:
            add("ERROR", "R18.shall-missing", it, 'no "shall": a REQ states one binding obligation (ISO 5.2.4, GtWR R1).')
        elif nshall > 1:
            add("ERROR", "R18.shall-multiple", it, '%d "shall": split into singular requirements (GtWR R18, ISO 5.2.5).' % nshall)
        if _sentence_breaks(clean):
            add("ERROR", "R18.multi-sentence", it,
                "more than one sentence: move conditions into the sentence and reasons into Rationale (GtWR R18).")
        if ";" in clean:
            add("WARN", "R18.semicolon", it, "semicolon joins clauses; check the requirement is singular (GtWR R18, R14).")
        if ip and not re.search(r"(?<![\w-])" + re.escape(ip) + r"\s+shall\b", stmt.replace("`", "")):
            add("WARN", "R3.subject", it,
                'subject is not the entity "%s"; requirements in this set apply to that entity only (GtWR R2, R3).' % ip)
        if ANDOR_RE.search(clean):
            add("ERROR", "R15.and-or", it, '"and/or" is ambiguous; write [X OR Y] or split the requirement (GtWR R15, R17).')
        clean_words = ANDOR_RE.sub(" ANDOR ", clean)
        for code, sev, regex, msg in COMPILED_RULES:
            for w in sorted({m.group(0) for m in regex.finditer(clean_words)}, key=str.lower):
                add(sev, code, it, msg.format(w=w))
        if not QUANTIFIED_TIME_RE.search(clean):
            for w in sorted({m.group(0) for m in TEMPORAL_UNQ_RE.finditer(clean_words)}, key=str.lower):
                add("WARN", "R35", it, 'timing word "%s" without a quantified limit; state the time with units (GtWR R35).' % w)
        weak = WEAK_VERB_RE.search(clean)
        if weak:
            add("WARN", "R3.weak-verb", it,
                'vague verb "%s"; use an observable action such as encrypt, set, return, assert (GtWR R3, ISO 5.2.7).' % weak.group(1))
        passive = PASSIVE_RE.search(clean)
        if passive:
            add("WARN", "R2.passive", it,
                'passive voice "%s"; make the entity the subject of an active verb (GtWR R2, ISO 5.2.4).' % passive.group(0))
        for tok in _oblique_hits(ANDOR_RE.sub(" ", clean)):
            add("WARN", "R17", it, 'oblique "/" in "%s"; state each alternative explicitly (GtWR R17).' % tok)
        for par in _parentheses_hits(clean):
            add("WARN", "R21", it, 'bracketed text "%s"; move it to Rationale or rewrite (GtWR R21).' % par)
        for num in _unitless_numbers(clean):
            add("INFO", "R6", it, 'number "%s" has no unit or counted noun (GtWR R6).' % num)

        for m in TERM_RE.finditer(stmt):
            term = m.group(1) or m.group(2)
            if TBX_RE.fullmatch(term.strip()):
                continue
            parts = [p for p in re.findall(r"[A-Za-z0-9_]+", term)
                     if not re.fullmatch(r"\d+|0x[0-9A-Fa-f_]+|[01_]+b|[0-9A-Fa-f_]+h", p)]
            missing = [p for p in parts if p not in vocabulary]
            if missing:
                add("WARN", "R4.undefined-term", it,
                    'term "%s" (%s) is not defined in any INFO item, e.g. definitions or register tables (GtWR R4, R36).'
                    % (term, ", ".join(missing)))

        key = re.sub(r"\s+", " ", stmt.strip().rstrip(".").lower())
        if key in seen:
            add("ERROR", "R30.duplicate", it, "duplicates %s; express each requirement once (GtWR R30)." % seen[key].ref)
        else:
            seen[key] = it

        for name in required:
            value = it.attr(name)
            if value is None or not value.strip():
                add("ERROR", "ATTR.missing", it, 'missing attribute "%s".' % name)
        for name, value in it.attrs.items():
            line = it.attr_lines.get(name, it.line)
            if SHALL_RE.search(value):
                add("ERROR", "NRM-15.attr-shall", it,
                    'attribute "%s" contains "shall"; attributes are informative and must not add requirements (NRM 15).' % name, line)
            for dec in DEC_RE.findall(value):
                decisions.setdefault(dec, it)
        verification = it.attr("Verification")
        if verification and methods:
            for method in re.split(r"[,;+]|\band\b", verification):
                if method.strip() and method.strip().lower() not in methods:
                    add("ERROR", "ATTR.method", it,
                        'verification method "%s" is not one of: %s.'
                        % (method.strip(), ", ".join(_as_list(spec.meta.get("verification_methods")))))

    if notes_text is not None:
        registered = {"%s-%s" % pair for pair in TBX_RE.findall(notes_text)}
        for tbx, it in used_tbx.items():
            if tbx not in registered:
                add("ERROR", "TBX.unregistered", it, "%s is not logged in the notes file (NRM 14.2.4)." % tbx)
        for tbx in sorted(registered - set(used_tbx)):
            out.append(Finding("INFO", "TBX.unused", "notes", 0,
                               "%s is logged in the notes file but no longer used in the spec; mark it resolved." % tbx))
        known_dec = set(DEC_RE.findall(notes_text))
        for dec, it in decisions.items():
            if dec not in known_dec:
                add("WARN", "SRC.unknown-decision", it, "%s is cited as a source but not logged in the notes file." % dec)
    elif used_tbx:
        first = next(iter(used_tbx.values()))
        add("WARN", "TBX.no-notes", first, "TBD/TBR items exist but no notes file was found to cross-check them.")
    out.sort(key=lambda f: (f.line, SEVERITY_ORDER[f.severity], f.code))
    return out


def format_findings(spec: Spec, findings: List[Finding], min_severity: str = "INFO") -> str:
    limit = SEVERITY_ORDER[min_severity.upper()]
    shown = [f for f in findings if SEVERITY_ORDER[f.severity] <= limit]
    lines = ["spec: %s" % (spec.path or "<text>")]
    for f in shown:
        lines.append("%-5s %-18s L%-5d %-22s %s" % (f.severity, f.ref, f.line, f.code, f.message))
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITY_ORDER}
    lines.append("summary: %d error(s), %d warning(s), %d info; %d REQ, %d INFO, %d headings"
                 % (counts["ERROR"], counts["WARN"], counts["INFO"],
                    len(spec.of("req")), len(spec.of("info")), len(spec.of("heading"))))
    return "\n".join(lines)


# ------------------------------------------------------------------------- markdown

def _inline(text: str, emphasize_shall: bool = False) -> str:
    """Render the inline Markdown subset used in specs to HTML."""
    out = []
    for part in re.split(r"(`[^`]*`)", text):
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            out.append("<code>%s</code>" % html.escape(part[1:-1]))
            continue
        t = html.escape(part, quote=False)
        t = TBX_HIGHLIGHT_RE.sub(lambda m: '<mark class="tbx">%s</mark>' % m.group(0), t)
        t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img alt="\1" src="\2">', t)
        t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
        if emphasize_shall:
            t = re.sub(r"\bshall\b", '<span class="kw">shall</span>', t)
        out.append(t)
    return "".join(out)


TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+")
NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+")


def _cells(row: str) -> List[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row)]


def markdown_blocks(text: str) -> str:
    """Render the block Markdown subset (paragraphs, lists, tables, code) to HTML."""
    lines = text.split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if FENCE_RE.match(line):
            fence = line.strip()[:3]
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(buf)))
            continue
        if "|" in line and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1]):
            head = _cells(line)
            rows = []
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(_cells(lines[i]))
                i += 1
            parts = ["<table><thead><tr>"]
            parts += ["<th>%s</th>" % _inline(c) for c in head]
            parts.append("</tr></thead><tbody>")
            for r in rows:
                parts.append("<tr>" + "".join("<td>%s</td>" % _inline(c) for c in r) + "</tr>")
            parts.append("</tbody></table>")
            out.append("".join(parts))
            continue
        for regex, tag in ((BULLET_RE, "ul"), (NUMBERED_RE, "ol")):
            if regex.match(line):
                entries: List[str] = []
                while i < len(lines) and (regex.match(lines[i]) or (entries and lines[i][:2] == "  " and lines[i].strip())):
                    if regex.match(lines[i]):
                        entries.append(regex.sub("", lines[i], count=1).strip())
                    else:
                        entries[-1] += " " + lines[i].strip()
                    i += 1
                out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % _inline(e) for e in entries), tag))
                break
        else:
            buf = []
            while i < len(lines) and lines[i].strip() and not FENCE_RE.match(lines[i]) \
                    and not BULLET_RE.match(lines[i]) and not NUMBERED_RE.match(lines[i]) \
                    and not ("|" in lines[i] and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1])):
                buf.append(lines[i].strip())
                i += 1
            if not buf:              # defensive: always consume the current line
                buf.append(lines[i].strip())
                i += 1
            out.append("<p>%s</p>" % _inline(" ".join(buf)))
    return "\n".join(out)


# --------------------------------------------------------------------------- export

def _type_name(spec: Spec, it: Item) -> str:
    names = spec.meta.get("type_names") or {}
    kind = "info" if it.kind == "loose" else it.kind
    return str(names.get(kind, kind)) if isinstance(names, dict) else kind


def cell_value(spec: Spec, it: Item, column: str, cell_format: str = "text") -> str:
    col = column.strip().lower()
    body = it.text if it.kind != "heading" else ""
    if cell_format == "html" and body:
        body = _inline(body) if it.kind == "req" else markdown_blocks(body)
    if col == "type":
        return _type_name(spec, it)
    if col == "level":
        return str(it.level) if it.kind == "heading" else ""
    if col == "section":
        return it.number if it.kind == "heading" else it.section
    if col in ("section title", "section_title"):
        return it.text if it.kind == "heading" else it.section_title
    if col == "ref":
        return it.ref
    if col == "heading":
        return it.text if it.kind == "heading" else ""
    if col == "title":
        return it.text if it.kind == "heading" else (it.attr("Title") or "")
    if col == "description":
        return body
    if col == "text":
        return it.text if it.kind == "heading" else body
    return it.attr(column) or ""


def csv_rows(spec: Spec, columns: Optional[Sequence[str]] = None, cell_format: str = "text") -> List[List[str]]:
    cols = list(columns or _as_list(spec.meta.get("csv_columns")) or DEFAULT_META["csv_columns"])  # type: ignore[arg-type]
    rows = [cols]
    for it in spec.items:
        rows.append([cell_value(spec, it, c, cell_format) for c in cols])
    return rows


def write_csv(spec: Spec, path: str, bom: bool = True, delimiter: Optional[str] = None,
              cell_format: str = "text") -> int:
    delim = delimiter or str(spec.meta.get("csv_delimiter") or ",")
    if delim == "\\t":
        delim = "\t"
    rows = csv_rows(spec, cell_format=cell_format)
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=delim, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)
    return len(rows) - 1


HTML_CSS = """
:root{--fg:#1f2328;--muted:#59636e;--bg:#fff;--line:#d0d7de;--req:#0969da;--req-bg:#f3f8ff;
--info:#6e40c9;--info-bg:#f8f5ff;--warn:#9a6700;--warn-bg:#fff8c5;--tbx:#fff1a8}
@media (prefers-color-scheme:dark){:root{--fg:#e6edf3;--muted:#9198a1;--bg:#0d1117;--line:#30363d;
--req:#4493f8;--req-bg:#0c1d33;--info:#ab7df8;--info-bg:#1b1430;--warn:#d29922;--warn-bg:#2b2111;--tbx:#5c4b00}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
main{max-width:920px;margin:0 auto;padding:28px 16px 64px}
header{border-bottom:2px solid var(--line);padding-bottom:12px;margin-bottom:16px}
header h1{font-size:26px;margin:0 0 6px}
.meta,.summary,.legend{color:var(--muted);font-size:13px;margin:2px 0}
.legend span{display:inline-block;margin-right:14px}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
nav.toc{border:1px solid var(--line);border-radius:6px;padding:10px 16px;margin:16px 0;font-size:14px}
nav.toc ul{list-style:none;padding-left:16px;margin:2px 0}nav.toc>ul{padding-left:0}
nav.toc a{color:inherit;text-decoration:none}nav.toc a:hover{text-decoration:underline}
h2,h3,h4,h5,h6{margin:28px 0 8px;line-height:1.3}h2{font-size:21px;border-bottom:1px solid var(--line);padding-bottom:4px}
h3{font-size:18px}h4{font-size:16px}h5,h6{font-size:15px}
.num{color:var(--muted);margin-right:8px;font-variant-numeric:tabular-nums}
.item{border-left:4px solid var(--line);border-radius:4px;padding:8px 12px;margin:10px 0}
.item.req{border-left-color:var(--req);background:var(--req-bg)}
.item.info{border-left-color:var(--info);background:var(--info-bg)}
.item.loose{border-left-color:var(--warn);background:var(--warn-bg)}
.tag{display:flex;flex-wrap:wrap;gap:10px;font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.item.req .kind{color:var(--req)}.item.info .kind{color:var(--info)}.item.loose .kind{color:var(--warn)}
.pid,.ref{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:none;letter-spacing:0}
.stmt{margin:4px 0 2px;font-weight:500}.kw{font-weight:700}
.item p{margin:4px 0}.item ul,.item ol{margin:4px 0;padding-left:22px}
dl.attrs{display:grid;grid-template-columns:max-content 1fr;gap:1px 12px;margin:6px 0 0;font-size:13px;color:var(--muted)}
dl.attrs dt{font-weight:600}dl.attrs dd{margin:0}
table{border-collapse:collapse;margin:6px 0;font-size:13px;max-width:100%}
th,td{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}
th{background:rgba(127,127,127,.08)}
code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.9em}
pre{overflow-x:auto;padding:8px;border:1px solid var(--line);border-radius:4px}
mark.tbx{background:var(--tbx);color:inherit;padding:0 3px;border-radius:3px}
img{max-width:100%}
footer{margin-top:40px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:8px}
@media (max-width:640px){dl.attrs{grid-template-columns:1fr}table{display:block;overflow-x:auto}}
@media print{body{background:#fff;color:#000}main{max-width:none;padding:0}.item{break-inside:avoid}nav.toc{break-after:page}}
"""


def render_html(spec: Spec, source_name: str = "") -> str:
    meta = spec.meta
    esc = html.escape
    title = str(meta.get("title") or meta.get("ip") or "Specification")
    facts = []
    for key, label in (("ip", "IP"), ("version", "Version"), ("owner", "Owner"), ("date", "Date")):
        if meta.get(key):
            facts.append("%s: %s" % (label, esc(str(meta[key]))))
    reqs, infos = spec.of("req"), spec.of("info") + spec.of("loose")
    tbx = sorted({m.group(0) for it in spec.items
                  for m in TBX_RE.finditer(it.text + " " + " ".join(it.attrs.values()))},
                 key=lambda s: (s[:3], int(s[4:])))
    parts = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             "<title>%s</title><style>%s</style></head><body><main>" % (esc(title), HTML_CSS),
             "<header><h1>%s</h1>" % esc(title)]
    if facts:
        parts.append('<p class="meta">%s</p>' % " · ".join(facts))
    parts.append('<p class="summary">%d requirements · %d information items · open TBD/TBR: %s</p>'
                 % (len(reqs), len(infos), esc(", ".join(tbx)) if tbx else "none"))
    parts.append('<p class="legend"><span><i class="sw" style="background:var(--req)"></i>Requirement (binding)</span>'
                 '<span><i class="sw" style="background:var(--info)"></i>Information (context, non-binding)</span>'
                 '<span><mark class="tbx">TBD/TBR</mark> open value</span></p></header>')

    headings = spec.of("heading")
    if headings:
        parts.append('<nav class="toc"><strong>Contents</strong>')
        stack: List[int] = []            # levels of the open <ul> elements
        for h in headings:
            if stack and h.level > stack[-1]:
                parts.append("<ul>")
                stack.append(h.level)
            else:
                while stack and stack[-1] > h.level:
                    parts.append("</li></ul>")
                    stack.pop()
                if stack and stack[-1] == h.level:
                    parts.append("</li>")
                else:
                    parts.append("<ul>")
                    stack.append(h.level)
            parts.append('<li><a href="#sec-%s"><span class="num">%s</span>%s</a>'
                         % (h.number.replace(".", "-"), h.number, _inline(h.text)))
        parts.append("</li></ul>" * len(stack) + "</nav>")

    for it in spec.items:
        if it.kind == "heading":
            tag = "h%d" % min(it.level + 1, 6)
            parts.append('<%s id="sec-%s"><span class="num">%s</span>%s</%s>'
                         % (tag, it.number.replace(".", "-"), it.number, _inline(it.text), tag))
        elif it.kind == "req":
            pid = it.attr("ID")
            parts.append('<div class="item req"><div class="tag"><span class="kind">%s</span>'
                         '<span class="pid">%s</span><span class="ref">%s</span></div>'
                         % (esc(_type_name(spec, it)), esc(pid) if pid else "‹Polarion ID›", esc(it.ref)))
            if it.attr("Title"):
                parts.append('<p class="stmt"><strong>%s</strong></p>' % _inline(it.attr("Title") or ""))
            parts.append('<p class="stmt">%s</p>' % _inline(it.text, emphasize_shall=True))
            attrs = [(k, v) for k, v in it.attrs.items() if k.lower() not in ("id", "title")]
            if attrs:
                parts.append('<dl class="attrs">%s</dl>'
                             % "".join("<dt>%s</dt><dd>%s</dd>" % (esc(k), _inline(v)) for k, v in attrs))
            parts.append("</div>")
        else:
            kind_label = _type_name(spec, it) + (" · untagged text" if it.kind == "loose" else "")
            parts.append('<div class="item %s"><div class="tag"><span class="kind">%s</span>'
                         '<span class="ref">%s</span></div>%s</div>'
                         % (it.kind, esc(kind_label), esc(it.ref), markdown_blocks(it.text)))
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    parts.append("<footer>Preview generated by spectool from %s on %s. Requirement IDs are assigned by Polarion; "
                 "section references (§) are positional and change when items move.</footer>"
                 % (esc(source_name or spec.path or "spec"), stamp))
    parts.append("</main></body></html>")
    return "\n".join(parts)


# ------------------------------------------------------------------------------ CLI

def _read_notes(spec_path: str, notes_arg: Optional[str]) -> Optional[str]:
    path = notes_arg or default_notes_path(spec_path)
    if os.path.isfile(path):
        with open(path, encoding="utf-8-sig") as fh:
            return fh.read()
    if notes_arg:
        raise SpecError("notes file not found: %s" % notes_arg)
    return None


def cmd_lint(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    findings = lint(spec, _read_notes(args.spec, args.notes))
    if args.format == "json":
        print(json.dumps([f.as_dict() for f in findings], indent=2, ensure_ascii=False))
    else:
        print(format_findings(spec, findings, args.min_severity))
    return 1 if any(f.severity == "ERROR" for f in findings) else 0


def cmd_export(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    stem = os.path.splitext(os.path.basename(args.spec))[0]
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.spec))
    os.makedirs(out_dir, exist_ok=True)
    if args.only != "html":
        path = args.csv or os.path.join(out_dir, stem + ".csv")
        n = write_csv(spec, path, bom=not args.no_bom, delimiter=args.delimiter, cell_format=args.cell_format)
        print("csv:  %s (%d rows)" % (path, n))
    if args.only != "csv":
        path = args.html or os.path.join(out_dir, stem + ".html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render_html(spec, os.path.basename(args.spec)))
        print("html: %s" % path)
    return 0


def cmd_refs(args: argparse.Namespace) -> int:
    for it in load_spec(args.spec).items:
        if args.kind != "all" and it.kind != args.kind:
            continue
        preview = " ".join(it.text.split())
        print("%-18s L%-5d %-7s %s" % (it.ref, it.line, it.kind.upper(), preview[:90]))
    return 0


def cmd_tbx(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    notes = _read_notes(args.spec, args.notes)
    registered = {"%s-%s" % pair for pair in TBX_RE.findall(notes or "")}
    found = False
    for it in spec.items:
        for m in TBX_RE.finditer(it.text + " " + " ".join(it.attrs.values())):
            found = True
            state = "logged" if m.group(0) in registered else ("NOT LOGGED" if notes is not None else "no notes file")
            print("%-8s %-18s L%-5d %s" % (m.group(0), it.ref, it.line, state))
    if not found:
        print("no TBD/TBR in spec")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="spectool", description="Lint and export Markdown requirement specs.")
    sub = parser.add_subparsers(dest="cmd")
    sub.required = True
    p = sub.add_parser("lint", help="check REQ/INFO items against the writing rules")
    p.add_argument("spec")
    p.add_argument("--notes", help="notes file (default: <spec>.notes.md next to the spec)")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--min-severity", choices=["info", "warn", "error"], default="info")
    p.set_defaults(func=cmd_lint)
    p = sub.add_parser("export", help="write the CSV (Polarion import) and HTML preview")
    p.add_argument("spec")
    p.add_argument("--csv", help="CSV output path")
    p.add_argument("--html", help="HTML output path")
    p.add_argument("--out-dir", help="directory for default output names (default: next to the spec)")
    p.add_argument("--only", choices=["csv", "html"])
    p.add_argument("--no-bom", action="store_true", help="write the CSV without a UTF-8 BOM")
    p.add_argument("--delimiter", help="CSV delimiter (default: csv_delimiter from front matter, else ',')")
    p.add_argument("--cell-format", choices=["text", "html"], default="text",
                   help="write Description cells as Markdown text or as HTML fragments")
    p.set_defaults(func=cmd_export)
    p = sub.add_parser("refs", help="list items with their positional references")
    p.add_argument("spec")
    p.add_argument("--kind", choices=["all", "req", "info", "heading", "loose"], default="all")
    p.set_defaults(func=cmd_refs)
    p = sub.add_parser("tbx", help="list TBD/TBR markers and whether they are logged in the notes")
    p.add_argument("spec")
    p.add_argument("--notes")
    p.set_defaults(func=cmd_tbx)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SpecError as exc:
        print("spectool: error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
