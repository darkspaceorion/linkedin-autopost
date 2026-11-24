"""
LinkedIn Sunday sync.

    1. Finds the newest LinkedIn analytics export (.xlsx) in My Drive/LinkedIn/,
       then Downloads. Copies it to exports/ and moves the original to _done/.
    2. Reads the five sheets: overall totals, daily impressions, per-post numbers,
       followers and viewer demographics.
    3. If N8N_API_KEY is set, pulls li_posts (weekday, pillar, topic, news link) and
       the real post time from the "Post to LinkedIn" node in recent executions.
       Post times are saved to posted_times.csv, because n8n prunes old executions.
    4. Joins posts to li_posts by date, updates the CSVs, writes weekly-report.md and
       prints a === LINKEDIN SYNC === block.

    python pull_linkedin.py            full run
    python pull_linkedin.py --summary  rebuild the report from the CSVs only

LinkedIn counts a post's impressions inside the export's date range only, not since it went
up. So a post's numbers are only kept when the range starts on or before its publish date.
Exporting "Past 90 days" each Sunday keeps every post's count whole until it is 12 weeks old
(switched from 28 days on 2026-11-15).
"""
import csv
import glob
import json
import os
import re
import shutil
import sys
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(HERE, "exports")
STATS = os.path.join(HERE, "post_stats.csv")
TIMES = os.path.join(HERE, "posted_times.csv")
DAILY = os.path.join(HERE, "daily.csv")
SNAPS = os.path.join(HERE, "snapshots.csv")
DEMOS = os.path.join(HERE, "demographics.csv")
REPORT = os.path.join(HERE, "weekly-report.md")
DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")

# Desktop mirrors Drive under the user folder, the laptop under G:.
DRIVES = [os.path.join(os.path.expanduser("~"), "My Drive", "LinkedIn"), r"G:\My Drive\LinkedIn"]
DOWNLOAD_NAMES = ("aggregateanalytics", "content_", "linkedin")

N8N = os.environ.get("N8N_URL", "https://your-instance.app.n8n.cloud").rstrip("/") + "/api/v1"
WORKFLOW = os.environ.get("LI_WORKFLOW_ID", "<workflow-id>")  # LinkedIn Daily Post
POSTS_TABLE = "<li_posts-table-id>"   # li_posts
POST_NODE = "Post to LinkedIn"
LOG_NODE = "Log draft"

STAT_COLS = ["post_url", "publish_date", "impressions", "engagements", "eng_rate", "measured_to",
             "age_days", "weekday", "pillar", "topic", "has_link", "posted_at", "source", "last_export"]
MIN_GROUP = 4   # fewer posts than this in a group and the report says "too early"
MIN_AGE = 3     # posts younger than this many days stay out of the averages
V2_LIVE = "2026-10-12"   # li_posts also holds the old workflow's posts from before this date
DEMO_SHOW = ("Industry", "Seniority", "Job title")


def chicago(utc):
    """UTC to Chicago time. Windows Python ships no tz database, so US daylight time is
    worked out by hand: 2nd Sunday of March to 1st Sunday of November, 2am local."""
    def sunday(month, nth):
        d = datetime(utc.year, month, 1, tzinfo=timezone.utc)
        return d + timedelta(days=(6 - d.weekday()) % 7 + 7 * (nth - 1))
    dst = sunday(3, 2) + timedelta(hours=8) <= utc < sunday(11, 1) + timedelta(hours=7)
    return utc.astimezone(timezone(timedelta(hours=-5 if dst else -6)))


# ---------- 1. find the export ----------

def find_export():
    """Newest .xlsx in a Drive drop folder, else a LinkedIn-looking one in Downloads."""
    for d in DRIVES:
        files = [f for f in glob.glob(os.path.join(d, "*.xlsx")) if not os.path.basename(f).startswith("~$")]
        if files:
            return max(files, key=os.path.getmtime), d
    files = [f for f in glob.glob(os.path.join(DOWNLOADS, "*.xlsx"))
             if os.path.basename(f).lower().startswith(DOWNLOAD_NAMES)]
    if files:
        return max(files, key=os.path.getmtime), DOWNLOADS
    return None, None


def archive(path, src_dir):
    os.makedirs(EXPORTS, exist_ok=True)
    shutil.copy2(path, os.path.join(EXPORTS, os.path.basename(path)))
    if src_dir and src_dir != DOWNLOADS:
        done = os.path.join(src_dir, "_done")
        os.makedirs(done, exist_ok=True)
        shutil.move(path, os.path.join(done, os.path.basename(path)))


# ---------- 2. read the export ----------

def to_date(v):
    if isinstance(v, datetime):
        return v.date().isoformat()
    s = str(v or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def to_num(v):
    try:
        return int(float(str(v).replace(",", "").replace("%", "")))
    except (TypeError, ValueError):
        return None


def sheet(wb, name):
    for ws in wb.worksheets:
        if ws.title.strip().upper() == name:
            return [list(r) for r in ws.iter_rows(values_only=True)]
    return []


def read_posts(rows):
    """TOP POSTS holds two tables side by side (by engagements, by impressions),
    so each 'Post URL' header is read as its own block."""
    posts, saw_eng = {}, False
    for i, row in enumerate(rows):
        heads = [str(c or "").strip().lower() for c in row]
        for j in [j for j, h in enumerate(heads) if h == "post url"]:
            block = heads[j:j + 4]
            date_col = next((j + k for k, h in enumerate(block) if "date" in h), None)
            metrics = {j + k: h for k, h in enumerate(block) if h in ("impressions", "engagements")}
            saw_eng |= "engagements" in metrics.values()
            for r in rows[i + 1:]:
                url = str(r[j] or "").strip() if j < len(r) else ""
                if not url.startswith("http"):
                    continue
                p = posts.setdefault(url, {"post_url": url})
                if date_col is not None and not p.get("publish_date"):
                    p["publish_date"] = to_date(r[date_col])
                for c, name in metrics.items():
                    n = to_num(r[c]) if c < len(r) else None
                    if n is not None:
                        p[name] = n
    if saw_eng:   # the engagements table only lists posts with at least one
        for p in posts.values():
            p.setdefault("engagements", 0)
    return posts


def read_export(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {"name": os.path.basename(path), "window": ("", ""), "totals": {}, "daily": {}, "demos": []}

    disc = sheet(wb, "DISCOVERY")
    for r in disc:
        k = str(r[0] or "").strip().lower()
        if k == "overall performance" and len(r) > 1:
            ds = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", str(r[1]))
            if len(ds) == 2:
                out["window"] = (to_date(ds[0]), to_date(ds[1]))
        elif k in ("impressions", "members reached") and len(r) > 1:
            out["totals"][k.replace(" ", "_")] = to_num(r[1])
    if not out["window"][0]:   # fall back to the dates in the file name
        ds = re.findall(r"\d{4}-\d{2}-\d{2}", out["name"])
        if len(ds) == 2:
            out["window"] = tuple(ds)

    for r in sheet(wb, "ENGAGEMENT")[1:]:
        d = to_date(r[0]) if r else ""
        if d:
            out["daily"].setdefault(d, {})["impressions"] = to_num(r[1])
            out["daily"][d]["engagements"] = to_num(r[2]) if len(r) > 2 else None
    for r in sheet(wb, "FOLLOWERS"):
        k = str(r[0] or "")
        if k.lower().startswith("total followers") and len(r) > 1:
            out["totals"]["total_followers"] = to_num(r[1])
        elif to_date(k) and len(r) > 1:
            out["daily"].setdefault(to_date(k), {})["new_followers"] = to_num(r[1])

    for name, tag in (("AUDIENCE DEMOGRAPHICS", "audience"), ("CONTENT DEMOGRAPHICS", "content")):
        for r in sheet(wb, name)[1:]:
            if r and r[0] and len(r) > 2:
                out["demos"].append({"group": tag, "category": str(r[0]).strip(),
                                     "value": str(r[1]).strip(), "pct": to_num(r[2])})

    out["posts"] = read_posts(sheet(wb, "TOP POSTS"))
    wb.close()   # read-only mode holds the file open, which blocks the move to _done
    return out


# ---------- 3. n8n ----------

def n8n_get(path):
    req = urllib.request.Request(N8N + path, headers={"X-N8N-API-KEY": os.environ["N8N_API_KEY"],
                                                      "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def pull_li_posts():
    rows, cursor = [], None
    while True:
        q = f"/data-tables/{POSTS_TABLE}/rows?limit=250" + (f"&cursor={cursor}" if cursor else "")
        res = n8n_get(q)
        rows += res["data"] if isinstance(res, dict) else res
        cursor = res.get("nextCursor") if isinstance(res, dict) else None
        if not cursor:
            return rows


def pull_post_times(days=35):
    """Real post time per post date, from the Post node's start time in each run."""
    found, cursor = {}, None
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for _ in range(10):
        q = f"/executions?workflowId={WORKFLOW}&status=success&includeData=true&limit=25"
        res = n8n_get(q + (f"&cursor={cursor}" if cursor else ""))
        old = False
        for ex in res.get("data", []):
            started = ex.get("startedAt") or ""
            if started and datetime.fromisoformat(started.replace("Z", "+00:00")) < cutoff:
                old = True
            run = (((ex.get("data") or {}).get("resultData") or {}).get("runData")) or {}
            if POST_NODE not in run or LOG_NODE not in run:
                continue
            try:
                post_date = run[LOG_NODE][0]["data"]["main"][0][0]["json"]["post_date"]
            except (KeyError, IndexError, TypeError):
                continue
            ms = run[POST_NODE][0].get("startTime")
            if ms:
                at = chicago(datetime.fromtimestamp(ms / 1000, timezone.utc))
                found[post_date] = {"post_date": post_date, "posted_at": at.strftime("%Y-%m-%d %H:%M"),
                                    "execution_id": ex.get("id", "")}
        cursor = res.get("nextCursor")
        if old or not cursor:
            break
    return found


# ---------- 4. store ----------

def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def save_times(new):
    times = {r["post_date"]: r for r in read_csv(TIMES)}
    times.update(new)
    write_csv(TIMES, sorted(times.values(), key=lambda r: r["post_date"]),
              ["post_date", "posted_at", "execution_id"])
    return times


def save_side_tables(ex):
    start, end = ex["window"]
    daily = {r["date"]: r for r in read_csv(DAILY)}
    for d, v in ex["daily"].items():
        row = daily.setdefault(d, {"date": d})
        row.update({k: "" if n is None else n for k, n in v.items()})
    write_csv(DAILY, sorted(daily.values(), key=lambda r: r["date"]),
              ["date", "impressions", "engagements", "new_followers"])

    snaps = [r for r in read_csv(SNAPS) if r["export"] != ex["name"]]
    snaps.append({"export": ex["name"], "window_start": start, "window_end": end, **ex["totals"]})
    write_csv(SNAPS, sorted(snaps, key=lambda r: r["window_end"]),
              ["export", "window_start", "window_end", "impressions", "members_reached", "total_followers"])

    demos = [r for r in read_csv(DEMOS) if r["window_end"] != end]
    demos += [{"window_end": end, **d} for d in ex["demos"]]
    write_csv(DEMOS, demos, ["window_end", "group", "category", "value", "pct"])


def merge(ex, li_rows, times):
    """Keep a post's numbers only when the window covers it from day one. A later window wins."""
    start, end = ex["window"]
    stats = {r["post_url"]: r for r in read_csv(STATS)}
    posted = defaultdict(list)
    for r in li_rows:
        if str(r.get("status", "")).startswith("posted"):
            posted[str(r.get("post_date", ""))[:10]].append(r)
    partial = 0
    for url, p in ex["posts"].items():
        pd = p.get("publish_date", "")
        if not pd or (start and pd < start):
            partial += 1
            continue
        row = stats.get(url, {})
        if row.get("measured_to", "") > end:
            continue
        row.update(post_url=url, publish_date=pd, impressions=p.get("impressions", ""),
                   engagements=p.get("engagements", ""), measured_to=end, last_export=ex["name"])
        row["age_days"] = (date.fromisoformat(end) - date.fromisoformat(pd)).days if end else ""
        imp, eng = to_num(row["impressions"]), to_num(row["engagements"])
        row["eng_rate"] = f"{eng / imp * 100:.1f}" if imp and eng is not None else ""
        match = posted.get(pd, [])
        if len(match) == 1:
            m = match[0]
            row.update(weekday=m.get("weekday", ""), pillar=m.get("pillar", ""), topic=m.get("topic", ""),
                       has_link="yes" if "Read the article" in (m.get("draft") or "") else "no",
                       source="workflow")
        elif li_rows and not row.get("source"):
            row["source"] = "manual"
        t = times.get(pd)
        if t and row.get("source") == "workflow":
            row["posted_at"] = t["posted_at"]
        stats[url] = row
    out = sorted(stats.values(), key=lambda r: r.get("publish_date", ""))
    write_csv(STATS, out, STAT_COLS)
    return out, partial


# ---------- 5. report ----------

def slot(posted_at):
    if not posted_at:
        return ""
    h, m = map(int, posted_at[11:16].split(":"))
    mins = h * 60 + m
    return "8:00-8:44" if 480 <= mins < 525 else "8:45-9:45" if 525 <= mins <= 585 else "other"


def eras():
    """Writing eras from ../versions.csv as [(first_post, era, label)], oldest first.
    A process-only version (--process) stays inside its era."""
    path = os.path.join(os.path.dirname(HERE), "versions.csv")
    out = {}
    for v in read_csv(path) if os.path.exists(path) else []:
        if v["era"] not in out:
            out[v["era"]] = (v["first_post"], v["era"], v.get("label") or v["era"])
    return sorted(out.values())


def era_of(publish_date, era_list):
    hit = ""
    for start, era, label in era_list:
        if start <= publish_date:
            hit = f"{era} {label}"
    return hit


def group_lines(rows, key, label, in_order=False):
    groups = defaultdict(list)
    for r in rows:
        k = key(r)
        if k and to_num(r.get("impressions")) is not None:
            groups[k].append(r)
    if not groups:
        return []
    lines = [f"By {label}:"]
    order = (lambda kv: kv[0]) if in_order else (lambda kv: -sum(to_num(r["impressions"]) for r in kv[1]) / len(kv[1]))
    for k, g in sorted(groups.items(), key=order):
        imp = sum(to_num(r["impressions"]) for r in g)
        eng = sum(to_num(r.get("engagements")) or 0 for r in g)
        avg = imp / len(g)
        rate = f", {eng / imp * 100:.1f}% engagement" if imp else ""
        note = "  (too early)" if len(g) < MIN_GROUP else ""
        lines.append(f"  {k}: {avg:,.0f} avg impressions{rate}, {len(g)} post{'s' if len(g) != 1 else ''}{note}")
    return lines


def report(notes):
    stats, snaps, daily = read_csv(STATS), read_csv(SNAPS), read_csv(DAILY)
    snap = snaps[-1] if snaps else {}
    start, end = snap.get("window_start", ""), snap.get("window_end", "")
    out = ["=== LINKEDIN SYNC ===", *notes]
    if snap:
        new_f = sum(to_num(r.get("new_followers")) or 0 for r in daily if start <= r["date"] <= end)
        out.append(f"{start} to {end}: {to_num(snap.get('impressions')) or 0:,} impressions, "
                   f"{to_num(snap.get('members_reached')) or 0:,} people reached, "
                   f"{snap.get('total_followers') or '?'} followers (+{new_f})")
    wf = [r for r in stats if r.get("source") == "workflow"]
    out += [f"Posts on file: {len(stats)} ({len(wf)} matched to the workflow)", ""]

    week_start = (date.fromisoformat(end) - timedelta(days=6)).isoformat() if end else ""
    week = [r for r in stats if r.get("publish_date", "") >= week_start]
    if week:
        out.append(f"Posts from {week_start} on:")
        for r in week:
            tag = r.get("pillar") or r.get("source") or "?"
            at = f" at {r['posted_at'][11:]}" if r.get("posted_at") else ""
            rate = f", {r['eng_rate']}%" if r.get("eng_rate") else ""
            out.append(f"  {r['publish_date']} {r.get('weekday', '')[:3]} [{tag}]{at}, day {r.get('age_days', '?')}: "
                       f"{to_num(r.get('impressions')) or 0:,} impressions, {r.get('engagements') or 0} engagements{rate}")
        out.append("")
    settled = [r for r in wf if (to_num(r.get("age_days")) or 0) >= MIN_AGE]
    if len(settled) < len(wf):
        out.append(f"Averages leave out {len(wf) - len(settled)} post(s) under {MIN_AGE} days old.")
    era_list = eras()
    if era_list:
        out += group_lines(settled, lambda r: era_of(r["publish_date"], era_list), "version (writing era, see versions.csv)", in_order=True)
    else:
        out += group_lines(settled, lambda r: "old workflow" if r["publish_date"] < V2_LIVE else "v2", "workflow")
    out += group_lines(settled, lambda r: r.get("pillar"), "pillar")
    out += group_lines(settled, lambda r: slot(r.get("posted_at")), "post time")
    out += group_lines(settled, lambda r: r.get("has_link"), "article link")

    demos = [d for d in read_csv(DEMOS) if d["window_end"] == end and d["group"] == "content"]
    if demos:
        out += ["", "Who saw your posts:"]
        for cat in DEMO_SHOW:
            top = [d for d in demos if d["category"] == cat][:3]
            if top:
                out.append(f"  {cat}: " + ", ".join(f"{d['value']} {d['pct']}%" for d in top))
    if len(wf) < 20:
        out += ["", f"Sample is small ({len(wf)} matched posts). Read patterns as hints, not findings."]
    text = "\n".join(out)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(f"# LinkedIn weekly report\n\nBuilt {chicago(datetime.now(timezone.utc)):%Y-%m-%d %H:%M} Chicago.\n\n```\n{text}\n```\n")
    print(text)
    try:  # the dashboard never blocks the sync
        import build_dashboard
        build_dashboard.build()
        print("Dashboard: rebuilt")
    except Exception as e:
        print(f"Dashboard: FAILED ({e})")


def main():
    if "--summary" in sys.argv:
        report([])
        return
    path, src_dir = find_export()
    if not path:
        sys.exit("No LinkedIn export found in My Drive/LinkedIn/ or Downloads. "
                 "Export it from Profile > Analytics > Post impressions > Export.")
    name = os.path.basename(path)
    if src_dir == DOWNLOADS and os.path.exists(os.path.join(EXPORTS, name)):
        sys.exit(f"{name} is already imported. Export a fresh one.")
    ex = read_export(path)
    if not ex["posts"]:
        sys.exit(f"{name} has no post rows. Make sure it is the Post impressions export, not the data archive.")
    archive(path, src_dir)
    save_side_tables(ex)
    li_rows, times = [], {r["post_date"]: r for r in read_csv(TIMES)}
    notes = []
    if os.environ.get("N8N_API_KEY"):
        try:
            li_rows = pull_li_posts()
            times = save_times(pull_post_times())
            notes.append(f"n8n: {len(li_rows)} li_posts rows, {len(times)} post times on file")
        except Exception as e:  # report and carry on with the export alone
            notes.append(f"WARNING: n8n not reachable ({e}). Stats saved without pillar or post time.")
    else:
        notes.append("WARNING: no N8N_API_KEY on this computer. Stats saved without pillar or post time.")
    _, partial = merge(ex, li_rows, times)
    notes.insert(0, f"Export: {name}, {len(ex['posts'])} posts read, {len(ex['posts']) - partial} counted in full"
                    + (f", {partial} older than the window skipped" if partial else ""))
    report(notes)


if __name__ == "__main__":
    main()
