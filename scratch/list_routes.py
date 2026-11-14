import sys

sys.path.insert(0, "backend")
from app.main import app

def get_all_routes(app_or_router):
    out = []
    for route in app_or_router.routes:
        if hasattr(route, "routes"):
            out.extend(get_all_routes(route))
        elif hasattr(route, "path") and hasattr(route, "methods"):
            out.append((route.path, list(route.methods), route.name))
    return out

all_routes = get_all_routes(app)
print(f"Total endpoints found: {len(all_routes)}")
for path, methods, name in sorted(all_routes):
    methods_str = ",".join([m for m in methods if m not in ("HEAD", "OPTIONS")])
    if methods_str:
        print(f"{methods_str:<8} {path:<60} ({name})")
