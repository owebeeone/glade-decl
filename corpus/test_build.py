"""Tests for `corpus/build.py`'s gates: the `--compat` comparator, the
Shape-coverage assertion (SAF-P3-8), the DeclSurface mirror check and the
CONTRACT_VERSION pin check (A1).

stdlib `unittest` only, on plain dicts and strings — no git, no filesystem, no
rustfmt — except the one test that reads the real schema and curated set, and
the write test, which uses a temporary directory. Run
from the glade-decl repo root:

    python3 -m unittest corpus/test_build.py -v
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_BUILD_PY = Path(__file__).resolve().parent / "build.py"
_SPEC = importlib.util.spec_from_file_location("glade_decl_corpus_build", _BUILD_PY)
build = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build)


def _entry(message: str, cbor: str) -> dict:
    return {"message": message, "cbor": cbor}


# A small v0: two survivors and one vector that v1 is meant to drop.
V0 = {
    "Keep": _entry("GladeId", "a1016173"),
    "edge/keep": _entry("GladeId", "a10162"),
    "Gone": _entry("Old", "a0"),
}


def _v1(**overrides) -> dict:
    """v1 = the two v0 survivors, byte-identical, plus one added vector."""
    v1 = {"Keep": V0["Keep"], "edge/keep": V0["edge/keep"],
          "Added": _entry("New", "a0")}
    v1.update(overrides)
    return v1


class CompatComparatorTest(unittest.TestCase):
    def test_declared_absence_passes(self):
        self.assertEqual(build.compat_failures(V0, _v1(), {"Gone"}), [])

    def test_byte_drift_fails(self):
        failures = build.compat_failures(
            V0, _v1(Keep=_entry("GladeId", "a1016174")), {"Gone"})
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("Keep", failures[0])
        self.assertIn("a1016173", failures[0])
        self.assertIn("a1016174", failures[0])

    def test_changed_message_with_identical_bytes_fails(self):
        failures = build.compat_failures(
            V0, _v1(Keep=_entry("Renamed", "a1016173")), {"Gone"})
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("Keep", failures[0])
        self.assertIn("Renamed", failures[0])

    def test_undeclared_absence_fails(self):
        failures = build.compat_failures(V0, _v1(), set())
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("Gone", failures[0])
        self.assertIn("--deleted", failures[0])

    def test_declared_name_still_present_fails(self):
        failures = build.compat_failures(V0, _v1(), {"Gone", "edge/keep"})
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("edge/keep", failures[0])
        self.assertIn("still present", failures[0])

    def test_declared_added_name_is_still_present_and_fails(self):
        failures = build.compat_failures(V0, _v1(), {"Gone", "Added"})
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("Added", failures[0])

    def test_declared_name_absent_from_v0_fails(self):
        failures = build.compat_failures(V0, _v1(), {"Gone", "Typo"})
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("Typo", failures[0])

    def test_every_failure_is_reported_not_just_the_first(self):
        v1 = _v1(Keep=_entry("GladeId", "ff"))
        del v1["edge/keep"]
        failures = build.compat_failures(V0, v1, {"Gone", "Added"})
        joined = "\n".join(failures)
        self.assertEqual(len(failures), 3, failures)
        for name in ("Keep", "edge/keep", "Added"):
            self.assertIn(name, joined)

    def test_deleted_list_parsing(self):
        self.assertEqual(
            build.parse_deleted(" AdvertisementRecord, edge/advert ,,"),
            {"AdvertisementRecord", "edge/advert"})
        self.assertEqual(build.parse_deleted(""), set())
        self.assertEqual(build.parse_deleted(None), set())


class ShapeCoverageTest(unittest.TestCase):
    CURATED = {
        "edge/binding-a": ("BindingDecl", {"shape": "value"}),
        "edge/binding-b": ("BindingDecl", {"shape": "log"}),
        # Not a BindingDecl: its shape must not count as coverage.
        "edge/change": ("ChangeEvent", {"shape": "atom"}),
    }

    def test_full_coverage_passes(self):
        self.assertEqual(build.uncovered_shapes(["value", "log"], self.CURATED), [])
        build.require_shape_coverage(["value", "log"], self.CURATED)

    def test_uncovered_member_fails_the_build(self):
        self.assertEqual(
            build.uncovered_shapes(["value", "log", "atom"], self.CURATED), ["atom"])
        with self.assertRaises(SystemExit) as raised:
            build.require_shape_coverage(["value", "log", "atom"], self.CURATED)
        message = str(raised.exception.code)
        self.assertIn("atom", message)
        self.assertIn("BindingDecl", message)

    def test_the_real_curated_set_covers_the_schema(self):
        schema = build._load_schema()
        members = list(schema.enums["Shape"].members)
        self.assertIn("atom", members)
        self.assertEqual(build.uncovered_shapes(members, build.curated_values()), [])


ROOT_PAGE = "# Title\n\nBody line.\n"


class MirrorCheckTest(unittest.TestCase):
    def test_banner_plus_root_passes(self):
        mirror = f"{build.MIRROR_BANNER}\n\n{ROOT_PAGE}"
        self.assertEqual(build.mirror_failures(mirror, ROOT_PAGE), [])

    def test_missing_banner_fails(self):
        failures = build.mirror_failures(ROOT_PAGE, ROOT_PAGE)
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("banner", failures[0])

    def test_content_drift_fails(self):
        mirror = f"{build.MIRROR_BANNER}\n\n# Title\n\nEdited here.\n"
        failures = build.mirror_failures(mirror, ROOT_PAGE)
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("drift", failures[0])


SHA_A = "a" * 40
SHA_B = "b" * 40


class ContractPinTest(unittest.TestCase):
    def test_reads_the_pin_in_each_rendering_form(self):
        self.assertEqual(
            build.read_pin(f'pub const CONTRACT_VERSION: &str = "{SHA_A}";\n'), SHA_A)
        self.assertEqual(
            build.read_pin(f'export const CONTRACT_VERSION = "{SHA_A}";\n'), SHA_A)
        self.assertEqual(build.read_pin(f'CONTRACT_VERSION = "{SHA_A}"\n'), SHA_A)
        self.assertIsNone(build.read_pin("// no pin here\n"))

    def test_matching_pins_on_a_clean_contract_pass(self):
        pins = {"rs": SHA_A, "ts": SHA_A, "py": SHA_A}
        self.assertEqual(build.pin_failures(pins, SHA_A, dirty=[]), [])

    def test_each_stale_pin_fails(self):
        pins = {"rs": SHA_A, "ts": SHA_B, "py": SHA_A}
        failures = build.pin_failures(pins, SHA_B, dirty=[])
        self.assertEqual(len(failures), 2, failures)
        self.assertTrue(all(SHA_B in f for f in failures))

    def test_missing_pin_fails(self):
        failures = build.pin_failures({"rs": None}, SHA_A, dirty=[])
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("rs", failures[0])

    def test_uncommitted_contract_fails_even_a_matching_pin(self):
        failures = build.pin_failures({"rs": SHA_A}, SHA_A,
                                      dirty=["ir/glade_decl.taut.py"])
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("uncommitted", failures[0])
        self.assertIn("ir/glade_decl.taut.py", failures[0])


if __name__ == "__main__":
    unittest.main()


class WriteReplacesTest(unittest.TestCase):
    """pnpm injects `glade-decl-ts` into its consumers by HARD LINK, so a write
    into a rendering's file in place also rewrites every consumer's installed
    copy. The build must replace a file, never write through it."""

    def test_a_write_leaves_a_hard_linked_copy_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            ours = Path(d) / "glade_decl.ir.json"
            ours.write_text("v0\n")
            installed = Path(d) / "installed.json"
            os.link(ours, installed)
            build.write_artifact(ours, "v1\n")
            self.assertEqual(ours.read_text(), "v1\n")
            self.assertEqual(installed.read_text(), "v0\n")
            self.assertEqual(os.stat(ours).st_nlink, 1)

    def test_a_write_keeps_the_file_mode(self):
        with tempfile.TemporaryDirectory() as d:
            ours = Path(d) / "vectors.rs"
            ours.write_text("old\n")
            os.chmod(ours, 0o640)
            build.write_artifact(ours, "new\n")
            self.assertEqual(os.stat(ours).st_mode & 0o777, 0o640)

    def test_a_write_creates_a_missing_file_and_its_directory(self):
        with tempfile.TemporaryDirectory() as d:
            ours = Path(d) / "new" / "decl.v1.json"
            build.write_artifact(ours, "{}\n")
            self.assertEqual(ours.read_text(), "{}\n")
            self.assertEqual([p.name for p in ours.parent.iterdir()], ["decl.v1.json"])
