# glade-decl — open notes (schema decisions the spec didn't fully answer)

`DeclSurface.md` (GDL-035/037; a mirror of the glade-wz root's
`dev-docs/glade/GladeDeclSurface.md`) is the ratified spec. Where authoring the
taut schema needed a call the spec left open, the smallest reasonable decision
is recorded here so it stays visible for the implementation step. None of N1–N6
expand the surface beyond §Contents; each is additive-friendly. N7–N9 and the
retired-name record at the end come from the v1 amendment's rulings (R1–R11,
ruled 2026-09-23 in the root's `dev-docs/glade/GladeDeclReconciliation.md` §3).

## N1 — Domain modeled as an anchor kind, not a concrete id
`DomainAnchor { account, document, deployment }`. The spec says a surface's
domain is "which replicated world" (→ wire `share`), anchored to an account or a
document/workspace. The *concrete* domain id (how `?doc=N` resolves) is marked
open/runtime in GladeZones §Open, so it is deliberately **absent** from the
declaration — a `BindingDecl` declares the anchor KIND; the binder resolves the
id at bind time. Adding a concrete-id field later is additive.

## N2 — Zone modeled as `ZoneKind { commons, private }` only
v0 carries the zone *kind*. GladeZones lists future partition axes
(device / cohort / tab) but marks the full axis vocabulary **open**. Encoding a
speculative axis enum now would be scope creep and, per the codebase's
"additive-only versioning" rule, belongs in a later ratified revision. `private`
implies the `self` axis by construction (privacy-by-keying). When axes are
ratified, `zone` grows from an enum to a message `{kind, axes: [...]}` — a
breaking change flagged by the taut evolution gate, taken deliberately then.

## N3 — Retention modeled as `{policy, ttl_ms?}`
The seed had `retention: STRING (ttl | latest | from-cursor)`. Modeled as an
enum `RetentionPolicy { latest, from_cursor, ttl }` plus an optional `ttl_ms`
present only when `policy == ttl`. Typed beats a free-form string (the codebase's
declarative-first rule); the coupling of ttl-value-to-ttl-policy is documented,
not enforced (taut has no cross-field constraint primitive).

**v1 (R2(a), with row 18b (ii)).** The vocabulary stays `{latest, from_cursor,
ttl}` + `ttl_ms`. `windowed`, which one app-file surface used, is not a member:
a window is an application projection over a base shape (GDL-041), so that
surface declares `from_cursor` and keeps its window app-side. **Deferred past
v1:** enforcement — the policy is declarative and nothing applies it (GC-4,
open) — and a duration in an app file: `ttl_ms` carries it in the record, but a
binding line cannot state it until the node parses R11(a)'s `ttl=<duration>`
tail key. **Spelling:** an app file writes `from-cursor`, the hyphen only;
`from_cursor` is the contract's spelling, and R9(b2) has the node normalise the
file's hyphen to it on the way into the stored record.

## N4 — `canonical_key` and `derive_glade_id` are signatures, not encoded data
`DeclSurface §Contents` lists the canonical-key **interface** and the
`derive_glade_id(package_id, grip_key)` **function**. taut models data
(enums / messages / services), and this module has no `service` (§Exclusions:
no runtime). So both are documented signatures in `README.md`, not schema
constructs:
- `canonical_key(param_shape_ir, params) -> BYTES` (deterministic CBOR).
- `derive_glade_id(package_id, grip_key) -> GladeId`.

The **data** halves that ARE in scope are encoded: `GladeIdManifest` is the
pinned-derivation record format (the checked-in manifest is a list of these).
The derivation ALGORITHM and its golden derivation vectors are deferred to the
implementation step — the spec does not fix the hash (GQ-6), and all three
languages must compute it identically, so its vectors join the golden corpus
(`corpus/decl.v1.json` in v1) once the algorithm is chosen. Until then the
corpus pins the manifest *format*, not the derivation *output*.

**v1 status (R6(a), ruled 2026-09-23): DEFERRED past v1.** `canonical_key`
and `derive_glade_id` are both **not implemented and not oracled in v1**, in any
language; both are deferred past contract v1, and `GladeIdManifest` ships as the
record of a derivation nothing performs yet. **Owner of `canonical_key`:
Gianni.** Meanwhile four ad-hoc key conventions are live in the consumers (the
reconciliation's row 49), which is why the interface has an owner before it has
an implementation.

## N5 — `ChangeEvent.origin_meta` typed as `OriginMeta { origin, seq }`
`DeclSurface` lists `ChangeEvent = {glade_id, shape, kind, base_seq, origin_meta,
payload: BYTES}` but does not define `origin_meta`'s shape. Modeled as the
smallest typed provenance matching the already-ratified glade `Head` vocabulary
(origin + per-origin seq) so grip-core can attribute an event without importing
glade. Optional (absent on a purely local/synthetic refresh). If provenance
needs more (lamport, hash) it is additive.

## N6 — `GladeId` is a message, not a bare `STR`
Wrapped so the address can grow fields (e.g. an explicit version) without a
breaking change to every field that references it. Wire cost is one extra map
layer; the freeze discipline makes the wrapper worth it.

## N7 — The shape profile is `ShapeProfileDecl`, keyed by glade id (R4(b))
GDL-041 ratifies profiles over engines — `snapshot_delta` (core `swmr`) and
`text_crdt` (core `crdt`); the IR's `shapes` block lists them with `class:
profile`. glial requires the profile to mount a `crdt` surface, so the contract
must be able to state it. It states it as a separate record,
`ShapeProfileDecl {glade_id, profile: STR}`, not as a `profile` field on
`BindingDecl`: taut's optional fields are always emitted, so a new
`BindingDecl` field would rewrite every vector that embeds one, while a new
message adds only its own synth vector. A consumer looks the profile up by glade
id (glial ahead of its `config.crdtProfile`, which stays for back-compat).

An app file writes it as a keyword tail on the binding line,
`shape-profile=<profile>` (R11(a)). The file key is `shape-profile`, not
`profile`, because "profile" already names the node's boot profile and an LLM
compatibility profile in the same product; the contract's field keeps GDL-041's
word. The key's rules, enforced at parse once the node carries the tail: refused
on `value` and `log` (no profile exists); optional on `swmr` (omitted means the
bare engine); required on `crdt` (glial cannot mount one without it).

**The node persists no tail key in this amendment.** `sysdata.BindingDecl`
gains no field: a new field changes the bytes of every stored binding record,
so the first boot would re-append all of them. A tail key that must reach a
consumer takes a record kind of its own, keyed by glade id — this message's
shape — which moves no stored byte and can be added later. None needs to yet:
no app file declares a `crdt` binding, and nothing enforces retention (GC-4).

## N8 — The domain anchor is a declaration-time hint the binder resolves (R1(a))
`BindingDecl.domain` and `DomainAnchor` stay as N1 models them, and the anchor
means exactly this: a hint fixed at declaration time, which the binder resolves
to the concrete world (the wire `share`) at bind time. The grip-share binder
already does — `manifestScope` looks `decl.domain` up in its manifest's
`domains` table (the demo maps `account` to `account:{self}` and `document` to
`doc:{doc}`). glial does not yet: its `Fill.domain` is a concrete string that
enters only a local instance key. Giving glial the mapping is GlialFitAssessment
S6 (R1(b), a separate step), which should lift grip-share's shape rather than
invent another. The node stores no domain and the app-file grammar has no token
for it: the declaration is app-static.

## N9 — `private` is honoured by one binder of two (SAF-P2-4)
`ZoneKind.private` means keyed to the principal. It is honoured by the
grip-share binder (`glade/grip-share/src/manifest.ts:64-67` with the manifest's
`zones` table, where the demo maps `private` to `self:{self}`, filled from the
grant's identity). glial mounts do **not** produce the key today — `Fill.zone`
feeds a local instance key only (`glial/src/instance.ts:36,40-41`) — so a
surface declared `private` and mounted through glial converges in the commons
partition, and gryth-ui mounts through glial. The node mints no `self:` prefix
either: it routes on opaque key bytes. **Do not rely on `private` for
confidentiality until the glial mapping (GlialFitAssessment S6) lands.** The
same caveat stands beside `ZoneKind` in the schema and in `README.md`.

## Retired names
taut reserves a retired field's tag and name only within one message
(`Msg(reserved=...)`); a schema carries no reservation list for a retired
**message** name, and nothing would reject a later schema that re-declared one.
This list, with the schema's module docstring, is that record.

- **`AdvertisementRecord`** — retired in contract **v1** (R7(b)): held out until
  GDL-029 (grok enumeration, open) ratifies. Its v0 shape (glade-decl
  `bbce73d`) was `{binding: 1 Ref(BindingDecl), package: 2 STR, grip_key: 3
  STR}`. **The name must never be reused with a different shape**: if the record
  returns, it returns with exactly that shape, and any other shape takes a new
  name. A fail-open decoder — the node's `--legacy-codec` one is — would
  otherwise read bytes of the old shape into the new one quietly.
