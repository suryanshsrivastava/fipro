import json
import threading
import webbrowser
from collections import defaultdict
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from src.config import Settings
from src.connectors.gmail import load_password_hints
from src.core.annotations import overlay_labels, set_category_many, set_label, set_rule
from src.core.application import statement_gaps
from src.core.ingestion import discover_files
from src.core.monthly import available_months, default_month, month_summary
from src.core.orchestrator import process_pipeline
from src.core.parser_registry import is_locked_statement
from src.core.statement_passwords import load_statement_passwords
from src.core.suggestions import confident_suggestions
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
  .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; padding: 14px 24px; background: #1e293b; border-bottom: 1px solid #1e293b; position: sticky; top: 0; z-index: 90; }
  .toolbar input, .toolbar select { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 7px 12px; font-size: 13px; }
  .toolbar input { width: 180px; }
  .stat-badge { background: #334155; border: 1px solid #475569; border-radius: 6px; padding: 6px 10px; font-size: 12px; white-space: nowrap; display: flex; gap: 6px; align-items: center; }
  .stat-badge .val { color: #38bdf8; font-weight: 600; }
  .table-wrap { overflow-x: clip; padding: 0 12px 24px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  thead { position: sticky; top: 0; z-index: 50; }
  th { background: #1e293b; color: #94a3b8; font-weight: 500; text-align: left; padding: 10px 14px; cursor: pointer; user-select: none; white-space: nowrap; }
  th:hover { color: #e2e8f0; }
  th .arrow { margin-left: 4px; opacity: 0.4; }
  th.sorted .arrow { opacity: 1; }
  tr { border-bottom: 1px solid #1e293b; transition: background 0.1s; }
  th[data-col=description], td.c-description { width: 100%; max-width: 0; overflow: hidden; text-overflow: ellipsis; }
  td.c-frequency.auto select { font-style: italic; color: #8a6d00; }
  #screen-review { padding: 20px 24px 40px; max-width: 1280px; }
  #screen-review[hidden] { display: none; }
  #screen-review .head { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
  #screen-review h2 { font-size: 20px; } #screen-review .sub { font-size: 13px; color: #94a3b8; margin-bottom: 14px; }
  #screen-review select, #screen-review input { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 13px; }
  #screen-review .list { background: #1e293b; border: 1px solid #334155; border-radius: 10px; overflow: hidden; }
  #screen-review .item { display: grid; grid-template-columns: 220px 50px 100px 1fr 210px 80px; gap: 10px; padding: 8px 16px; font-size: 13px; align-items: center; border-bottom: 1px solid #0f1117; }
  #screen-review .item:hover { background: #0f1117; } #screen-review .item .d { color: #64748b; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #screen-review .item span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #screen-review button { border: 0; border-radius: 6px; padding: 5px 10px; font-weight: 600; cursor: pointer; background: #334155; color: #e2e8f0; }
  #screen-review .done { padding: 28px; text-align: center; color: #4ade80; }
  #tabs .n { margin-left: 6px; font-size: 11px; background: #f59e0b; color: #0f1117; border-radius: 9px; padding: 1px 6px; font-weight: 700; }
  #tabs { display: flex; gap: 6px; margin-top: 10px; }
  #tabs button { background: transparent; border: 1px solid #475569; color: #94a3b8; border-radius: 6px; padding: 5px 14px; font-size: 13px; cursor: pointer; }
  #tabs button.on { background: #38bdf8; border-color: #38bdf8; color: #0f1117; font-weight: 600; }
  #screen-month { padding: 20px 24px 40px; max-width: 1280px; }
  #screen-month[hidden], #screen-tx[hidden] { display: none; }
  .m-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
  .m-head h2 { font-size: 20px; min-width: 190px; text-align: center; }
  .m-head button, .m-head select { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 6px 12px; font-size: 13px; cursor: pointer; }
  .m-head button:disabled { opacity: .35; cursor: default; }
  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
  .card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px 16px; }
  .card h3 { font-size: 12px; font-weight: 500; color: #94a3b8; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 8px; }
  .kpi .v { font-size: 26px; font-weight: 600; } .kpi .d { font-size: 12px; margin-top: 4px; color: #94a3b8; }
  .up { color: #f87171; } .down { color: #4ade80; } .good-up { color: #4ade80; } .good-down { color: #f87171; }
  .grid2 { display: grid; grid-template-columns: 3fr 2fr; gap: 12px; margin-bottom: 12px; }
  .grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .bar-row { display: grid; grid-template-columns: minmax(120px, 230px) 1fr 100px; gap: 10px; align-items: center; font-size: 13px; padding: 4px 0; cursor: pointer; }
  .bar-row:hover .name { color: #38bdf8; } .bar-row .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar { position: relative; height: 10px; background: #0f1117; border-radius: 5px; }
  .bar i { position: absolute; left: 0; top: 0; bottom: 0; background: #38bdf8; border-radius: 5px; }
  .bar i.warn { background: #f59e0b; } .bar b { position: absolute; top: -3px; bottom: -3px; width: 2px; background: #e2e8f0; opacity: .7; }
  .amt { text-align: right; font-variant-numeric: tabular-nums; }
  .note { font-size: 12px; color: #94a3b8; margin-top: 8px; } .note button { margin-left: 8px; background: #f59e0b; color: #0f1117; border: 0; border-radius: 6px; padding: 3px 10px; font-weight: 600; cursor: pointer; }
  .stack { display: flex; height: 14px; border-radius: 7px; overflow: hidden; background: #0f1117; margin: 6px 0 10px; }
  .legend { font-size: 12px; color: #94a3b8; display: flex; gap: 14px; flex-wrap: wrap; } .legend span::before { content: ''; display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 5px; background: var(--c); }
  svg.days { width: 100%; height: 120px; } svg.days rect { fill: #38bdf8; } svg.days rect:hover { fill: #f1f5f9; }
  @media (max-width: 900px) { .kpis, .grid2, .grid3 { grid-template-columns: 1fr; } }
  #coverage { display: flex; flex-wrap: wrap; column-gap: 18px; row-gap: 2px; margin-top: 4px; }
  .cov { font-size: 12px; color: #94a3b8; white-space: nowrap; } .cov.gap { color: #f59e0b; font-weight: 600; }
  button.confirm { margin-left: 4px; cursor: pointer; }
  #confirm_all { display: none; cursor: pointer; }
  td.c-counterparty { max-width: 150px; overflow: hidden; text-overflow: ellipsis; }
  td.c-category, td.c-notes { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
  #modal { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: none; align-items: center; justify-content: center; z-index: 200; }
  #modal.open { display: flex; }
  #modal .box { background: #1e293b; border: 1px solid #475569; border-radius: 10px; width: min(900px, 94vw); max-height: 86vh; display: flex; flex-direction: column; }
  #modal h2 { font-size: 16px; padding: 16px 20px 4px; } #modal .sub { padding: 0 20px 10px; font-size: 12px; color: #94a3b8; }
  #modal .list { overflow: auto; border-top: 1px solid #334155; border-bottom: 1px solid #334155; }
  #modal .item { display: grid; grid-template-columns: 24px 90px 100px 1fr 60px; gap: 8px; padding: 6px 20px; font-size: 12px; align-items: center; }
  #modal .item:hover { background: #0f1117; } #modal .item .d { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #modal .other { display: none; padding: 10px 20px; font-size: 13px; background: #0f1117; border-bottom: 1px solid #334155; }
  #modal .other.show { display: block; } #modal .other input { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 6px 10px; width: 320px; margin-left: 8px; }
  #modal .foot { padding: 12px 20px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; font-size: 13px; }
  #modal .foot .sp { flex: 1; } #modal button { border: 0; border-radius: 6px; padding: 7px 14px; font-weight: 600; cursor: pointer; }
  #modal button.go { background: #22c55e; color: #052e16; } #modal button.no { background: #334155; color: #e2e8f0; } #modal button:disabled { opacity: .5; }
  button.accept { flex: none; max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; background: #14532d; color: #bbf7d0; border: 1px solid #166534; border-radius: 4px; padding: 1px 6px; font-size: 11px; cursor: pointer; }
  td select, td input { background: transparent; border: 1px solid transparent; border-radius: 4px; color: inherit; font: inherit; padding: 3px 6px; }
  td select { appearance: none; width: auto; min-width: 0; cursor: pointer; }
  td input { width: 100%; min-width: 110px; }
  th[data-col=description] { min-width: 150px; }
  td select:hover, td input:hover, td select:focus, td input:focus { border-color: #475569; background: #1e293b; outline: none; }
  td select option { background: #1e293b; }
  td .saved { border-color: #34d399; }
  td .failed { border-color: #f87171; }
  th, td { padding-left: 8px; padding-right: 8px; }
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
  <div class=subtitle id=coverage></div>
  <nav id=tabs><button data-tab=month>Monthly</button><button data-tab=tx>Transactions</button><button data-tab=review>Review<span class=n id=review_n></span></button></nav>
</header>
<section id=locked aria-label="Locked statements"></section>
<div id=screen-month hidden></div>
<section id=screen-review hidden>
  <div class=head><h2>Review queue</h2><select id=p_month></select></div>
  <div class=sub>Payees with no category yet, most transactions first. Label each once: a friend as Settlements/Friends (kept out of spend and income), a driver or shop as a normal category. Nothing is guessed.</div>
  <div class=list id=p_list></div>
</section>
<div id=screen-tx>
<div class=toolbar>
  <input type=text id=search placeholder=\"Search description...\" oninput=\"render()\">
  <select id=bank_filter onchange=\"render()\"><option value=\"\">All banks</option></select>
  <datalist id=categories></datalist>
  <select id=category_filter onchange=\"render()\"><option value=\"\">All categories</option><option value=__none__>Uncategorized</option></select>
  <select id=type_filter onchange=\"render()\"><option value=\"\">All types</option><option value=debit>Debit</option><option value=credit>Credit</option><option value=internal_transfer>Transfer</option></select>
  <select id=month_filter onchange=\"localStorage.month=this.value;render()\"><option value=\"\">All months</option></select>
  <select id=freq_filter onchange=\"render()\"><option value=\"\">Any frequency</option><option value=detected>Detected monthly</option><option value=Monthly>Monthly (recurring)</option><option value=Once>Once</option></select>
  <button id=confirm_all onclick=\"confirmShown()\">✓ Confirm all</button>
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
</div>
<div id=modal><div class=box><h2 id=m_title></h2><div class=sub id=m_sub></div><div class=list id=m_list></div><div class=other id=m_other><label>Unticked rows: <b id=m_other_n></b> — optionally give them another category <input id=m_other_cat list=categories placeholder="Leave empty to keep them uncategorised"></label></div><div class=foot><label><input type=checkbox id=m_all checked> Select all</label><label id=m_rem_l><input type=checkbox id=m_rem checked> Remember for future statements</label><span class=sp id=m_err></span><button class=no id=m_cancel>Cancel</button><button class=go id=m_go></button></div></div></div>
<script>
const DATA = {{DATA}};
const LOCKED = {{LOCKED}};
const GAPS = {{GAPS}};  // [bank, first uncovered day, last uncovered day]
const SUGGESTIONS = {{SUGGESTIONS}};  // counterparty -> {category, probability}, from `fipro suggest`

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
const COLS = ['transaction_date','counterparty','description','amount','category','suggested','source_bank','payment_mode','review_status','need_want','frequency','splitwise','notes'];
// Labels you can edit in place; selects for the fixed vocabularies, text inputs for category and notes.
const CHOICES = {review_status:['cleared','reconciled','waiting','doubt'], need_want:['Need','Want'], frequency:['Monthly','Once'], splitwise:['yes']};
const HEADERS = {suggested:'suggested', transaction_date:'date', source_bank:'bank', payment_mode:'mode', review_status:'status', need_want:'need/want', frequency:'freq'};
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

// Newest transaction per bank (what to download from) and any stretch no statement covers.
function renderCoverage() {
  const last = {};
  DATA.forEach(r => { if (r.transaction_date && (!last[r.source_bank] || r.transaction_date > last[r.source_bank])) last[r.source_bank] = r.transaction_date; });
  const today = new Date(), days = d => Math.round((today - new Date(d)) / 864e5);
  const box = document.getElementById('coverage');
  box.replaceChildren();
  Object.entries(last).sort().forEach(([bank, d]) => box.append(el('span', 'cov', `${bank}: latest ${d} (${days(d)}d ago)`)));
  GAPS.forEach(([bank, from, to]) => box.append(el('span', 'cov gap', `${bank}: no statement ${from} → ${to}`)));
}

function init() {
  const th = document.getElementById('thead');
  th.innerHTML = COLS.map(c => `<th data-col=${c} onclick=\"toggleSort('${c}')\">${HEADERS[c] || c.replace(/_/g,' ')}<span class=arrow>▼</span></th>`).join('');
  const banks = [...new Set(DATA.map(r=>r.source_bank))].sort();
  const sel = document.getElementById('bank_filter');
  sel.innerHTML = '<option value=\"\">All banks</option>' + banks.map(b=>`<option value=${b}>${b}</option>`).join('');
  const months = [...new Set(DATA.map(r => r.transaction_date.slice(0, 7)).filter(Boolean))].sort().reverse();
  const mf = document.getElementById('month_filter');
  mf.insertAdjacentHTML('beforeend', months.map(m => `<option value=${m}>${m}</option>`).join(''));
  mf.value = months.includes(localStorage.month) ? localStorage.month : '';
  const cats = [...new Set(DATA.map(r=>r.category).filter(Boolean))].sort();
  document.getElementById('category_filter').insertAdjacentHTML('beforeend', cats.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join(''));
  cats.forEach(addCategory);
  search = document.getElementById('search').value;
  bank = sel.value; type = document.getElementById('type_filter').value;
  renderSummary();
  renderCoverage();
  renderLocked();
  setStickyOffsets();
  render();
}

function toggleSort(col) {
  if (sortCol===col) sortDir*=-1; else { sortCol=col; sortDir = col === 'suggested' ? -1 : 1; }  // suggestions first
  render();
}

function paintSortArrows() {
  document.querySelectorAll('th[data-col]').forEach(t => {
    const active = t.dataset.col === sortCol;
    t.classList.toggle('sorted', active);
    t.querySelector('.arrow').textContent = active ? (sortDir === 1 ? '▲' : '▼') : '↕';
  });
}

let view = [], rowH = 37, rowHMeasured = false, drawing = false;

// Narrations and notes come from other people (UPI remarks), so they must never reach innerHTML raw.
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function editCell(col, r) {
  const value = r[col] || '', attrs = `data-hash="${esc(r.hash)}" data-field="${col}"`;
  if (CHOICES[col]) {
    const options = ['', ...CHOICES[col]].map(o => `<option value="${esc(o)}"${o === value ? ' selected' : ''}>${esc(o) || '—'}</option>`).join('');
    const auto = col === 'frequency' && r.frequency_detected ? ' auto" title="Detected: same payee, similar amount, same day each month. Pick a value to override.' : '';
    return `<td class="c-${col}${auto}"><select ${attrs}>${options}</select>${auto ? `<button class=confirm data-hash="${esc(r.hash)}" title="Confirm Monthly for every detected payment to this payee">✓</button>` : ''}</td>`;
  }
  const input = `<input ${attrs} value="${esc(value)}"${col === 'category' ? ' list=categories' : ''}>`;
  return `<td class="c-${col}">${input}</td>`;
}

// A suggestion is offered only while the row has no category; sorting by this column brings them together.
const suggestionFor = r => (!r.category && r.hash && SUGGESTIONS[r.counterparty]) || null;
function suggestedCell(r) {
  const hint = suggestionFor(r);
  if (!hint) return '<td class="c-suggested"></td>';
  const tip = `Local model suggestion (${Math.round(hint.probability * 100)}% sure). Click to review and apply it to every ${esc(r.counterparty)} transaction.`;
  return `<td class="c-suggested"><button class=accept data-counterparty="${esc(r.counterparty)}" data-category="${esc(hint.category)}" title="${tip}">✓ ${esc(hint.category)}</button></td>`;
}

function rowHtml(r) {
  const amt = parseFloat(r.amount)||0;
  const cls = r.status==='internal_transfer' ? 'transfer' : (amt<0 ? 'debit' : 'credit');
  const td = (col, value) => `<td class="c-${col}" title="${esc(value)}">${esc(value)}</td>`;
  const label = col => r.hash ? editCell(col, r) : td(col, r[col]);
  return `<tr>
    ${td('transaction_date', r.transaction_date)}
    ${td('counterparty', r.counterparty)}
    ${td('description', r.description)}
    <td class="amount ${cls}">${amt<0?'−':'+'}${Math.abs(amt).toLocaleString('en-IN',{minimumFractionDigits:2})}</td>
    ${label('category')}
    ${suggestedCell(r)}
    <td><span class=account>${esc(r.source_bank)}</span></td>
    ${td('payment_mode', r.payment_mode)}
    ${label('review_status')}
    ${label('need_want')}
    ${label('frequency')}
    ${label('splitwise')}
    ${label('notes')}
  </tr>`;
}

const byHash = new Map(DATA.map(r => [r.hash, r]));
function payeeGroups(month) {
  const g = new Map();
  DATA.filter(r => r.hash && r.counterparty && !r.category && r.status !== 'internal_transfer' && (!month || r.transaction_date.startsWith(month))).forEach(r => {
    const e = g.get(r.counterparty) || {name: r.counterparty, n: 0, total: 0, like: r};
    e.n++; e.total += parseFloat(r.amount) || 0; g.set(r.counterparty, e);
  });
  return [...g.values()].sort((a, b) => b.n - a.n || Math.abs(b.total) - Math.abs(a.total));
}
function fillReview() {
  const rows = payeeGroups($('p_month').value);
  $('review_n').textContent = rows.length ? (rows.length > 99 ? '99+' : rows.length) : '';
  $('p_list').replaceChildren(...(rows.length ? rows.slice(0, 300).map(e => {
    const row = el('div', 'item');
    row.innerHTML = `<span title="${esc(e.name)}">${esc(e.name)}</span><span>${e.n}</span><span>${e.total < 0 ? '−' : '+'}${Math.abs(e.total).toLocaleString('en-IN', {maximumFractionDigits: 0})}</span><span class=d title="${esc(e.like.description)}">${esc(e.like.description)}</span><input list=categories placeholder="category…"><button>Friend</button>`;
    const go = category => { if (category) openReview(e.name, category, e.like); };
    row.querySelector('input').addEventListener('change', ev => go(ev.target.value.trim()));
    row.querySelector('button').addEventListener('click', () => go('Settlements/Friends'));
    return row;
  }) : [el('div', 'done', 'Nothing left to review for this month ✓')]));
}
// Months with uncategorised payees, newest first; opens on the latest month with at least 20 such rows.
function fillReviewMonths(preferred) {
  const counts = {};
  DATA.filter(r => r.hash && r.counterparty && !r.category && r.status !== 'internal_transfer').forEach(r => { const m = r.transaction_date.slice(0, 7); counts[m] = (counts[m] || 0) + 1; });
  const months = Object.keys(counts).sort().reverse(), keep = preferred ?? $('p_month').value;
  $('p_month').innerHTML = '<option value="">All months</option>' + months.map(m => `<option value="${m}">${m} (${counts[m]})</option>`).join('');
  $('p_month').value = months.includes(keep) || keep === '' ? keep : (months.find(m => counts[m] >= 20) || '');
}
function openReviewTab(month) { fillReviewMonths(month); showTab('review'); }
async function confirmMonthly(hash) {
  const res = await fetch('/annotate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({hash, field: 'frequency', value: 'Monthly'})});
  if (!res.ok) throw new Error((await res.json()).error || res.status);
  const r = byHash.get(hash); r.frequency = 'Monthly'; r.frequency_detected = '';
}
// One request at a time: each save rewrites annotations.csv, so concurrent saves could lose labels.
async function confirmShown() {
  const todo = view.filter(r => r.frequency_detected), btn = document.getElementById('confirm_all');
  if (!todo.length || !confirm(`Confirm ${todo.length} detected payments as Monthly?`)) return;
  btn.disabled = true;
  try { for (const r of todo) await confirmMonthly(r.hash); }
  catch (err) { alert(`Stopped: ${err.message}`); }
  btn.disabled = false;
  render();
}
document.getElementById('tbody').addEventListener('click', async e => {
  const b = e.target.closest('button.confirm');
  if (!b) return;
  const who = byHash.get(b.dataset.hash).counterparty;
  const group = DATA.filter(r => r.frequency_detected && (who ? r.counterparty === who : r.hash === b.dataset.hash));
  try { for (const r of group) await confirmMonthly(r.hash); render(); } catch (err) { b.title = `Not saved: ${err.message}`; }
});
document.getElementById('tbody').addEventListener('change', async e => {
  const el = e.target, {hash, field} = el.dataset;
  if (!field) return;
  el.classList.remove('saved', 'failed');
  try {
    const res = await fetch('/annotate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({hash, field, value: el.value})});
    if (!res.ok) throw new Error((await res.json()).error || res.status);
    byHash.get(hash)[field] = el.value.trim();
    if (field === 'frequency') { byHash.get(hash).frequency_detected = ''; el.closest('td').classList.remove('auto'); }
    if (field === 'category' && el.value.trim()) { addCategory(el.value.trim()); openReview(byHash.get(hash).counterparty, el.value.trim(), byHash.get(hash)); }
    el.classList.add('saved');
  } catch (err) {
    el.classList.add('failed');
    el.title = `Not saved: ${err.message}`;
  }
});

// Review step: apply one approved category to the same counterparty's other uncategorized rows, minus any you untick.
let pending = null;
const $ = id => document.getElementById(id);
$('p_month').addEventListener('change', fillReview);
// Rows with no counterparty (ATM withdrawals, cash deposits) are grouped by payment mode and direction instead.
const sameGroup = (r, counterparty, like) => counterparty ? r.counterparty === counterparty
  : !r.counterparty && r.payment_mode === like.payment_mode && r.transaction_type === like.transaction_type;
function openReview(counterparty, category, like) {
  if (!counterparty && !like) return;
  const rows = DATA.filter(r => r.hash && sameGroup(r, counterparty, like) && !r.category)
    .sort((a, b) => a.transaction_date.localeCompare(b.transaction_date));
  if (!rows.length) return;
  pending = {counterparty, category, rows};
  $('m_title').textContent = `Apply “${category}” to ${rows.length} transaction${rows.length === 1 ? '' : 's'}?`;
  $('m_sub').textContent = `All ${counterparty || `${like.payment_mode} ${like.transaction_type}`} transactions that have no category yet. Untick any that don't belong.`;
  $('m_list').replaceChildren(...rows.map((r, i) => {
    const amt = parseFloat(r.amount) || 0, row = el('label', 'item');
    row.innerHTML = `<input type=checkbox data-i=${i} checked><span>${esc(r.transaction_date)}</span><span>${amt < 0 ? '−' : '+'}${Math.abs(amt).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span><span class=d title="${esc(r.description)}">${esc(r.description)}</span><span>${esc(r.source_bank)}</span>`;
    return row;
  }));
  $('m_err').textContent = ''; $('m_other_cat').value = ''; $('m_all').checked = true; syncReview();
  $('modal').classList.add('open');
}
function ticked() { return [...document.querySelectorAll('#m_list input:checked')].map(c => pending.rows[+c.dataset.i]); }
function syncReview() {
  const n = ticked().length, all = n === pending.rows.length;
  $('m_all').checked = all;
  $('m_rem').disabled = !all || !pending.counterparty; if (!all || !pending.counterparty) $('m_rem').checked = false;
  $('m_rem_l').style.display = pending.counterparty ? '' : 'none';
  $('m_rem_l').style.opacity = all ? 1 : .5;
  const rest = pending.rows.length - n;
  $('m_other').classList.toggle('show', rest > 0); $('m_other_n').textContent = `${rest} row${rest === 1 ? '' : 's'}`;
  $('m_go').textContent = `Apply to ${n}`; $('m_go').disabled = !n;
}
function closeReview() { $('modal').classList.remove('open'); pending = null; }
$('m_list').addEventListener('change', syncReview);
$('m_all').addEventListener('change', e => { document.querySelectorAll('#m_list input').forEach(c => c.checked = e.target.checked); if (e.target.checked) $('m_rem').checked = true; syncReview(); });
$('m_cancel').addEventListener('click', closeReview);
document.addEventListener('keydown', e => { if (e.key === 'Escape' && pending) closeReview(); });
$('m_go').addEventListener('click', async () => {
  const chosen = ticked(), rest = pending.rows.filter(r => !chosen.includes(r)), other = $('m_other_cat').value.trim();
  const remember = $('m_rem').checked && !rest.length && !!pending.counterparty;
  const save = async (category, rows, remember) => {
    const res = await fetch('/accept', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({counterparty: pending.counterparty, category, remember, hashes: rows.map(r => r.hash)})});
    if (!res.ok) throw new Error((await res.json()).error || res.status);
    rows.forEach(r => { r.category = category; });
    addCategory(category);
  };
  $('m_go').disabled = true;
  try {
    await save(pending.category, chosen, remember);
    if (other && rest.length) await save(other, rest, false);  // never a rule: these rows disagreed with the suggestion
    closeReview(); render(); fillReviewMonths(); fillReview();
  } catch (err) { $('m_err').textContent = `Not saved: ${err.message}`; $('m_go').disabled = false; }
});
document.getElementById('tbody').addEventListener('click', e => {
  const button = e.target.closest('button.accept');
  if (button) openReview(button.dataset.counterparty, button.dataset.category);
});

function addCategory(name) {
  const list = document.getElementById('categories');
  if (![...list.options].some(o => o.value === name)) list.insertAdjacentHTML('beforeend', `<option value="${esc(name)}">`);
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
  if (sample && !rowHMeasured) {  // measure once: re-measuring every draw can loop forever on fractional row heights
    rowHMeasured = true;
    rowH = sample.getBoundingClientRect().height;
    drawWindow();
  }
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
  const category = document.getElementById('category_filter').value;
  const freq = document.getElementById('freq_filter').value;
  const month = document.getElementById('month_filter').value;
  document.getElementById('confirm_all').style.display = freq === 'detected' ? 'inline-block' : 'none';
  let rows = DATA.filter(r => {
    if (search && !r.description.toLowerCase().includes(search)) return false;
    if (bank && r.source_bank !== bank) return false;
    if (month && !r.transaction_date.startsWith(month)) return false;
    if (freq === 'detected' ? !r.frequency_detected : (freq && r.frequency !== freq)) return false;
    if (category === '__none__' ? r.category : (category && r.category !== category)) return false;
    if (type === 'internal_transfer') return r.status === 'internal_transfer';
    if (type && r.transaction_type !== type) return false;
    if (type && r.status === 'internal_transfer') return false;
    return true;
  });
  const sortFn = (a,b) => {
    let va=a[sortCol], vb=b[sortCol];
    if (sortCol==='suggested') { va=suggestionFor(a)?.probability ?? -1; vb=suggestionFor(b)?.probability ?? -1; }
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

// ---- Monthly screen -------------------------------------------------------------------------
const inr = n => Math.round(n).toLocaleString('en-IN');
const monthLabel = m => new Date(m + '-15').toLocaleString('en-IN', {month: 'long', year: 'numeric'});
let months = [], currentMonth = '';

function change(cur, prev, label, goodUp) {
  if (!prev) return `<span>no ${label} data</span>`;
  const pct = Math.round((cur - prev) / prev * 100), up = cur > prev;
  const cls = goodUp ? (up ? 'good-up' : 'good-down') : (up ? 'up' : 'down');
  return `<span class=${cls}>${up ? '▲' : '▼'} ${Math.abs(pct)}%</span> vs ${label} (${inr(prev)})`;
}

function bars(items, {total, drill} = {}) {
  const max = Math.max(...items.map(i => Math.max(i.amount, i.previous)), 1);
  return items.map(i => `<div class=bar-row ${drill ? `data-drill='${esc(i.name)}'` : ''} title='Last month: ${inr(i.previous)}'>
    <span class=name>${esc(i.name)}</span>
    <span class=bar><i class='${i.name === 'Uncategorised' ? 'warn' : ''}' style='width:${i.amount / max * 100}%'></i>${i.previous ? `<b style='left:${i.previous / max * 100}%'></b>` : ''}</span>
    <span class=amt>${inr(i.amount)}${total ? ` <small>${Math.round(i.amount / total * 100)}%</small>` : ''}</span></div>`).join('');
}

function dayChart(s) {
  const [y, m] = s.month.split('-').map(Number), n = new Date(y, m, 0).getDate();
  const by = Object.fromEntries(s.by_day.map(d => [d.day, d.amount]));
  const vals = Array.from({length: n}, (_, i) => Math.max(by[`${s.month}-${String(i + 1).padStart(2, '0')}`] || 0, 0));
  const max = Math.max(...vals, 1), w = 100 / n;
  return `<svg class=days viewBox='0 0 100 40' preserveAspectRatio='none'>${vals.map((v, i) => `<rect x='${i * w + w * .12}' y='${40 - v / max * 38}' width='${w * .76}' height='${v / max * 38}'><title>${s.month}-${String(i + 1).padStart(2, '0')}: ${inr(v)}</title></rect>`).join('')}</svg>
    <div class=note>Busiest day ${inr(max)} · average ${inr(vals.reduce((a, b) => a + b, 0) / n)} a day</div>`;
}

function stackBar(parts, colours) {
  const total = parts.reduce((a, [, v]) => a + v, 0) || 1;
  return `<div class=stack>${parts.map(([k, v], i) => `<div style='width:${v / total * 100}%;background:${colours[i % colours.length]}' title='${esc(k)}: ${inr(v)}'></div>`).join('')}</div>
    <div class=legend>${parts.map(([k, v], i) => `<span style='--c:${colours[i % colours.length]}'>${esc(k)} ${inr(v)} (${Math.round(v / total * 100)}%)</span>`).join('')}</div>`;
}

function renderMonth(data) {
  months = data.months; const s = data.summary, box = $('screen-month');
  if (!s) { box.innerHTML = '<p class=note>No transactions yet. Run fipro process first.</p>'; return; }
  currentMonth = s.month;
  const i = months.indexOf(s.month), rate = s.income ? Math.round(s.saved / s.income * 100) : 0;
  const nw = Object.entries(s.need_want).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  box.innerHTML = `
    <div class=m-head><button id=m_prev ${i >= months.length - 1 ? 'disabled' : ''}>◀</button><h2>${monthLabel(s.month)}</h2><button id=m_next ${i <= 0 ? 'disabled' : ''}>▶</button>
      <select id=m_pick>${months.map(m => `<option value=${m} ${m === s.month ? 'selected' : ''}>${m}</option>`).join('')}</select></div>
    <div class=kpis>
      <div class='card kpi'><h3>Income</h3><div class=v>₹${inr(s.income)}</div><div class=d>${change(s.income, s.previous.income, monthLabel(s.previous_month).split(' ')[0], true)}</div></div>
      <div class='card kpi'><h3>Spend</h3><div class=v>₹${inr(s.net_spend)}</div><div class=d>${change(s.net_spend, s.previous.net_spend, monthLabel(s.previous_month).split(' ')[0], false)}${s.refunds ? ` · after ₹${inr(s.refunds)} refunds` : ''}</div></div>
      <div class='card kpi'><h3>Saved</h3><div class='v ${s.saved < 0 ? 'up' : ''}'>${s.saved < 0 ? '−' : ''}₹${inr(Math.abs(s.saved))}</div><div class=d>income minus spend</div></div>
      <div class='card kpi'><h3>Savings rate</h3><div class='v ${rate < 0 ? 'up' : ''}'>${rate}%</div><div class=d>${s.transactions} transactions · ${s.transfers.count} transfers left out (₹${inr(s.transfers.amount)})</div></div>
    </div>
    <div class=grid2>
      <div class=card><h3>Spend by category — click one to see its transactions</h3>${bars(s.by_category, {total: s.net_spend, drill: true})}
        ${s.uncategorised.count ? `<div class=note>${s.uncategorised.count} spend rows (₹${inr(s.uncategorised.amount)}) still have no category.<button id=m_review>Review payees</button></div>` : ''}
        <div class=note>The white tick marks last month's figure.</div></div>
      <div class=card><h3>Top payees</h3>${bars(s.top_payees)}</div>
    </div>
    <div class=grid3>
      <div class=card><h3>Spend each day</h3>${dayChart(s)}</div>
      <div class=card><h3>By account</h3>${bars(s.by_account, {total: s.spend - s.refunds})}</div>
      <div class=card><h3>Need, want and recurring</h3>${nw.length ? stackBar(nw, ['#38bdf8', '#f59e0b', '#64748b']) : ''}<div class=note>Recurring (monthly) payments: ₹${inr(s.recurring)}</div></div>
    </div>`;
  $('m_prev').onclick = () => loadMonth(months[i + 1]);
  $('m_next').onclick = () => loadMonth(months[i - 1]);
  $('m_pick').onchange = e => loadMonth(e.target.value);
  if ($('m_review')) $('m_review').onclick = () => openReviewTab(s.month);
  box.querySelectorAll('[data-drill]').forEach(r => r.onclick = () => drill(r.dataset.drill));
}

async function loadMonth(m) {
  const res = await fetch('/month' + (m ? '?m=' + m : ''));
  renderMonth(await res.json());
  if (m) localStorage.analysisMonth = m;
}

// Open the transactions table on one month and category.
function drill(category) {
  localStorage.month = currentMonth; $('month_filter').value = currentMonth;
  $('category_filter').value = category === 'Uncategorised' ? '__none__' : category;
  showTab('tx');
}

function showTab(tab) {
  localStorage.tab = tab;
  $('screen-month').hidden = tab !== 'month'; $('screen-tx').hidden = tab !== 'tx';
  document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
  $('screen-review').hidden = tab !== 'review';
  if (tab === 'month') loadMonth(localStorage.analysisMonth);
  else if (tab === 'review') { if (!$('p_month').options.length) fillReviewMonths(); fillReview(); }
  else { setStickyOffsets(); render(); }
}
document.querySelectorAll('#tabs button').forEach(b => b.addEventListener('click', () => showTab(b.dataset.tab)));

init();
fillReviewMonths(); fillReview();
showTab(localStorage.tab || 'month');
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


def build_server(csv_path: str, port: int, settings: Settings | None = None) -> ThreadingHTTPServer:
    def current_rows() -> list[dict]:
        rows = load_csv_data(csv_path) if Path(csv_path).exists() else []
        if settings:
            overlay_labels(rows, settings.paths.annotations, settings.paths.category_rules)
        return rows

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                locked = locked_statements(settings) if settings else []
                suggestions = confident_suggestions(settings.paths.suggestions) if settings else {}
                html = (
                    HTML_TEMPLATE.replace("{{DATA}}", _script_json(current_rows()))
                    .replace("{{LOCKED}}", _script_json(locked))
                    .replace("{{GAPS}}", _script_json(statement_gaps(settings.paths.input) if settings else []))
                    .replace("{{SUGGESTIONS}}", _script_json(suggestions))
                )
                self._send(200, "text/html; charset=utf-8", html.encode())
            elif self.path.split("?")[0] == "/month":
                rows = current_rows()
                months = available_months(rows)
                asked = parse_qs(urlsplit(self.path).query).get("m", [""])[0]
                month = asked if asked in months else default_month(months, date.today())
                self._send_json(200, {"months": months, "summary": month_summary(rows, month) if month else None})
            elif self.path == "/data":
                self._send_json(200, current_rows())
            else:
                self._send(404, "text/plain", b"")

        def do_POST(self):
            if self.path not in ("/unlock", "/annotate", "/accept") or settings is None:
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
            if self.path == "/annotate":
                self._annotate(settings)
                return
            if self.path == "/accept":
                self._accept(settings)
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

        def _annotate(self, settings: Settings) -> None:
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                set_label(settings.paths.annotations, str(body["hash"]), str(body["field"]), str(body["value"]))
            except (KeyError, ValueError) as exc:  # bad request from the page, not a server fault
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, {"ok": True})

        def _accept(self, settings: Settings) -> None:
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                category = str(body["category"])
                if body.get("remember"):  # every transaction of this counterparty was approved: one rule covers them
                    set_rule(settings.paths.category_rules, str(body["counterparty"]), category)
                else:  # some were unticked, so a rule would wrongly cover them: label only the approved ones
                    set_category_many(settings.paths.annotations, [str(h) for h in body["hashes"]], category)
            except (KeyError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, {"ok": True})

        def _send_json(self, status: int, payload: object) -> None:
            self._send(status, "application/json", json.dumps(payload, default=str).encode())

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass  # silence request logs

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)  # port 0 picks a free port; handlers read the bound one
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
