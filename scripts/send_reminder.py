"""Daily study reminder, run by .github/workflows/reminder.yml.

Emails the day after the last finished day (docs/data/progress.json). Skips
sending if a day was already finished today (WIB) or the plan is complete.

Env: GMAIL_USER, GMAIL_APP_PASSWORD, REMINDER_TO (optional), SITE_URL (optional),
     DRY_RUN=1 writes the HTML to reminder-preview.html instead of sending.
"""
import html
import json
import os
import re
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIB = timezone(timedelta(hours=7))
SITE = os.environ.get("SITE_URL", "https://inayarhmns.github.io/PRML/")
TO = os.environ.get("REMINDER_TO", "inaya.rahmanisa@gmail.com")

CAT_COLOR = {"lc": "#ffa116", "ml": "#3e9bff", "py": "#00b8a3", "log": "#8b929c", "math": "#8b5cf6"}
TIPS = [
    "Practice before reviewing: start every block with a closed-book attempt.",
    "Rescue loop: try 5–10 min → find the exact gap → read only that subsection → close it → solve a similar one.",
    "Log errors, not notes: prompt, wrong reasoning, correct principle, retry date.",
    "Retest mistakes the next day, three days later, and in the final week.",
    "Readiness means solving a fresh question without notes, not \"this looks familiar\".",
    "Protect your energy: 80–90 minute blocks with real breaks.",
]


def cat_class(cat):
    c = cat.lower()
    if "leetcode" in c:
        return "lc"
    if re.search(r"python|implementation|programming|algorithm|control", c):
        return "py"
    if re.search(r"log|mark|review|plan|cool|check|break", c):
        return "log"
    if re.search(r"ml|neural|classification|pca|cnn|cv|convolution|d2l|image|representation|geometry", c):
        return "ml"
    return "math"


def strip_links(text):
    return re.sub(r"\[([^\]]+)\]\((https?:[^)\s]+)\)", r'<a href="\2" style="color:#3e9bff;text-decoration:none">\1</a>',
                  html.escape(text, quote=False))


def pick_day(plan, progress, now):
    finished = progress.get("finished", {})
    if any(datetime.fromisoformat(v).astimezone(WIB).date() == now.date() for v in finished.values()):
        return None, "a day was already finished today"
    n = max(map(int, finished), default=0) + 1
    if n > len(plan["days"]):
        return None, "plan complete"
    return next(d for d in plan["days"] if d["n"] == n), None


def render(day, plan, progress, errors, now):
    done = len(progress.get("finished", {}))
    pct = round(done / len(plan["days"]) * 100)
    planned = next((d for d in plan["days"] if d["date"] == now.date().isoformat()), None)
    behind = planned["n"] - day["n"] if planned else 0
    due = [e for e in errors for i, r in enumerate(e["retry"]) if not e["retry_done"][i] and r <= now.date().isoformat()]
    week = next(w for w in plan["weeks"] if w["n"] == day["week"])
    link = f"{SITE}#/day/{day['n']}"
    tip = TIPS[day["n"] % len(TIPS)]
    weekend = now.weekday() >= 5
    greeting = "Good morning" if weekend else "Good afternoon"

    rows = []
    for t in day["tasks"]:
        color = CAT_COLOR[cat_class(t["cat"])]
        probs = "".join(
            f'<a href="{p["url"]}" style="display:inline-block;margin:6px 6px 0 0;padding:3px 9px;border-radius:6px;'
            f'background:#2f2f2f;color:#eff1f6;font-size:12px;text-decoration:none">#{p["id"]} {html.escape(p["title"])}</a>'
            for p in t["problems"])
        rows.append(f"""
        <tr><td style="padding:14px 18px;border-top:1px solid #333">
          <div style="font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:{color}">
            {html.escape(t['cat'])} <span style="color:#8b929c;font-weight:400;text-transform:none;letter-spacing:0">· {html.escape(t['time'])}</span></div>
          <div style="margin-top:4px;color:#d7dae0;font-size:14px;line-height:1.55">{strip_links(t['text'])}</div>
          {f'<div>{probs}</div>' if probs else ''}
        </td></tr>""")

    status = (f'<span style="color:#ffa116">{behind} day{"s" if behind > 1 else ""} behind the calendar. '
              "Today's session catches you up one step.</span>" if behind > 0 else
              '<span style="color:#2cbb5d">On schedule.</span>')
    retries = (f'<tr><td style="padding:14px 18px;border-top:1px solid #333;color:#ffa116;font-size:14px">'
               f'⚠ {len(due)} error-log retr{"ies" if len(due) != 1 else "y"} due. Start with these in your 10-minute retrieval warm-up.'
               f'</td></tr>') if due else ""

    return f"""<!doctype html><html><body style="margin:0;background:#111;padding:24px 12px;font-family:Inter,Segoe UI,Arial,sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:620px;margin:0 auto;background:#1a1a1a;border-radius:14px;overflow:hidden;border:1px solid #2f2f2f">
  <tr><td style="padding:22px 18px 18px;background:linear-gradient(135deg,#3a2a10,#1a1a1a 70%)">
    <table role="presentation" width="100%"><tr>
      <td><span style="display:inline-block;width:28px;height:28px;line-height:28px;text-align:center;border-radius:7px;background:#ffa116;color:#1a1a1a;font-weight:700">Σ</span>
        <span style="color:#eff1f6;font-weight:600;font-size:15px;vertical-align:middle;margin-left:6px">MML<span style="color:#ffa116">30</span></span></td>
      <td align="right" style="color:#8b929c;font-size:12px">{now.strftime('%A, %d %B %Y')}</td></tr></table>
    <div style="margin-top:18px;color:#8b929c;font-size:13px">{greeting}, Inaya. Here is today's session.</div>
    <div style="margin-top:4px;color:#ffa116;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase">Week {day['week']} · Day {day['n']} of 30</div>
    <div style="margin-top:4px;color:#eff1f6;font-size:22px;font-weight:700;line-height:1.3">{html.escape(day['title'])}</div>
    <div style="margin-top:6px;color:#9ca3af;font-size:13px">⏳ {html.escape(day['hours'])} · {len(day['tasks'])} tasks · planned for {datetime.fromisoformat(day['date']).strftime('%a %d %b')}</div>
    <div style="margin-top:14px;height:6px;background:#2f2f2f;border-radius:99px"><div style="height:6px;width:{pct}%;background:#ffa116;border-radius:99px"></div></div>
    <div style="margin-top:6px;color:#8b929c;font-size:12px">{done}/30 days finished · {status}</div>
  </td></tr>
  <tr><td style="padding:14px 18px;border-top:1px solid #333;color:#9ca3af;font-size:13px"><b style="color:#eff1f6">Week goal:</b> {html.escape(week['goal'])}</td></tr>
  {retries}
  {''.join(rows)}
  <tr><td style="padding:20px 18px;border-top:1px solid #333" align="center">
    <a href="{link}" style="display:inline-block;background:#ffa116;color:#1a1a1a;font-weight:700;padding:12px 26px;border-radius:9px;text-decoration:none;font-size:15px">Open Day {day['n']} →</a>
    <div style="margin-top:10px"><a href="{plan['overleaf']}" style="color:#3e9bff;font-size:13px;text-decoration:none">Overleaf workspace</a>
      <span style="color:#555"> · </span><a href="{SITE}#/errors" style="color:#3e9bff;font-size:13px;text-decoration:none">Error Checks</a></div>
  </td></tr>
  <tr><td style="padding:16px 18px;background:#222;color:#9ca3af;font-size:13px;line-height:1.5">💡 {html.escape(tip)}</td></tr>
</table>
<div style="text-align:center;color:#555;font-size:11px;margin-top:12px">Sent by the PRML study repo · 17:00 WIB on weekdays, 06:00 WIB on weekends</div>
</body></html>"""


def main():
    now = datetime.now(WIB)
    plan = json.loads((ROOT / "docs/data/plan.json").read_text())
    progress = json.loads((ROOT / "docs/data/progress.json").read_text())
    errors = json.loads((ROOT / "docs/data/errors.json").read_text())
    day, reason = pick_day(plan, progress, now)
    if day is None:
        print(f"No reminder: {reason}")
        return
    body = render(day, plan, progress, errors, now)
    subject = f"📚 Day {day['n']}/30 · {day['title']} ({day['hours']})"
    if os.environ.get("DRY_RUN"):
        (ROOT / "reminder-preview.html").write_text(body)
        print(f"DRY_RUN: {subject} -> reminder-preview.html")
        return
    user, pw = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, f"MML30 Study <{user}>", TO
    msg.attach(MIMEText(f"Day {day['n']}: {day['title']}\n{SITE}#/day/{day['n']}", "plain"))
    msg.attach(MIMEText(body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.sendmail(user, [TO], msg.as_string())
    print(f"Sent: {subject} -> {TO}")


if __name__ == "__main__":
    sys.exit(main())
