"""glade-decl — the declaration surface, authored as a taut schema.

Design: `dev-docs/DeclSurface.md` (GDL-035/037, RATIFIED 2026-07-07);
zones vocabulary in `glade/dev-docs/GladeZones.md`.

This is the shared LEAF module both grip-core and glial import (the razel
`*-api` crate idiom; seams-at-inception). It is DECLARATION ONLY — enums +
messages describing what a tap declares and what grok enumeration emits. There
is deliberately NO `service`, NO wire ops, NO folds, NO sessions, NO
persistence: if a field needs a network or a store to mean anything, it belongs
in glade (kernel) or glial (client runtime), not here (DeclSurface §Exclusions).

Read whole. Three groups:
  1. vocabulary enums — Shape, Authority, DomainAnchor, ZoneKind,
     RetentionPolicy, ChangeKind
  2. the declared unit — GladeId, Retention, BindingDecl, ShapeProfileDecl
  3. the generic event shell + id derivation record — OriginMeta, ChangeEvent,
     GladeIdManifest

The **canonical-key interface** (`canonical_key(param_shape_ir, params) ->
BYTES`) and the **derive_glade_id** function are SIGNATURES, not data — taut
models data (enums/messages), so they are documented in `README.md`/DeclSurface,
not encoded here. `GladeIdManifest` is the pinned-derivation RECORD format (the
data half of GQ-6).

DEFERRED past contract v1 (R6(a), ruled 2026-09-23): neither signature is
implemented, and neither has golden vectors, in any language in v1 — so
`GladeIdManifest` ships as the record of a derivation nothing performs yet.
`canonical_key`'s owner is Gianni. See `dev-docs/OpenNotes.md` N4.

Retired message names. taut has no schema-level reservation for a message name
(a `Msg(reserved=...)` list retires FIELD tags and names within one message),
so this docstring and `dev-docs/OpenNotes.md` are the record:
  - `AdvertisementRecord` — retired in contract v1 (R7(b)): held out of the
    contract until GDL-029 (grok enumeration, open) ratifies. Its v0 shape was
    {binding: 1 Ref(BindingDecl), package: 2 STR, grip_key: 3 STR} (v0 is at
    glade-decl bbce73d). The name must never be re-declared with a different
    shape: if the record returns it returns with exactly that shape, and any
    other shape takes a new name.

Regenerate the exported IR + golden corpus (from the glade-decl repo root):
  python3 corpus/build.py            # rewrite ir/glade_decl.ir.json + corpus/decl.v1.json
  python3 corpus/build.py --check    # CI drift gate
  python3 corpus/build.py --compat --deleted AdvertisementRecord,edge/advert
                                     # v1 against the v0 oracle (bbce73d)

Render the per-language types with tautc (the taut member is a sibling):
  PYTHONPATH=../taut/src python3 -m taut.cli gen ir/glade_decl.taut.py \
      -o <out> -l rust,typescript,python --api-only [--with-runtime]
"""

import sys
from pathlib import Path

# Make the taut builder importable when this file is loaded by path (taut is a
# sibling member of the gwz workspace), mirroring shape_log.taut.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "taut" / "src"))

from taut.ir.dsl import BYTES, INT, STR, Enum, F, Msg, Ref, schema

SCHEMA = schema(
    # ---- vocabulary enums ---------------------------------------------------
    # The delivery-shape enum. It NAMES shapes and owns none of them: GDL-041
    # owns the catalogue (engines, profiles, interactions — exported verbatim in
    # this IR's `shapes` block), and each engine's payload/delta type lives in
    # its own taut-shape contract. RECOGNITION IS NOT SUPPORT: a member here
    # says the name is recognised, never that a node binds it or a client
    # mounts it. Numbers are wire values and never move.
    #   value, log, swmr, crdt — the members an app file may bind (the node's
    #     BINDING_SHAPES under the v1 amendment).
    #   stream (3) — a GDL-041 engine with a glial delivery adapter; not
    #     bindable as a declared surface.
    #   exchange (4) — a separate correlated service interaction, authored by
    #     an app file's `service` line, not by `binding`.
    #   message (2), window (5) — RESERVED: recognised so diagnostics stay
    #     precise and their numbers stay held. GDL-041 rules `message`
    #     unsupported, and a window an application projection over an explicit
    #     base shape, not an engine.
    #   atom (8) — a GDL-041 engine, RECOGNISED BUT NOT BINDABLE: it enters the
    #     node's KNOWN_SHAPES and not BINDING_SHAPES, and glial's
    #     requireMountShapeAdapter rejects it (requireShapeAdapter accepts it),
    #     so a consumer can legally emit BindingDecl{shape: atom} that no node
    #     accepts and no client mounts.
    # Profiles (snapshot_delta over swmr, text_crdt over crdt) are not shapes;
    # a surface's profile is a ShapeProfileDecl keyed by its glade id.
    Enum("Shape",
         value=0, log=1, message=2, stream=3, exchange=4, window=5, swmr=6,
         crdt=7, atom=8),
    # Who authored the surface: `share` (produced within this share space) vs
    # `external` (bridged from a named outside source; BindingDecl.source names
    # it). `external` and `source` are DECLARED, NOT YET AUTHORABLE (R5(b)):
    # the app-file grammar has no token that names the source.
    Enum("Authority",
         share=0, external=1),
    # Which replicated world a surface anchors to (-> wire `share` at bind
    # time): the account (personal) domain, a document/workspace domain, or the
    # whole deployment. The concrete domain id (e.g. `?doc=N` resolution) is a
    # RUNTIME binding value, not a declaration — it is deliberately absent here
    # (GladeZones §Open). The anchor is a DECLARATION-TIME HINT the binder
    # resolves (R1(a)): the grip-share binder already does (its manifest's
    # `domains` table); glial does not yet (GlialFitAssessment S6). OpenNotes N8.
    Enum("DomainAnchor",
         account=0, document=1, deployment=2),
    # Who converges within a domain (-> wire `key`): `commons` (everyone in the
    # domain; empty key) or `private` (keyed to the principal). SCOPED: `private`
    # is honoured by the grip-share binder (glade/grip-share/src/manifest.ts:64-67
    # with the manifest's `zones` table); glial mounts do NOT produce the key
    # today — `Fill.zone` feeds a local instance key only
    # (glial/src/instance.ts:36,40-41) — so a surface declared `private` and
    # mounted through glial converges in the commons partition. Do not rely on
    # `private` for confidentiality until the glial mapping (GlialFitAssessment
    # S6) lands. OpenNotes N9.
    # v1 carries the kind only; the future axis vocabulary (device/cohort/tab,
    # GladeZones §Open) is deferred — additive when ratified.
    Enum("ZoneKind",
         commons=0, private=1),
    # Declared retention policy for a surface — DECLARATIVE and UNENFORCED:
    # nothing applies it yet (retention enforcement is GC-4, open). `latest`:
    # one value, last write wins. `from_cursor`: the history is kept and a
    # subscriber resumes from a position (the contract's spelling; an app file
    # writes `from-cursor`). `ttl`: records expire after a duration, which the
    # record expresses (Retention.ttl_ms) but an app file cannot, today (R11(a):
    # the binding line has no slot for it until the node parses the line's
    # `ttl=<duration>` tail key). `windowed` is not a member (R2(a)): a window
    # is a projection over a base shape (GDL-041), not a retention policy.
    Enum("RetentionPolicy",
         latest=0, from_cursor=1, ttl=2),
    # ChangeEvent discriminator: a full `refresh` (a new baseline) or a `delta`
    # against `base_seq`.
    Enum("ChangeKind",
         refresh=0, delta=1),

    # ---- the declared unit --------------------------------------------------
    # The stable share-space address. `id` is runtime-neutral and frozen once
    # shared (GQ-6); renames are alias/migration records, never new ids. GQ-6's
    # design derives it from package id + grip key and pins it in a checked-in
    # manifest (GladeIdManifest), but that derivation is deferred past v1
    # (OpenNotes N4): every id in use today is AUTHORED — an app file states it
    # literally (README). A named message (not a bare STR) so the address can
    # grow fields (e.g. an explicit version) without a breaking change.
    Msg("GladeId",
        F("id", 1, STR)),
    # Declared retention. `ttl_ms` is present only when `policy == ttl`.
    Msg("Retention",
        F("policy", 1, Ref("RetentionPolicy")),
        F("ttl_ms", 2, INT, optional=True)),
    # The unit a tap declares and glial binds — a *surface* in zones terms:
    # (glade id, shape, authority, domain, zone, retention). Inert data without
    # a binder; declaring it costs nothing until a glial binder exists in the
    # process (DeclSurface rule 3). `source` is set iff authority == external.
    Msg("BindingDecl",
        F("glade_id", 1, Ref("GladeId")),
        F("shape", 2, Ref("Shape")),
        F("authority", 3, Ref("Authority")),
        F("source", 4, STR, optional=True),
        F("domain", 5, Ref("DomainAnchor")),
        F("zone", 6, Ref("ZoneKind")),
        F("retention", 7, Ref("Retention"))),
    # The shape PROFILE a declared surface needs, keyed by glade id (R4(b)):
    # one of GDL-041's profiles — `snapshot_delta` over swmr, `text_crdt` over
    # crdt (this IR's `shapes` block, `class: profile`, with its `core`). A
    # separate record rather than a BindingDecl field, so BindingDecl and every
    # vector that embeds it keep their bytes. An app file writes it as the
    # binding line's `shape-profile=<profile>` tail key (R11(a)); the node
    # persists no such record in this amendment (OpenNotes N7).
    Msg("ShapeProfileDecl",
        F("glade_id", 1, Ref("GladeId")),
        F("profile", 2, STR)),

    # ---- the generic event shell + id-derivation record ---------------------
    # Provenance carried by the event shell: which origin produced a change and
    # its per-origin sequence. Grip-core can render "from origin X at seq N"
    # without importing glade. (Underspecified in DeclSurface; smallest typed
    # model matching the ratified glade Head vocabulary — see OpenNotes.md.)
    Msg("OriginMeta",
        F("origin", 1, STR),
        F("seq", 2, INT)),
    # The envelope SHELL (GC-1 split): grip-core types events without glial
    # existing; each shape's DELTA payload stays in its own taut-shape contract,
    # carried opaquely in `payload`. `base_seq` is the position this event is
    # anchored at (the baseline a delta applies against; the current position
    # on a refresh); `origin_meta` is optional provenance.
    Msg("ChangeEvent",
        F("glade_id", 1, Ref("GladeId")),
        F("shape", 2, Ref("Shape")),
        F("kind", 3, Ref("ChangeKind")),
        F("base_seq", 4, INT, optional=True),
        F("origin_meta", 5, Ref("OriginMeta"), optional=True),
        F("payload", 6, BYTES)),
    # The pinned GQ-6 derivation record: the (package id, grip key) inputs and
    # the glade id they froze to. The checked-in manifest is a list of these;
    # re-registration diffs against it (renames become alias records, never new
    # ids). The DERIVATION FUNCTION itself is a signature, documented not
    # encoded (OpenNotes.md).
    Msg("GladeIdManifest",
        F("package_id", 1, STR),
        F("grip_key", 2, STR),
        F("glade_id", 3, Ref("GladeId"))),
)
