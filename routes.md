# KAPI routes: principle, tiers, conventions

*Draft for maintainer review, October 2026.* This document, [registry.md](registry.md) and [routes.toml](routes.toml) revive KAPI for a narrow purpose: to give every route that keripy serves or sends a recorded home, and to give new routes a set of conventions to follow. [kapi.md](kapi.md) remains the design essay; where it and keripy disagree, this document says so rather than silently picking a side.

## Routes, not APIs

keripy is a library. What it offers other software is routes: the `r` values of routed messages (`qry`, `rpy`, `exn`, and in future `xip`, `pro` and `bar`) together with the handlers that act on them. An API is something an application assembles from routes, policy and transport, and it belongs to that application. The falcon app that turns keripy into a witness is such an application, even though it currently ships inside keripy, so its HTTP endpoints are listed here separately from routed-message routes.

Some routes are part of the KERI and ACDC protocols and are specified there. Most are not. Of the 56 routes keripy registers or uses on main, a KERI or ACDC spec mentions only the `/end/role`, `/loc/scheme`, `/ipex/*` and `/oobi` families. Multisig coordination, delegation requests, challenge responses, key and transaction state notices, mailbox forwarding and every `qry` route are implemented without a written definition. KAPI is the place to write them down.

## Tiers

Each route is assigned one of three tiers. The test is who needs to agree on it.

- **protocol**: a verifier needs it to establish key state or trust. It is specified in the KERI or ACDC spec, and KAPI only records it.
- **interop**: no verifier needs it, but two independent implementations must agree on it to work together (a controller and someone else's witness, a multisig member and its peers). KAPI is the normative definition until a spec takes it.
- **application**: one application's own surface. KAPI registers it so names don't collide, but others need not implement it.

The tier of every current route is a first draft in [routes.toml](routes.toml) and is open to correction.

## The registry

[registry.md](registry.md) is generated, not written. [scripts/getroutes.py](scripts/getroutes.py) parses the syntax trees of a keripy source tree and finds routes from each of the ways keripy registers them: `Router.addRoute` for `rpy`, handler `resource` attributes for `exn`, the comparisons in `processQuery` for `qry`, falcon `add_route` for HTTP, and mailbox `topic`/`topics` arguments. It also records where each route is emitted, and searches the spec sources for each route. [routes.toml](routes.toml) holds the parts a program cannot decide: tier, notes, and whether a route is only proposed.

The script exits non-zero when keripy has a route that routes.toml does not list, or routes.toml lists a route keripy no longer has. That check is what lets the registry stay current without anyone remembering to update it:

```
python3 scripts/getroutes.py <keripy> --spec KERI=<keri-spec>/spec --spec ACDC=<acdc-spec>/spec \
    --curated routes.toml --label "<what was scanned>" > registry.md
```

It can run on a schedule against keripy main, and later as a check in keripy's own CI if the maintainers want that.

## Conventions

These describe what keripy already does, and propose rules for new routes where keripy is already consistent.

1. A route is a `/`-delimited path of short lowercase segments. Existing first segments are abbreviations of three or four letters (`loc`, `end`, `ksn`, `tsn`, `mbx`, `fwd`, `ipex`); new ones should be similar.
2. The first segment is a namespace, and a namespace should belong to one tier and one owner (a spec, or one KAPI entry). This matters for security as well as tidiness; see the next section.
3. `rpy` and `exn` routes are absolute (they start with `/`). `qry` routes are not: keripy uses bare `logs`, `ksn`, `mbx`, `tels` and `tsn`. kapi.md says absolute and relative routes resolve to the same route, but keripy compares exact strings, so `/logs` is rejected. New routes should be absolute.
4. A route names a resource, and the last segment may name an action on it (`/end/role/add`, `/end/role/cut`, `/ipex/grant`). Routed-message routes use the singular; `/oobis` is the one exception.
5. A new route is added to routes.toml in the same change that adds it to keripy.

## Why placement is a security decision

KRAM, keripy's replay protection, is off unless a node's configuration enables it (`kram.enabled`, default false), and its exemptions are configured per protocol version. When it is on, it can exempt messages from its timeliness checks. Exemptions are configured as (version, ilk, route) and matched as string prefixes of the message's route (`Kramer.intake`, `src/keri/core/kraming.py`). When KRAM is enabled, keripy adds two built-in exemptions, for v2 `rpy /end/role` and v2 `rpy /loc/scheme` (`Kramer.OobiDenials`), because those replies are replayed through OOBI resolution long after they were signed, so they rely on BADA ordering rather than freshness.

So on a node with KRAM enabled, where a route sits in the tree decides whether it is replay-protected. A route placed under an exempt prefix is exempt without anyone deciding it should be, and a route that needs the same treatment as `/loc/scheme` but lives elsewhere is not exempt unless someone adds it. The matching is by string, not by segment, so an exemption for `/end/role` also covers `/end/roles`. This is the most concrete reason a route namespace needs an owner.

## First entry: `/decl/tags` and `/decl/attribs` (keripy#1685)

keripy#1685 lets a witness's controller publish self-asserted metadata: tags such as `testnet`, and name=value attributes such as `geo=ca`. It uses two `rpy` routes shaped like `/loc/scheme`. They are signed by the endpoint, ordered by BADA, and sent along with the endpoint's location replies during OOBI resolution. There are two routes because BADA orders each route separately, and tags and attributes change at very different rates.

Proposed registration: tier **interop**. A verifier never needs these to establish key state, but a consumer that reads `testnet` from one implementation's witness has to find it under the same route and with the same meaning on another's.

Two consequences follow from the sections above.

- `/decl` is a new namespace, so it doesn't inherit the KRAM exemption that `/loc/scheme` has. Decls travel in the same OOBI replay, and a KRAM-enabled node dropped old v2 decls while keeping the location sent with them, so #1685 now adds `/decl` to `Kramer.OobiDenials`. The default `Oobiery` runs no KRAM and was never affected.
- If `/decl` were placed under `/end` or `/loc` instead, it would inherit whatever exemptions and policies cover those prefixes. Keeping it at the top level makes that choice explicit.

## Open questions for maintainers

These are decisions for the maintainers. They are not settled here, and automation cannot check conformance to them until they are.

1. **Parametrized routes.** kapi.md says routes carry no parameters and that parameters go in `q` or `a`. keripy registers `/ksn/{aid}`, `/end/role/{action}`, `/watcher/{aid}/{action}` and `/tsn/*/{aid}` as URI templates. Should KAPI accept templates, or record those routes as nonconforming?
2. **Tiers.** Is the protocol/interop/application split right, and are the draft assignments in routes.toml?
3. **`/decl`.** Should it go at the top level as proposed, or under an existing namespace, given the KRAM point above?
4. **IPEX route names.** The ACDC spec's IPEX table names the steps as bare words (`apply`, `offer`, …), while keripy and the KERI spec's example use `/ipex/apply` and so on. Which form is normative?

## Not covered yet

The parts of kapi.md that have no implementation are out of scope for this revision: directory routes, `rr` return-route matching, `xip`/`pro`/`bar` processing, and the pre-router that separates them. So is the KERIA REST API described in kapi.md's Web API Mapping and in `docs/api-spec.yaml`, which predates KERIA's current API.
