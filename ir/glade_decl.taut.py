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
  2. the declared unit — GladeId, Retention, BindingDecl, AdvertisementRecord
  3. the generic event shell + id derivation record — OriginMeta, ChangeEvent,
     GladeIdManifest

The **canonical-key interface** (`canonical_key(param_shape_ir, params) ->
BYTES`) and the **derive_glade_id** function are SIGNATURES, not data — taut
models data (enums/messages), so they are documented in `README.md`/DeclSurface,
not encoded here. `GladeIdManifest` is the pinned-derivation RECORD format (the
data half of GQ-6); the derivation algorithm and its golden vectors are deferred
to the implementation step (see `dev-docs/OpenNotes.md`).

Regenerate the exported IR + golden corpus (from the glade-decl repo root):
  python3 corpus/build.py            # rewrite ir/glade_decl.ir.json + corpus/decl.v0.json
  python3 corpus/build.py --check    # CI drift gate

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
    # The delivery-shape enum: NAMES the taut-shape contracts, owns none of them
    # (each shape's payload/delta type lives in its own taut-shape schema). Open
    # registry — CRDT names the canonical engine; text_crdt is its payload
    # profile and therefore is not a second delivery shape.
    Enum("Shape",
         value=0, log=1, message=2, stream=3, exchange=4, window=5, swmr=6,
         crdt=7),
    # Who authored the surface: `share` (produced within this share space) vs
    # `external` (bridged from a named outside source; BindingDecl.source names
    # it).
    Enum("Authority",
         share=0, external=1),
    # Which replicated world a surface anchors to (-> wire `share` at bind
    # time): the account (personal) domain, a document/workspace domain, or the
    # whole deployment. The concrete domain id (e.g. `?doc=N` resolution) is a
    # RUNTIME binding value, not a declaration — it is deliberately absent here
    # (GladeZones §Open).
    Enum("DomainAnchor",
         account=0, document=1, deployment=2),
    # Who converges within a domain (-> wire `key`): `commons` (everyone in the
    # domain, empty key) or `private` (keyed to a self, `self:<id>` at runtime).
    # v0 carries the kind only; the future axis vocabulary (device/cohort/tab,
    # GladeZones §Open) is deferred — additive when ratified.
    Enum("ZoneKind",
         commons=0, private=1),
    # Declared retention policy for a surface: keep only the latest value,
    # replay from a cursor (log-like), or expire after a TTL (Retention.ttl_ms).
    Enum("RetentionPolicy",
         latest=0, from_cursor=1, ttl=2),
    # ChangeEvent discriminator: a full `refresh` (a new baseline) or a `delta`
    # against `base_seq`.
    Enum("ChangeKind",
         refresh=0, delta=1),

    # ---- the declared unit --------------------------------------------------
    # The stable share-space address. `id` is runtime-neutral and frozen once
    # shared (GQ-6): derived from package id + grip key, pinned in a checked-in
    # manifest (GladeIdManifest); renames are alias/migration records, never new
    # ids. A named message (not a bare STR) so the address can grow fields
    # (e.g. an explicit version) without a breaking change.
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
    # What grok enumeration emits for a sharable tap (GDL-029): the binding plus
    # the enumeration context (which package + grip key produced it — the inputs
    # to derive the glade id).
    Msg("AdvertisementRecord",
        F("binding", 1, Ref("BindingDecl")),
        F("package", 2, STR),
        F("grip_key", 3, STR)),

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
    # carried opaquely in `payload`. `base_seq` is the refresh baseline a delta
    # applies against; `origin_meta` is optional provenance.
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
