# glade-decl — open notes (schema decisions the spec didn't fully answer)

`DeclSurface.md` (GDL-035/037) is the ratified spec. Where authoring the taut
schema needed a call the spec left open, the smallest reasonable decision is
recorded here so it stays visible for the implementation step. None of these
expand the surface beyond §Contents; each is additive-friendly.

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
languages must compute it identically, so its vectors join `corpus/decl.v0.json`
once the algorithm is chosen. Until then the corpus pins the manifest *format*,
not the derivation *output*.

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
