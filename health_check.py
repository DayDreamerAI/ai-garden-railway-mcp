import os, sys, urllib.request

BASE = os.environ.get("BASE_URL")
if not BASE:
    print("Usage: BASE_URL=https://<service>.up.railway.app python health_check.py")
    sys.exit(2)

def fetch(path):
    url = BASE.rstrip("/") + path
    req = urllib.request.Request(url, headers={"Accept":"application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, r.getheader("content-type",""), r.read(2048)

code, ctype, data = fetch("/health")
print("HEALTH", code, ctype, data[:120])

try:
    code, ctype, data = fetch("/sse")
    print("SSE", code, ctype, data[:120])
except Exception as e:
    print("SSE OPEN ERROR:", e)
    sys.exit(1)

print("OK")
