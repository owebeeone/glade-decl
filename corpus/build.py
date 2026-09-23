#!/usr/bin/env python3
"""Build (or --check, or --compat) the glade-decl exported IR + golden corpus — the oracle.

The golden corpus (`corpus/decl.v1.json`) is the FROZEN oracle: each reference
value encoded by taut's canonical (Python) codec to exact CBOR bytes. Every
`glade-decl-<lang>` rendering conforms iff its codec reproduces these bytes
(parity == correctness). Values = synth coverage (one per message, exercising
every field type) + curated edge cases (optionals set/unset, all shapes/domains/
zones/retention policies, both change kinds, unicode). No hand-written hex.
Every `Shape` member must be the shape of at least one curated `BindingDecl`
vector: the build fails otherwise, in every mode (SAF-P3-8).

This mirrors taut's own `glade_build.py`: it also re-exports the language-neutral
IR (`ir/glade_decl.ir.json`) and, for each sibling rendering present, writes what
that rendering's gate reads — the Rust byte-parity harness
(`glade-decl-rs/src/vectors.rs`) and the IR + corpus copies in
`glade-decl-ts/src/` and `glade-decl-py/src/glade_decl/` (SAF-P2-5).

Generated Rust is passed through `rustfmt` before it is written AND before
`--check` compares it, so the committed file is what `cargo fmt` leaves and the
gate compares like with like. `rustfmt` is therefore REQUIRED whenever the
sibling crate is present: a missing one is a hard error, never a silent
comparison of unformatted output against formatted files.

`--check` compares every artifact above against the schema, and also:
  - the DeclSurface mirror: `dev-docs/DeclSurface.md` must be its banner line,
    one blank line, then the controlling root page
    `../dev-docs/glade/GladeDeclSurface.md` byte for byte (checked when that
    page exists, i.e. inside the glade-wz workspace);
  - CONTRACT_VERSION (A1): the pin in each rendering present must equal the
    last glade-decl commit that touched the contract — the schema, the IR or
    the corpus — and the contract must have no uncommitted changes, because a
    pin can only name a commit. Needs `git`.

`--compat` proves v1 against the v0 oracle, read from git at bbce73d: every
vector in both is byte-identical (and names the same message); every v0 vector
missing from v1 is named in `--deleted`; every name in `--deleted` is a v0
vector that v1 no longer has. v1 is the corpus as BUILT from the schema, not
the committed file, so the gate cannot pass on a stale corpus.

`--ts-from <dir>` is the plain run plus the TypeScript rendering's generated
sources: it also copies tautc's output, `<dir>/*.ts`, into
`glade-decl-ts/src/`. Those files are written like every artifact above, by
replacing each file, because pnpm hard-links that package's files into its
consumers and a `cp` onto one would rewrite every consumer's installed copy.

Run from the glade-decl repo root:
  python3 corpus/build.py            # write ir/glade_decl.ir.json + corpus/decl.v1.json (+ rendering artifacts)
  python3 corpus/build.py --check    # exit nonzero if anything is stale (CI gate; needs rustfmt + git)
  python3 corpus/build.py --compat --deleted AdvertisementRecord,edge/advert
                                     # exit nonzero unless v1 keeps v0's bytes, minus exactly the declared names
  python3 corpus/build.py --ts-from /tmp/g/typescript
                                     # the plain run, plus tautc's <dir>/*.ts into ../glade-decl-ts/src/

The taut builder is bootstrapped from the sibling `../taut/src` (gwz layout).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import tempfile
import sys
from collections.abc import Iterable
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent
REPO = CORPUS_DIR.parent
WORKSPACE = REPO.parent
SCHEMA_PY = REPO / "ir" / "glade_decl.taut.py"
IR_JSON = REPO / "ir" / "glade_decl.ir.json"
GOLDEN = CORPUS_DIR / "decl.v1.json"
RS_CRATE = WORKSPACE / "glade-decl-rs"
RS_CARGO_TOML = RS_CRATE / "Cargo.toml"
RS_VECTORS = RS_CRATE / "src" / "vectors.rs"
RS_FMT_CONFIGS = ("rustfmt.toml", ".rustfmt.toml")
TS_SRC = WORKSPACE / "glade-decl-ts" / "src"
PY_PKG = WORKSPACE / "glade-decl-py" / "src" / "glade_decl"

# The contract a rendering pins: a commit that last touched any of these is the
# only legal CONTRACT_VERSION (A1).
CONTRACT_PATHS = (SCHEMA_PY, IR_JSON, GOLDEN)
# (rendering directory, the file that carries its CONTRACT_VERSION pin)
RENDERING_PINS = (
    (RS_CRATE / "src", RS_CRATE / "src" / "lib.rs"),
    (TS_SRC, TS_SRC / "index.ts"),
    (PY_PKG, PY_PKG / "__init__.py"),
)

# The repository copy of the declaration-surface page is a mirror of the
# controlling root page (CON-P2-5): this banner line, one blank line, then the
# root page byte for byte.
MIRROR = REPO / "dev-docs" / "DeclSurface.md"
ROOT_PAGE = WORKSPACE / "dev-docs" / "glade" / "GladeDeclSurface.md"
MIRROR_BANNER = ("Mirror of `dev-docs/glade/GladeDeclSurface.md` in the glade-wz "
                 "root — do not edit here")

# The v0 oracle, for --compat: v1 replaced it, and it stays recoverable here.
V0_REV = "bbce73d67146124780c3f5fc226d032618aa446c"
V0_PATH = "corpus/decl.v0.json"

# Bootstrap the taut builder (sibling gwz member), mirroring the schema module.
sys.path.insert(0, str(WORKSPACE / "taut" / "src"))

from taut.corpus import kit, synth              # noqa: E402
from taut.corpus.kit import rust_vectors        # noqa: E402
from taut.ir.export import schema_json          # noqa: E402
from taut.ir.model import Schema                # noqa: E402
from taut.ir.validate import validate_or_raise  # noqa: E402


def _load_schema() -> Schema:
    spec = importlib.util.spec_from_file_location("glade_decl_taut", SCHEMA_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SCHEMA


def _gid(id: str) -> dict:
    return {"id": id}


def _binding(*, glade_id="acct.settings", shape="value", authority="share",
             source=None, domain="account", zone="commons",
             policy="latest", ttl_ms=None) -> dict:
    return {
        "glade_id": _gid(glade_id),
        "shape": shape,
        "authority": authority,
        "source": source,
        "domain": domain,
        "zone": zone,
        "retention": {"policy": policy, "ttl_ms": ttl_ms},
    }


def curated_values() -> dict[str, tuple[str, dict]]:
    """name -> (message, native dict). Hand-authored edge cases; None for absent
    optionals (the taut convention). Keys are `edge/*` — no collision with the
    synth coverage values (keyed by message name)."""
    # Every retention policy, one each.
    ret_latest = {"policy": "latest", "ttl_ms": None}
    ret_ttl = {"policy": "ttl", "ttl_ms": 30000}
    ret_cursor = {"policy": "from_cursor", "ttl_ms": None}
    # A representative binding per (shape, authority, domain, zone) spread.
    b_share_commons = _binding(glade_id="doc.body", shape="log", authority="share",
                               domain="document", zone="commons", policy="from_cursor")
    b_external_private = _binding(glade_id="doc.cursor", shape="stream",
                                  authority="external", source="meteo",
                                  domain="document", zone="private",
                                  policy="ttl", ttl_ms=5000)
    om = {"origin": "node-a", "seq": 12}
    return {
        # --- glade id: ascii + unicode ---
        "edge/gladeid": ("GladeId", _gid("grazel.workspaces")),
        "edge/gladeid-unicode": ("GladeId", _gid("café.notĕs.\U0001f600")),
        # --- retention: each policy (ttl set / unset) ---
        "edge/retention-latest": ("Retention", ret_latest),
        "edge/retention-ttl": ("Retention", ret_ttl),
        "edge/retention-cursor": ("Retention", ret_cursor),
        # --- bindings: the surface, several axis combinations. Every Shape
        #     member is the shape of at least one of these (SAF-P3-8, asserted
        #     by require_shape_coverage at build). ---
        "edge/binding-account-commons": ("BindingDecl", _binding(
            glade_id="acct.settings", shape="value", authority="share",
            domain="account", zone="commons", policy="latest")),
        "edge/binding-doc-commons-log": ("BindingDecl", b_share_commons),
        "edge/binding-doc-swmr": ("BindingDecl", _binding(
            glade_id="ws.files", shape="swmr", authority="share",
            domain="document", zone="commons", policy="from_cursor")),
        "edge/binding-doc-crdt": ("BindingDecl", _binding(
            glade_id="doc.collaborative-notes", shape="crdt", authority="share",
            domain="document", zone="commons", policy="from_cursor")),
        "edge/binding-external-private-ttl": ("BindingDecl", b_external_private),
        # A recognition case (R3(a)): `window` is reserved — recognised, not
        # bindable. The key is kept from v0, so the relabelling is no rename.
        "edge/binding-deployment-window": ("BindingDecl", _binding(
            glade_id="sys.notice", shape="window", authority="share",
            domain="deployment", zone="commons", policy="latest")),
        "edge/binding-exchange": ("BindingDecl", _binding(
            glade_id="grazel.run", shape="exchange", authority="share",
            domain="document", zone="commons", policy="latest")),
        # A recognition case (R3(a)): `message` is reserved — recognised, not
        # bindable. The key is kept from v0, so the relabelling is no rename.
        "edge/binding-message-private": ("BindingDecl", _binding(
            glade_id="doc.chat", shape="message", authority="share",
            domain="document", zone="private", policy="from_cursor")),
        # A recognition case: `atom` (8) is a GDL-041 engine that a node
        # recognises and does not bind (§4.1 item 1, SAF-P3-8).
        "edge/binding-account-atom": ("BindingDecl", _binding(
            glade_id="acct.presence", shape="atom", authority="share",
            domain="account", zone="commons", policy="latest")),
        # --- origin meta ---
        "edge/origin-meta": ("OriginMeta", om),
        # --- change event shell: refresh, delta, and minimal (optionals unset) ---
        "edge/change-refresh": ("ChangeEvent", {
            "glade_id": _gid("doc.body"), "shape": "log", "kind": "refresh",
            "base_seq": None, "origin_meta": om, "payload": b"\x01\x02\x03"}),
        "edge/change-delta": ("ChangeEvent", {
            "glade_id": _gid("doc.body"), "shape": "log", "kind": "delta",
            "base_seq": 41, "origin_meta": om, "payload": b"appended"}),
        "edge/change-min": ("ChangeEvent", {
            "glade_id": _gid("acct.settings"), "shape": "value", "kind": "refresh",
            "base_seq": None, "origin_meta": None, "payload": b""}),
        # --- pinned id-derivation record (GQ-6 manifest format) ---
        "edge/manifest": ("GladeIdManifest", {
            "package_id": "grazel-app", "grip_key": "doc:42/body",
            "glade_id": _gid("doc.body")}),
    }


def uncovered_shapes(shape_members: Iterable[str],
                     curated: dict[str, tuple[str, dict]]) -> list[str]:
    """The `Shape` members that no curated `BindingDecl` vector uses as its
    `shape`, in member order. Synth vectors do not count: synth picks one
    member per message, never one per member."""
    covered = {value.get("shape") for message, value in curated.values()
               if message == "BindingDecl"}
    return [member for member in shape_members if member not in covered]


def require_shape_coverage(shape_members: Iterable[str],
                           curated: dict[str, tuple[str, dict]]) -> None:
    """Fail the build unless every `Shape` member has a curated `BindingDecl`
    vector (SAF-P3-8) — otherwise the corpus's "every shape" claim is false."""
    missing = uncovered_shapes(shape_members, curated)
    if missing:
        names = ", ".join(f"`{member}`" for member in missing)
        raise SystemExit(
            f"Shape coverage (SAF-P3-8): no curated BindingDecl vector has shape "
            f"{names}. Every Shape member must be the shape of at least one "
            f"curated BindingDecl vector — add an `edge/binding-*` vector for "
            f"each to curated_values() in corpus/build.py.")


def glade_decl_values(schema: Schema) -> dict[str, tuple[str, dict]]:
    """Synth coverage (every message) + curated edge cases, after asserting
    that the curated set covers every `Shape` member."""
    curated = curated_values()
    require_shape_coverage(schema.enums["Shape"].members, curated)
    values = dict(synth.synth_values(schema))
    values.update(curated)
    return values


# --- --compat: v1 against the v0 oracle (§4.2) ------------------------------


def parse_deleted(text: str | None) -> set[str]:
    """`--deleted A,B` -> {"A", "B"}; blanks and surrounding spaces ignored."""
    return {name.strip() for name in (text or "").split(",") if name.strip()}


def compat_failures(v0: dict[str, dict], v1: dict[str, dict],
                    deleted: Iterable[str]) -> list[str]:
    """Every way v1 fails to keep v0, over `{name: {message, cbor}}` corpora.

    1. a vector in both must have the same bytes (and the same message);
    2. a v0 vector absent from v1 must be named in `deleted`;
    3. a name in `deleted` must not still be present in v1;
    4. a name in `deleted` must be a v0 vector, so the list declares exactly
       the departing vectors and cannot rot into a blanket waiver.
    Returns one message per failure, all of them; empty means green.
    """
    deleted = set(deleted)
    failures: list[str] = []
    for name in sorted(v0.keys() & v1.keys()):
        old, new = v0[name], v1[name]
        drift = []
        if new["cbor"] != old["cbor"]:
            drift.append(f"bytes {old['cbor']} -> {new['cbor']}")
        if new["message"] != old["message"]:
            drift.append(f"message {old['message']} -> {new['message']}")
        if drift:
            failures.append(f"drift: `{name}` changed between v0 and v1: "
                            + "; ".join(drift))
    for name in sorted(v0.keys() - v1.keys() - deleted):
        failures.append(f"undeclared absence: v0 vector `{name}` "
                        f"({v0[name]['message']}) is missing from v1 and is not "
                        f"named in --deleted")
    for name in sorted(deleted & v1.keys()):
        failures.append(f"declared but present: `{name}` is named in --deleted "
                        f"but is still present in v1")
    for name in sorted(deleted - v0.keys() - v1.keys()):
        failures.append(f"declared but never in v0: `{name}` is named in "
                        f"--deleted but v0 has no such vector")
    return failures


# --- the DeclSurface mirror -------------------------------------------------


def _first_differing_line(a: str, b: str) -> int:
    a_lines, b_lines = a.splitlines(), b.splitlines()
    for number, (x, y) in enumerate(zip(a_lines, b_lines), start=1):
        if x != y:
            return number
    return min(len(a_lines), len(b_lines)) + 1


def mirror_failures(mirror_text: str, root_text: str) -> list[str]:
    """The mirror must be the banner line, one blank line, then the root page
    byte for byte. Empty means in lockstep."""
    prefix = f"{MIRROR_BANNER}\n\n"
    if not mirror_text.startswith(prefix):
        return [f"banner missing or altered: the mirror must open with the line "
                f"`{MIRROR_BANNER}` followed by one blank line"]
    body = mirror_text[len(prefix):]
    if body != root_text:
        line = _first_differing_line(body, root_text)
        return [f"drift: the mirror's text below its banner differs from the root "
                f"page (first at root line {line}) — edit the root page, then copy "
                f"it under the banner"]
    return []


# --- CONTRACT_VERSION (A1) --------------------------------------------------

_PIN_RE = re.compile(
    r'(?m)^[ \t]*(?:pub[ \t]+const[ \t]+|export[ \t]+const[ \t]+)?'
    r'CONTRACT_VERSION\b[^=\n]*=[ \t]*"([^"\n]*)"')


def read_pin(text: str) -> str | None:
    """The one `CONTRACT_VERSION = "<commit>"` in a rendering's Rust, TypeScript
    or Python source; None when there is none, or more than one."""
    found = _PIN_RE.findall(text)
    return found[0] if len(found) == 1 else None


def pin_failures(pins: dict[str, str | None], expected: str | None,
                 dirty: list[str]) -> list[str]:
    """Each rendering's pin against the last commit that touched the contract.

    `pins` maps where -> the pin read there (None: no single pin found);
    `expected` is that commit (None: no commit has touched the contract);
    `dirty` lists contract paths with uncommitted changes — while any exist no
    commit describes the contract, so no pin can be right.
    """
    failures: list[str] = []
    for where, pin in pins.items():
        if pin is None:
            failures.append(f"MISSING PIN: {where}: expected exactly one "
                            f"`CONTRACT_VERSION = \"<commit>\"` line")
        elif dirty:
            failures.append(f"STALE PIN: {where}: CONTRACT_VERSION = {pin}, but no "
                            f"commit can match — the contract has uncommitted "
                            f"changes ({', '.join(dirty)}; its last commit is "
                            f"{expected}); commit them, then pin that commit in "
                            f"every rendering")
        elif expected is None:
            failures.append(f"STALE PIN: {where}: CONTRACT_VERSION = {pin}, but no "
                            f"glade-decl commit has touched the contract yet")
        elif pin != expected:
            failures.append(f"STALE PIN: {where}: CONTRACT_VERSION = {pin}, expected "
                            f"{expected} — the last glade-decl commit that touched "
                            f"the contract")
    return failures


def _git(*args: str) -> str:
    cmd = ["git", "-C", str(REPO), *args]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("git not found on PATH — the CONTRACT_VERSION check and "
                         "--compat both read the glade-decl history.")
    if done.returncode != 0:
        raise SystemExit(f"`{' '.join(cmd)}` failed ({done.returncode}):\n"
                         f"{done.stderr}")
    return done.stdout


def _contract_state() -> tuple[str | None, list[str]]:
    """(the last commit that touched the contract, its uncommitted paths)."""
    paths = [p.relative_to(REPO).as_posix() for p in CONTRACT_PATHS]
    last = _git("log", "-1", "--format=%H", "--", *paths).strip() or None
    status = _git("status", "--porcelain", "--", *paths)
    dirty = sorted(line[3:] for line in status.splitlines() if line.strip())
    return last, dirty


# --- the artifacts ----------------------------------------------------------


def _ir_text(schema: Schema) -> str:
    return json.dumps(schema_json(schema), indent=2) + "\n"


def _rust_edition() -> str:
    """The crate's own edition — rustfmt must parse what `cargo fmt` parses."""
    match = re.search(r'(?m)^\s*edition\s*=\s*"([^"]+)"',
                      RS_CARGO_TOML.read_text())
    if match is None:
        raise SystemExit(f"no `edition` in {RS_CARGO_TOML} — cannot format the "
                         "generated Rust the way `cargo fmt` would.")
    return match.group(1)


def _rustfmt(text: str) -> str:
    """Format generated Rust via rustfmt's stdin/stdout (no temp file in tree).

    Both the write path and `--check` go through here, so the gate never
    compares unformatted output against formatted, committed files.
    """
    cmd = ["rustfmt", "--edition", _rust_edition(), "--emit", "stdout"]
    for name in RS_FMT_CONFIGS:
        config = RS_CRATE / name
        if config.exists():
            cmd += ["--config-path", str(config)]
            break
    try:
        done = subprocess.run(cmd, input=text, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("rustfmt not found on PATH — it is REQUIRED by the "
                         "glade-decl drift gate: the generated Rust is "
                         "formatted before it is written and before --check "
                         "compares it. Install: `rustup component add rustfmt`.")
    if done.returncode != 0:
        raise SystemExit(f"rustfmt failed ({done.returncode}) on the generated "
                         f"Rust:\n{done.stderr}")
    return done.stdout


def _artifacts(schema: Schema, corpus: dict[str, dict]) -> list[tuple[Path, str]]:
    """Every file the schema determines: the IR and the corpus, plus what each
    sibling rendering's gate reads, for each rendering present."""
    ir_text = _ir_text(schema)
    golden_text = kit.golden_json(corpus)
    artifacts = [(IR_JSON, ir_text), (GOLDEN, golden_text)]
    if RS_VECTORS.parent.exists():   # glade-decl-rs crate scaffolded
        artifacts.append((RS_VECTORS, _rustfmt(rust_vectors(schema, corpus))))
    for rendering in (TS_SRC, PY_PKG):   # their gates read local copies (SAF-P2-5)
        if rendering.exists():
            artifacts.append((rendering / IR_JSON.name, ir_text))
            artifacts.append((rendering / GOLDEN.name, golden_text))
    return artifacts


def ts_copies(source: Path, dest: Path) -> list[tuple[Path, str]]:
    """`--ts-from`: tautc's TypeScript output, `source/*.ts`, as artifacts bound
    for the rendering's `dest` directory, so `write_artifact` writes them the
    way it writes every artifact. Each file's text is kept exactly as tautc
    wrote it. A missing rendering, or a `source` with no `.ts` file, is an
    error before anything is written."""
    if not dest.is_dir():
        raise SystemExit(f"--ts-from: no TypeScript rendering at {dest} — the "
                         f"glade-decl-ts sibling is not checked out.")
    files = sorted(source.glob("*.ts"))
    if not files:
        raise SystemExit(f"--ts-from: no .ts files in {source} — generate them "
                         f"first (`taut.cli gen … -l typescript --api-only "
                         f"--with-runtime`).")
    copies = []
    for file in files:
        with file.open(encoding="utf-8", newline="") as fh:
            copies.append((dest / file.name, fh.read()))
    return copies


def write_artifact(path: Path, text: str) -> None:
    """Write `text` to `path` by REPLACING the file, never by writing through it.

    pnpm injects `glade-decl-ts` into its consumers by HARD LINK, so a write
    into one of its files in place would also rewrite every consumer's
    installed copy (it did, once, for `glade_decl.ir.json`). A temporary file
    beside the target, renamed over it, leaves those copies as installed; the
    target keeps its file mode, and a new file gets the umask's default.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        mode = path.stat().st_mode & 0o777
    else:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# --- the modes --------------------------------------------------------------


def _check(artifacts: list[tuple[Path, str]]) -> int:
    ok = True

    stale = [p for p, text in artifacts
             if (p.read_text() if p.exists() else "") != text]
    for p in stale:
        print(f"STALE: {p} — run `python3 corpus/build.py`", file=sys.stderr)
    if stale:
        ok = False
    else:
        print(f"all {len(artifacts)} glade-decl artifacts in lockstep with the schema.",
              flush=True)

    if ROOT_PAGE.exists():
        mirror = MIRROR.read_text(encoding="utf-8") if MIRROR.exists() else ""
        failures = mirror_failures(mirror, ROOT_PAGE.read_text(encoding="utf-8"))
        for failure in failures:
            print(f"MIRROR: {MIRROR}: {failure}", file=sys.stderr)
        if failures:
            ok = False
        else:
            print(f"{MIRROR.relative_to(REPO)} mirrors {ROOT_PAGE} "
                  f"(banner + byte-identical).", flush=True)
    else:
        print(f"mirror check skipped: no root page at {ROOT_PAGE}.", flush=True)

    pin_files = [pin_file for rendering, pin_file in RENDERING_PINS
                 if rendering.exists()]
    if pin_files:
        expected, dirty = _contract_state()
        pins = {str(f): read_pin(f.read_text()) if f.exists() else None
                for f in pin_files}
        failures = pin_failures(pins, expected, dirty)
        for failure in failures:
            print(failure, file=sys.stderr)
        if failures:
            ok = False
        else:
            print(f"CONTRACT_VERSION = {expected} in all {len(pins)} renderings "
                  f"(the last glade-decl commit that touched the contract).",
                  flush=True)
    return 0 if ok else 1


def _compat(v1: dict[str, dict], deleted: set[str]) -> int:
    source = f"{V0_REV[:7]}:{V0_PATH}"
    try:
        v0 = json.loads(_git("show", f"{V0_REV}:{V0_PATH}"))
    except json.JSONDecodeError as err:
        raise SystemExit(f"v0 oracle at {source} is not JSON: {err}")
    failures = compat_failures(v0, v1, deleted)
    if failures:
        for failure in failures:
            print(f"COMPAT: {failure}", file=sys.stderr)
        print(f"compat: RED — {len(failures)} failure(s), v1 as built from the "
              f"schema against v0 at {source}.", file=sys.stderr)
        return 1
    shared = v0.keys() & v1.keys()
    departed = sorted(v0.keys() - v1.keys())
    added = sorted(v1.keys() - v0.keys())
    print(f"compat: v1 as built from the schema ({len(v1)} vectors) against v0 at "
          f"{source} ({len(v0)} vectors)")
    print(f"  shared:   {len(shared)}, every one byte-identical")
    print(f"  departed: {', '.join(departed) or 'none'} — exactly the --deleted list")
    print(f"  added:    {', '.join(added) or 'none'}")
    print("compat: green.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="exit nonzero if any committed artifact is stale "
                           "(the Rust vectors are rustfmt'd first, as on write), "
                           "the DeclSurface mirror has drifted, or a rendering's "
                           "CONTRACT_VERSION is not the contract's last commit")
    mode.add_argument("--compat", action="store_true",
                      help="exit nonzero unless the corpus built from the schema "
                           "keeps every v0 vector's bytes (v0 read from git at "
                           f"{V0_REV[:7]}), minus exactly the --deleted names")
    mode.add_argument("--ts-from", metavar="DIR",
                      help="the plain run, plus tautc's TypeScript output "
                           "(DIR/*.ts) copied into ../glade-decl-ts/src/ by "
                           "replacing each file, never writing through it: "
                           "pnpm hard-links that package into its consumers")
    parser.add_argument("--deleted", metavar="NAME[,NAME...]",
                        help="with --compat: the v0 vectors v1 deletes on purpose")
    args = parser.parse_args(argv)
    if args.deleted is not None and not args.compat:
        parser.error("--deleted applies only to --compat")

    schema = _load_schema()
    validate_or_raise(schema)
    corpus = kit.build_corpus(schema, glade_decl_values(schema))

    if args.compat:
        return _compat(corpus, parse_deleted(args.deleted))

    artifacts = _artifacts(schema, corpus)
    if args.check:
        return _check(artifacts)
    if args.ts_from is not None:
        artifacts += ts_copies(Path(args.ts_from), TS_SRC)

    for p, text in artifacts:
        write_artifact(p, text)
        print(f"wrote {p} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
