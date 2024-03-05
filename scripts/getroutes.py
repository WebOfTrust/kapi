import os
import re
import sys

def get_routes(folder):
    routes = {}
    folder = os.path.abspath(folder)
    for root, _, files in os.walk(folder):
        for file_name in files:
            if file_name.endswith('.py') and 'test_' not in file_name:
                path = os.path.join(root, file_name)
                relpath = os.path.relpath(path, folder)
                scan_file(path, relpath, routes)
    return routes

ROUTE_REGEX = re.compile(r'(?:\W|_)routes?(?:\s*=\s*"([^"]*)"(?:\s+if.*\Welse\s+"([^"]*)")?|s*[(\[]\s*"([^"]*)")')

def scan_file(path, relpath, routes):
    with open(path, "rt") as f:
        lines = f.readlines()
        for i in range(len(lines)):
            line = lines[i].rstrip()
            m = ROUTE_REGEX.search(line)
            if m:
                for i in range(1, 4):
                    key = m.group(i)
                    if key:
                        if key not in routes:
                            routes[key] = []
                        fragment = line[m.start() + 1:]
                        j = fragment.find(',')
                        if j > -1:
                            fragment = fragment[:j].strip()
                        routes[key].append((relpath, i + 1, fragment))

def print_routes(routes):
    keys = sorted([k for k in routes.keys()], key=lambda x: x[1:] if x[0] == '/' else x)
    unique_paths = set()
    for key in keys:
        matches = routes[key]
        print(f"{key}: {len(matches)}")
        for match in matches:
            print(f"    {match[0]}({match[1]}): {match[2]}")
            unique_paths.add(match[0])
    print(f"----\n{len(keys)} unique routes in {len(unique_paths)} unique files")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) == 2 else None
    if not target:
        print("getroutes <folder>")
    routes = get_routes(target)
    print_routes(routes)