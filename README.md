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

This is contract **v1**, amended to reconcile the contract with the node under
the rulings R1–R11 recorded on 2026-09-23 in the glade-wz root's
`dev-docs/glade/GladeDeclReconciliation.md` §3. The ruling codes below point
there.

## Contents (declaration ONLY — no runtime, no wire, no folds, no persistence)

Authored in `ir/glade_decl.taut.py`:

| Kind | Names |
| --- | --- |
| enums | `Shape`, `Authority`, `DomainAnchor`, `ZoneKind`, `RetentionPolicy`, `ChangeKind` |
| the declared unit | `GladeId`, `Retention`, `BindingDecl`, `ShapeProfileDecl` |
| event shell + id record | `OriginMeta`, `ChangeEvent`, `GladeIdManifest` |

- **`GladeId`** — stable share-space address; frozen once shared (GQ-6);
  renames are alias records, never new ids. GQ-6's design derives an id from
  package id + grip key and pins it in a `GladeIdManifest`, but that derivation
  (`derive_glade_id`, below) is implemented nowhere, so **today every glade id
  is authored, not derived**: an `<app>.glade` file states each id as a literal
  token (`binding <glade_id> …`, `service <name> <glade_id>`) that the node
  stores verbatim. The node's parser (`glade/node/src/appdecl.rs`) enforces no
  syntax rule on it: an id is any single whitespace-free token without `#`
  (which opens a comment), and it must be unique within its file across
  `binding` and `service` lines. No charset, length or meaning for the dot is
  fixed — the dotted names in the shipped files (`ws.files`, `term.log`) are
  convention — and no rule for authored ids has been decided.
  `derive_glade_id` is for ids derived from a (package id, grip key) pair; no
  app-file id passes through it.
- **`BindingDecl`** — the *surface* a tap declares and glial binds:
  `(glade id, shape, authority, source?, domain, zone, retention)`. Inert data
  without a binder. `source` is set iff `authority == external`, and both are
  **declared, not yet authorable** (R5(b)): the app-file grammar has no token
  that names a source.
- **`ShapeProfileDecl`** — `{glade_id, profile}`: the shape profile a surface
  needs (GDL-041's `snapshot_delta` over `swmr`, `text_crdt` over `crdt`),
  keyed by glade id — a separate record, so `BindingDecl`'s bytes stay
  untouched (R4(b)). An app file's binding line names the profile with the
  `shape-profile=<profile>` tail key (R11(a)), but nothing registers a
  `ShapeProfileDecl` yet: the node validates the tail keys `ttl=<duration>`
  and `shape-profile=<profile>` and records neither. A `crdt` mount gets its
  profile from glial's `MountConfig.crdtProfile` today
  (`glial/src/binder.ts:98-106`). See `dev-docs/OpenNotes.md` N7.
- **`AdvertisementRecord`** — **held out of v1** until GDL-029 (grok
  enumeration, still open) ratifies (R7(b)). Its name is retired, not free: it
  may come back only with its v0 shape (`dev-docs/OpenNotes.md`, "Retired
  names").
- **`ChangeEvent`** — the generic envelope SHELL (GC-1 split): grip-core types
  events without glial existing; each shape's delta payload rides `payload:
  BYTES` opaquely.
- **`DomainAnchor` / `ZoneKind`** — the GladeZones vocabulary: which replicated
  world (→ wire `share`) and who converges within it (→ wire `key`). The domain
  anchor is a declaration-time hint the binder resolves (N8). **`private` is
  scoped**: it is honoured by the grip-share binder
  (`glade/grip-share/src/manifest.ts:64-67` with the manifest's `zones` table);
  glial mounts do **not** produce the key today — `Fill.zone` feeds a local
  instance key only (`glial/src/instance.ts:36,40-41`) — so a surface declared
  `private` and mounted through glial converges in the commons partition. Do
  not rely on `private` for confidentiality until the glial mapping
  (GlialFitAssessment S6) lands (N9).

### Members, and what an app file may write

A member is **recognition, not support**: GDL-041 owns the shape catalogue (the
IR's `shapes` block), and a name here never promises that a node binds it or a
client mounts it. Numbers are wire values and never move. "App file" means the
five-token binding line of an `<app>.glade` file, `binding <glade_id> <shape>
<authority> <zone> <retention>`, after this amendment; none of its tokens has a
default.

**`Shape`** — an app file may bind `value`, `log`, `swmr` and `crdt`, the node's
`BINDING_SHAPES` under this amendment (a node from before it refuses `crdt` as an
unknown shape).

| Member | Gloss | App file |
| --- | --- | --- |
| `value` (0) | one materialised value; concurrent writes resolve last-writer-wins | bindable |
| `log` (1) | an append-only record log, read from a cursor | bindable |
| `message` (2) | reserved: unsupported (GDL-041), its number held | refused |
| `stream` (3) | live pushed events with no history (a GDL-041 engine) | refused as a binding |
| `exchange` (4) | a correlated request/response service interaction, not a surface | refused as a binding: write a `service` line |
| `window` (5) | reserved: a window is a view over an explicit base shape (GDL-041), not an engine | refused |
| `swmr` (6) | one writer, many readers: snapshots plus deltas, read from an epoch cursor | bindable |
| `crdt` (7) | a multi-writer replica that converges by its profile's merge | bindable, with `shape-profile=text_crdt` |
| `atom` (8) | a single-writer latest value, replaced whole (a GDL-041 engine) | recognised, not bindable |

**`Authority`**

| Member | Gloss | App file |
| --- | --- | --- |
| `share` (0) | the share is the source of record | `share` |
| `external` (1) | the share caches truth bridged from a named outside source (`BindingDecl.source`) | parses, but no token names the source: declared, not yet authorable (R5(b)) |

**`DomainAnchor`** — no app-file token: the node's record has no domain, and the
binder resolves the anchor to a concrete share (N1, N8).

| Member | Gloss | App file |
| --- | --- | --- |
| `account` (0) | the principal's own world, the same across documents | — |
| `document` (1) | one document's or workspace's world | — |
| `deployment` (2) | the whole deployment | — |

**`ZoneKind`** — the binding line's zone token.

| Member | Gloss | App file |
| --- | --- | --- |
| `commons` (0) | everyone in the domain converges; the wire `key` is empty | `commons` |
| `private` (1) | keyed to the principal — honoured by grip-share, not by glial mounts (the scope note above) | `private` |

**`RetentionPolicy`** — the binding line's retention token, carried in the
record as `Retention {policy, ttl_ms?}` (`ttl_ms` only when `policy` is `ttl`).
Declarative and unenforced: nothing applies it yet (GC-4). App files spell the
second member `from-cursor`; the contract spells it `from_cursor`.

| Member | Gloss | App file |
| --- | --- | --- |
| `latest` (0) | the surface keeps one value, last write wins — on a `log` it silently turns an append log into a single value, and on a `crdt` it does not mean "the merged value" | `latest` |
| `from_cursor` (1) | the history is kept, and a subscriber resumes from a position rather than from the head | `from-cursor` |
| `ttl` (2) | records expire after a duration (`Retention.ttl_ms`) | `ttl`; the line may state the duration with R11(a)'s `ttl=<duration>` tail key, which the node validates and does not record, so no record carries a duration yet |

Which to write: `value` → `latest`; `log` and `swmr` → `from-cursor`; `crdt` → by
how the surface is read — `from-cursor` if a subscriber resumes a history, `ttl`
if its entries expire. `windowed` is not a member (R2(a)): a window is a
projection over a base shape, so a windowed log declares `from-cursor` and keeps
its window app-side.

**`ChangeKind`** — the client-side event vocabulary; not in app files.

| Member | Gloss | App file |
| --- | --- | --- |
| `refresh` (0) | a full new baseline | — |
| `delta` (1) | a change applied against `base_seq` | — |

### Interfaces (signatures, documented — not encoded; see `dev-docs/OpenNotes.md`)

taut models data, so these two live as documented signatures, not schema
constructs:

- `canonical_key(param_shape_ir, params) -> BYTES` — deterministic CBOR keys.
  **Not implemented and not oracled in v1**: deferred past v1 (N4). Owner:
  Gianni.
- `derive_glade_id(package_id, grip_key) -> GladeId` — the GQ-6 pure function;
  its pinned record format is `GladeIdManifest`. **Not implemented and not
  oracled in v1**: the algorithm + its golden derivation vectors are deferred to
  the implementation step, past v1 (N4).

## The oracle (mandatory)

`corpus/decl.v1.json` is the FROZEN oracle: `{name -> {message, cbor-hex}}`,
each value encoded by taut's canonical (Python) codec. Every rendering conforms
iff its codec reproduces these bytes (parity == correctness). Values = synth
coverage (one per message) + curated edge cases (optionals set/unset, every
shape / domain / zone / retention policy, both change kinds, unicode); the build
fails unless every `Shape` member is the shape of a curated `BindingDecl` vector.

v1 replaced v0, which stays recoverable at `bbce73d`. Every vector the two share
is byte-identical; v1 drops exactly `AdvertisementRecord` and `edge/advert`
(R7(b)) and adds `ShapeProfileDecl` and `edge/binding-account-atom`. So v1 is a
byte superset of v0 minus those two vectors — and that claim's proof is the gate
`python3 corpus/build.py --compat --deleted AdvertisementRecord,edge/advert`,
green with the declaration and red without it.

```sh
python3 corpus/build.py            # rewrite ir/glade_decl.ir.json + corpus/decl.v1.json (+ the rendering artifacts)
python3 corpus/build.py --check    # CI drift gate (fails if anything below is stale)
python3 corpus/build.py --compat --deleted AdvertisementRecord,edge/advert
                                   # v1, as built from the schema, against v0 read from git at bbce73d
python3 -m unittest corpus/test_build.py   # the gates' own tests
```

`build.py` also writes, for each sibling rendering present, what that
rendering's gate reads: `../glade-decl-rs/src/vectors.rs`, and the IR + corpus
copies (`glade_decl.ir.json`, `decl.v1.json`) in `../glade-decl-ts/src/` and
`../glade-decl-py/src/glade_decl/`. `--check` compares every one of them against
the schema, and also checks:

- **the mirror** — `dev-docs/DeclSurface.md` must be its banner line, a blank
  line, then the controlling root page `../dev-docs/glade/GladeDeclSurface.md`
  byte for byte (when the root page is present);
- **`CONTRACT_VERSION`** — each rendering's pin must equal the last glade-decl
  commit that touched the contract (`ir/glade_decl.taut.py`,
  `ir/glade_decl.ir.json`, `corpus/decl.v1.json`), and none of those may carry
  an uncommitted change, so a rendering cannot claim a contract it was not
  generated from (A1).

The Rust output is passed through **`rustfmt`** — on the write path and on the
`--check` path alike — so the committed file is what `cargo fmt` leaves and the
gate compares like with like. **`rustfmt` is a requirement of the gate**
whenever the sibling crate is present: if it is not on `PATH`, `build.py` fails
loudly rather than compare unformatted output against formatted files
(`rustup component add rustfmt`). The edition comes from the crate's `Cargo.toml`
and a crate `rustfmt.toml` / `.rustfmt.toml` is honoured, so `cargo fmt` in
`glade-decl-rs` and this generator cannot disagree. The pin check and `--compat`
read the history, so they need `git`.

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
python3 corpus/build.py                     # rewrites ../glade-decl-rs/src/vectors.rs (rustfmt'd) + the ts/py ir/corpus copies
cd ../glade-decl-rs && cargo fmt            # api.rs: the compiler does not format its own output
```

Generated files are COMMITTED in the rendering repos (consumers install a plain
package, no tautc at build time) and carry a `do not edit` header — regenerate,
never hand-edit.

Design: `dev-docs/DeclSurface.md` — a banner-marked mirror of the controlling
root page `dev-docs/glade/GladeDeclSurface.md` (GDL-035/037, RATIFIED
2026-07-07; amended 2026-09-23); decisions the spec left open:
`dev-docs/OpenNotes.md`.
