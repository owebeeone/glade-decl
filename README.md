# glade-decl — the declaration surface (the CONTRACT)

The shared LEAF module fixing the grip→glial→glade arrows:

```text
grip-core ──▶ glade-decl ◀── glial
                  ▲
                  │ implements
               glade kernel
```

This repo is the **contract only** — a taut schema + its exported IR + a frozen
golden corpus. Zero language code. The three renderings live in sibling repos
(`glade-decl-ts` / `glade-decl-rs` / `glade-decl-py`): committed generated types
+ a thin index, each gated against this repo's corpus. Lockstep comes from the
CORPUS GATE, not co-location.

## Contents (declaration ONLY — no runtime, no wire, no folds, no persistence)

Authored in `ir/glade_decl.taut.py`:

| Kind | Names |
| --- | --- |
| enums | `Shape`, `Authority`, `DomainAnchor`, `ZoneKind`, `RetentionPolicy`, `ChangeKind` |
| the declared unit | `GladeId`, `Retention`, `BindingDecl`, `AdvertisementRecord` |
| event shell + id record | `OriginMeta`, `ChangeEvent`, `GladeIdManifest` |

- **`GladeId`** — stable share-space address; frozen once shared (GQ-6),
  derived from package id + grip key, pinned in a `GladeIdManifest`; renames are
  alias records, never new ids.
- **`BindingDecl`** — the *surface* a tap declares and glial binds:
  `(glade id, shape, authority, source?, domain, zone, retention)`. Inert data
  without a binder.
- **`AdvertisementRecord`** — what grok enumeration emits for a sharable tap
  (GDL-029).
- **`ChangeEvent`** — the generic envelope SHELL (GC-1 split): grip-core types
  events without glial existing; each shape's delta payload rides `payload:
  BYTES` opaquely.
- **`DomainAnchor` / `ZoneKind`** — the GladeZones vocabulary: which replicated
  world (→ wire `share`) and who converges within it (→ wire `key`).

### Interfaces (signatures, documented — not encoded; see `dev-docs/OpenNotes.md`)

taut models data, so these two live as documented signatures, not schema
constructs:

- `canonical_key(param_shape_ir, params) -> BYTES` — deterministic CBOR keys.
- `derive_glade_id(package_id, grip_key) -> GladeId` — the GQ-6 pure function;
  its pinned record format is `GladeIdManifest`. The algorithm + its golden
  derivation vectors are deferred to the implementation step (N4).

## The oracle (mandatory)

`corpus/decl.v0.json` is the FROZEN oracle: `{name -> {message, cbor-hex}}`,
each value encoded by taut's canonical (Python) codec. Every rendering conforms
iff its codec reproduces these bytes (parity == correctness). Values = synth
coverage (one per message) + curated edge cases (optionals set/unset, every
shape / domain / zone / retention policy, both change kinds, unicode).

```sh
python3 corpus/build.py            # rewrite ir/glade_decl.ir.json + corpus/decl.v0.json
python3 corpus/build.py --check    # CI drift gate (fails if committed artifacts are stale)
```

`build.py` also regenerates `../glade-decl-rs/src/vectors.rs` when that crate is
present. That Rust output is passed through **`rustfmt`** — on the write path and
on the `--check` path alike — so the committed file is what `cargo fmt` leaves and
the gate compares like with like. **`rustfmt` is a requirement of the gate**
whenever the sibling crate is present: if it is not on `PATH`, `build.py` fails
loudly rather than compare unformatted output against formatted files
(`rustup component add rustfmt`). The edition comes from the crate's `Cargo.toml`
and a crate `rustfmt.toml` / `.rustfmt.toml` is honoured, so `cargo fmt` in
`glade-decl-rs` and this generator cannot disagree.

The taut builder is bootstrapped from the sibling `../taut/src` (gwz workspace
layout).

## Rendering (how the sibling repos are generated)

```sh
# types (per language) — from the taut member:
PYTHONPATH=../taut/src python3 -m taut.cli gen ir/glade_decl.taut.py \
    -o <out> -l rust --api-only --with-runtime          # api.rs + cbor.rs + ext.rs
PYTHONPATH=../taut/src python3 -m taut.cli gen ir/glade_decl.taut.py \
    -o <out> -l typescript --api-only --with-runtime    # api.ts + codec/cbor/schema runtime
PYTHONPATH=../taut/src python3 -m taut.cli gen ir/glade_decl.taut.py \
    -o <out> -l python --api-only                        # api.py (dataclasses)
```

For Rust, once the generated files are copied into the crate, format them — the
compiler emits unformatted code, and formatted is the convention the corpus gate
compares against:

```sh
cp <out>/rust/*.rs ../glade-decl-rs/src/    # api.rs + cbor.rs + ext.rs
python3 corpus/build.py                     # rewrites ../glade-decl-rs/src/vectors.rs (rustfmt'd)
cd ../glade-decl-rs && cargo fmt            # api.rs: the compiler does not format its own output
```

Generated files are COMMITTED in the rendering repos (consumers install a plain
package, no tautc at build time) and carry a `do not edit` header — regenerate,
never hand-edit.

Design: `dev-docs/DeclSurface.md` (GDL-035/037, RATIFIED 2026-07-07);
decisions the spec left open: `dev-docs/OpenNotes.md`.
