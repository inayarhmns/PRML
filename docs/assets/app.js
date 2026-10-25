/* MML30 — single-page study app. Static on GitHub Pages; actions need the local helper (bin/study). */
const HELPER = "http://127.0.0.1:8765";
const OVERLEAF_URL = "https://www.overleaf.com/project/6adaca2e9783ef342efceec6";
const S = { plan: null, progress: { finished: {}, tasks: {} }, errors: [], evals: {}, helper: false, base: ".", meta: {} };

// ------------------------------------------------------------------ utils
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const md = (s) => esc(s).replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
const todayWIB = () => new Date(Date.now() + 7 * 3600e3).toISOString().slice(0, 10);
const fmtDate = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
const fmtTime = (iso) => iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "never";
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};
function toast(msg, err = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast show" + (err ? " err" : "");
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.className = "toast"), 4200);
}
async function getJSON(path, fallback) {
  try {
    const r = await fetch(`${S.base}/${path}?t=${Date.now()}`, { cache: "no-store" });
    return r.ok ? await r.json() : fallback;
  } catch { return fallback; }
}
async function api(path, body) {
  const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(HELPER + path, opts);
  const data = await r.json();
  if (!r.ok || data.error) throw new Error(data.error || r.statusText);
  return data;
}

// ------------------------------------------------------------------ data
async function detectHelper() {
  try {
    const ctl = new AbortController(); setTimeout(() => ctl.abort(), 1200);
    const r = await fetch(`${HELPER}/api/status`, { signal: ctl.signal });
    S.helper = r.ok;
  } catch { S.helper = false; }
  S.base = S.helper ? HELPER : ".";
  const pill = $("#helper-pill");
  pill.className = "helper-pill " + (S.helper ? "on" : "off");
  pill.textContent = S.helper ? "helper on" : "helper off";
  pill.title = S.helper ? "Local helper running: Overleaf, Evaluate, Finish and local books enabled"
    : "Start the local helper with bin/study to enable Overleaf download, Evaluate, Finish and local PDFs";
}
async function loadData() {
  [S.plan, S.progress, S.errors, S.meta] = await Promise.all([
    getJSON("data/plan.json", null),
    getJSON("data/progress.json", { finished: {}, tasks: {} }),
    getJSON("data/errors.json", []),
    getJSON("overleaf/meta.json", {}),
  ]);
  if (!S.helper) S.progress.tasks = { ...S.progress.tasks, ...store.get("tasks", {}) };
}
const day = (n) => S.plan.days.find((d) => d.n === n);
const isDone = (n) => Boolean(S.progress.finished[String(n)]);
const nextDay = () => {
  const done = Object.keys(S.progress.finished).map(Number);
  return Math.min(30, (done.length ? Math.max(...done) : 0) + 1);
};
const taskDone = (id) => Boolean(S.progress.tasks[id]);
const bookUrl = (r) => (S.helper ? `${HELPER}/books/${encodeURI(r.file)}#page=${r.page}` : r.online);
const pdfUrl = () => `${S.base}/overleaf/${S.meta.pdf || "MML-BOOK.pdf"}?t=${encodeURIComponent(S.meta.pulled_at || "")}`;

function catClass(cat) {
  const c = cat.toLowerCase();
  if (c.includes("leetcode")) return "lc";
  if (/python|implementation|programming|algorithm|control/.test(c)) return "py";
  if (/log|mark|review|plan|cool|check|break/.test(c)) return "log";
  if (/ml|neural|classification|pca|cnn|cv|convolution|d2l|image|representation|geometry/.test(c)) return "ml";
  return "math";
}
function dayTags(d) {
  const set = new Set(d.tasks.map((t) => catClass(t.cat)).filter((c) => c !== "log"));
  const names = { math: "Math", lc: "LeetCode", ml: "ML", py: "Python" };
  return [...set].map((c) => `<span class="chip ${c}">${names[c]}</span>`).join(" ");
}

// ------------------------------------------------------------------ router
function nav(active) {
  const links = [["#/", "Dashboard"], ...S.plan.weeks.map((w) => [`#/week/${w.n}`, `Week ${w.n}`]), ["#/errors", "Error Checks"]];
  $("#nav").innerHTML = links.map(([h, t]) => `<a href="${h}" class="${h === active ? "active" : ""}">${t}</a>`).join("");
}
async function route() {
  const h = location.hash || "#/";
  let m;
  if ((m = h.match(/^#\/week\/(\d)/))) { nav(`#/week/${m[1]}`); return renderWeek(+m[1]); }
  if ((m = h.match(/^#\/day\/(\d+)/))) { const d = day(+m[1]); nav(`#/week/${d ? d.week : 1}`); return renderDay(+m[1]); }
  if (h.startsWith("#/errors")) { nav("#/errors"); return renderErrors(); }
  nav("#/"); renderDashboard();
}

// ------------------------------------------------------------------ dashboard
function renderDashboard() {
  const n = nextDay(), d = day(n), today = todayWIB();
  const finished = Object.keys(S.progress.finished).length;
  const planned = S.plan.days.find((x) => x.date === today);
  const behind = planned ? planned.n - n : 0;
  const dueRetries = S.errors.flatMap((e) => e.retry.map((r, i) => ({ e, r, i }))).filter((x) => !x.e.retry_done[x.i] && x.r <= today);
  const allTasks = S.plan.days.flatMap((x) => x.tasks);
  const doneTasks = allTasks.filter((t) => taskDone(t.id)).length;
  const weekCard = (w) => {
    const days = S.plan.days.filter((x) => x.week === w.n);
    const done = days.filter((x) => isDone(x.n)).length;
    return `<a class="card" href="#/week/${w.n}">
      <div class="eyebrow">Week ${w.n} · Days ${days[0].n}–${days.at(-1).n}</div>
      <h3 style="margin:6px 0 6px;font-size:15px">${esc(w.title)}</h3>
      <div class="muted" style="font-size:13px">${fmtDate(days[0].date)} – ${fmtDate(days.at(-1).date)}</div>
      <div class="bar"><span style="width:${(done / days.length) * 100}%"></span></div>
      <div class="row" style="margin-top:8px;font-size:12px"><span class="muted">${done}/${days.length} days finished</span></div>
    </a>`;
  };
  $("#app").innerHTML = `<div class="page">
    <div class="card hero">
      <div>
        <div class="eyebrow">${finished === 30 ? "All done" : "Up next"}</div>
        <h1>Day ${n} — ${esc(d.title)}</h1>
        <p class="sub">${fmtDate(d.date)} · ${esc(d.hours)} · ${d.tasks.length} tasks
          ${behind > 0 ? ` · <span style="color:var(--accent)">${behind} day${behind > 1 ? "s" : ""} behind the calendar</span>` : ""}</p>
        <div class="row" style="margin-top:14px">${dayTags(d)}</div>
        <div class="row" style="margin-top:16px">
          <a class="btn primary" href="#/day/${n}">Start Day ${n} →</a>
          <a class="btn" href="${OVERLEAF_URL}" target="_blank" rel="noopener">Open Overleaf</a>
        </div>
      </div>
      <div class="ring" style="--p:${(finished / 30) * 100}"><div><b>${finished}</b><small>of 30 days</small></div></div>
    </div>

    <div class="stats" style="margin-top:14px">
      <div class="card stat"><b>${doneTasks}<span class="faint" style="font-size:14px">/${allTasks.length}</span></b><span>tasks checked</span></div>
      <div class="card stat"><b>${S.errors.length}</b><span>errors logged</span></div>
      <div class="card stat"><b style="color:${dueRetries.length ? "var(--accent)" : "inherit"}">${dueRetries.length}</b><span>retries due</span></div>
      <div class="card stat"><b style="font-size:15px;padding-top:5px">${fmtTime(S.meta.pulled_at)}</b><span>last Overleaf download</span></div>
    </div>

    <h2>Weeks</h2>
    <div class="grid weeks">${S.plan.weeks.map(weekCard).join("")}</div>

    <h2 class="row"><span>Error Checks — retries due</span><span class="spacer"></span><a href="#/errors" style="font-size:13px;font-weight:500">Open full log →</a></h2>
    ${dueRetries.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>Due</th><th>Topic</th><th>Question / task</th><th>Correct rule / idea</th></tr></thead><tbody>
      ${dueRetries.slice(0, 6).map((x) => `<tr><td class="retry due">${x.r} · R${x.i + 1}</td><td>${esc(x.e.topic)}</td><td>${esc(x.e.question)}</td><td>${esc(x.e.correct_rule)}</td></tr>`).join("")}
      </tbody></table></div>` : `<div class="empty">No retries due. Evaluate a day to fill the error log.</div>`}

    <h2>What counts as a successful day?</h2>
    <div class="card"><ol style="margin:0;padding-left:20px">
      <li><b>Practice before reviewing.</b> Start with a closed-book attempt. Do not watch a full lecture just because the topic feels rusty.</li>
      <li><b>Use the rescue loop:</b> try for 5–10 minutes → identify the exact gap → read only the relevant subsection or video segment → close the resource → solve a similar question without help.</li>
      <li><b>Log errors, not notes.</b> Record the prompt/topic, your wrong reasoning, the correct principle, and when you will retry it.</li>
      <li><b>Retest mistakes:</b> retry each missed question the next day, three days later, and in the final week.</li>
      <li><b>Protect weekends.</b> 80–90 minute blocks with breaks. Stop around 8–9 focused hours.</li>
    </ol></div>
  </div>`;
}

// ------------------------------------------------------------------ week
function renderWeek(w) {
  const wk = S.plan.weeks.find((x) => x.n === w);
  const days = S.plan.days.filter((x) => x.week === w);
  const today = todayWIB(), next = nextDay();
  $("#app").innerHTML = `<div class="page">
    <div class="eyebrow">Week ${w}</div>
    <h1>${esc(wk.title)}</h1>
    <p class="sub">Goal: ${esc(wk.goal)}</p>
    <h2>Days</h2>
    <div class="table-wrap"><table class="table">
      <thead><tr><th class="status-dot"></th><th>Day</th><th>Title</th><th>Subjects</th><th>Date</th><th>Load</th><th>Tasks</th></tr></thead>
      <tbody>${days.map((d) => {
        const done = isDone(d.n), checked = d.tasks.filter((t) => taskDone(t.id)).length;
        const icon = done ? `<span class="status-done" title="Finished">✓</span>` : d.n === next ? `<span class="status-today" title="Up next">●</span>` : "";
        const load = d.hours.startsWith("8") || d.hours.startsWith("9") ? "Medium" : "Easy";
        return `<tr class="link" onclick="location.hash='#/day/${d.n}'">
          <td class="status-dot">${icon}</td><td class="faint">${d.n}</td>
          <td><a class="title" href="#/day/${d.n}">${esc(d.title)}</a></td>
          <td>${dayTags(d)}</td>
          <td style="white-space:nowrap">${fmtDate(d.date)}${d.date === today ? ' <span class="chip lc">today</span>' : ""}</td>
          <td class="diff-${load}" style="white-space:nowrap">${esc(d.hours)}</td>
          <td class="faint">${checked}/${d.tasks.length}</td></tr>`;
      }).join("")}</tbody></table></div>
  </div>`;
}

// ------------------------------------------------------------------ day
const DAY_TABS = { left: "desc", right: "overleaf" };
function renderDay(n) {
  const d = day(n);
  if (!d) { $("#app").innerHTML = `<div class="page"><div class="empty">No such day.</div></div>`; return; }
  const lcProblems = [...new Map(d.tasks.flatMap((t) => t.problems).map((p) => [p.id, p])).values()];
  const notebookTasks = d.tasks.filter((t) => t.workspace === "notebook");
  $("#app").innerHTML = `<div class="split">
    <section class="pane">
      <div class="tabs" id="ltabs">
        ${[["desc", "📝 Description"], ["eval", "✅ Evaluation"], ["sol", "🔑 Solutions"]].map(([k, t]) => `<button class="tab" data-k="${k}">${t}</button>`).join("")}
      </div>
      <div class="pane-body" id="lbody"></div>
      <div class="pane-foot">
        <a class="btn small" href="#/day/${Math.max(1, n - 1)}" ${n === 1 ? 'style="visibility:hidden"' : ""}>← Day ${n - 1}</a>
        <a class="btn small" href="#/week/${d.week}">Week ${d.week}</a>
        <span class="spacer"></span>
        <a class="btn small" href="#/day/${Math.min(30, n + 1)}" ${n === 30 ? 'style="visibility:hidden"' : ""}>Day ${n + 1} →</a>
      </div>
    </section>
    <section class="pane">
      <div class="tabs" id="rtabs">
        ${[["overleaf", "∑ Overleaf"], ["leetcode", `⌨ LeetCode${lcProblems.length ? ` (${lcProblems.length})` : ""}`], ["notebook", "🐍 Python"], ["errors", "⚠ Errors"]].map(([k, t]) => `<button class="tab" data-k="${k}">${t}</button>`).join("")}
      </div>
      <div class="pane-body" id="rbody"></div>
      <div class="pane-foot" id="actions"></div>
    </section>
  </div>`;
  const left = {
    desc: () => dayDescription(d),
    eval: () => dayEvaluation(d),
    sol: () => daySolutions(d),
  };
  const right = {
    overleaf: () => `<div class="ws-section">
        <div class="row"><h3 style="margin:0">Overleaf · MML-BOOK</h3><span class="spacer"></span>
          <a class="btn small primary" href="${OVERLEAF_URL}" target="_blank" rel="noopener">Open project ↗</a></div>
        <p class="note">Write math, statistics and D2L answers here. Put them under <code>\\section{Day ${n}}</code> so Evaluate can find them.
        Last download: <b>${fmtTime(S.meta.pulled_at)}</b>.</p>
      </div>
      ${S.meta.pulled_at ? `<iframe class="pdf-frame" src="${pdfUrl()}#view=FitH" title="Overleaf PDF"></iframe>`
        : `<div class="empty">No PDF downloaded yet. Use <b>Download Overleaf PDF</b> below.</div>`}`,
    leetcode: () => `<div class="ws-section"><h3>Today's problems</h3>
        ${lcProblems.length ? lcProblems.map((p) => `<div class="lc-row"><span class="faint" style="width:44px">#${p.id}</span>
          <a href="${p.url}" target="_blank" rel="noopener">${esc(p.title)}</a><span class="diff-${p.difficulty}">${p.difficulty}</span>
          <a class="btn small" href="${p.url}" target="_blank" rel="noopener" style="flex:none">Solve ↗</a></div>`).join("")
          : `<div class="empty">No fixed problems today. Use your error log or the <a href="https://leetcode.com/studyplan/leetcode-75/" target="_blank">LeetCode 75</a> list.</div>`}
      </div><p class="note">LeetCode grades these itself; record misses in the Error Checks log.</p>`,
    notebook: () => `<div class="ws-section"><h3>Python workspace</h3>
        ${notebookTasks.length ? `<div class="callout">Create <code>notebooks/day${String(n).padStart(2, "0")}.ipynb</code> in the PRML repo. It is committed with the day when you press Finish, and Evaluate reads it.</div>
          ${notebookTasks.map((t) => `<div class="task"><div class="task-head"><span class="chip py">${esc(t.cat)}</span><span class="faint">${esc(t.time)}</span></div><p style="margin-left:0">${md(t.text)}</p></div>`).join("")}`
          : `<div class="empty">No Python implementation task today.</div>`}</div>`,
    errors: () => {
      const errs = S.errors.filter((e) => e.day === n);
      return `<div class="ws-section"><div class="row"><h3 style="margin:0">Errors logged for Day ${n}</h3><span class="spacer"></span><a class="btn small" href="#/errors">Full log →</a></div></div>
        ${errs.length ? errs.map((e) => `<div class="task"><div class="task-head"><span class="why ${e.why}">${e.why}</span><b>${esc(e.topic)}</b></div>
          <p style="margin-left:0"><span class="muted">Q:</span> ${esc(e.question)}</p>
          ${e.wrong_reasoning ? `<p style="margin-left:0"><span class="muted">You:</span> ${esc(e.wrong_reasoning)}</p>` : ""}
          <p style="margin-left:0"><span class="muted">Rule:</span> ${esc(e.correct_rule)}</p></div>`).join("")
          : `<div class="empty">Nothing logged for this day yet.</div>`}`;
    },
  };
  const wire = (tabsId, bodyId, views, side) => {
    const show = (k) => {
      DAY_TABS[side] = k;
      document.querySelectorAll(`#${tabsId} .tab`).forEach((b) => b.classList.toggle("active", b.dataset.k === k));
      $(`#${bodyId}`).innerHTML = views[k]();
      if (bodyId === "lbody" && k === "desc") wireTasks();
      if (bodyId === "lbody" && k === "eval") pollEval(n);
    };
    document.querySelectorAll(`#${tabsId} .tab`).forEach((b) => (b.onclick = () => show(b.dataset.k)));
    show(views[DAY_TABS[side]] ? DAY_TABS[side] : Object.keys(views)[0]);
  };
  wire("ltabs", "lbody", left, "left");
  wire("rtabs", "rbody", right, "right");
  renderActions(d);
}

function dayDescription(d) {
  const next = nextDay();
  return `<div class="day-head">
      <div class="row" style="margin-bottom:6px"><span class="eyebrow">Week ${d.week} · Day ${d.n}</span>
        ${isDone(d.n) ? '<span class="chip" style="color:var(--green)">✓ finished</span>' : d.n === next ? '<span class="chip lc">up next</span>' : ""}</div>
      <h1>${d.n}. ${esc(d.title)}</h1>
      <div class="row" style="margin-bottom:16px">
        <span class="chip">${fmtDate(d.date)}</span><span class="chip">⏳ ${esc(d.hours)}</span>${dayTags(d)}
      </div>
    </div>
    ${d.tasks.map((t) => `<div class="task ${taskDone(t.id) ? "done" : ""}" data-id="${t.id}">
      <label class="task-head"><input type="checkbox" ${taskDone(t.id) ? "checked" : ""} data-task="${t.id}">
        <span class="cat chip ${catClass(t.cat)}" style="font-size:13px">${esc(t.cat)}</span><span class="faint">${esc(t.time)}</span>
        <span class="spacer"></span><span class="faint" style="font-size:12px">${{ overleaf: "∑ Overleaf", leetcode: "⌨ LeetCode", notebook: "🐍 Python", errors: "⚠ Error log", none: "" }[t.workspace] || ""}</span></label>
      <p>${md(t.text)}</p>
      ${t.resources.length ? `<div class="res">${t.resources.map(resLink).join("")}</div>` : ""}
    </div>`).join("")}
    <p class="note">Book buttons open the exact page in your local PDF when the helper is on; otherwise they open the free online edition.</p>`;
}
function resLink(r) {
  if (r.kind === "app") return `<a href="${r.url}"><span class="k">↪</span>${esc(r.label)}</a>`;
  const icon = { book: "📖", video: "▶", course: "🎓", web: "🔗" }[r.kind] || "🔗";
  const url = r.kind === "book" ? bookUrl(r) : r.url;
  const page = r.kind === "book" ? ` <span class="faint">p.${r.page}</span>` : "";
  return `<a href="${url}" target="_blank" rel="noopener"><span class="k">${icon}</span>${esc(r.label)}${page}</a>`;
}
function wireTasks() {
  document.querySelectorAll("[data-task]").forEach((cb) => (cb.onchange = async () => {
    const id = cb.dataset.task;
    S.progress.tasks[id] = cb.checked;
    cb.closest(".task").classList.toggle("done", cb.checked);
    if (S.helper) {
      try { await api("/api/task", { id, done: cb.checked }); } catch (e) { toast(e.message, true); }
    } else {
      const local = store.get("tasks", {}); local[id] = cb.checked; store.set("tasks", local);
    }
  }));
}
function daySolutions(d) {
  const sols = d.tasks.flatMap((t) => t.resources.filter((r) => r.solution));
  const uniq = [...new Map(sols.map((r) => [r.solution, r])).values()];
  return `<div class="callout"><b>Attempt first.</b> Only open a solution after a genuine closed-book attempt. Evaluate uses these same keys.</div>
    ${uniq.length ? uniq.map((r) => `<div class="lc-row"><span>📖</span><span style="flex:1">${esc(r.label)}</span>
      <a class="btn small" href="${r.solution}" target="_blank" rel="noopener">Solution ↗</a></div>`).join("")
      : `<div class="empty">No official answer key for today's tasks. D2L has no published solutions, so Evaluate has Claude solve those questions itself and grade against that.</div>`}
    <p class="note">Answer sources: <a href="https://github.com/ilmoi/MML-Book" target="_blank">ilmoi/MML-Book</a> (MML Ch 2–7),
    <a href="https://ocw.mit.edu/courses/18-05-introduction-to-probability-and-statistics-spring-2022/pages/problem-sets/" target="_blank">MIT 18.05</a>,
    <a href="https://github.com/d2l-ai/d2l-en" target="_blank">d2l-ai/d2l-en</a> (text only).</p>`;
}
function dayEvaluation(d) {
  const ev = S.evals[d.n];
  const head = `<div class="row" style="margin-bottom:10px"><h3 style="margin:0">Evaluation by Claude Code</h3><span class="spacer"></span>
    <span class="note" id="eval-status"></span></div>`;
  if (!ev) return head + `<div class="empty">Not evaluated yet. Download the Overleaf PDF, then press <b>Evaluate</b>.<br>
    Claude reads your Overleaf source + PDF, compares them with the answer keys, and logs each mistake in Error Checks.</div>`;
  const pct = ev.score && ev.score.total ? Math.round((ev.score.correct / ev.score.total) * 100) : null;
  const band = pct === null ? "" : pct >= 80 ? "var(--green)" : pct >= 60 ? "var(--medium)" : "var(--red)";
  return head + `<div class="card" style="margin-bottom:12px">
      <div class="row"><b style="font-size:22px;color:${band}">${ev.score ? `${ev.score.correct}/${ev.score.total}` : "—"}</b>
      ${pct !== null ? `<span style="color:${band}">${pct}% · ${pct >= 80 ? "Green: move on" : pct >= 60 ? "Yellow: another small set within 48 h" : "Red: review the subsection, then 3 similar questions"}</span>` : ""}
      <span class="spacer"></span><span class="note">${fmtTime(ev.evaluated_at)} · ${ev.errors_added || 0} errors logged</span></div>
      <p style="margin:10px 0 0">${esc(ev.summary)}</p></div>
    ${(ev.items || []).map((it) => `<div class="eval-item"><div class="row"><span class="verdict ${it.verdict}">${it.verdict}</span>
      <b>${esc(it.question)}</b><span class="spacer"></span><span class="faint" style="font-size:12px">${esc(it.task)}</span></div>
      <p style="margin:6px 0 0">${esc(it.feedback)}</p>
      ${it.ground_truth ? `<details style="margin-top:6px"><summary class="note" style="cursor:pointer">Ground truth</summary><p style="margin:6px 0 0" class="muted">${esc(it.ground_truth)}</p></details>` : ""}</div>`).join("")}`;
}
async function pollEval(n) {
  if (!S.evals[n]) S.evals[n] = await getJSON(`data/evaluations/day-${String(n).padStart(2, "0")}.json`, null);
  if (DAY_TABS.left === "eval" && location.hash === `#/day/${n}`) $("#lbody").innerHTML = dayEvaluation(day(n));
  if (!S.helper) return;
  const st = await api(`/api/evaluate?day=${n}`).catch(() => ({ status: "idle" }));
  const el = $("#eval-status");
  if (st.status === "running") {
    if (el) el.innerHTML = `<span class="spinner"></span> Claude is grading…`;
    setTimeout(() => location.hash === `#/day/${n}` && pollEval(n), 4000);
  } else if (st.status === "done") {
    S.evals[n] = st.result; S.errors = await getJSON("data/errors.json", S.errors);
    if (location.hash === `#/day/${n}` && DAY_TABS.left === "eval") $("#lbody").innerHTML = dayEvaluation(day(n));
    renderActions(day(n));
  } else if (st.status === "error" && el) {
    el.innerHTML = `<span style="color:var(--red)">Failed: ${esc(st.error).slice(0, 300)}</span>`;
  }
}
async function renderActions(d) {
  const el = $("#actions");
  if (!el) return;
  if (!S.helper) {
    el.innerHTML = `<span class="note">Start the helper (<code>bin/study</code>) to download Overleaf, evaluate and finish.</span>`;
    return;
  }
  const fin = await api(`/api/finish-state?day=${d.n}`).catch(() => ({ ok: false, message: "helper error" }));
  const evalRunning = (await api(`/api/evaluate?day=${d.n}`).catch(() => ({}))).status === "running";
  el.innerHTML = `
    <button class="btn" id="btn-pull" title="Delete the saved Overleaf copy in the repo and download it again">⟳ Download Overleaf PDF</button>
    <button class="btn" id="btn-eval" ${evalRunning || !S.meta.pulled_at ? "disabled" : ""} title="${S.meta.pulled_at ? "Grade today's answers with Claude Code" : "Download the Overleaf PDF first"}">
      ${evalRunning ? '<span class="spinner"></span> Evaluating…' : "▶ Evaluate"}</button>
    <span class="spacer"></span>
    <span class="note" style="max-width:240px">${isDone(d.n) ? "" : esc(fin.message)}</span>
    <button class="btn green" id="btn-finish" ${fin.ok ? "" : "disabled"}>${isDone(d.n) ? "✓ Finished" : "Finish & push"}</button>`;
  $("#btn-pull").onclick = async (ev) => {
    const b = ev.currentTarget; b.disabled = true; b.innerHTML = '<span class="spinner"></span> Downloading…';
    try {
      S.meta = await api("/api/overleaf/pull", {});
      toast(`Overleaf downloaded (${S.meta.files.length} files)`);
      if (DAY_TABS.right === "overleaf") document.querySelector('#rtabs .tab[data-k="overleaf"]').click();
    } catch (e) { toast(e.message, true); }
    renderActions(d);
  };
  $("#btn-eval").onclick = async () => {
    try {
      await api("/api/evaluate", { day: d.n });
      toast("Claude Code is grading today's answers. This takes a few minutes.");
      document.querySelector('#ltabs .tab[data-k="eval"]').click();
      renderActions(d);
    } catch (e) { toast(e.message, true); }
  };
  $("#btn-finish").onclick = async (ev) => {
    if (!confirm(`Finish Day ${d.n}? This commits everything and pushes to GitHub.`)) return;
    const b = ev.currentTarget; b.disabled = true; b.innerHTML = '<span class="spinner"></span> Pushing…';
    try {
      const r = await api("/api/finish", { day: d.n });
      S.progress.finished[String(d.n)] = r.finished_at;
      toast(`Day ${d.n} finished and pushed (${r.commit}). Tomorrow's reminder covers Day ${d.n + 1}.`);
      renderDay(d.n);
    } catch (e) { toast(e.message, true); renderActions(d); }
  };
}

// ------------------------------------------------------------------ errors
function renderErrors() {
  const today = todayWIB();
  const filter = store.get("errFilter", "All");
  const rows = S.errors.filter((e) => filter === "All" || e.why === filter).slice().reverse();
  const counts = ["Concept", "Calculation", "Careless", "Coding"].map((w) => [w, S.errors.filter((e) => e.why === w).length]);
  $("#app").innerHTML = `<div class="page">
    <div class="eyebrow">Error log</div><h1>Error Checks</h1>
    <p class="sub">Log errors, not notes. Retry each missed question the next day, three days later, and in the final week.</p>
    <div class="row" style="margin:16px 0">
      ${["All", ...counts.map((c) => c[0])].map((w) => `<button class="btn small ${w === filter ? "primary" : ""}" data-f="${w}">${w}${w !== "All" ? ` · ${counts.find((c) => c[0] === w)[1]}` : ` · ${S.errors.length}`}</button>`).join("")}
    </div>
    <div class="table-wrap"><table class="table">
      <thead><tr><th>Date</th><th>Topic</th><th>Question / task</th><th>Why I missed it</th><th>Correct rule / idea</th><th>Retry 1</th><th>Retry 2</th><th>Retry 3</th><th></th></tr></thead>
      <tbody>${rows.length ? rows.map((e) => `<tr>
        <td style="white-space:nowrap">${e.date}<div class="faint" style="font-size:12px">${e.day ? `<a href="#/day/${e.day}">Day ${e.day}</a>` : ""}</div></td>
        <td>${esc(e.topic)}</td>
        <td>${esc(e.question)}${e.wrong_reasoning ? `<div class="faint" style="font-size:12px;margin-top:4px">You: ${esc(e.wrong_reasoning)}</div>` : ""}</td>
        <td><span class="why ${e.why}">${e.why}</span></td>
        <td>${esc(e.correct_rule)}</td>
        ${e.retry.map((r, i) => `<td><label class="retry ${!e.retry_done[i] && r <= today ? "due" : ""}">
          <input type="checkbox" ${e.retry_done[i] ? "checked" : ""} ${S.helper ? "" : "disabled"} data-err="${e.id}" data-i="${i}">${r.slice(5)}</label></td>`).join("")}
        <td>${S.helper ? `<button class="btn small" data-del="${e.id}" title="Delete">✕</button>` : ""}</td></tr>`).join("")
        : `<tr><td colspan="9"><div class="empty" style="border:0">No errors logged${filter !== "All" ? " in this category" : ""}.</div></td></tr>`}</tbody>
    </table></div>

    ${S.helper ? `<h2>Add an error manually</h2>
    <form class="card" id="err-form"><div class="form-grid">
      <input type="text" name="topic" placeholder="Topic (e.g. Bayes' rule)" required>
      <input type="text" name="day" placeholder="Day # (optional)">
      <select name="why"><option>Concept</option><option>Calculation</option><option>Careless</option><option>Coding</option></select>
    </div>
    <div class="form-grid" style="margin-top:10px">
      <textarea name="question" placeholder="Question / task" required></textarea>
      <textarea name="wrong_reasoning" placeholder="What I did (wrong reasoning)"></textarea>
      <textarea name="correct_rule" placeholder="Correct rule / idea" required></textarea>
    </div><div class="row" style="margin-top:10px"><span class="spacer"></span><button class="btn primary">Add to log</button></div></form>` : ""}

    <h2>Suggested performance thresholds</h2>
    <div class="card"><div class="legend">
      <span class="g"><b>Green</b>: 80%+ on fresh questions and you can explain the reasoning. Move on.</span>
      <span class="y"><b>Yellow</b>: 60–79% or repeated hesitation. Another small set within 48 hours.</span>
      <span class="r"><b>Red</b>: below 60% or you can't start without notes. Review the subsection, then 3 similar questions.</span>
    </div><p class="note" style="margin-bottom:0">Don't judge readiness by recognition. Readiness means solving a fresh question without notes and explaining why the method works.</p></div>
  </div>`;
  document.querySelectorAll("[data-f]").forEach((b) => (b.onclick = () => { store.set("errFilter", b.dataset.f); renderErrors(); }));
  document.querySelectorAll("[data-err]").forEach((cb) => (cb.onchange = async () => {
    try { S.errors = await api("/api/errors/update", { id: cb.dataset.err, retry_index: +cb.dataset.i, value: cb.checked }); renderErrors(); }
    catch (e) { toast(e.message, true); }
  }));
  document.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!confirm("Delete this error entry?")) return;
    try { S.errors = await api("/api/errors/update", { id: b.dataset.del, delete: true }); renderErrors(); } catch (e) { toast(e.message, true); }
  }));
  const form = $("#err-form");
  if (form) form.onsubmit = async (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(form));
    f.day = f.day ? +f.day : null;
    try { S.errors = await api("/api/errors/add", f); toast("Added to the error log"); renderErrors(); } catch (e) { toast(e.message, true); }
  };
}

// ------------------------------------------------------------------ timer
function initTimer() {
  const el = $("#timer"), text = $("#timer-text");
  let st = store.get("timer", { start: null, acc: 0 });
  const tick = () => {
    const ms = st.acc + (st.start ? Date.now() - st.start : 0);
    const s = Math.floor(ms / 1000), h = Math.floor(s / 3600);
    text.textContent = (h ? `${h}:` : "") + `${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    el.classList.toggle("running", Boolean(st.start));
  };
  el.onclick = () => {
    st = st.start ? { start: null, acc: st.acc + Date.now() - st.start } : { start: Date.now(), acc: st.acc };
    store.set("timer", st); tick();
  };
  el.ondblclick = () => { st = { start: null, acc: 0 }; store.set("timer", st); tick(); };
  setInterval(tick, 1000); tick();
}

// ------------------------------------------------------------------ boot
(async function main() {
  initTimer();
  await detectHelper();
  await loadData();
  if (!S.plan) { $("#app").innerHTML = `<div class="page"><div class="empty">Could not load data/plan.json.</div></div>`; return; }
  window.addEventListener("hashchange", route);
  route();
})();
