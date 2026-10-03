#!/usr/bin/env python3
"""Find out how a ControlByWeb device answers (stdlib only, never crashes).

  python probe.py 192.168.1.2 --user admin --password webrelay
  python probe.py 192.168.1.2 --password webrelay --path customState.json
  python probe.py 192.168.1.2 --password webrelay --set showUnits=1   # read-only
  python probe.py 192.168.1.2 --password webrelay --set relay1=1      # REAL command!

With no --path it tries state.json (400 series), then state.xml (older WebRelay),
then state.xml without a login, and reports what each one did.
"""
import argparse, base64, json, ssl, sys, urllib.error, urllib.parse, urllib.request

p = argparse.ArgumentParser()
p.add_argument("host")
p.add_argument("--port", type=int, default=80)
p.add_argument("--https", action="store_true")
p.add_argument("--user", default="admin")
p.add_argument("--password", default="")
p.add_argument("--path", help="file to read, e.g. customState.json (default: try several)")
p.add_argument("--set", help="e.g. relay1=1 (sends a real command!)")
a = p.parse_args()

ctx = ssl._create_unverified_context() if a.https else None
base = f"{'https' if a.https else 'http'}://{a.host}:{a.port}"
query = ("?" + urllib.parse.urlencode(dict([a.set.split("=", 1)]))) if a.set else ""


def fetch(path, with_auth=True):
    req = urllib.request.Request(base + "/" + path.lstrip("/") + query)
    if with_auth and a.password:
        tok = base64.b64encode(f"{a.user}:{a.password}".encode()).decode()
        req.add_header("Authorization", f"Basic {tok}")
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]
    except Exception as e:  # connection reset, timeout, refused ...
        return None, f"{type(e).__name__}: {e}"


def show(path, with_auth=True):
    label = f"GET {path}" + ("" if with_auth else " (no login)")
    status, body = fetch(path, with_auth)
    if status is None:
        print(f"[FAIL] {label} -> {body}")
        return False
    print(f"[{'OK' if status == 200 else 'HTTP ' + str(status)}] {label}")
    if status == 200:
        try:
            print(json.dumps(json.loads(body), indent=2))
        except ValueError:
            print(body)
        return True
    print("   ", body.strip()[:200])
    return False


try:
    if a.path:
        show(a.path)
    else:
        found = show("state.json") or show("state.xml") or (a.password and show("state.xml", False))
        if not found:
            print("\nNothing answered with data. Check: IP/port, that this is a ControlByWeb "
                  "device (open http://%s:%s in a browser), and the login." % (a.host, a.port))
except KeyboardInterrupt:
    pass
sys.exit(0)
