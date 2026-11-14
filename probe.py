"""One-off test: can GitHub's servers reach SF Rec & Park's ActiveNet API?"""
import json, urllib.request, datetime

URL = "https://anc.apm.activecommunities.com/sfrecpark/rest/activities/list?locale=en-US"
BODY = {"activity_search_pattern": {"site_ids": ["170"], "activity_select_param": 2},
        "activity_transfer_pattern": {}}

req = urllib.request.Request(URL, data=json.dumps(BODY).encode(), method="POST", headers={
    "Content-Type": "application/json;charset=utf-8",
    "page_info": json.dumps({"order_by": "Date range", "page_number": 1, "total_records_per_page": 50}),
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
    "Accept": "application/json",
})
lines = [f"run at {datetime.datetime.utcnow().isoformat()}Z"]
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
        items = data["body"]["activity_items"]
        lines.append(f"PASS http={r.status} code={data['headers']['response_code']} classes={len(items)}")
        for a in items[:5]:
            lines.append(f"  {a['name']} | {a['date_range']} | openings={a['openings']}")
except Exception as e:
    lines.append(f"FAIL {type(e).__name__}: {e}")
out = "\n".join(lines)
print(out)
open("probe-result.txt", "w").write(out + "\n")
