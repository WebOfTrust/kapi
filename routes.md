# KAPI routes: principle, tiers, conventions

*Draft for maintainer review, October 2026.* This document, [registry.md](registry.md) and [routes.toml](routes.toml) revive KAPI for a narrow purpose: to give every route that keripy serves or sends a recorded home, and to give new routes a set of conventions to follow. [kapi.md](kapi.md) remains the design essay; where it and keripy disagree, this document says so rather than silently picking a side.

## Routes, not APIs

keripy is a library. What it offers other software is routes: the `r` values of routed messages (`qry`, `rpy`, `exn`, and in future `xip`, `pro` and `bar`) together with the handlers that act on them. An API is something an application assembles from routes, policy and transport, and it belongs to that application. The falcon app that turns keripy into a witness is such an application, even though it currently ships inside keripy, so its HTTP endpoints are listed here separately from routed-message routes.

Some routes are part of the KERI and ACDC protocols and are specified there. Most are not. Of the 58 routes keripy registers or uses on main, a KERI or ACDC spec mentions only the `/end/role`, `/loc/scheme`, `/ipex/*` and `/oobi` families. Multisig coordination, delegation requests, challenge responses, key and transaction state notices, mailbox forwarding and every `qry` route are implemented without a written definition.

## What the registry is, and is not

This revision is descriptive. It records which routes exist, where keripy handles and sends them, which specs mention them, and which policies they inherit from their place in the tree. An entry does not yet define a route: there is no payload schema, signer, acceptance or replay regime, or version scope in routes.toml. Until an entry has those, keripy's implementation is the reference for what the route means, and the registry only names it.

Giving interop entries a normative body is the natural next step, and the drift check would then be able to tell "keripy diverged from KAPI" apart from "KAPI is out of date". It is deliberately not attempted here, because what such a body must contain is itself a question for the maintainers.

## Tiers

Each route is assigned one of three tiers. The test is who has to agree on it.

- **protocol**: the KERI or ACDC specification names it, whether normatively or in an example. Some of these mentions are weak. The ACDC IPEX section calls itself non-normative, and the KERI spec writes IPEX routes both as `/ipex/offer` and as bare `/offer`. routes.toml notes those cases.
- **interop**: no spec names it, but independent implementations must agree on it to work together: a controller and someone else's witness, or a multisig member and its peers.
- **application**: one application's own surface. KAPI registers it so names don't collide, but others need not implement it.

The tier of every current route is a first draft in [routes.toml](routes.toml) and is open to correction.

## The registry

[registry.md](registry.md) is generated, not written. [scripts/getroutes.py](scripts/getroutes.py) parses the syntax trees of a keripy source tree and finds routes in each of the ways keripy registers or dispatches them: `Router.addRoute` for `rpy`, handler `resource` attributes for `exn`, the comparisons in `processQuery` and the gate lists in front of it for `qry`, comparisons on a route elsewhere (such as `Oobiery`'s check for `/oobi/witness`), falcon `add_route` for HTTP, and mailbox `topic`/`topics` arguments. It records where each route is sent from, and which prefix policies cover it. It searches the spec sources for each route. [routes.toml](routes.toml) holds the parts a program cannot decide: tier, notes, and whether a route is proposed or retired.

The script exits non-zero when keripy and routes.toml disagree, whichever side moved:

```
python3 scripts/getroutes.py <keripy> --spec KERI=<keri-spec>/spec --spec ACDC=<acdc-spec>/spec \
    --spec-skip '*old*.md' --curated routes.toml --label "<what was scanned>" > registry.md
```

It can run on a schedule against keripy main, and later as a check in keripy's own CI if the maintainers want that. A route keripy drops is marked `retired` rather than deleted, so its name is not reused with a different meaning while older peers still send it.

The check is only as complete as the forms it recognizes. A route dispatched in a way it does not model would pass unnoticed, and a route a spec defines but keripy does not implement is not looked for.

## Conventions

These describe what keripy already does and propose rules for new routes.

1. A route is a `/`-delimited path of lowercase segments. Most first segments are short abbreviations (`loc`, `end`, `ksn`, `tsn`, `mbx`, `fwd`, `ipex`); others are full words (`multisig`, `challenge`, `delegate`, `watcher`, `introduce`). Either is acceptable. What matters is the next rule.
2. The first segment is a namespace, and a namespace should belong to one tier and one owner: a spec, or one KAPI entry. This matters for security as well as tidiness; see the next section.
3. `rpy` and `exn` routes are absolute (they start with `/`). `qry` routes are not: keripy uses bare `logs`, `ksn`, `mbx`, `tels` and `tsn`. kapi.md says absolute and relative routes resolve to the same route, but keripy compares exact strings, so `/logs` is rejected. New routes should be absolute.
4. A route names a resource, and the last segment may name an action on it (`/end/role/add`, `/end/role/cut`, `/ipex/grant`). Routed-message routes use the singular; `/oobis` is the one exception.
5. A route that lands in keripy is registered here when the drift check reports it. A keripy PR that adds a route should say which tier it belongs in.

## Why placement is a security decision

keripy decides several things about a message from a prefix of its route rather than from the route's own registration, and the matchers do not agree on their rules:

- **KRAM exemptions.** KRAM, keripy's replay protection, is off unless a node's configuration enables it (`kram.enabled`, default false). When it is on, it can exempt messages from its timeliness checks. Exemptions are (version, ilk, route) triples, matched as plain string prefixes of `version.ilk.route` (`Kramer.intake`, `src/keri/core/kraming.py`). So they are pinned to an exact protocol version, and they don't respect segment boundaries: an exemption for `/end/role` also covers `/end/roles`. When KRAM is enabled, keripy adds built-in exemptions for v2.0 `rpy /end/role` and `rpy /loc/scheme` (`Kramer.OobiDenials`). Those replies are replayed through OOBI resolution long after they were signed, so they rely on BADA ordering rather than freshness. A v1 reply on the same route is not exempt.
- **Embedded messages.** `Exchanger.processEvent` passes embedded messages to an `exn` handler only when the route starts with `/multisig` or `/ipex`, or equals `/fwd` (`src/keri/peer/exchanging.py:323`). A new route under `/ipex` receives embeds whether or not anyone intended it to.
- **Case.** The `rpy` router matches case-insensitively (`src/keri/core/routing.py`), while `exn` and `qry` dispatch, KRAM exemptions, and the prefix checks inside handlers are case-sensitive.

So where a route sits in the tree decides what it inherits. A route placed under a prefix with a policy gets that policy without anyone deciding it should, and a route that needs the policy but lives elsewhere does not get it unless someone adds it. The registry's *Inherited policy* column lists these for each route. This is the most concrete reason a route namespace needs an owner.

## First entry: `/decl/tags` and `/decl/attribs` (keripy#1685)

keripy#1685 lets a witness's controller publish self-asserted metadata: tags such as `testnet`, and name=value attributes such as `geo=ca`. It uses two `rpy` routes shaped like `/loc/scheme`. They are signed by the endpoint, ordered by BADA, and sent along with the endpoint's location replies during OOBI resolution. The two kinds are split by how a consumer uses them. A consumer acts on tags, and tags can be unioned across a witness set. A consumer only displays attributes, and attributes have no natural merge. Each kind is stored under its own (eid, kind) key, so BADA orders them independently, and correcting an attribute does not re-stamp a tag.

Proposed registration: tier **interop**. A verifier never needs these to establish key state, but a consumer that reads `testnet` from one implementation's witness has to find it under the same route and with the same meaning on another's.

Two consequences follow from the section above.

- `/decl` is a new namespace, so it doesn't inherit the KRAM exemption that `/loc/scheme` has. Decls travel in the same OOBI replay. A KRAM-enabled node dropped old v2 decls while keeping the location sent with them, so #1685 now adds a v2 exemption for `/decl/`. The trailing slash keeps it from also covering a later `/declare`. The default `Oobiery` runs no KRAM and was never affected.
- If `/decl` were placed under `/end` or `/loc` instead, it would inherit whatever policies cover those prefixes. Keeping it at the top level makes that choice explicit.

## Open questions for maintainers

These are decisions for the maintainers. They are not settled here, and automation cannot check conformance to them until they are.

1. **Parametrized routes.** kapi.md says routes carry no parameters and that parameters go in `q` or `a`. keripy registers `/ksn/{aid}`, `/end/role/{action}`, `/watcher/{aid}/{action}` and `/tsn/*/{aid}` as URI templates. Should KAPI accept templates, or record those routes as nonconforming? There is a security angle as well as a style one. KRAM chooses a route's replay window by exact match on the concrete route, so a templated route that carries an AID can never be given a window of its own. It always gets its ilk's default.
2. **Tiers.** Is the protocol/interop/application split right, and are the draft assignments in routes.toml?
3. **`/decl`.** Should it go at the top level as proposed, or under an existing namespace, given the section above? And should it be interop from the start, or application until a second implementation consumes it?
4. **IPEX route names.** keripy uses `/ipex/apply` and so on. The ACDC spec's IPEX table, in a section it calls non-normative, uses bare `apply`, `offer`, and so on. The KERI spec uses `/ipex/offer` when defining the route field, but bare `/offer` and `/agree` in its examples. Which form is normative? Separately, keripy has two IPEX handler modules that disagree on what may precede `/ipex/grant`, and only one of them is wired in.

## Not covered yet

The parts of kapi.md that have no implementation are out of scope for this revision: directory routes, `rr` return-route matching, `xip`/`pro`/`bar` processing, and the pre-router that separates them. So is the KERIA REST API described in kapi.md's Web API Mapping and in `docs/api-spec.yaml`, which predates KERIA's current API.
