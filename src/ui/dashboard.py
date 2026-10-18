import json
import threading
import webbrowser
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from src.config import Settings
from src.connectors.gmail import load_password_hints
from src.core.ingestion import discover_files
from src.core.orchestrator import process_pipeline
from src.core.parser_registry import is_locked_statement
from src.core.statement_passwords import load_statement_passwords
from src.exporters.report import summarize_pipeline_run
from src.ui.dashboard_data import load_csv_data as _load_csv_data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang=en>
<head>
<meta charset=UTF-8>
<meta name=viewport content=\"width=device-width,initial-scale=1\">
<title>Fipro Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }
  header { background: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px; position: sticky; top: 0; z-index: 100; }
  h1 { font-size: 20px; font-weight: 600; color: #f1f5f9; margin-bottom: 4px; }
  .subtitle { font-size: 13px; color: #94a3b8; }
  .toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; padding: 14px 24px; background: #1e293b; border-bottom: 1px solid #1e293b; position: sticky; top: 0; z-index: 90; }
  .toolbar input, .toolbar select { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 7px 12px; font-size: 13px; }
  .toolbar input { width: 220px; }
  .stat-badge { background: #334155; border: 1px solid #475569; border-radius: 6px; padding: 6px 14px; font-size: 12px; display: flex; gap: 6px; align-items: center; }
  .stat-badge .val { color: #38bdf8; font-weight: 600; }
  .table-wrap { overflow-x: clip; padding: 0 24px 24px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  thead { position: sticky; top: 0; z-index: 50; }
  th { background: #1e293b; color: #94a3b8; font-weight: 500; text-align: left; padding: 10px 14px; cursor: pointer; user-select: none; white-space: nowrap; }
  th:hover { color: #e2e8f0; }
  th .arrow { margin-left: 4px; opacity: 0.4; }
  th.sorted .arrow { opacity: 1; }
  tr { border-bottom: 1px solid #1e293b; transition: background 0.1s; }
  th:nth-child(2), td:nth-child(2) { width: 100%; max-width: 0; overflow: hidden; text-overflow: ellipsis; }
  td:nth-child(7) { max-width: 180px; overflow: hidden; text-overflow: ellipsis; }
  tr:hover { background: #1e293b; }
  tr.spacer, tr.spacer:hover { border: 0; background: none; }
  td { padding: 9px 14px; white-space: nowrap; }
  td.amount { font-variant-numeric: tabular-nums; }
  td.debit { color: #f87171; }
  td.credit { color: #4ade80; }
  td.transfer { color: #fbbf24; }
  td.account { background: #334155; border-radius: 4px; padding: 2px 8px; font-size: 12px; }
  .empty { padding: 60px; text-align: center; color: #64748b; }
  .footer { padding: 10px 24px; border-top: 1px solid #1e293b; font-size: 12px; color: #475569; display: flex; justify-content: space-between; }
  #locked { padding: 16px 24px 0; display: grid; gap: 12px; }
  .lock-card { background: #1e293b; border: 1px solid #f59e0b; border-radius: 8px; padding: 14px 16px; }
  .lock-card h2 { font-size: 15px; font-weight: 600; color: #fbbf24; margin-bottom: 6px; }
  .lock-card .files { font-size: 12px; color: #94a3b8; margin-bottom: 8px; }
  .lock-card .hint { font-size: 13px; color: #e2e8f0; background: #0f1117; border-radius: 6px; padding: 8px 10px; margin-bottom: 10px; }
  .lock-card .hint.missing { color: #94a3b8; font-style: italic; }
  .lock-card form { display: flex; gap: 8px; flex-wrap: wrap; }
  .lock-card input { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 7px 12px; font-size: 13px; width: 260px; }
  .lock-card button { background: #f59e0b; color: #0f1117; border: 0; border-radius: 6px; padding: 7px 14px; font-weight: 600; cursor: pointer; }
  .lock-card button:disabled { opacity: 0.5; cursor: wait; }
  .lock-status { white-space: pre-wrap; font-size: 12px; color: #94a3b8; margin-top: 8px; }
  @media (max-width: 768px) { .toolbar { flex-direction: column; align-items: stretch; } .toolbar input { width: 100%; } }
</style>
</head>
<body>
<header>
  <h1>Fipro Dashboard</h1>
  <div class=subtitle id=summary>—</div>
</header>
<section id=locked aria-label="Locked statements"></section>
<div class=toolbar>
  <input type=text id=search placeholder=\"Search description...\" oninput=\"render()\">
  <select id=bank_filter onchange=\"render()\"><option value=\"\">All banks</option></select>
  <select id=type_filter onchange=\"render()\"><option value=\"\">All types</option><option value=debit>Debit</option><option value=credit>Credit</option><option value=internal_transfer>Transfer</option></select>
  <div class=stat-badge>Total <span class=val id=total>0</span></div>
  <div class=stat-badge>Filtered <span class=val id=filtered>0</span></div>
  <div class=stat-badge>Net <span class=val id=net>0</span></div>
</div>
<div class=table-wrap>
  <table id=table>
    <thead id=thead></thead>
    <tbody id=tbody></tbody>
  </table>
  <div class=empty id=empty style=\"display:none\">No transactions match your filters.</div>
</div>
<div class=footer>
  <span id=range>—</span>
  <span>Fipro</span>
</div>
<script>
const DATA = {{DATA}};
const LOCKED = {{LOCKED}};

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderLocked() {
  const box = document.getElementById('locked');
  if (!LOCKED.length) { box.style.display = 'none'; return; }
  box.replaceChildren(...LOCKED.map(item => {
    const card = el('div', 'lock-card');
    card.append(el('h2', null, `🔒 ${item.bank}: ${item.files.length} password-protected statement(s)`));
    card.append(el('div', 'files', item.files.join(', ')));
    card.append(item.hint
      ? el('div', 'hint', `Hint from your bank's email (${item.received}): ${item.hint}`)
      : el('div', 'hint missing', 'No hint yet. Run `fipro gmail` to fetch it from the bank email.'));
    const form = el('form');
    const input = Object.assign(el('input'), {type: 'password', required: true, autocomplete: 'off', placeholder: `${item.bank} statement password`});
    const button = el('button', null, 'Unlock & process');
    const status = el('div', 'lock-status');
    form.append(input, button);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      button.disabled = true;
      status.textContent = 'Processing…';
      try {
        const res = await fetch('/unlock', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({passwords: {[item.bank]: input.value}})});
        const out = await res.json();
        status.textContent = res.ok ? out.lines.join('\\n') : out.error;
        if (res.ok && !out.locked.some(name => item.files.includes(name))) setTimeout(() => location.reload(), 1500);
      } catch (err) {
        status.textContent = String(err);
      } finally {
        input.value = '';
        button.disabled = false;
      }
    });
    card.append(form, status);
    return card;
  }));
}
const COLS = ['transaction_date','description','amount','transaction_type','source_bank','status','notes'];
const DIR = {transaction_date:1, description:1, amount:1, transaction_type:1, source_bank:1};
let sortCol='transaction_date', sortDir=1, search='', bank='', type='';

function setStickyOffsets() {
  const hh = document.querySelector('header').offsetHeight;
  const toolbar = document.querySelector('.toolbar');
  toolbar.style.top = hh + 'px';
  document.querySelector('thead').style.top = (hh + toolbar.offsetHeight) + 'px';
}
window.addEventListener('resize', setStickyOffsets);

function renderSummary() {
  const dates = DATA.map(r => r.transaction_date).filter(Boolean).sort();
  const count = `${DATA.length} transaction${DATA.length === 1 ? '' : 's'}`;
  document.getElementById('summary').textContent =
    dates.length ? `${count} · ${dates[0]} → ${dates[dates.length - 1]}` : count;
}

function init() {
  const th = document.getElementById('thead');
  th.innerHTML = COLS.map(c => `<th data-col=${c} onclick=\"toggleSort('${c}')\">${c.replace(/_/g,' ')}<span class=arrow>▼</span></th>`).join('');
  const banks = [...new Set(DATA.map(r=>r.source_bank))].sort();
  const sel = document.getElementById('bank_filter');
  sel.innerHTML = '<option value=\"\">All banks</option>' + banks.map(b=>`<option value=${b}>${b}</option>`).join('');
  search = document.getElementById('search').value;
  bank = sel.value; type = document.getElementById('type_filter').value;
  renderSummary();
  renderLocked();
  setStickyOffsets();
  render();
}

function toggleSort(col) {
  if (sortCol===col) sortDir*=-1; else { sortCol=col; sortDir=1; }
  render();
}

function paintSortArrows() {
  document.querySelectorAll('th[data-col]').forEach(t => {
    const active = t.dataset.col === sortCol;
    t.classList.toggle('sorted', active);
    t.querySelector('.arrow').textContent = active ? (sortDir === 1 ? '▲' : '▼') : '↕';
  });
}

let view = [], rowH = 37, drawing = false;

function rowHtml(r) {
  const amt = parseFloat(r.amount)||0;
  const cls = r.status==='internal_transfer' ? 'transfer' : (amt<0 ? 'debit' : 'credit');
  return `<tr>
    <td>${r.transaction_date}</td>
    <td title=\"${r.description}\">${r.description.length>45?r.description.slice(0,45)+'…':r.description}</td>
    <td class=\"amount ${cls}\">${amt<0?'−':'+'}${Math.abs(amt).toLocaleString('en-IN',{minimumFractionDigits:2})}</td>
    <td>${r.transaction_type}</td>
    <td><span class=account>${r.source_bank}</span></td>
    <td>${r.status}</td>
    <td title=\"${r.notes||''}\">${(r.notes||'').slice(0,30)}</td>
  </tr>`;
}

// Only the rows near the viewport are in the DOM; spacer rows keep the scrollbar the size of the full table.
function drawWindow() {
  const body = document.getElementById('tbody');
  const top = body.getBoundingClientRect().top + window.scrollY;
  const first = Math.max(0, Math.floor((window.scrollY - top) / rowH) - 20);
  const last = Math.min(view.length, first + Math.ceil(window.innerHeight / rowH) + 40);
  const spacer = n => `<tr class=spacer style="height:${n * rowH}px"></tr>`;
  body.innerHTML = spacer(first) + view.slice(first, last).map(rowHtml).join('') + spacer(view.length - last);
  const sample = body.querySelector('tr:not(.spacer)');
  if (sample && Math.abs(sample.getBoundingClientRect().height - rowH) > 0.5) { rowH = sample.getBoundingClientRect().height; drawWindow(); }
}

window.addEventListener('scroll', () => {
  if (drawing) return;
  drawing = true;
  requestAnimationFrame(() => { drawWindow(); drawing = false; });
});

function render() {
  paintSortArrows();
  search = document.getElementById('search').value.toLowerCase();
  bank = document.getElementById('bank_filter').value;
  type = document.getElementById('type_filter').value;
  let rows = DATA.filter(r => {
    if (search && !r.description.toLowerCase().includes(search)) return false;
    if (bank && r.source_bank !== bank) return false;
    if (type === 'internal_transfer') return r.status === 'internal_transfer';
    if (type && r.transaction_type !== type) return false;
    if (type && r.status === 'internal_transfer') return false;
    return true;
  });
  const sortFn = (a,b) => {
    let va=a[sortCol], vb=b[sortCol];
    if (sortCol==='amount') { va=parseFloat(va)||0; vb=parseFloat(vb)||0; }
    if (va<vb) return -sortDir; if (va>vb) return sortDir; return 0;
  };
  rows = rows.sort(sortFn);
  view = rows;
  drawWindow();
  document.getElementById('empty').style.display = rows.length ? 'none' : 'block';
  const filtered = rows.length;
  const net = rows.reduce((s,r)=>s+(parseFloat(r.amount)||0),0);
  document.getElementById('total').textContent = DATA.length;
  document.getElementById('filtered').textContent = filtered;
  document.getElementById('net').textContent = (net<0?'−':'+')+Math.abs(net).toLocaleString('en-IN',{minimumFractionDigits:2});
  const dates = rows.map(r=>r.transaction_date).filter(Boolean).sort();
  document.getElementById('range').textContent = dates.length ? (dates[0]+' → '+dates[dates.length-1]) : '—';
}

init();
</script>
</body>
</html>
"""


def load_csv_data(csv_path: str) -> list[dict]:
    """Compatibility wrapper around normalized dashboard data loader."""
    return _load_csv_data(csv_path)


def locked_statements(settings: Settings) -> list[dict]:
    """Statements that cannot be opened with the saved passwords, grouped by bank, with any saved Gmail hint."""
    passwords = load_statement_passwords(settings.paths.statement_passwords)
    by_bank: dict[str, list[str]] = defaultdict(list)
    for crawled in discover_files(settings):
        bank = crawled.metadata.get("bank", "UNKNOWN")
        if is_locked_statement(crawled.filepath, bank, passwords):
            by_bank[bank].append(crawled.filename)
    hints = load_password_hints(settings.paths.password_hints)
    return [
        {
            "bank": bank,
            "files": sorted(files),
            "hint": hints.get(bank, {}).get("hint"),
            "received": hints.get(bank, {}).get("received"),
        }
        for bank, files in sorted(by_bank.items())
    ]


def _script_json(value: object) -> str:
    """JSON safe to inline in <script>: email-derived text must not be able to close the tag."""
    return json.dumps(value, default=str).replace("<", "\\u003c")


def build_server(csv_path: str, port: int, settings: Settings | None = None) -> HTTPServer:
    def current_rows() -> list[dict]:
        return load_csv_data(csv_path) if Path(csv_path).exists() else []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                locked = locked_statements(settings) if settings else []
                html = HTML_TEMPLATE.replace("{{DATA}}", _script_json(current_rows())).replace(
                    "{{LOCKED}}", _script_json(locked)
                )
                self._send(200, "text/html; charset=utf-8", html.encode())
            elif self.path == "/data":
                self._send_json(200, current_rows())
            else:
                self._send(404, "text/plain", b"")

        def do_POST(self):
            if self.path != "/unlock" or settings is None:
                self._send_json(404, {"error": "not found"})
                return
            # JSON-only + same-origin: a page on another site cannot trigger processing through the browser.
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                self._send_json(415, {"error": "expected application/json"})
                return
            # Checking Host as well as Origin also blocks DNS-rebinding pages that resolve to 127.0.0.1.
            local_hosts = {f"localhost:{server.server_port}", f"127.0.0.1:{server.server_port}"}
            origin = self.headers.get("Origin")
            if self.headers.get("Host") not in local_hosts or (
                origin is not None and origin not in {f"http://{h}" for h in local_hosts}
            ):
                self._send_json(403, {"error": "cross-origin request refused"})
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                passwords = {str(bank).upper(): str(pw) for bank, pw in body.get("passwords", {}).items() if pw}
                run = process_pipeline(settings, passwords=passwords)
            except Exception as exc:  # report to the page; the server keeps running
                self._send_json(500, {"error": f"Processing failed: {exc}"})
                return
            self._send_json(
                200,
                {
                    "lines": summarize_pipeline_run(run),
                    "locked": [Path(path).name for path in run.locked_files],
                },
            )

        def _send_json(self, status: int, payload: object) -> None:
            self._send(status, "application/json", json.dumps(payload, default=str).encode())

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass  # silence request logs

    server = HTTPServer(("127.0.0.1", port), Handler)  # port 0 picks a free port; handlers read the bound one
    return server


def serve_dashboard(
    csv_path: str = "corpus/output/dashboard_data.csv",
    port: int = 8080,
    open_browser: bool = False,
    settings: Settings | None = None,
):
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    server = build_server(csv_path, port, settings)
    url = f"http://localhost:{port}"
    print(f"Dashboard: {url}")
    if open_browser:
        webbrowser.open(url)
    server.serve_forever()


def start_dashboard_thread(
    csv_path: str = "corpus/output/dashboard_data.csv", port: int = 8080, open_browser: bool = False
):
    t = threading.Thread(target=serve_dashboard, args=(csv_path, port, open_browser), daemon=True)
    t.start()
    return t
