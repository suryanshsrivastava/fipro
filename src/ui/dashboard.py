import csv
import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import List


HTML_TEMPLATE = '''
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
  tr:hover { background: #1e293b; }
  td { padding: 9px 14px; white-space: nowrap; }
  td.amount { font-variant-numeric: tabular-nums; }
  td.debit { color: #f87171; }
  td.credit { color: #4ade80; }
  td.transfer { color: #fbbf24; }
  td.account { background: #334155; border-radius: 4px; padding: 2px 8px; font-size: 12px; }
  .empty { padding: 60px; text-align: center; color: #64748b; }
  .footer { padding: 10px 24px; border-top: 1px solid #1e293b; font-size: 12px; color: #475569; display: flex; justify-content: space-between; }
  @media (max-width: 768px) { .toolbar { flex-direction: column; align-items: stretch; } .toolbar input { width: 100%; } }
</style>
</head>
<body>
<header>
  <h1>Fipro Dashboard</h1>
  <div class=subtitle id=filename>Loading...</div>
</header>
<div class=toolbar>
  <input type=text id=search placeholder=\"Search description...\" oninput=\"render()\">
  <select id=bank_filter onchange=\"render()\"><option value=\"\">All banks</option></select>
  <select id=type_filter onchange=\"render()\"><option value=\"\">All types</option><option value=debit>Debit</option><option value=credit>Credit</option><option value=internal_transfer>Transfer</option></select>
  <div class=stat-badge>Total <span class=val id=total>0</span></div>
  <div class=stat-badge>Filtered <span class=val id=filtered>0</span></div>
  <div class=stat-badge>Net <span class=val id=net>0</span></div>
  <div class=stat-badge><a href="/summary" style="color:#38bdf8;text-decoration:none;">Monthly summary</a></div>
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
const COLS = ['transaction_date','description','amount','transaction_type','source_bank','source_file','status','notes'];
const DIR = {transaction_date:1, description:1, amount:1, transaction_type:1, source_bank:1};
let sortCol='transaction_date', sortDir=-1, search='', bank='', type='';

function setStickyOffsets() {
  const hh = document.querySelector('header').offsetHeight;
  const toolbar = document.querySelector('.toolbar');
  toolbar.style.top = hh + 'px';
  document.querySelector('thead').style.top = (hh + toolbar.offsetHeight) + 'px';
}
window.addEventListener('resize', setStickyOffsets);

function init() {
  const th = document.getElementById('thead');
  th.innerHTML = COLS.map(c => `<th data-col=${c} onclick=\"toggleSort('${c}')\">${c.replace(/_/g,' ')}<span class=arrow>▼</span></th>`).join('');
  const banks = [...new Set(DATA.map(r=>r.source_bank))].sort();
  const sel = document.getElementById('bank_filter');
  sel.innerHTML = '<option value=\"\">All banks</option>' + banks.map(b=>`<option value=${b}>${b}</option>`).join('');
  search = document.getElementById('search').value;
  bank = sel.value; type = document.getElementById('type_filter').value;
  setStickyOffsets();
  render();
}

function toggleSort(col) {
  if (sortCol===col) sortDir*=-1; else { sortCol=col; sortDir=1; }
  document.querySelectorAll('th').forEach(t=>t.classList.remove('sorted'));
  document.querySelector(`th[data-col=${col}]`).classList.add('sorted');
  render();
}

function render() {
  search = document.getElementById('search').value.toLowerCase();
  bank = document.getElementById('bank_filter').value;
  type = document.getElementById('type_filter').value;
  let rows = DATA.filter(r => {
    if (search && !r.description.toLowerCase().includes(search)) return false;
    if (bank && r.source_bank !== bank) return false;
    if (type && r.transaction_type !== type && r.status !== 'internal_transfer') return false;
    return true;
  });
  const sortFn = (a,b) => {
    let va=a[sortCol], vb=b[sortCol];
    if (sortCol==='amount') { va=parseFloat(va)||0; vb=parseFloat(vb)||0; }
    if (va<vb) return -sortDir; if (va>vb) return sortDir; return 0;
  };
  rows = rows.sort(sortFn);
  const body = document.getElementById('tbody');
  body.innerHTML = rows.map(r => {
    const amt = parseFloat(r.amount)||0;
    const cls = r.status==='internal_transfer' ? 'transfer' : (amt<0 ? 'debit' : 'credit');
    return `<tr>
      <td>${r.transaction_date}</td>
      <td title=\"${r.description}\">${r.description.length>45?r.description.slice(0,45)+'…':r.description}</td>
      <td class=\"amount ${cls}\">${amt<0?'−':'+'}${Math.abs(amt).toLocaleString('en-IN',{minimumFractionDigits:2})}</td>
      <td>${r.transaction_type}</td>
      <td><span class=account>${r.source_bank}</span></td>
      <td title=\"${r.source_file}\">${r.source_file.split('/').pop()}</td>
      <td>${r.status}</td>
      <td title=\"${r.notes||''}\">${(r.notes||'').slice(0,30)}</td>
    </tr>`;
  }).join('');
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
'''

SUMMARY_TEMPLATE = '''
<!DOCTYPE html>
<html lang=en>
<head>
<meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Fipro Monthly Summary</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }
  header { background: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px; position: sticky; top: 0; z-index: 100; }
  h1 { font-size: 20px; font-weight: 600; color: #f1f5f9; margin-bottom: 4px; }
  .subtitle { font-size: 13px; color: #94a3b8; }
  .toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; padding: 14px 24px; background: #1e293b; border-bottom: 1px solid #1e293b; }
  .toolbar select { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 7px 12px; font-size: 13px; }
  .layout { padding: 16px 24px 24px; display: grid; gap: 12px; }
  .month-total { border: 1px solid #334155; border-radius: 10px; background: #111827; padding: 12px; display: grid; grid-template-columns: repeat(4, minmax(130px, 1fr)); gap: 10px; }
  .metric { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px; }
  .label { color: #94a3b8; font-size: 12px; margin-bottom: 6px; }
  .value { font-size: 18px; font-weight: 600; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 12px; }
  .card { border: 1px solid #334155; border-radius: 10px; background: #111827; padding: 12px; }
  .card h3 { font-size: 14px; margin-bottom: 8px; color: #cbd5e1; }
  .section-title { font-size: 12px; color: #94a3b8; margin: 8px 0 4px; }
  .row { display: flex; justify-content: space-between; font-size: 13px; padding: 2px 0; }
  .top-item { font-size: 12px; color: #cbd5e1; padding: 2px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .debit { color: #f87171; }
  .credit { color: #4ade80; }
  .transfer { color: #fbbf24; }
  .nav { margin-left: auto; font-size: 12px; }
  .nav a { color: #38bdf8; text-decoration: none; margin-left: 10px; }
</style>
</head>
<body>
<header>
  <h1>Fipro Monthly Consolidation</h1>
  <div class=subtitle>Monthly totals with weekly checkpoints</div>
</header>
<div class=toolbar>
  <label for=month>Select month:</label>
  <select id=month onchange="render()"></select>
  <div class=nav><a href="/">Transactions</a><a href="/summary">Summary</a></div>
</div>
<div class=layout>
  <div class=month-total id=month_total></div>
  <div class=cards id=cards></div>
</div>
<script>
const DATA = {{DATA}};
const TOP_N = {{TOP_N}};

function parseTxn(row) {
  const signed = parseFloat(row.amount ?? row.Amount ?? 0) || 0;
  return {
    date: new Date((row.transaction_date || row.Date) + 'T00:00:00'),
    description: row.description || row.Name || '',
    signed,
    source_bank: row.source_bank || row.Account || 'UNKNOWN',
    status: (row.status || row.Status || '').toLowerCase(),
  };
}

function monthKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
}

function monthRange(year, monthIndex) {
  const start = new Date(year, monthIndex, 1);
  const end = new Date(year, monthIndex + 1, 0);
  return { start, end };
}

function saturdayCheckpoints(year, monthIndex) {
  const { start, end } = monthRange(year, monthIndex);
  const checkpoints = [];
  let cursor = new Date(start);
  while (cursor <= end) {
    const sliceStart = new Date(cursor);
    const daysUntilSat = (6 - cursor.getDay() + 7) % 7;
    const sliceEnd = new Date(cursor);
    sliceEnd.setDate(sliceEnd.getDate() + daysUntilSat);
    if (sliceEnd > end) sliceEnd.setTime(end.getTime());
    checkpoints.push({ start: sliceStart, end: sliceEnd });
    cursor = new Date(sliceEnd);
    cursor.setDate(cursor.getDate() + 1);
  }
  return checkpoints;
}

function metrics(txns) {
  let spend = 0;
  let income = 0;
  let transfer_total = 0;
  const per_bank = {};
  for (const txn of txns) {
    if (!per_bank[txn.source_bank]) per_bank[txn.source_bank] = { spend: 0, income: 0, net: 0, transfer_total: 0 };
    const bank = per_bank[txn.source_bank];
    if (txn.status === 'internal_transfer') {
      transfer_total += Math.abs(txn.signed);
      bank.transfer_total += Math.abs(txn.signed);
      continue;
    }
    if (txn.signed < 0) {
      spend += Math.abs(txn.signed);
      bank.spend += Math.abs(txn.signed);
    } else {
      income += txn.signed;
      bank.income += txn.signed;
    }
    bank.net = bank.income - bank.spend;
  }
  return {
    spend, income, net: income - spend, transfer_total, per_bank,
    top: [...txns].sort((a,b) => Math.abs(b.signed) - Math.abs(a.signed)).slice(0, TOP_N),
  };
}

function fmt(amount) {
  const sign = amount >= 0 ? '+' : '-';
  return `${sign}${Math.abs(amount).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
}

function init() {
  const txns = DATA.map(parseTxn).filter(t => !Number.isNaN(t.date.getTime()));
  const months = [...new Set(txns.map(t => monthKey(t.date)))].sort();
  const select = document.getElementById('month');
  select.innerHTML = months.map(m => `<option value="${m}">${m}</option>`).join('');
  if (months.length) select.value = months[months.length - 1];
  window.__summaryTransactions = txns;
  render();
}

function render() {
  const select = document.getElementById('month');
  if (!select.value) return;
  const [yearStr, monthStr] = select.value.split('-');
  const year = Number(yearStr);
  const monthIndex = Number(monthStr) - 1;
  const txns = window.__summaryTransactions.filter(t => t.date.getFullYear() === year && t.date.getMonth() === monthIndex);
  txns.sort((a,b) => a.date - b.date);

  const checkpoints = saturdayCheckpoints(year, monthIndex);
  const cards = [];
  for (let i = 0; i < checkpoints.length; i++) {
    const c = checkpoints[i];
    const weekTxns = txns.filter(t => t.date >= c.start && t.date <= c.end);
    const mtdTxns = txns.filter(t => t.date >= checkpoints[0].start && t.date <= c.end);
    const week = metrics(weekTxns);
    const mtd = metrics(mtdTxns);
    const top = week.top.map(t => `<div class=top-item>${t.date.toISOString().slice(0,10)} | ${t.source_bank} | ${fmt(t.signed)} | ${t.description}</div>`).join('') || '<div class=top-item>—</div>';
    const bankRows = Object.entries(week.per_bank).sort(([a],[b]) => a.localeCompare(b))
      .map(([name, val]) => `<div class=row><span>${name}</span><span>spend ${fmt(-val.spend)} | income ${fmt(val.income)} | net ${fmt(val.net)}</span></div>`)
      .join('') || '<div class=row><span>—</span><span>—</span></div>';
    cards.push(`
      <div class=card>
        <h3>Week ${i+1}: ${c.start.toISOString().slice(0,10)} to ${c.end.toISOString().slice(0,10)}</h3>
        <div class=section-title>Week slice</div>
        <div class=row><span>Spend</span><span class=debit>${fmt(-week.spend)}</span></div>
        <div class=row><span>Income</span><span class=credit>${fmt(week.income)}</span></div>
        <div class=row><span>Net</span><span>${fmt(week.net)}</span></div>
        <div class=row><span>Transfers</span><span class=transfer>${fmt(week.transfer_total)}</span></div>
        <div class=section-title>Month-to-date</div>
        <div class=row><span>MTD Spend</span><span class=debit>${fmt(-mtd.spend)}</span></div>
        <div class=row><span>MTD Income</span><span class=credit>${fmt(mtd.income)}</span></div>
        <div class=row><span>MTD Net / Running</span><span>${fmt(mtd.net)}</span></div>
        <div class=section-title>Per-bank (week)</div>
        ${bankRows}
        <div class=section-title>Top transactions (week)</div>
        ${top}
      </div>
    `);
  }

  const monthStats = metrics(txns);
  document.getElementById('month_total').innerHTML = `
    <div class=metric><div class=label>Month Spend</div><div class="value debit">${fmt(-monthStats.spend)}</div></div>
    <div class=metric><div class=label>Month Income</div><div class="value credit">${fmt(monthStats.income)}</div></div>
    <div class=metric><div class=label>Month Net</div><div class=value>${fmt(monthStats.net)}</div></div>
    <div class=metric><div class=label>Transfers</div><div class="value transfer">${fmt(monthStats.transfer_total)}</div></div>
  `;
  document.getElementById('cards').innerHTML = cards.join('');
}

init();
</script>
</body>
</html>
'''

def load_csv_data(csv_path: str) -> List[dict]:
    with open(csv_path, newline='') as f:
        return list(csv.DictReader(f))


def serve_dashboard(csv_path: str = 'data/output/goodbudget_export.csv', port: int = 8080, summary_top_n: int = 5):
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    rows = load_csv_data(csv_path)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/index.html':
                html = HTML_TEMPLATE.replace('{{DATA}}', json.dumps(rows, default=str))
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode())
            elif self.path == '/summary':
                html = SUMMARY_TEMPLATE.replace('{{DATA}}', json.dumps(rows, default=str))
                html = html.replace('{{TOP_N}}', str(summary_top_n))
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode())
            elif self.path == '/data':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(rows, default=str).encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, fmt, *args):
            pass  # silence request logs

    server = HTTPServer(('127.0.0.1', port), Handler)
    url = f'http://localhost:{port}'
    print(f'Dashboard: {url}')
    webbrowser.open(url)
    server.serve_forever()


def start_dashboard_thread(csv_path: str = 'data/output/goodbudget_export.csv', port: int = 8080):
    t = threading.Thread(target=serve_dashboard, args=(csv_path, port), daemon=True)
    t.start()
    return t
