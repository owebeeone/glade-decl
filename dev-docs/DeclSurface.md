Mirror of `dev-docs/glade/GladeDeclSurface.md` in the glade-wz root — do not edit here

# Glade Declaration Surface (`glade-decl`) — the shared leaf module

Status: working draft — **seam definition; skeletons land with the glade-dev
extraction decision**

Purpose: fix the grip→glial→glade layering with one small module. Today the
prototype has taps talking directly to glade (grip-share binds tap ↔ glade
session), and grip-core carries hand-rolled share-declaration types. The
correct arrows need a **leaf** both sides can import without importing each
other:

```text
grip-core ──▶ glade-decl ◀── glial
                  ▲
                  │ implements
               glade kernel
```

This is the razel `*-api` crate idiom applied here, and the
seams-at-inception rule: the wall exists from day one, even around a stub.

## Contents (declaration surface ONLY)

| Item | What it is |
| --- | --- |
| `GladeId` | stable share-space address + the GQ-6 derivation/pinning rules (derive from package id + grip key; frozen once shared; renames are alias records). The derivation is deferred past contract v1 (R6(a), 2026-09-23), so every id in use today is authored: an app file states it literally, and no syntax rule is fixed for it (glade-decl `README.md`) |
| `Shape` | a compatibility declaration discriminator governed by `TautShapeCatalogAdoption.md`: canonical engines are `value`, `atom`, `log`, `stream`, `swmr`, `crdt`; `snapshot_delta`/`text_crdt` are profiles. Registry recognition does not grant runtime support. `exchange` is a separate Glade service interaction; `message` is unsupported; `window` is a view over an explicit base shape. The module names contracts and capabilities, and owns none of their engines. |
| `Authority` | `share` \| `external(source)` |
| `Domain` / `Zone` | the ZONES vocabulary (`glade/dev-docs/GladeZones.md`, implemented 2026-06-14): domain = which replicated world (→ wire `share`); zone = who converges within it — `commons` \| `private(self)` + future axes (→ wire `key`). The domain is a declaration-time hint the binder resolves to a concrete share: the grip-share binder does, through its manifest's `domains` table; glial does not yet. The zone is the author's to choose and write — in an `<app>.glade` file it is the binding line's zone token, which has no default. A mount does not override it: on the grip-share path `manifestScope` reads `decl.zone ?? spec?.zone ?? ""`, so the declared zone wins and the manifest's surface spec is only a fallback; on the glial path the mount's zone fill enters only a local instance key and never reaches the wire, so a surface declared `private` and mounted through glial converges in the commons partition. |
| `Retention` | `{policy, ttl_ms?}` — how much of a surface's history is kept. **Declarative and unenforced**: nothing applies it yet (GC-4). `latest` — the surface keeps one value, last write wins; the hazardous one to reach for by reflex, because on a `log` it silently turns an append log into a single value, and on a `crdt` it does not mean "the merged value". `from_cursor` (written `from-cursor` in an app file) — the history is kept and a subscriber resumes from a position rather than from the head: logs, output streams, file trees. `ttl` — records expire after a duration, `ttl_ms` in the record; an app file states the duration with the binding line's `ttl=<duration>` tail key (R11(a)), but the node validates the tail keys `ttl=<duration>` and `shape-profile=<profile>` and records neither: no record carries a duration or a profile yet. `windowed` is not a retention: a window is a view over an explicit base shape. |
| `BindingDecl` | `(glade id, shape, authority, source?, domain, zone, retention)` — the unit a tap declares and glial binds (a *surface*, in zones terms). `source` names the outside source iff the authority is `external`; both are declared, not yet authorable, because no app-file token names a source (R5(b)). The decl is app-static; each **mount** creates a binding *instance* `(decl, fill)`, and several instances of one decl may be live at once (clarified 2026-07-10; lifecycle + idiom-agnostic seam in `GlialClientRuntime.md` §Boundaries). The fill carries what the decl leaves to runtime — which document, which principal — and does not override the declared zone (see `Domain` / `Zone`). |
| `ShapeProfileDecl` | `(glade id, profile)` — the GDL-041 profile a surface needs (`snapshot_delta` over `swmr`, `text_crdt` over `crdt`), keyed by glade id rather than carried on `BindingDecl`, so no `BindingDecl` byte moves (R4(b), 2026-09-23). An app file's binding line names the profile with the `shape-profile=<profile>` tail key (R11(a)), but nothing registers a `ShapeProfileDecl` yet, because the node records no tail key (see `Retention`); a `crdt` mount gets its profile from glial's `MountConfig.crdtProfile` today (`glial/src/binder.ts:98-106`) |
| `AdvertisementRecord` | what grok enumeration emits for sharable taps (GDL-029, open) — **held out of contract v1** (R7(b), 2026-09-23) until GDL-029 ratifies; the retired name may return only with its v0 shape (glade-decl `dev-docs/OpenNotes.md`) |
| **Supplier** (vocabulary, GDL-040) | the authority-side module standing behind declared surfaces and answering for them — the counterpart of a tap; wire-attached as an ordinary authority session (working assumption, GLP-0006 P00-a). Not a wire message: suppliers register/serve via ordinary records + sessions |
| Canonical-key **interface** | the signature for param→canonical-CBOR keys; implementations live below. Not implemented and not oracled in contract v1 (R6(a), 2026-09-23); owner: Gianni |

## Exclusions (the point of the module)

No runtime, no wire, no folds, no sessions, no persistence. If a change here
needs a network or a store to make sense, it belongs in glade or glial.

## Form

Defined as a **taut schema** (`glade_decl.taut.py`) so Rust/TS/Python agree by
generation, not convention — the module is itself a mini-contract with the
freeze discipline: additive evolution, versioned, oracle-checked once it has
two consumers.

## Repo structure (ruled 2026-07-07 — gwz members of glade-dev)

FOUR sibling repos, the taut-shape idiom verbatim — contract + per-language
renderings. Lockstep comes from the CORPUS GATE, not co-location; in a gwz
workspace the multi-repo coordination is one workspace gesture (an early
dogfood case: "regen all decl members + run vectors").

```
glade-decl/                    # contract ONLY — zero language code
  dev-docs/DeclSurface.md      # banner-marked mirror of this root page, which is controlling
  ir/glade_decl.taut.py        # THE schema
  ir/glade_decl.ir.json        # exported IR (regen.py --check = CI gate)
  corpus/decl.v1.json          # golden vectors — MANDATORY (see below)
glade-decl-ts/                 # @owebeeone/glade-decl (generated + thin index)
glade-decl-rs/                 # glade-decl crate
glade-decl-py/                 # glade_decl
```

Lockstep conditions (what makes the split safe): each `glade-decl-<lang>`
pins a `CONTRACT_VERSION` and its CI regenerates from the pinned IR + runs
the corpus vectors — skew fails the lang repo's build, never silently.
Generated code is COMMITTED in the lang repos, so consumers (grip-core)
install a plain package with no tautc at build time.

Additions to the §Contents inventory:

- **`ChangeEvent` — the envelope SHELL** `{glade_id, shape, kind:
  refresh|delta, base_seq, origin_meta, payload: BYTES}`. Resolves GC-1 by a
  split: the generic shell lives here (grip-core types events without glial
  existing); each shape's DELTA payload stays in its taut-shape contract,
  carried opaquely.
- **`derive_glade_id(package_id, grip_key)`** — the GQ-6 pure function +
  pinned-manifest format. All three languages must compute it identically,
  which is why `corpus/` is mandatory: golden vectors for id derivation and
  canonical encodings of every message. Reference code optional, oracle
  mandatory — for the interface package too. *(Deferred past contract v1 —
  R6(a), 2026-09-23: the function and its golden vectors are implemented in no
  language; the v1 corpus carries canonical encodings only.)*

Rules that keep it a leaf:

1. Depends on the taut runtime per language and NOTHING else.
2. grip-core's import path is **types-only** (TS type-imports erase at
   build; Rust `codec` feature off by default) — a grip app deploys with
   glade-decl and no glade/glial anywhere.
3. A `BindingDecl` without a binder is **inert data** — declaration costs
   nothing until a glial binder exists in the process (mock→real at package
   granularity).
4. Additive-only versioning; consumers treat unknown mandatory
   fields/shapes as binding-unusable, never process-fatal (AZ-11 posture).

## Consumers and the migration

- **grip-core**: the base-tap `share:` declaration types come from here;
  grip-core's zero-glade-imports promise becomes structural.
- **glial**: binds declared taps (persistence always, glade when configured —
  `GlialClientRuntime.md`); composes environments/workspaces by referencing
  `BindingDecl`s it never implements.
- **glade kernel**: implements the surface; the wire and folds stay its own.
- **grip-share**: shrinks to declaration plumbing (tap ↔ glial), losing its
  direct glade coupling — see StackMap row change (GDL-035).

Migration steps: (1) skeleton schema + generated rs/ts; (2) grip-core swaps
its inline types for the import; (3) glial binder consumes `BindingDecl`; (4)
grip-share's glade imports deleted — the compile wall proves the seam.

## The `<app>.glade` file (re-scoped 2026-07-06 — GDL-037)

The FILE form of this surface: an application's declaration package — its
`BindingDecl`s (glade ids, shapes, key-type refs), `ServiceDefinition`s, and
**ACL seeds**. `grazel-app.glade` is the first instance (gryth's workspace
app: workspaces, files, workspace-local diffs, terminals); a gryth peer node
= glade node + grazel authority sessions + this file.

**Amended 2026-09-23 (R8(b), `GladeDeclReconciliation.md` §3).** `glade-decl`
is the tap/binding vocabulary only: of those three record kinds it types the
`BindingDecl`. `ServiceDefinition`s and the ACL-seed records (the
`CapabilityGrant`s a seed compiles to) stay node `sysdata`
(`glade/node/ir/sysdata.taut.py`), typed and registered by the node — as does
the `WorkspaceEntry` a `workspace` line registers. The file still carries all
of them; only its `binding` lines are this contract's.

- **Loaded, not compiled.** A node REGISTERS the file's declarations as
  ordinary runtime records — the same records dynamic configuration writes.
  Cross-language (TS/RS/PY) consistency of ids/shapes/keys comes from reading
  the same declarations; key TYPES reference taut messages (existing
  codegen). `.glade` is data; it never becomes a compiler front-end.
- **ACL seeds compile to grant records** at registration, under the
  registrant's chain. The file is a bootstrap shortcut; the FOLD stays the
  only runtime authority — runtime ACL updates win by ordinary fold rules,
  and re-registration diffs against records (the GQ-6 pinning discipline).
  Never a parallel ACL system.
- **Base glade stays app-agnostic**: transport, endpoint discovery, ephemeral
  endpoint management (service instantiation), ACL enforcement, and
  `~/.glade/sys` persistence all operate on records — whoever wrote them.
  Applications only ever CONTRIBUTE records; grazel is an application.
- **Base glade ships its own app file: `glade-sys.glade`** (GDL-038) — the
  system declaration package: bindings over the system shares
  (`dir.workspaces`, `dir.principals`, `dir.grants`, `node.status`, claims)
  plus the admin/lifecycle exchange verbs. Management UIs are ORDINARY grip
  apps over these bindings; there is no privileged management plane —
  reads are subscriptions, writes are the same record-appends, effects are
  verbs, all gated by the same check(). (GDL-023's console, collapsed to
  user scale.)
- **Glial's role unchanged** (GDL-035): consumes the same declarations for
  the taut-shape→grip-tap transformation.

Deliberately out of scope, with hooks in place: **dynamic grip-context-graph
sharing** (sharing internal state not pre-declared) is a separate glial-grip
mechanism — buildable later WITHOUT substrate change, because BindingDecls
are runtime records: a (headless AI) session "inserting taps" = appending
declarations + grants it is authorized to append. GDL-004 and GDL-030 own its
open questions; it is the enabler for AI clients on live sessions.
