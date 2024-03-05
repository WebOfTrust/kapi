import os
import re
import sys

FOLDER_TO_SCAN = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))

def get_routes(folder):
    routes = {}
    folder = os.path.normpath(os.path.abspath(folder))
    for root, dirs, files in os.walk(FOLDER_TO_SCAN):
        for file_name in files:
            if file_name.endswith('.py') and 'test_' not in file_name:
                path = os.path.join(root, file_name)
                relpath = os.path.relpath(path, folder)
                scan_file(path, relpath, routes)
    return routes

ROUTE_REGEX = re.compile(r'\Wroute(?:\s*=\s*"([^"]*)"|s*\[\s*"([^"]*)"\])')

def scan_file(path, relpath, routes):
    with open(path, "rt") as f:
        lines = f.readlines()
        for i in range(len(lines)):
            line = lines[i].rstrip()
            m = ROUTE_REGEX.search(line)
            if m:
                key = m.group(1)
                if not key:
                    key = m.group(2)
                if not key:
                    continue
                if key not in routes:
                    routes[key] = []
                fragment = line[m.start() + 1:]
                j = fragment.find(',')
                if j > -1:
                    fragment = fragment[:j].strip()
                routes[key].append((relpath, i + 1, fragment))

def print_routes(routes):
    keys = sorted([k for k in routes.keys()], key=lambda x: x[1:] if x[0] == '/' else x)
    for key in keys:
        matches = routes[key]
        print(f"{key}: {len(matches)}")
        for match in matches:
            print(f"    {match[0]}({match[1]}): {match[2]}") 

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) == 2 else None
    if not target:
        print("getroutes <folder>")
    routes = get_routes(target)
    print_routes(routes)