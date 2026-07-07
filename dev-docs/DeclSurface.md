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
| `GladeId` | stable share-space address + the GQ-6 derivation/pinning rules (derive from package id + grip key; frozen once shared; renames are alias records) |
| `Shape` | the delivery-shape enum (`value`, `log`, `message`, `stream`, `exchange`, `window`…) — names taut-shape contracts, owns none of them |
| `Authority` | `share` \| `external(source)` |
| `Domain` / `Zone` | the ZONES vocabulary (`glade/dev-docs/GladeZones.md`, implemented 2026-06-14): domain = which replicated world (→ wire `share`); zone = who converges within it — `commons` \| `private(self)` + future axes (→ wire `key`). The binder's scope maps them at bind time. |
| `BindingDecl` | `(glade id, shape, authority, domain, zone, retention)` — the unit a tap declares and glial binds (a *surface*, in zones terms) |
| `AdvertisementRecord` | what grok enumeration emits for sharable taps (GDL-029) |
| Canonical-key **interface** | the signature for param→canonical-CBOR keys; implementations live below |

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
  dev-docs/DeclSurface.md      # this doc graduates here
  ir/glade_decl.taut.py        # THE schema
  ir/glade_decl.ir.json        # exported IR (regen.py --check = CI gate)
  corpus/decl.v0.json          # golden vectors — MANDATORY (see below)
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
  mandatory — for the interface package too.

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
