#!/usr/bin/env python3
"""Build (or --check) the glade-decl exported IR + golden corpus — the oracle.

The golden corpus (`corpus/decl.v0.json`) is the FROZEN oracle: each reference
value encoded by taut's canonical (Python) codec to exact CBOR bytes. Every
`glade-decl-<lang>` rendering conforms iff its codec reproduces these bytes
(parity == correctness). Values = synth coverage (one per message, exercising
every field type) + curated edge cases (optionals set/unset, all shapes/domains/
zones/retention policies, both change kinds, unicode). No hand-written hex.

This mirrors taut's own `glade_build.py`: it also re-exports the language-neutral
IR (`ir/glade_decl.ir.json`) and, when a sibling `glade-decl-rs` crate exists,
regenerates the Rust byte-parity harness (`glade-decl-rs/src/vectors.rs`).

Generated Rust is passed through `rustfmt` before it is written AND before
`--check` compares it, so the committed file is what `cargo fmt` leaves and the
gate compares like with like. `rustfmt` is therefore REQUIRED whenever the
sibling crate is present: a missing one is a hard error, never a silent
comparison of unformatted output against formatted files.

Run from the glade-decl repo root:
  python3 corpus/build.py            # write ir/glade_decl.ir.json + corpus/decl.v0.json (+ rustfmt'd rs vectors)
  python3 corpus/build.py --check    # exit nonzero if any committed artifact is stale (CI gate; needs rustfmt)

The taut builder is bootstrapped from the sibling `../taut/src` (gwz layout).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent
REPO = CORPUS_DIR.parent
WORKSPACE = REPO.parent
SCHEMA_PY = REPO / "ir" / "glade_decl.taut.py"
IR_JSON = REPO / "ir" / "glade_decl.ir.json"
GOLDEN = CORPUS_DIR / "decl.v0.json"
RS_CRATE = WORKSPACE / "glade-decl-rs"
RS_CARGO_TOML = RS_CRATE / "Cargo.toml"
RS_VECTORS = RS_CRATE / "src" / "vectors.rs"
RS_FMT_CONFIGS = ("rustfmt.toml", ".rustfmt.toml")

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
        # --- bindings: the surface, several axis combinations ---
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
        "edge/binding-deployment-window": ("BindingDecl", _binding(
            glade_id="sys.notice", shape="window", authority="share",
            domain="deployment", zone="commons", policy="latest")),
        "edge/binding-exchange": ("BindingDecl", _binding(
            glade_id="grazel.run", shape="exchange", authority="share",
            domain="document", zone="commons", policy="latest")),
        "edge/binding-message-private": ("BindingDecl", _binding(
            glade_id="doc.chat", shape="message", authority="share",
            domain="document", zone="private", policy="from_cursor")),
        # --- advertisement record (grok enumeration output) ---
        "edge/advert": ("AdvertisementRecord", {
            "binding": b_share_commons,
            "package": "grazel-app",
            "grip_key": "doc:42/body"}),
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


def glade_decl_values(schema: Schema) -> dict[str, tuple[str, dict]]:
    """Synth coverage (every message) + curated edge cases."""
    values = dict(synth.synth_values(schema))
    values.update(curated_values())
    return values


def _ir_text(schema: Schema) -> str:
    return json.dumps(schema_json(schema), indent=2) + "\n"


def _golden_text(schema: Schema) -> str:
    corpus = kit.build_corpus(schema, glade_decl_values(schema))
    return kit.golden_json(corpus)


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


def _vectors_text(schema: Schema) -> str:
    corpus = kit.build_corpus(schema, glade_decl_values(schema))
    return _rustfmt(rust_vectors(schema, corpus))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit nonzero if any committed artifact is stale "
                             "(the Rust vectors are rustfmt'd first, as on write)")
    args = parser.parse_args(argv)

    schema = _load_schema()
    validate_or_raise(schema)

    artifacts = [(IR_JSON, _ir_text(schema)), (GOLDEN, _golden_text(schema))]
    if RS_VECTORS.parent.exists():   # glade-decl-rs crate scaffolded
        artifacts.append((RS_VECTORS, _vectors_text(schema)))

    if args.check:
        stale = [p for p, text in artifacts
                 if (p.read_text() if p.exists() else "") != text]
        if stale:
            for p in stale:
                print(f"STALE: {p} — run `python3 corpus/build.py`", file=sys.stderr)
            return 1
        print(f"all {len(artifacts)} glade-decl artifacts in lockstep with the schema.")
        return 0

    for p, text in artifacts:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"wrote {p} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
