"""Regression tests for skills/spec-specialist/scripts/spectool.py.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "spec-specialist", "scripts", "spectool.py")
FIX = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, os.path.dirname(SCRIPT))

import spectool  # noqa: E402


def fixture(name):
    return os.path.join(FIX, name)


def read(name):
    with open(fixture(name), encoding="utf-8") as fh:
        return fh.read()


class GoodSpecLint(unittest.TestCase):
    def test_no_errors_or_warnings(self):
        spec = spectool.load_spec(fixture("good_spec.md"))
        findings = spectool.lint(spec, read("good_spec.notes.md"))
        noisy = [f for f in findings if f.severity in ("ERROR", "WARN")]
        self.assertEqual([], noisy, spectool.format_findings(spec, noisy))

    def test_structure(self):
        spec = spectool.load_spec(fixture("good_spec.md"))
        self.assertEqual("DEMO_AES", spec.meta["ip"])
        self.assertEqual(4, len(spec.of("req")))
        self.assertEqual(5, len(spec.of("info")))
        self.assertEqual(0, len(spec.of("loose")))
        first_req = spec.of("req")[0]
        self.assertEqual("§2.1 REQ 1", first_req.ref)
        self.assertEqual("Test", first_req.attr("verification"))
        self.assertEqual("DEC-01", first_req.attr("Source"))


class BadSpecLint(unittest.TestCase):
    SEEDED = [
        ("encrypts the input block", "R18.shall-missing"),
        ("encrypts the input block", "R3.subject"),
        ("encrypt the first block and shall set", "R18.shall-multiple"),
        ("must clear the output buffer", "ISO-5.2.4.must"),
        ("shall be cleared by the BAD_IP", "R2.passive"),
        ("The software shall wait", "R3.subject"),
        ("adequate throughput", "R7"),
        ("if possible", "R8"),
        ("CTR modes, etc.", "R9"),
        ("be able to decrypt", "R10"),
        ("and/or the error flag", "R15.and-or"),
        ("encrypt/decrypt", "R17"),
        ("shall not output the key", "R16"),
        ("so that software", "R20"),
        ("(after a zeroize command)", "R21"),
        ("when it finishes", "R24"),
        ("always report errors", "R26"),
        ("ignore any write", "R32"),
        ("fast key expansion", "R34"),
        ("interrupt output immediately", "R35"),
        ("wait for the done flag before", "R35"),
        ("AHB interface", "NRM-6.2.3.interface"),
        ("e.g. an unsupported key size", "R21.example"),
        ("`FOO.BAR`", "R4.undefined-term"),
        ("reset the round counter", "ATTR.missing"),
        ("hold the key register value", "ATTR.method"),
        ("hold the status register value", "NRM-15.attr-shall"),
        ("within TBD-99 clock cycles", "TBX.unregistered"),
        ("zeroize TBD key slots", "TBX.untracked"),
        ("The operation ends when", "R18.multi-sentence"),
        ("handle bus errors", "R3.weak-verb"),
        ("within 20 after the start", "R6"),
        ("within TBR-02 clock cycles", "TBX.tbr-format"),
        ("within 4 clock cycles of an abort request", "SRC.unknown-decision"),
    ]

    @classmethod
    def setUpClass(cls):
        cls.spec = spectool.load_spec(fixture("bad_spec.md"))
        cls.findings = spectool.lint(cls.spec, read("bad_spec.notes.md"))

    def codes_for(self, phrase):
        items = [it for it in self.spec.items if it.kind == "req" and phrase in it.text]
        self.assertEqual(1, len(items), "phrase must identify one REQ: %r" % phrase)
        return {f.code for f in self.findings if f.ref == items[0].ref}

    def test_each_seeded_defect_is_reported(self):
        for phrase, code in self.SEEDED:
            with self.subTest(code=code, phrase=phrase):
                self.assertIn(code, self.codes_for(phrase))

    def test_duplicate_reported_on_second_copy(self):
        dups = [f for f in self.findings if f.code == "R30.duplicate"]
        self.assertEqual(1, len(dups))

    def test_structure_findings(self):
        codes = {f.code for f in self.findings}
        for code in ("STRUCT.heading-number", "STRUCT.loose-text", "INFO.hidden-req", "TBX.unused"):
            with self.subTest(code=code):
                self.assertIn(code, codes)

    def test_and_or_not_double_counted_as_combinator(self):
        codes = self.codes_for("and/or the error flag")
        self.assertNotIn("R19", codes)
        self.assertNotIn("R17", codes)


class ParserEdgeCases(unittest.TestCase):
    def test_wrapped_statement_attributes_and_fences(self):
        text = (
            "---\nip: X_IP\ncsv_columns: [Type, Description]\n---\n"
            "# Heading\n"
            "INFO: Context with a list:\n\n- first\n- second\n\n"
            "```\nREQ: inside a code fence is not a requirement\n```\n"
            "REQ: The X_IP shall set the flag\n  within 3 clock cycles.\n"
            "- Rationale: first line\n  continued line\n"
            "- Verification: Test\n"
        )
        spec = spectool.parse_spec(text)
        reqs = spec.of("req")
        self.assertEqual(1, len(reqs))
        self.assertEqual("The X_IP shall set the flag within 3 clock cycles.", reqs[0].text)
        self.assertEqual("first line continued line", reqs[0].attr("Rationale"))
        info = spec.of("info")[0]
        self.assertIn("inside a code fence", info.text)

    def test_logical_brackets_and_if_then_are_allowed(self):
        text = ("---\nip: X_IP\n---\n# H\nINFO: X_IP, FLAG_A and FLAG_B are defined here.\n"
                "REQ: If [FLAG_A is set OR FLAG_B is set], then the X_IP shall assert the IRQ output "
                "within 2 clock cycles.\n- Rationale: r\n- Verification: Test\n")
        spec = spectool.parse_spec(text)
        codes = {f.code for f in spectool.lint(spec, notes_text="")}
        self.assertNotIn("R21", codes)
        self.assertNotIn("R19", codes)

    def test_bad_front_matter_raises(self):
        with self.assertRaises(spectool.SpecError):
            spectool.parse_spec("---\nip: X\nnot yaml at all\n---\n")


class Export(unittest.TestCase):
    def setUp(self):
        self.spec = spectool.load_spec(fixture("good_spec.md"))

    def test_csv_columns_order_and_types(self):
        rows = spectool.csv_rows(self.spec)
        self.assertEqual(["Type", "Level", "Title", "Description", "Rationale", "Verification", "Source"], rows[0])
        self.assertEqual(len(self.spec.items) + 1, len(rows))
        self.assertEqual(["Heading", "1", "Introduction"], rows[1][:3])
        req_rows = [r for r in rows if r[0] == "Requirement"]
        self.assertEqual(4, len(req_rows))
        self.assertTrue(req_rows[0][3].startswith("When `CTRL.START` is written to 1"))
        self.assertEqual(["Test", "DEC-01"], req_rows[0][5:7])

    def test_csv_file_bom_and_delimiter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.csv")
            spectool.write_csv(self.spec, path, bom=True, delimiter=";")
            with open(path, "rb") as fh:
                self.assertEqual(b"\xef\xbb\xbf", fh.read(3))
            with open(path, encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.reader(fh, delimiter=";"))
            self.assertEqual("Type", rows[0][0])
            spectool.write_csv(self.spec, path, bom=False)
            with open(path, "rb") as fh:
                self.assertNotEqual(b"\xef\xbb\xbf", fh.read(3))

    def test_html_preview(self):
        page = spectool.render_html(self.spec, "good_spec.md")
        self.assertEqual(4, page.count('class="item req"'))
        self.assertEqual(5, page.count('class="item info"'))
        self.assertIn('<mark class="tbx">[20 TBR-01]</mark>', page)
        self.assertIn('id="sec-2-1"', page)
        self.assertIn("‹Polarion ID›", page)
        self.assertNotIn("REQ:", page)
        self.assertIn("<table>", page)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)

    def test_lint_exit_codes(self):
        self.assertEqual(0, self.run_cli("lint", fixture("good_spec.md")).returncode)
        bad = self.run_cli("lint", fixture("bad_spec.md"))
        self.assertEqual(1, bad.returncode)
        self.assertIn("R18.shall-missing", bad.stdout)

    def test_export_writes_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("export", fixture("good_spec.md"), "--out-dir", tmp)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "good_spec.csv")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "good_spec.html")))

    def test_missing_file_is_reported(self):
        result = self.run_cli("lint", fixture("does_not_exist.md"))
        self.assertEqual(2, result.returncode)
        self.assertIn("spectool: error", result.stderr)


if __name__ == "__main__":
    unittest.main()
