#!/usr/bin/env python3
"""
List every route a keripy source tree serves or emits, by parsing its syntax trees.

keripy registers routes in several unrelated ways, and this script knows each of them:

  rpy   Router.addRoute("/loc/scheme", resource, suffix=...)     reply routes
  exn   handler classes with a class-level resource = "/..."      exchange routes
        or constructed with resource="/..."
  qry   route == "logs" comparisons inside processQuery()         query routes
        route in ["logs", ...] gates that decide which processQuery is reached
  http  falcon app.add_route("/oobi/{aid}", ...) and add_sink     HTTP endpoints
  mbx   topic="receipt" / topics=["/receipt", ...] on mailbox calls  mailbox topics

It also records where routes are emitted: route="..." keyword arguments on the calls
that build exn, rpy and qry messages (exchange, specialExchange, reply, query), and
dict(kin="reply", route=...) cues. A route held in a local variable is followed to the
string or f-string assigned to it. So a route that keripy sends but never handles
shows up too.

With --spec, each route is looked up as a quoted or backticked literal in the given
specification sources, so the registry can say which routes a spec mentions.

With --curated, tiers and notes from a hand-maintained TOML file are merged in. The run
exits 1, listing the cause on stderr, when the source and the curated file disagree:
a route in the source that the curated file does not list; a listed route the source
no longer has (unless it is marked status = "proposed"); a proposed route that has
since appeared in the source; or a qry route that processQuery handles but no gate
admits, or the reverse.

Usage:
    getroutes.py <keripy-repo-or-src-dir> [--spec [NAME=]DIR ...] [--curated routes.toml]
                 [--label TEXT] [--json]
"""

import argparse
import ast
import json
import os
import re
import sys

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

EMITTERS = {"exchange": "exn", "specialExchange": "exn", "reply": "rpy", "query": "qry"}
CUES = {"reply": "rpy", "query": "qry"}  # dict(kin=..., route=...) cue kinds


def render(node):
    """Render a route expression as a string, turning variables into {placeholders}."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        v = node.value
        return v.decode() if isinstance(v, bytes) else v
    if isinstance(node, ast.JoinedStr):
        out = []
        for part in node.values:
            if isinstance(part, ast.Constant):
                out.append(str(part.value))
            else:
                out.append("{" + ast.unparse(part.value) + "}")
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = render(node.left), render(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, (ast.Name, ast.Attribute)):
        return "{" + ast.unparse(node) + "}"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr == "encode":
        return render(node.func.value)
    return None


def literal(route):
    """True if a rendered route has some fixed text, not just a variable."""
    return route is not None and re.sub(r"\{[^}]*\}", "", route) != ""


def callname(node):
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def kwarg(node, name):
    for k in node.keywords:
        if k.arg == name:
            return k.value
    return None


def topic_key(t):
    """Mailbox topics are written both with and without a leading slash."""
    return "/" + t.lstrip("/")


class Scanner(ast.NodeVisitor):
    def __init__(self, relpath, found, emitted, gates):
        self.relpath = relpath
        self.found = found
        self.emitted = emitted
        self.gates = gates
        self.classes = []
        self.funcs = []
        self.calls = []    # per function: local name -> class it was constructed from
        self.strings = []  # per function: local name -> strings assigned to it

    def where(self, node):
        return f"{self.relpath}:{node.lineno}"

    def scope(self):
        return ".".join(self.classes[-1:] + self.funcs[-1:])

    def owner(self):
        return self.classes[-1] if self.classes else "<module>"

    def add(self, msg, route, handler, node):
        self.found.append(dict(msg=msg, route=route, handler=handler, where=self.where(node)))

    def emit(self, msg, route, role, node):
        self.emitted.append(dict(msg=msg, route=route, role=role,
                                 where=self.where(node), by=self.scope()))

    def values(self, node):
        """Every string a route expression can take, following one level of locals."""
        if isinstance(node, ast.Name) and self.strings and node.id in self.strings[-1]:
            return self.strings[-1][node.id]
        if isinstance(node, ast.IfExp):
            return self.values(node.body) + self.values(node.orelse)
        r = render(node)
        return [r] if r is not None else []

    def visit_ClassDef(self, node):
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                    and isinstance(stmt.targets[0], ast.Name) \
                    and stmt.targets[0].id == "resource":
                route = render(stmt.value)
                if route and route.startswith("/"):
                    self.add("exn", route, node.name, stmt)
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node):
        self.funcs.append(node.name)
        calls, strings = {}, {}
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if not isinstance(t, ast.Name):
                        continue
                    if isinstance(stmt.value, ast.Call):
                        calls[t.id] = callname(stmt.value)
                    elif isinstance(stmt.value, (ast.Constant, ast.JoinedStr, ast.IfExp, ast.BinOp)):
                        # values() with no locals yet: render the expression itself
                        self.strings.append({})
                        vals = self.values(stmt.value)
                        self.strings.pop()
                        strings.setdefault(t.id, []).extend(v for v in vals if literal(v))
        self.calls.append(calls)
        self.strings.append(strings)
        self.generic_visit(node)
        self.strings.pop()
        self.calls.pop()
        self.funcs.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def handler(self, node):
        """Name the class that handles a route: the callee, or what a local was built from."""
        if isinstance(node, ast.Call):
            return callname(node) or ast.unparse(node)
        if isinstance(node, ast.Name) and self.calls and self.calls[-1].get(node.id):
            return self.calls[-1][node.id]
        return ast.unparse(node)

    def visit_Compare(self, node):
        if isinstance(node.left, ast.Name) and node.left.id == "route":
            for op, comp in zip(node.ops, node.comparators):
                # query dispatch: `if route == "logs":` inside a processQuery method
                if isinstance(op, ast.Eq) and self.funcs and self.funcs[-1] == "processQuery":
                    route = render(comp)
                    if route:
                        self.add("qry", route, f"{self.owner()}.processQuery", node)
                # query gate: `if route in ["logs", "ksn", "mbx"]:` ahead of processQuery
                elif isinstance(op, ast.In) and isinstance(comp, (ast.List, ast.Tuple)):
                    for elt in comp.elts:
                        route = render(elt)
                        if route:
                            self.gates.append(dict(route=route, where=self.where(node)))
        self.generic_visit(node)

    def visit_Call(self, node):
        name = callname(node)
        if name == "addRoute" and node.args:
            route = render(node.args[0])
            suffix = kwarg(node, "suffix")
            method = "processReply" + (suffix.value if isinstance(suffix, ast.Constant) else "")
            if route:
                self.add("rpy", route, f"{self.owner()}.{method}", node)
        elif name == "add_route" and node.args:
            route = render(node.args[0])
            handler = self.handler(node.args[1]) if len(node.args) > 1 else "?"
            if route:
                self.add("http", route, handler, node)
        elif name == "add_sink":
            prefix = kwarg(node, "prefix")
            handler = self.handler(node.args[0]) if node.args else "?"
            self.add("http", (render(prefix) if prefix else "/") + " (sink)", handler, node)
        else:
            resource = kwarg(node, "resource")
            if resource is not None and name and name[0].isupper():
                route = render(resource)
                if route and route.startswith("/"):
                    self.add("exn", route, name, node)
            topics = kwarg(node, "topics")
            if isinstance(topics, ast.List):
                for elt in topics.elts:
                    t = render(elt)
                    if t and "{" not in t:
                        self.emit("mbx", topic_key(t), "reads", node)
            topic = kwarg(node, "topic")
            if topic is not None:
                for t in self.values(topic):
                    if "{" not in t:  # f"{recp}/{topic}" is the storage key, not a topic
                        self.emit("mbx", topic_key(t), "writes", node)
            route = kwarg(node, "route")
            msg = EMITTERS.get(name)
            if name == "dict":
                kin = kwarg(node, "kin")
                if isinstance(kin, ast.Constant):
                    msg = CUES.get(kin.value)
            if route is not None and msg:
                for r in self.values(route):
                    if literal(r):
                        self.emit(msg, r, "emits", node)
        self.generic_visit(node)


def scan(src):
    found, emitted, gates = [], [], []
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in ("tests", "test", "__pycache__"))
        for fn in sorted(files):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, os.path.dirname(src))
            with open(path, "rb") as f:
                tree = ast.parse(f.read(), filename=path)
            Scanner(rel, found, emitted, gates).visit(tree)
    return found, emitted, gates


def shape(route):
    """Normalize placeholders so /ksn/{aid} and /ksn/{src} compare equal."""
    return re.sub(r"\{[^}]*\}", "{}", route)


def load_specs(specdirs):
    """Read every markdown line of each spec source once: [(label, line)]."""
    lines = []
    for name, d in specdirs:
        if not os.path.isdir(d):
            sys.exit(f"--spec {name}={d}: not a directory")
        before = len(lines)
        for root, _, files in os.walk(d):
            for fn in sorted(files):
                if fn.endswith(".md"):
                    path = os.path.join(root, fn)
                    with open(path, encoding="utf-8", errors="replace") as f:
                        lines += [(f"{name}:{os.path.relpath(path, d)}:{i}", line)
                                  for i, line in enumerate(f, 1)]
        if len(lines) == before:
            sys.exit(f"--spec {name}={d}: no markdown files found")
    return lines


def spec_hits(route, speclines):
    """Find the route as a quoted or backticked literal, placeholders matching one segment."""
    if not literal(route) or route.strip("/") == "":
        return []
    body = "".join("[^/\"'`\\s]+" if part.startswith("{") else re.escape(part)
                   for part in re.split(r"(\{[^}]*\})", route) if part)
    pat = re.compile(r"[\"'`]" + body + r"[\"'`]")
    return [where for where, line in speclines if pat.search(line)]


def load_curated(path):
    if not path:
        return {}
    if tomllib is None:
        sys.exit("--curated needs Python 3.11+ (tomllib)")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    curated = {}
    for r in data.get("route", []):
        key = (r["msg"], shape(r["route"]))
        if key in curated:
            sys.exit(f"{path}: duplicate entry for {r['msg']} {r['route']}")
        curated[key] = r
    return curated


def build(src, speclines, curated):
    found, emitted, gates = scan(src)
    entries = {}
    for f in found:
        key = (f["msg"], shape(f["route"]))
        e = entries.setdefault(key, dict(msg=f["msg"], route=f["route"], handled=[], emitted=[]))
        e["handled"].append(f"{f['handler']} ({f['where']})")
    for x in emitted:
        key = (x["msg"], shape(x["route"]))
        if key not in entries:
            # an emitted route that is not handled: match it against handled templates
            for k, e in entries.items():
                if k[0] == x["msg"] and re.fullmatch(
                        re.escape(k[1]).replace(r"\{\}", r"[^/]+"), shape(x["route"])):
                    key = k
                    break
        e = entries.setdefault(key, dict(msg=x["msg"], route=x["route"], handled=[], emitted=[]))
        e["emitted"].append(f"{x['role']} {x['by']} ({x['where']})")
    for key, e in entries.items():
        e["spec"] = spec_hits(e["route"], speclines)
        c = curated.get(key, {})
        e["tier"] = c.get("tier", "unclassified")
        e["note"] = c.get("note", "")
        e["proposed"] = c.get("status") == "proposed"
    for key, c in curated.items():
        if key not in entries:
            entries[key] = dict(msg=c["msg"], route=c["route"], handled=[], emitted=[],
                                spec=[], tier=c.get("tier", "unclassified"),
                                note=c.get("note", ""), absent=True,
                                proposed=c.get("status") == "proposed")
    # qry routes must be admitted by a gate and handled by processQuery, or neither
    handled_qry = {e["route"] for e in entries.values() if e["msg"] == "qry" and e["handled"]}
    gated = {g["route"] for g in gates}
    gate_problems = sorted(f"qry {r}: handled in processQuery but admitted by no gate"
                           for r in handled_qry - gated)
    gate_problems += sorted(f"qry {r}: admitted by a gate but handled by no processQuery"
                            for r in gated - handled_qry)
    order = {"rpy": 0, "qry": 1, "exn": 2, "http": 3, "mbx": 4}
    rows = sorted(entries.values(), key=lambda e: (order.get(e["msg"], 9), e["route"]))
    return rows, gate_problems


def md(entries, label):
    out = [f"<!-- Generated by scripts/getroutes.py. Do not edit by hand; edit routes.toml. -->",
           "", "# KAPI route registry", "",
           f"Generated from {label}. Tiers and conventions are explained in "
           "[routes.md](routes.md). *In spec* is a literal search for the route in the "
           "specification sources, so it says where a spec mentions a route, not whether "
           "the spec makes it normative.", ""]
    titles = dict(rpy="Reply (`rpy`) routes", qry="Query (`qry`) routes",
                  exn="Exchange (`exn`) routes", http="HTTP endpoints",
                  mbx="Mailbox topics")
    for msg in ("rpy", "qry", "exn", "http", "mbx"):
        rows = [e for e in entries if e["msg"] == msg]
        if not rows:
            continue
        out += [f"## {titles[msg]}", "",
                "| Route | Tier | In spec | Handled by | Emitted / used by | Note |",
                "|---|---|---|---|---|---|"]
        for e in rows:
            def cell(items, n=3):
                rank = {"writes": 0, "emits": 0, "reads": 1}
                items = sorted(set(items), key=lambda i: (rank.get(i.split()[0], 0), i))
                s = "<br>".join(f"`{i}`" for i in items[:n])
                return s + (f"<br>+{len(items) - n} more" if len(items) > n else "")
            handled = cell(e["handled"]) or (
                "*proposed*" if e.get("absent") and e.get("proposed") else
                "*not in this source*" if e.get("absent") else "—")
            out.append(f"| `{e['route']}` | {e['tier']} | {cell(e['spec'], 2) or '—'} | "
                       f"{handled} | {cell(e['emitted']) or '—'} | {e['note']} |")
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source", help="keripy repo root or its src/keri directory")
    ap.add_argument("--spec", action="append", default=[], metavar="[NAME=]DIR",
                    help="specification source directory to search (repeatable)")
    ap.add_argument("--curated", help="TOML file of tiers and notes")
    ap.add_argument("--label", default=None, help="source description for the header")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    src = os.path.abspath(args.source)
    if os.path.isdir(os.path.join(src, "src", "keri")):
        src = os.path.join(src, "src", "keri")
    if not os.path.isdir(src):
        sys.exit(f"{args.source}: not a directory")
    specs = [tuple(s.split("=", 1)) if "=" in s else (os.path.basename(s.rstrip("/")), s)
             for s in args.spec]
    entries, gate_problems = build(src, load_specs(specs), load_curated(args.curated))
    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        print(md(entries, args.label or src))

    problems = list(gate_problems)
    if args.curated:
        for e in entries:
            if e["tier"] == "unclassified":
                problems.append(f"{e['msg']} {e['route']}: in source, not in registry")
            elif e.get("absent") and not e.get("proposed"):
                problems.append(f"{e['msg']} {e['route']}: in registry, not in source")
            elif e["proposed"] and not e.get("absent"):
                problems.append(f"{e['msg']} {e['route']}: marked proposed, but now in source")
    for p in problems:
        print(p, file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
