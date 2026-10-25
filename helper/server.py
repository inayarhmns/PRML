"""Local helper for the MML study app (stdlib only).

Serves the site in docs/, your iCloud book PDFs under /books/, and the actions a
static GitHub Pages site can't do: pull the Overleaf project + PDF, run Claude
Code to evaluate a day, and commit/push when a day is finished.

Run: python3 helper/server.py   (or bin/study)
"""
import io
import json
import os
import pickle
import re
import shutil
import subprocess
import sys
import threading
import traceback
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("MML_PORT", "8765"))
REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
DATA = DOCS / "data"
OVERLEAF_DIR = DOCS / "overleaf"
BOOKS = Path(os.environ.get("MML_BOOKS", "~/Library/Mobile Documents/com~apple~CloudDocs/MML")).expanduser()
CONFIG = Path("~/.config/mml-study").expanduser()
CACHE = Path("~/.cache/mml-study").expanduser()
OLAUTH = Path(os.environ.get("MML_OLAUTH", CONFIG / ".olauth")).expanduser()
OVERLEAF = "https://www.overleaf.com"
PROJECT_ID = "6adaca2e9783ef342efceec6"
PDF_NAME = "MML-BOOK.pdf"
ALLOWED_ORIGINS = {"https://inayarhmns.github.io", f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}
WIB = timezone(timedelta(hours=7))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
MML_SOL = "https://raw.githubusercontent.com/ilmoi/MML-Book/master/end%20of%20chapter%20exercises/Chapter%20{}%20Exercises%20-%20PDF.pdf"

lock = threading.Lock()
evaluations = {}  # day -> {"status": "running"|"done"|"error", ...}


def now():
    return datetime.now(WIB)


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def plan_day(n):
    plan = read_json(DATA / "plan.json", {"days": []})
    return next((d for d in plan["days"] if d["n"] == n), None)


# ------------------------------------------------------------------ overleaf
class Overleaf:
    def __init__(self):
        if not OLAUTH.exists():
            raise RuntimeError(f"No Overleaf login at {OLAUTH}. Run: bin/study login")
        auth = pickle.loads(OLAUTH.read_bytes())
        self.cookie = "; ".join(f"{k}={v}" for k, v in auth["cookie"].items())
        self.csrf = None

    def request(self, url, data=None, headers=None):
        h = {"Cookie": self.cookie, "User-Agent": UA, **(headers or {})}
        if data is not None:
            data = json.dumps(data).encode()
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(url if url.startswith("http") else OVERLEAF + url, data=data, headers=h)
        with urllib.request.urlopen(req, timeout=180) as r:
            if "/login" in r.geturl():
                raise RuntimeError("Overleaf session expired. Run: bin/study login")
            return r.read()

    def fetch_csrf(self):
        html = self.request(f"/project/{PROJECT_ID}").decode("utf-8", "replace")
        m = re.search(r'name="ol-csrfToken" content="([^"]+)"', html)
        if not m:
            raise RuntimeError("Overleaf session expired. Run: bin/study login")
        self.csrf = m.group(1)

    def download_zip(self):
        return self.request(f"/project/{PROJECT_ID}/download/zip")

    def compile_pdf(self):
        self.fetch_csrf()
        res = json.loads(self.request(
            f"/project/{PROJECT_ID}/compile?auto_compile=true",
            data={"check": "silent", "draft": False, "incrementalCompilesEnabled": True, "rootDoc_id": None,
                  "stopOnFirstError": False},
            headers={"X-Csrf-Token": self.csrf}))
        if res.get("status") != "success":
            raise RuntimeError(f"Overleaf compile failed: {res.get('status')} (check the LaTeX errors in Overleaf)")
        pdf = next(f for f in res["outputFiles"] if f["type"] == "pdf")
        q = {}
        if res.get("compileGroup"):
            q["compileGroup"] = res["compileGroup"]
        if res.get("clsiServerId"):
            q["clsiserverid"] = res["clsiServerId"]
        url = res.get("pdfDownloadDomain", OVERLEAF) + pdf["url"] + ("?" + urllib.parse.urlencode(q) if q else "")
        return self.request(url)


def pull_overleaf():
    ol = Overleaf()
    zip_bytes = ol.download_zip()
    pdf_bytes = ol.compile_pdf()
    # Replace the saved copy wholesale so deleted Overleaf files disappear too.
    if OVERLEAF_DIR.exists():
        shutil.rmtree(OVERLEAF_DIR)
    (OVERLEAF_DIR / "src").mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for info in z.infolist():
            target = (OVERLEAF_DIR / "src" / info.filename).resolve()
            if not str(target).startswith(str((OVERLEAF_DIR / "src").resolve())):
                continue
            z.extract(info, OVERLEAF_DIR / "src")
    (OVERLEAF_DIR / PDF_NAME).write_bytes(pdf_bytes)
    files = sorted(str(p.relative_to(OVERLEAF_DIR)) for p in OVERLEAF_DIR.rglob("*") if p.is_file())
    meta = {"pulled_at": now().isoformat(timespec="seconds"), "pdf": PDF_NAME, "files": files}
    write_json(OVERLEAF_DIR / "meta.json", meta)
    return meta


# ------------------------------------------------------------------ evaluate
EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "score": {"type": "object", "properties": {"correct": {"type": "integer"}, "total": {"type": "integer"}},
                  "required": ["correct", "total"]},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "task": {"type": "string"}, "question": {"type": "string"},
            "verdict": {"type": "string", "enum": ["correct", "partial", "wrong", "missing"]},
            "feedback": {"type": "string"}, "ground_truth": {"type": "string"}},
            "required": ["task", "question", "verdict", "feedback", "ground_truth"]}},
        "errors": {"type": "array", "items": {"type": "object", "properties": {
            "topic": {"type": "string"}, "question": {"type": "string"},
            "why": {"type": "string", "enum": ["Concept", "Calculation", "Careless", "Coding"]},
            "wrong_reasoning": {"type": "string"}, "correct_rule": {"type": "string"}},
            "required": ["topic", "question", "why", "wrong_reasoning", "correct_rule"]}},
    },
    "required": ["summary", "score", "items", "errors"],
}


def cache_file(url, name):
    path = CACHE / "answers" / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
    return path


def answer_keys(day):
    keys = []
    for task in day["tasks"]:
        for res in task["resources"]:
            sol = res.get("solution")
            if not sol:
                continue
            m = re.search(r"Chapter%20(\d+)%20Exercises", sol)
            try:
                if m:
                    keys.append((res["label"], cache_file(MML_SOL.format(m.group(1)), f"mml-ch{m.group(1)}-solutions.pdf")))
                else:
                    keys.append((res["label"], cache_file(sol, sol.rsplit("/", 1)[-1])))
            except OSError as e:
                keys.append((res["label"], f"(could not download {sol}: {e})"))
    return list(dict.fromkeys(keys))


def build_prompt(day, keys):
    lines = [f"You are grading Day {day['n']} ({day['date']}, \"{day['title']}\") of a 30-day study plan for the "
             "self-study of math for ML, deep learning and Python. Be a strict but fair grader.", "", "## Today's tasks"]
    for t in day["tasks"]:
        if t["workspace"] in ("overleaf", "notebook"):
            refs = "; ".join(f"{r['label']} → {BOOKS / r['file']} page {r['page']}" for r in t["resources"]
                             if r["kind"] == "book")
            lines.append(f"- [{t['cat']}] {t['text']}" + (f"\n  Question sources: {refs}" if refs else ""))
    lines += ["", "## The student's answers",
              f"- Overleaf LaTeX source: {OVERLEAF_DIR / 'src'} (read every .tex file)",
              f"- Compiled PDF of the same answers: {OVERLEAF_DIR / PDF_NAME}",
              f"- Python notebooks for today, if any: {REPO / 'notebooks'} (files mentioning day{day['n']:02d})",
              "Only grade answers that belong to today: look for a heading such as \"Day "
              f"{day['n']}\" first; otherwise match answers to today's tasks by topic. Ignore answers to other days.",
              "", "## Ground truth"]
    for label, path in keys:
        lines.append(f"- {label}: {path}")
    lines += ["- MML Chapters 2–7 solutions above are from github.com/ilmoi/MML-Book; MIT 18.05 solutions are official.",
              "- D2L (github.com/d2l-ai/d2l-en) has no official exercise solutions: solve those questions yourself "
              "carefully, using the D2L text as reference, and grade against your own worked answer.",
              "- StatQuest and similar conceptual questions: grade against standard textbook definitions.",
              "- LeetCode tasks are graded by LeetCode itself; skip them.", "",
              "## Output",
              "Return JSON matching the schema. `items`: one entry per question you found an answer for "
              "(or expected but is missing). `errors`: one entry per wrong/partial answer for the error log, "
              "with `why` being Concept, Calculation, Careless or Coding, `wrong_reasoning` quoting what the "
              "student did, and `correct_rule` a compact rule they can memorise. `summary`: 2–4 sentences on "
              "the biggest gaps. If no answers for today exist yet, return empty items/errors and say so."]
    return "\n".join(lines)


def run_evaluation(n):
    try:
        day = plan_day(n)
        keys = answer_keys(day)
        prompt = build_prompt(day, keys)
        cmd = ["claude", "-p", "--output-format", "json", "--json-schema", json.dumps(EVAL_SCHEMA),
               "--permission-mode", "dontAsk", "--allowedTools", "Read", "Glob", "Grep", "WebFetch",
               "--add-dir", str(BOOKS), str(CACHE)]
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=REPO, timeout=1800)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip()[-2000:])
        out = json.loads(proc.stdout)
        result = out.get("structured_output")
        if result is None:
            m = re.search(r"\{.*\}", out.get("result", ""), re.S)
            result = json.loads(m.group(0)) if m else None
        if not isinstance(result, dict):
            raise RuntimeError("Claude returned no structured result: " + str(out.get("result", ""))[:500])
        added = log_errors(n, result.get("errors", []))
        record = {"day": n, "evaluated_at": now().isoformat(timespec="seconds"),
                  "overleaf_pulled_at": read_json(OVERLEAF_DIR / "meta.json", {}).get("pulled_at"),
                  "cost_usd": out.get("total_cost_usd"), "errors_added": added, **result}
        write_json(DATA / "evaluations" / f"day-{n:02d}.json", record)
        evaluations[n] = {"status": "done", "result": record}
    except Exception as e:  # surfaced to the UI
        traceback.print_exc()
        evaluations[n] = {"status": "error", "error": str(e)}


def log_errors(n, errors):
    if not errors:
        return 0
    final_week = datetime(2026, 11, 9, tzinfo=WIB).date()
    today = now().date()
    with lock:
        log = read_json(DATA / "errors.json", [])
        for i, e in enumerate(errors):
            log.append({
                "id": f"{now().strftime('%Y%m%d%H%M%S')}-{n}-{i}", "date": today.isoformat(), "day": n,
                "topic": e["topic"], "question": e["question"], "why": e["why"],
                "wrong_reasoning": e.get("wrong_reasoning", ""), "correct_rule": e["correct_rule"],
                "retry": [(today + timedelta(days=1)).isoformat(), (today + timedelta(days=3)).isoformat(),
                          max(today + timedelta(days=7), final_week).isoformat()],
                "retry_done": [False, False, False], "source": "claude"})
        write_json(DATA / "errors.json", log)
    return len(errors)


# ------------------------------------------------------------------ git / progress
def git(*args):
    p = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{p.stderr.strip() or p.stdout.strip()}")
    return p.stdout.strip()


def finish_state(n):
    meta = read_json(OVERLEAF_DIR / "meta.json", {})
    progress = read_json(DATA / "progress.json", {"finished": {}, "tasks": {}})
    pulled = meta.get("pulled_at")
    if not pulled:
        return False, "Download the Overleaf PDF first."
    pulled_dt = datetime.fromisoformat(pulled)
    if pulled_dt.date() != now().date():
        return False, "Re-download the Overleaf PDF today before finishing."
    last = max((datetime.fromisoformat(v) for v in progress["finished"].values()), default=None)
    if last and pulled_dt <= last:
        return False, "Re-download the Overleaf PDF (the current copy predates your last finished day)."
    if str(n) in progress["finished"]:
        return False, f"Day {n} is already finished."
    return True, "Ready to finish."


def finish_day(n):
    ok, msg = finish_state(n)
    if not ok:
        raise RuntimeError(msg)
    day = plan_day(n)
    with lock:
        progress = read_json(DATA / "progress.json", {"finished": {}, "tasks": {}})
        progress["finished"][str(n)] = now().isoformat(timespec="seconds")
        write_json(DATA / "progress.json", progress)
    git("add", "-A")
    git("commit", "-m", f"Day {n} finished: {day['title']}")
    git("push", "origin", "HEAD")
    return {"finished_at": progress["finished"][str(n)], "commit": git("rev-parse", "--short", "HEAD")}


def set_task(task_id, done):
    with lock:
        progress = read_json(DATA / "progress.json", {"finished": {}, "tasks": {}})
        progress["tasks"][task_id] = bool(done)
        write_json(DATA / "progress.json", progress)
    return progress


def update_error(err_id, patch):
    with lock:
        log = read_json(DATA / "errors.json", [])
        for e in log:
            if e["id"] == err_id:
                if patch.get("delete"):
                    log.remove(e)
                elif "retry_index" in patch:
                    e["retry_done"][int(patch["retry_index"])] = bool(patch["value"])
                break
        else:
            raise RuntimeError("error entry not found")
        write_json(DATA / "errors.json", log)
    return log


def add_error(entry):
    today = now().date()
    with lock:
        log = read_json(DATA / "errors.json", [])
        log.append({"id": now().strftime("%Y%m%d%H%M%S") + "-m", "date": today.isoformat(),
                    "day": entry.get("day"), "topic": entry.get("topic", ""), "question": entry.get("question", ""),
                    "why": entry.get("why", "Concept"), "wrong_reasoning": entry.get("wrong_reasoning", ""),
                    "correct_rule": entry.get("correct_rule", ""),
                    "retry": [(today + timedelta(days=1)).isoformat(), (today + timedelta(days=3)).isoformat(),
                              max(today + timedelta(days=7), datetime(2026, 11, 9).date()).isoformat()],
                    "retry_done": [False, False, False], "source": "manual"})
        write_json(DATA / "errors.json", log)
    return log


# ------------------------------------------------------------------ http
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DOCS), **kw)

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)

    def end_headers(self):
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def reply(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/status":
            return self.reply(status())
        if url.path == "/api/evaluate":
            n = int(urllib.parse.parse_qs(url.query).get("day", ["0"])[0])
            return self.reply(evaluations.get(n, {"status": "idle"}))
        if url.path == "/api/finish-state":
            n = int(urllib.parse.parse_qs(url.query).get("day", ["0"])[0])
            ok, msg = finish_state(n)
            return self.reply({"ok": ok, "message": msg})
        if url.path.startswith("/books/"):
            return self.serve_book(urllib.parse.unquote(url.path[len("/books/"):]))
        return super().do_GET()

    def serve_book(self, rel):
        path = (BOOKS / rel).resolve()
        if not str(path).startswith(str(BOOKS.resolve())) or not path.is_file():
            return self.send_error(404, "Book not found")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        # Only the app itself may trigger actions (blocks drive-by requests from other sites).
        if self.headers.get("Origin") not in ALLOWED_ORIGINS:
            return self.reply({"error": "forbidden origin"}, 403)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/api/overleaf/pull":
                return self.reply(pull_overleaf())
            if path == "/api/evaluate":
                n = int(body["day"])
                if evaluations.get(n, {}).get("status") == "running":
                    return self.reply(evaluations[n])
                evaluations[n] = {"status": "running", "started_at": now().isoformat(timespec="seconds")}
                threading.Thread(target=run_evaluation, args=(n,), daemon=True).start()
                return self.reply(evaluations[n])
            if path == "/api/finish":
                return self.reply(finish_day(int(body["day"])))
            if path == "/api/task":
                return self.reply(set_task(body["id"], body["done"]))
            if path == "/api/errors/update":
                return self.reply(update_error(body["id"], body))
            if path == "/api/errors/add":
                return self.reply(add_error(body))
            return self.reply({"error": "unknown endpoint"}, 404)
        except Exception as e:
            traceback.print_exc()
            return self.reply({"error": str(e)}, 400)


def status():
    meta = read_json(OVERLEAF_DIR / "meta.json", {})
    return {"ok": True, "overleaf": {"pulled_at": meta.get("pulled_at"), "login": OLAUTH.exists()},
            "books": BOOKS.exists(),
            "evaluations": {k: v["status"] for k, v in evaluations.items()}}


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"MML study helper on http://127.0.0.1:{PORT}  (repo: {REPO})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
