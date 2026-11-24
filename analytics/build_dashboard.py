"""
Builds dashboard.html (LinkedIn Command) from the sync's CSVs. Built 2026-11-15.

    python build_dashboard.py

Run at the end of every pull_linkedin.py run (full and --summary). Edit template.html,
never dashboard.html. Reads post_stats.csv, daily.csv, snapshots.csv, demographics.csv.
The headline panel is the link test Joshua asked for: do posts with "Read the article"
links get less reach than posts without?
"""
import csv
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")
OUT = os.path.join(HERE, "dashboard.html")


def rows(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v, kind=float):
    try:
        return kind(float(v))
    except (TypeError, ValueError):
        return None


def page_data():
    posts = []
    for r in rows("post_stats.csv"):
        imp = num(r.get("impressions"), int)
        if imp is None:
            continue
        posts.append({
            "date": r["publish_date"], "url": r["post_url"], "imp": imp,
            "eng": num(r.get("engagements"), int), "rate": num(r.get("eng_rate")),
            "age": num(r.get("age_days"), int) or 0, "weekday": r.get("weekday", ""),
            "pillar": r.get("pillar", ""), "topic": r.get("topic", ""),
            "link": r.get("has_link", ""), "source": r.get("source", ""),
        })
    posts.sort(key=lambda p: p["date"])

    # one snapshot per window end (a short and a long export can end the same day: keep the longer)
    by_end = {}
    for s in rows("snapshots.csv"):
        e = s["window_end"]
        if e not in by_end or s["window_start"] < by_end[e]["window_start"]:
            by_end[e] = s
    snaps = [{"start": s["window_start"], "end": e, "impressions": num(s["impressions"], int) or 0,
              "reached": num(s["members_reached"], int) or 0, "followers": num(s["total_followers"], int) or 0}
             for e, s in sorted(by_end.items())]

    daily = [{"date": r["date"], "imp": num(r["impressions"], int) or 0,
              "eng": num(r["engagements"], int) or 0, "nf": num(r["new_followers"], int) or 0}
             for r in sorted(rows("daily.csv"), key=lambda r: r["date"])]

    demos = rows("demographics.csv")
    demo_end = max((d["window_end"] for d in demos if d["group"] == "content"), default="")
    demo = [{"category": d["category"], "value": d["value"], "pct": num(d["pct"]) or 0}
            for d in demos if d["group"] == "content" and d["window_end"] == demo_end]

    # writing eras from ../versions.csv (push_workflow.py adds a row per push). A process-only
    # version (buttons, emails) stays inside its era and shows as an "Also" note.
    eras = []
    vpath = os.path.join(os.path.dirname(HERE), "versions.csv")
    if os.path.exists(vpath):
        with open(vpath, newline="", encoding="utf-8") as f:
            for v in csv.DictReader(f):
                e = next((x for x in eras if x["era"] == v["era"]), None)
                if not e:
                    e = {"era": v["era"], "short": v.get("label") or v["era"], "start": v["first_post"],
                         "end": "", "changes": [], "process": []}
                    eras.append(e)
                (e["process"] if v["kind"] == "process" else e["changes"]).append(v["change"])
    eras.sort(key=lambda e: e["start"])
    for a, b in zip(eras, eras[1:]):
        prev_day = datetime.fromisoformat(b["start"]).toordinal() - 1
        a["end"] = datetime.fromordinal(prev_day).date().isoformat()
    for p in posts:
        p["era"] = ""
        if p["source"] == "workflow":
            for e in eras:
                if e["start"] <= p["date"]:
                    p["era"] = e["era"]

    link_dates = [p["date"] for p in posts if p["link"] == "yes"]
    return {
        "built": datetime.now().strftime("%d %b %Y %H:%M"),
        "posts": posts, "daily": daily, "snaps": snaps,
        "snap": snaps[-1] if snaps else {"start": "", "end": "", "impressions": 0, "reached": 0, "followers": 0},
        "prevSnap": snaps[-2] if len(snaps) > 1 else None,
        "demo": demo, "demoEnd": demo_end, "eras": eras,
        "linkSince": min(link_dates) if link_dates else "",
    }


def build():
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    data = json.dumps(page_data(), ensure_ascii=False).replace("</", "<\\/")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html.replace("/*DATA*/null", data, 1))
    return OUT


if __name__ == "__main__":
    print(f"Dashboard: rebuilt {build()}")
