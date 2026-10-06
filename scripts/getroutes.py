#!/usr/bin/env python3
"""
List every route a keripy source tree serves or emits, by parsing its syntax trees.

keripy registers routes in several unrelated ways, and this script knows each of them:

  rpy   Router.addRoute("/loc/scheme", resource, suffix=...)     reply routes
  exn   handler classes with a class-level resource = "/..."      exchange routes
        or constructed with resource="/..."
  qry   route == "logs" comparisons inside processQuery()         query routes
  http  falcon app.add_route("/oobi/{aid}", ...) and add_sink     HTTP endpoints
  mbx   topic="/receipt" / topics=[...] on mailbox calls          mailbox topics

It also records where routes are emitted (route="..." keyword arguments on the calls
that build exn, rpy and qry messages), so a route that keripy sends but never handles
shows up too.

With --spec, each route is looked up as a quoted or backticked literal in the given
specification sources, so the registry can say which routes a spec mentions.

With --curated, tiers and notes from a hand-maintained TOML file are merged in. A route
in the source that the curated file does not list, or a listed route (other than one
marked status = "proposed") that the source no longer has, is reported on stderr and
makes the exit status 1. That is the drift signal.

Usage:
    getroutes.py <keripy-repo-or-src-dir> [--spec DIR ...] [--curated routes.toml]
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

EMITTERS = {"exchange": "exn", "reply": "rpy", "query": "qry"}


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
    if isinstance(node, ast.Name):
        return "{" + node.id + "}"
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


class Scanner(ast.NodeVisitor):
    def __init__(self, relpath, found, emitted):
        self.relpath = relpath
        self.found = found
        self.emitted = emitted
        self.classes = []
        self.funcs = []
        self.locals = []

    def where(self, node):
        return f"{self.relpath}:{node.lineno}"

    def scope(self):
        parts = self.classes[-1:] + self.funcs[-1:]
        return ".".join(parts)

    def add(self, msg, route, handler, node):
        self.found.append(dict(msg=msg, route=route, handler=handler, where=self.where(node)))

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
        self.locals.append({})
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        self.locals[-1][t.id] = callname(stmt.value)
        self.generic_visit(node)
        self.locals.pop()
        self.funcs.pop()

    def handler(self, node):
        """Name the class that handles a route: the callee, or what a local was built from."""
        if isinstance(node, ast.Call):
            return callname(node) or ast.unparse(node)
        if isinstance(node, ast.Name) and self.locals and self.locals[-1].get(node.id):
            return self.locals[-1][node.id]
        return ast.unparse(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Compare(self, node):
        # query dispatch: `if route == "logs":` inside a processQuery method
        if self.funcs and self.funcs[-1] == "processQuery" \
                and isinstance(node.left, ast.Name) and node.left.id == "route":
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, ast.Eq):
                    route = render(comp)
                    if route:
                        self.add("qry", route, f"{self.classes[-1]}.processQuery", node)
        self.generic_visit(node)

    def visit_Call(self, node):
        name = callname(node)
        if name == "addRoute" and node.args:
            route = render(node.args[0])
            suffix = kwarg(node, "suffix")
            method = "processReply" + (suffix.value if isinstance(suffix, ast.Constant) else "")
            owner = self.classes[-1] if self.classes else "?"
            if route:
                self.add("rpy", route, f"{owner}.{method}", node)
        elif name == "add_route" and node.args:
            route = render(node.args[0])
            handler = self.handler(node.args[1]) if len(node.args) > 1 else "?"
            if route:
                self.add("http", route, handler, node)
        elif name == "add_sink":
            prefix = kwarg(node, "prefix")
            handler = self.handler(node.args[0]) if node.args else "?"
            self.add("http", (ast.unparse(prefix) if prefix else "/") + " (sink)", handler, node)
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
                    if t:
                        self.emitted.append(dict(msg="mbx", route=t, role="reads",
                                                 where=self.where(node), by=self.scope()))
            topic = kwarg(node, "topic")
            if topic is not None:
                t = render(topic)
                if t and t.startswith("/"):
                    self.emitted.append(dict(msg="mbx", route=t, role="writes",
                                             where=self.where(node), by=self.scope()))
            route = kwarg(node, "route")
            if route is not None and name in EMITTERS:
                r = render(route)
                if literal(r):
                    self.emitted.append(dict(msg=EMITTERS[name], route=r, role="emits",
                                             where=self.where(node), by=self.scope()))
        self.generic_visit(node)


def scan(src):
    found, emitted = [], []
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in ("tests", "test", "__pycache__"))
        for fn in sorted(files):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, os.path.dirname(src))
            with open(path, "rb") as f:
                tree = ast.parse(f.read(), filename=path)
            Scanner(rel, found, emitted).visit(tree)
    return found, emitted


def shape(route):
    """Normalize placeholders so /ksn/{aid} and /ksn/{src} compare equal."""
    return re.sub(r"\{[^}]*\}", "{}", route)


def spec_hits(route, specdirs):
    """Find the route as a quoted or backticked literal, placeholders matching one segment."""
    if not literal(route) or route.strip("/") == "":
        return []
    body = "".join("[^/\"'`\\s]+" if part.startswith("{") else re.escape(part)
                   for part in re.split(r"(\{[^}]*\})", route) if part)
    pat = re.compile(r"[\"'`]" + body + r"[\"'`]")
    hits = []
    for name, d in specdirs:
        for root, _, files in os.walk(d):
            for fn in sorted(files):
                if not fn.endswith(".md"):
                    continue
                path = os.path.join(root, fn)
                with open(path, encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if pat.search(line):
                            hits.append(f"{name}:{os.path.relpath(path, d)}:{i}")
    return hits


def load_curated(path):
    if not path:
        return {}
    if tomllib is None:
        sys.exit("--curated needs Python 3.11+ (tomllib)")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return {(r["msg"], shape(r["route"])): r for r in data.get("route", [])}


def build(src, specdirs, curated):
    found, emitted = scan(src)
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
                        re.escape(k[1]).replace(r"\{\}", r"[^/]+"), x["route"]):
                    key = k
                    break
        e = entries.setdefault(key, dict(msg=x["msg"], route=x["route"], handled=[], emitted=[]))
        e["emitted"].append(f"{x['role']} {x['by']} ({x['where']})")
    for key, e in entries.items():
        e["spec"] = spec_hits(e["route"], specdirs) if specdirs else []
        c = curated.get(key, {})
        e["tier"] = c.get("tier", "unclassified")
        e["note"] = c.get("note", "")
    for key, c in curated.items():
        if key not in entries:
            entries[key] = dict(msg=c["msg"], route=c["route"], handled=[], emitted=[],
                                spec=[], tier=c.get("tier", "unclassified"),
                                note=c.get("note", ""), absent=True,
                                proposed=c.get("status") == "proposed")
    order = {"rpy": 0, "qry": 1, "exn": 2, "http": 3, "mbx": 4}
    return sorted(entries.values(), key=lambda e: (order.get(e["msg"], 9), e["route"]))


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
                items = sorted(set(items))
                s = "<br>".join(f"`{i}`" for i in items[:n])
                return s + (f"<br>+{len(items) - n} more" if len(items) > n else "")
            handled = cell(e["handled"]) or (
                "*proposed*" if e.get("proposed") else
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
    specs = [tuple(s.split("=", 1)) if "=" in s else (os.path.basename(s.rstrip("/")), s)
             for s in args.spec]
    entries = build(src, specs, load_curated(args.curated))
    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        print(md(entries, args.label or src))
    if args.curated:
        unclassified = [e for e in entries if e["tier"] == "unclassified"]
        missing = [e for e in entries if e.get("absent") and not e.get("proposed")]
        for label, rows in (("unclassified (in source, not in registry)", unclassified),
                            ("missing (in registry, not in source)", missing)):
            if rows:
                print(f"{len(rows)} route(s) {label}:", file=sys.stderr)
                for e in rows:
                    print(f"  {e['msg']} {e['route']}", file=sys.stderr)
        sys.exit(1 if unclassified or missing else 0)


if __name__ == "__main__":
    main()
