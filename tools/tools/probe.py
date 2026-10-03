#!/usr/bin/env python3
"""Dump /state.json from a ControlByWeb 400 Series device (stdlib only).

  python3 probe.py 192.168.1.2
  python3 probe.py 192.168.1.2 --user admin --password webrelay
  python3 probe.py 192.168.1.2 --path customState.json
  python3 probe.py 192.168.1.2 --set relay1=1      # optional: test a command
"""
import argparse, base64, json, ssl, urllib.parse, urllib.request

p = argparse.ArgumentParser()
p.add_argument("host")
p.add_argument("--port", type=int, default=80)
p.add_argument("--https", action="store_true")
p.add_argument("--user", default="admin")
p.add_argument("--password", default="")
p.add_argument("--path", default="state.json", help="file to read, e.g. customState.json")
p.add_argument("--set", help="e.g. relay1=1 (sends a real command!)")
a = p.parse_args()

url = f"{'https' if a.https else 'http'}://{a.host}:{a.port}/{a.path.lstrip('/')}"
if a.set:
    url += "?" + urllib.parse.urlencode(dict([a.set.split("=", 1)]))
req = urllib.request.Request(url)
if a.password:
    tok = base64.b64encode(f"{a.user}:{a.password}".encode()).decode()
    req.add_header("Authorization", f"Basic {tok}")
ctx = ssl._create_unverified_context() if a.https else None
with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
    print("HTTP", r.status)
    body = r.read().decode()
try:
    print(json.dumps(json.loads(body), indent=2))
except ValueError:
    print(body)
