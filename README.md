# spec-specialist

A Claude Code skill that helps a system engineer write concise **functional requirements
specifications for hardware crypto IPs** (AES, SHA, HMAC, TRNG, PKA, PQC …) on AHB or other
standard buses.

- **The skill asks instead of inventing.** Every value, behavior and reference comes from the
  spec owner or a cited document. Proposals are labeled and need approval, and unknowns stay
  visible as `TBD-nn` / `[value TBR-nn]`.
- **The spec is a Markdown file** with two kinds of items: `REQ:` items (one "shall" each, plus
  attributes) and `INFO:` items (non-binding context). Requirements have no IDs, because Polarion
  assigns them.
- **`spectool.py`** lints the spec against the writing rules. It exports a **CSV for Polarion
  import** and an **HTML preview** of the final layout.

## Install

The skill source lives in this repository. Link it into your personal skills so it is available
in every project:

```bash
ln -s "$(pwd)/skills/spec-specialist" ~/.claude/skills/spec-specialist
```

## Use

```
/spec-specialist new                 # set up a spec, then scope, context, functions
/spec-specialist draft <function>    # elicit and draft the requirements of one function
/spec-specialist review [spec.md]    # lint + judgment review, findings table
/spec-specialist export [spec.md]    # <spec>.csv (Polarion) + <spec>.html (preview)
/spec-specialist status              # open TBD/TBR, open questions, coverage gaps
```

The tool also works on its own:

```bash
python3 skills/spec-specialist/scripts/spectool.py lint   my_ip_spec.md
python3 skills/spec-specialist/scripts/spectool.py export my_ip_spec.md
```

`tests/fixtures/good_spec.md` is a small example of the format. The format itself is described in
`skills/spec-specialist/references/spec-template.md`.

## Layout

```
skills/spec-specialist/
  SKILL.md                  behavior, workflow, rule digest
  references/               writing rules, patterns, question bank, review checklist, template
  scripts/spectool.py       lint / export / refs / tbx (Python 3.8+, standard library only)
tests/                      unit tests and fixtures: python3 -m unittest discover -s tests -v
```

## Sources

The rules paraphrase, with credit, the following documents:
- ISO/IEC/IEEE 29148:2018, *Requirements engineering*;
- the INCOSE *Guide to Writing Requirements* v3.1 (INCOSE-TP-2010-006-04, 2022);
- the INCOSE *Needs and Requirements Manual* (Wiley, 2025).

The documents themselves are copyrighted and are not part of this repository. `docs/` is
git-ignored for that reason.
