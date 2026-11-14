"""
Sharon Art Studio class watcher.

Reads Sharon Art Studio's classes from SF Rec & Park's registration system
(ActiveNet) and emails you when:
  1. NEW classes appear (e.g. the next session's catalog gets posted), or
  2. a class you couldn't sign up for becomes available (registration
     opens, or a spot frees up in a full class).

Run modes (POLL_MODE env var):
  ""          one check (the regular schedule)
  "saturday"  registration-morning mode: checks every 30 seconds until
              10:30 AM Pacific
  "test"      the same polling loop for 2 minutes, for testing
State is saved in state.json between runs.
"""
import datetime
import json
import os
import smtplib
import sys
import time
import urllib.request
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
SITE_ID = "170"  # Sharon Art Studio's location ID in ActiveNet
URL = "https://anc.apm.activecommunities.com/sfrecpark/rest/activities/list?locale=en-US"
STATE_FILE = "state.json"
SATURDAY_END = (10, 30)  # stop polling at 10:30 AM Pacific
POLL_SECONDS = 30


def fetch_classes():
    """Return {class id: info} for every Sharon Art Studio class listed."""
    body = {"activity_search_pattern": {"site_ids": [SITE_ID], "activity_select_param": 2},
            "activity_transfer_pattern": {}}
    classes, page = {}, 1
    while True:
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
            "Content-Type": "application/json;charset=utf-8",
            "Accept": "application/json",
            "page_info": json.dumps({"order_by": "Date range", "page_number": page,
                                     "total_records_per_page": 50}),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130 Safari/537.36",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        if data["headers"]["response_code"] != "0000":
            raise RuntimeError(f"ActiveNet error: {data['headers']}")
        for a in data["body"]["activity_items"]:
            classes[str(a["id"])] = summarize(a)
        if page >= data["headers"]["page_info"]["total_page"]:
            return classes
        page += 1


def summarize(a):
    status = (a.get("urgent_message") or {}).get("status_description") or ""
    enroll = a.get("enroll_now") or {}
    try:
        openings = int(a.get("openings") or 0)
    except ValueError:
        openings = 0
    return {
        "name": a.get("name", "").strip(),
        "number": a.get("number", ""),
        "dates": a.get("date_range", ""),
        "days": a.get("days_of_week", ""),
        "time": a.get("time_range", ""),
        "instructor": a.get("instructor", ""),
        "openings": openings,
        "status": status,
        "enroll_label": enroll.get("label", ""),
        "registration_opens": a.get("activity_online_start_time", ""),
        "url": a.get("detail_url", "").split("?")[0],
    }


def can_sign_up(c):
    """True if the class looks open for online signup right now."""
    return (c["openings"] > 0 and c["status"].lower() != "full"
            and c["enroll_label"].lower().startswith("enroll"))


def describe(c):
    when = " ".join(x for x in [c["days"], c["time"]] if x)
    lines = [f"- {c['name']} (#{c['number']})",
             f"  {c['dates']}" + (f", {when}" if when else ""),
             f"  Instructor: {c['instructor'] or 'TBA'} | Openings: {c['openings']}"
             + (f" | {c['status']}" if c["status"] else "")]
    if c["registration_opens"]:
        lines.append(f"  Online registration opens: {c['registration_opens']}")
    lines.append(f"  {c['url']}")
    return "\n".join(lines)


def compare(old, new):
    """Return (new classes, newly available classes)."""
    added = [new[i] for i in new if i not in old]
    opened = [new[i] for i in new
              if i in old and can_sign_up(new[i]) and not can_sign_up(old[i])]
    return added, opened


def send_email(subject, body):
    user = os.environ["SMTP_USER"]
    to_addrs = [x.strip() for x in os.environ.get("NOTIFY_EMAIL", user).split(",") if x.strip()]
    msg = MIMEText(body)
    msg["Subject"], msg["From"], msg["To"] = subject, user, ", ".join(to_addrs)
    with smtplib.SMTP(os.environ.get("SMTP_HOST", "smtp.gmail.com"),
                      int(os.environ.get("SMTP_PORT", "587"))) as s:
        s.starttls()
        s.login(user, os.environ["SMTP_PASSWORD"])
        s.sendmail(user, to_addrs, msg.as_string())
    print(f"Emailed: {subject}")


def alert(added, opened):
    parts, subject = [], []
    if opened:
        subject.append(f"{len(opened)} open to sign up")
        parts.append("OPEN TO SIGN UP NOW:\n\n" + "\n\n".join(describe(c) for c in opened))
    if added:
        subject.append(f"{len(added)} new class{'es' if len(added) != 1 else ''}")
        parts.append("NEWLY POSTED CLASSES:\n\n" + "\n\n".join(describe(c) for c in added))
    parts.append("Register: https://anc.apm.activecommunities.com/sfrecpark/activity/search"
                 "?onlineSiteId=0&activity_keyword=Sharon%20Art%20Studio&viewMode=list")
    send_email("Sharon Art Studio: " + ", ".join(subject), "\n\n\n".join(parts))


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save_state(classes):
    with open(STATE_FILE, "w") as f:
        json.dump(classes, f, indent=1, sort_keys=True)


def check_once(state):
    new = fetch_classes()
    if state is None:
        print(f"First run: saved a baseline of {len(new)} classes, no email.")
        return new
    added, opened = compare(state, new)
    print(f"{datetime.datetime.now(PACIFIC):%a %I:%M:%S %p}: {len(new)} classes, "
          f"{len(added)} new, {len(opened)} newly open")
    if added or opened:
        alert(added, opened)
    # Keep classes that dropped off the list, so they don't count as "new"
    # if they reappear.
    return {**state, **new}


def main():
    if os.environ.get("TEST_EMAIL") == "true":
        send_email("Sharon Art Studio watcher: test email",
                   "If you're reading this, email alerts are working.")
        return
    mode = os.environ.get("POLL_MODE", "")
    state = load_state()
    if mode in ("saturday", "test"):
        now = datetime.datetime.now(PACIFIC)
        end = (now + datetime.timedelta(minutes=2) if mode == "test"
               else now.replace(hour=SATURDAY_END[0], minute=SATURDAY_END[1], second=0))
        while True:
            try:
                state = check_once(state)
                save_state(state)
            except Exception as e:  # keep polling through hiccups
                print(f"Check failed: {e}", file=sys.stderr)
            if datetime.datetime.now(PACIFIC) + datetime.timedelta(seconds=POLL_SECONDS) > end:
                break
            time.sleep(POLL_SECONDS)
    else:
        save_state(check_once(state))


if __name__ == "__main__":
    main()
