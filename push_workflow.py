"""Pushes workflow-v2.json to the live LinkedIn Daily Post workflow and publishes it as a named version.

    python push_workflow.py "LinkedIn Daily Post v7" "What changed, in plain English."         dry run
    python push_workflow.py "LinkedIn Daily Post v7" "What changed, in plain English." --go    push
    add --process when the change doesn't touch what gets written or when it posts
    (buttons, emails, logging): it stays inside the current writing era on the dashboard.

Steps: copies each node's id and webhookId from live by
node name (or drafts waiting for approval lose their buttons), backs up live to backups/, saves a draft with
?publishIfActive=false, then publishes it with the version name and notes. Dry run stops before
the save. Needs N8N_API_KEY. Run python build_workflow.py first.

After a good publish (added 2026-11-15) it saves snapshots/<version>/ (the live workflow as published,
build_workflow.py and workflow-v2.json) and adds a row to versions.csv, which the LinkedIn dashboard
reads to compare versions. To revert: push the snapshot's workflow back, together in chat.
"""
import csv
import json
import os
import shutil
import sys
from datetime import date, timedelta
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
BASE = os.environ.get("N8N_URL", "https://your-instance.app.n8n.cloud").rstrip("/") + "/api/v1"
WID = os.environ.get("LI_WORKFLOW_ID", "<workflow-id>")   # LinkedIn Daily Post v2


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 headers={"X-N8N-API-KEY": os.environ["N8N_API_KEY"],
                                          "Content-Type": "application/json", "Accept": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:800]}")


def main():
    args = [a for a in sys.argv[1:] if a not in ("--go", "--process")]
    if len(args) != 2:
        sys.exit(__doc__)
    name, notes = args
    if not os.environ.get("N8N_API_KEY"):
        sys.exit("No N8N_API_KEY on this computer.")

    live = call("GET", f"/workflows/{WID}")
    print(f"Live: {len(live['nodes'])} nodes")
    new =json.loads((HERE / "workflow-v2.json").read_text(encoding="utf-8"))
    by_name = {n["name"]: n for n in live["nodes"]}
    added = []
    for n in new["nodes"]:
        old = by_name.get(n["name"])
        if not old:
            added.append(n["name"])
            continue
        n["id"] = old["id"]
        if old.get("webhookId"):
            n["webhookId"] = old["webhookId"]
    dropped = [k for k in by_name if k not in {n["name"] for n in new["nodes"]}]
    print(f"New nodes: {added or 'none'}")
    print(f"Dropped from live: {dropped or 'none'}")
    if "--go" not in sys.argv:
        print("Dry run only. Add --go to push.")
        return

    backup = HERE / "backups" / f"workflow-v2-live.{datetime.now():%Y%m%d-%H%M}-pre-{name.split()[-1]}.json"
    backup.parent.mkdir(exist_ok=True)
    backup.write_text(json.dumps(live, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Live backup: {backup.name}")
    saved = call("PUT", f"/workflows/{WID}?publishIfActive=false",
                 {"name": live["name"], "nodes": new["nodes"], "connections": new["connections"],
                  "settings": new["settings"]})
    call("POST", f"/workflows/{WID}/publish",
         {"versionId": saved["versionId"], "name": name, "description": notes})
    check = call("GET", f"/workflows/{WID}")
    ok = check.get("activeVersionId") == check.get("versionId")
    print(f"Published as {name}. Active: {check['active']}. Live version matches: {ok}. Nodes: {len(check['nodes'])}")
    if ok:
        log_version(name, notes, check, "--process" in sys.argv)


def log_version(name, notes, live, process):
    """Snapshot the published workflow and add it to versions.csv for the dashboard."""
    ver = name.split()[-1]
    snap = HERE / "snapshots" / ver
    snap.mkdir(parents=True, exist_ok=True)
    (snap / "workflow-live.json").write_text(json.dumps(live, indent=1, ensure_ascii=False), encoding="utf-8")
    for f in ("build_workflow.py", "workflow-v2.json"):
        shutil.copy(HERE / f, snap / f)
    log = HERE / "versions.csv"
    with open(log, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    era = rows[-1]["era"] if process and rows else ver
    first = date.today() + timedelta(days=1)          # the 7am draft today was written before this push
    while first.weekday() >= 5:
        first += timedelta(days=1)
    with open(log, "a", newline="", encoding="utf-8") as fh:
        label = " ".join(notes.split()[:3]).rstrip(".,:;")   # short name for the dashboard picker, edit by hand if clumsy
        csv.writer(fh).writerow([ver, "process" if process else "writing", era, label, date.today().isoformat(),
                                 first.isoformat(), notes, f"snapshots/{ver}/workflow-live.json"])
    print(f"Snapshot: snapshots/{ver}/. versions.csv: {ver} ({'process, stays in era ' + era if process else 'new writing era'}), "
          f"first post {first}.")


if __name__ == "__main__":
    main()
