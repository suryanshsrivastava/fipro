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
from src.core.card_dues import card_dues
from src.core.ingestion import discover_files
from src.core.monthly import available_months, default_month, month_summary
from src.core.orchestrator import process_pipeline
from src.core.parser_registry import is_locked_statement
from src.core.statement_passwords import load_statement_passwords
from src.core.suggestions import confident_suggestions
from src.core.tasks import add_task, all_tasks, set_task
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
  #screen-subs, #screen-work, #screen-tasks { padding: 20px 24px 40px; max-width: 1280px; } #screen-subs[hidden], #screen-work[hidden], #screen-tasks[hidden] { display: none; }
  .task { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding: 10px 14px; border-top: 1px solid #0f1117; } .task > div:nth-child(2) { flex: 1 1 340px; min-width: 0; } .task > select { width: 110px; } .task > input { flex: 0 1 220px; width: 220px; } .task:first-child { border-top: 0; }
  .task .bar1 { align-self: stretch; border-radius: 3px; background: #475569; } .task.p1 .bar1 { background: #f87171; } .task.p2 .bar1 { background: #f59e0b; }
  .task .tt { font-size: 14px; font-weight: 600; } .task .td { font-size: 12px; color: #94a3b8; margin-top: 2px; } .task.fin .tt { text-decoration: line-through; color: #64748b; }
  .task select, .task input, .addt input, .addt select { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 4px 8px; font-size: 12px; } .task input { width: 100%; }
  .pill.you { background: #1e3a8a; color: #bfdbfe; } .pill.agent { background: #4c1d95; color: #ddd6fe; }
  .addt { display: flex; gap: 8px; margin: 12px 0; } .addt input[name=title] { flex: 1; } .addt button, .task .cp { background: #38bdf8; color: #0f1117; border: 0; border-radius: 6px; padding: 5px 12px; font-weight: 600; cursor: pointer; font-size: 12px; } .task .cp { background: #7c3aed; color: #fff; margin-top: 6px; }
  .tbl { width: 100%; border-collapse: collapse; font-size: 13px; } .tbl th { text-align: left; color: #94a3b8; font-weight: 500; font-size: 12px; padding: 6px 10px; cursor: default; background: transparent; position: static; }
  .tbl td { padding: 7px 10px; border-top: 1px solid #0f1117; } .tbl tr.r:hover { background: #0f1117; } .tbl .num { text-align: right; font-variant-numeric: tabular-nums; }
  .tbl .nm { cursor: pointer; } .tbl .nm:hover { color: #38bdf8; } .tbl .sub2 td { color: #94a3b8; font-size: 12px; padding: 3px 10px 3px 30px; border: 0; background: #0f1117; }
  .tbl select, .tbl input, .sw select { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 4px 8px; font-size: 12px; } .tbl input { width: 100%; }
  .pill { font-size: 11px; border-radius: 9px; padding: 1px 8px; font-weight: 600; } .pill.act { background: #14532d; color: #86efac; } .pill.old { background: #334155; color: #94a3b8; }
  .pill.todo { background: #f59e0b; color: #0f1117; } .pill.filed { background: #1e3a8a; color: #bfdbfe; } .pill.done { background: #14532d; color: #86efac; }
  .tools { display: flex; gap: 10px; align-items: center; margin: 12px 0; } .tools button { background: #38bdf8; color: #0f1117; border: 0; border-radius: 6px; padding: 6px 12px; font-weight: 600; cursor: pointer; } .tools button.alt { background: #334155; color: #e2e8f0; }
  #screen-review { padding: 20px 24px 40px; max-width: 1280px; }
  #screen-review[hidden] { display: none; }
  #screen-review .head { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
  #screen-review h2 { font-size: 20px; } #screen-review .sub { font-size: 13px; color: #94a3b8; margin-bottom: 14px; }
  #screen-review select, #screen-review input { background: #334155; border: 1px solid #475569; color: #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 13px; }
  #screen-review .list { background: #1e293b; border: 1px solid #334155; border-radius: 10px; overflow: hidden; }
  #screen-review .item { display: grid; grid-template-columns: 220px 50px 100px 92px 1fr 210px 80px; gap: 10px; padding: 8px 16px; font-size: 13px; align-items: center; border-bottom: 1px solid #0f1117; }
  #screen-review .nm { cursor: pointer; } #screen-review .nm:hover { color: #38bdf8; } #screen-review .chev { font-style: normal; color: #64748b; display: inline-block; width: 14px; }
  #screen-review .det { background: #0f1117; padding: 4px 16px 8px 46px; border-bottom: 1px solid #0f1117; }
  #screen-review .drow { display: grid; grid-template-columns: 92px 52px 80px 90px 1fr; gap: 10px; font-size: 12px; padding: 3px 0; color: #cbd5e1; }
  #screen-review .drow .tm { color: #94a3b8; font-variant-numeric: tabular-nums; } #screen-review .drow .a { text-align: right; font-variant-numeric: tabular-nums; }
  #screen-review .drow .d { color: #64748b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #screen-review .trow.list { grid-template-columns: 84px 42px 62px 64px minmax(80px, 1fr) 150px 62px; gap: 8px; padding: 3px 0; font-size: 12px; } #screen-review .trow.cal { grid-template-columns: 42px 84px minmax(80px, 1fr) 70px 150px 62px; }
  #screen-review .det { padding-right: 16px; } #screen-review .trow .tm { color: #94a3b8; font-variant-numeric: tabular-nums; } #screen-review .trow .a { text-align: right; font-variant-numeric: tabular-nums; }
  #screen-review .trow .d { color: #64748b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } #screen-review .trow input { padding: 3px 8px; font-size: 12px; }
  #screen-review .item:hover { background: #0f1117; } #screen-review .item .when { color: #94a3b8; font-size: 12px; font-variant-numeric: tabular-nums; } #screen-review .item .d { color: #64748b; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #screen-review .item span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #screen-review button { border: 0; border-radius: 6px; padding: 5px 10px; font-weight: 600; cursor: pointer; background: #334155; color: #e2e8f0; }
  .seg { display: inline-flex; gap: 0; margin-left: auto; } #screen-review .seg button { border-radius: 0; background: #1e293b; color: #94a3b8; border: 1px solid #475569; } #screen-review .seg button:first-child { border-radius: 6px 0 0 6px; } #screen-review .seg button:last-child { border-radius: 0 6px 6px 0; } #screen-review .seg button.on { background: #38bdf8; color: #0f1117; border-color: #38bdf8; }
  #p_cal[hidden] { display: none; } .cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-bottom: 14px; }
  .cal .dow { font-size: 11px; color: #64748b; text-transform: uppercase; text-align: center; padding: 2px 0; }
  .cal .day { background: #1e293b; border: 1px solid #334155; border-radius: 8px; min-height: 78px; padding: 6px 8px; cursor: pointer; font-size: 12px; display: flex; flex-direction: column; gap: 3px; }
  .cal .day.empty { background: transparent; border-color: transparent; cursor: default; } .cal .day.none { opacity: .45; } .cal .day:not(.empty):hover, .cal .day.sel { border-color: #38bdf8; }
  .cal .day .n { color: #94a3b8; } .cal .day .out { font-variant-numeric: tabular-nums; } .cal .day .todo { align-self: flex-start; background: #f59e0b; color: #0f1117; border-radius: 9px; padding: 0 7px; font-weight: 700; font-size: 11px; } .cal .day .ok { color: #4ade80; font-size: 11px; } .cal .day .rec { color: #38bdf8; font-size: 11px; }
  #p_day .sub { padding: 10px 16px 4px; margin: 0; } #p_day .item { grid-template-columns: 60px 100px 1fr 120px 210px; } #p_day .item .a { text-align: right; font-variant-numeric: tabular-nums; }
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
  .cov { font-size: 12px; color: #94a3b8; white-space: nowrap; } .cov.gap { color: #f59e0b; font-weight: 600; } .cov.due.paid { color: #4ade80; } .cov.due.soon { color: #f59e0b; font-weight: 600; } .cov.due.late { color: #f87171; font-weight: 700; }
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
  .confetti { position: fixed; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 60; }
  .party { position: fixed; top: 22%; left: 50%; transform: translateX(-50%); z-index: 61; background: #16a34a; color: #fff; font-weight: 700; font-size: 20px; padding: 14px 26px; border-radius: 12px; box-shadow: 0 10px 40px #0008; pointer-events: none; animation: pop 3.4s ease forwards; }
  @keyframes pop { 0% { transform: translateX(-50%) scale(.6); opacity: 0; } 10% { transform: translateX(-50%) scale(1.08); opacity: 1; } 18% { transform: translateX(-50%) scale(1); } 85% { opacity: 1; } 100% { opacity: 0; } }
</style>
</head>
<body>
<header>
  <h1>Fipro Dashboard</h1>
  <div class=subtitle id=summary>—</div>
  <div class=subtitle id=coverage></div>
  <nav id=tabs><button data-tab=month>Monthly</button><button data-tab=tx>Transactions</button><button data-tab=review>Review<span class=n id=review_n></span></button><button data-tab=subs>Subscriptions</button><button data-tab=work>Work claims<span class=n id=work_n></span></button><button data-tab=tasks>Tasks<span class=n id=tasks_n></span></button></nav>
</header>
<section id=locked aria-label="Locked statements"></section>
<div id=screen-month hidden></div>
<section id=screen-review hidden>
  <div class=head><h2>Review queue</h2><select id=p_month></select><span class=seg><button data-rv=list class=on>List</button><button data-rv=cal>Calendar</button></span></div>
  <div class=sub>Payees with no category yet, most transactions first. Label each once: a friend as Settlements/Friends (kept out of spend and income), a driver or shop as a normal category. Nothing is guessed.</div>
  <div class=list id=p_list></div>
  <div id=p_cal hidden><div class=cal id=p_grid></div><div class=list id=p_day></div></div>
</section>
<section id=screen-subs hidden></section>
<section id=screen-work hidden></section>
<section id=screen-tasks hidden></section>
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
const DUES = {{DUES}};  // per card: bank, due date, total, days left, paid
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
  DUES.forEach(c => box.append(el('span', 'cov due ' + (c.paid ? 'paid' : c.days < 0 ? 'late' : c.days <= 3 ? 'soon' : ''), `${c.bank}: ${c.paid ? 'paid ✓' : c.days < 0 ? `OVERDUE ${-c.days}d` : c.days === 0 ? 'DUE TODAY' : `due in ${c.days}d`} · ₹${inr(c.total)} · ${c.due}`)));
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
    const e = g.get(r.counterparty) || {name: r.counterparty, n: 0, total: 0, like: r, last: r, rows: []};
    e.rows.push(r);
    if ((r.transaction_date + (r.time || '')) > (e.last.transaction_date + (e.last.time || ''))) e.last = r;
    e.n++; e.total += parseFloat(r.amount) || 0; g.set(r.counterparty, e);
  });
  return [...g.values()].sort((a, b) => b.n - a.n || Math.abs(b.total) - Math.abs(a.total));
}
let reviewView = localStorage.reviewView || 'list', calDay = '';
function calMonth() {
  const m = $('p_month').value;
  if (m) return m;
  const all = DATA.map(r => r.transaction_date.slice(0, 7)).filter(Boolean).sort();
  return all[all.length - 1] || '';
}
// One transaction row for both Review views (calendar day panel and expanded payee): same fields, same labelling.
async function labelTxn(r, category, input) {
  const res = await fetch('/annotate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({hash: r.hash, field: 'category', value: category})});
  if (!res.ok) { if (input) input.title = 'Not saved'; return; }
  r.category = category; if (category) addCategory(category);
  // A payee label offers to cover the payee's other rows; the refresh below follows when that dialog closes.
  if (category && r.counterparty) openReview(r.counterparty, category, r); else { refreshReview(); }
}
// Celebrate when the last unlabelled payee row of a month gets a category.
const openRows = m => DATA.filter(r => r.hash && r.counterparty && !r.category && r.status !== 'internal_transfer' && r.transaction_date.startsWith(m)).length;
let openByMonth = {};
function snapshotOpen() { const ms = new Set(DATA.map(r => r.transaction_date.slice(0, 7)).filter(Boolean)); openByMonth = Object.fromEntries([...ms].map(m => [m, openRows(m)])); }
function checkMonthDone() {
  const before = openByMonth; snapshotOpen();
  Object.keys(openByMonth).sort().filter(m => before[m] > 0 && openByMonth[m] === 0).forEach(celebrate);
}
function celebrate(month) {
  const msg = el('div', 'party', `${monthLabel(month)} fully labelled 🎉`); document.body.append(msg); setTimeout(() => msg.remove(), 3500);
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const cv = el('canvas', 'confetti'); cv.width = innerWidth; cv.height = innerHeight; document.body.append(cv);
  const g = cv.getContext('2d'), colours = ['#f59e0b', '#38bdf8', '#22c55e', '#f43f5e', '#a78bfa', '#facc15'];
  const bits = Array.from({length: 160}, (_, i) => ({x: innerWidth / 2, y: innerHeight * .3, vx: (Math.random() - .5) * 16, vy: -Math.random() * 14 - 3, w: 6 + Math.random() * 6, h: 4 + Math.random() * 5, a: Math.random() * 6, va: (Math.random() - .5) * .4, c: colours[i % colours.length]}));
  const t0 = performance.now();
  (function frame(t) {
    const k = t - t0; g.clearRect(0, 0, cv.width, cv.height);
    bits.forEach(b => { b.vy += .35; b.vx *= .99; b.x += b.vx; b.y += b.vy; b.a += b.va; g.save(); g.translate(b.x, b.y); g.rotate(b.a); g.globalAlpha = Math.max(0, 1 - k / 3200); g.fillStyle = b.c; g.fillRect(-b.w / 2, -b.h / 2, b.w, b.h); g.restore(); });
    if (k < 3300) requestAnimationFrame(frame); else cv.remove();
  })(t0);
}
function refreshReview() { fillReviewMonths(); fillReview(); if (reviewView === 'cal') renderCal(); checkMonthDone(); }
function txnRow(r, view) {
  const amt = parseFloat(r.amount) || 0, sign = amt < 0 ? '−' : '+';
  const row = el('div', 'item trow ' + view);
  const when = view === 'list' ? `<span>${esc(r.transaction_date)}</span><span class=tm>${esc(r.time) || '—'}</span>` : `<span class=tm>${esc(r.time) || '—'}</span>`;
  const who = view === 'list' ? esc(r.description.replace(/\\s+/g, ' ')) : esc(r.counterparty || r.description);
  const amount = `<span class=a>${sign}${inr(Math.abs(amt))}</span>`, bank = `<span>${esc(r.source_bank)}</span>`, what = `<span class=d title="${esc(r.description)}">${who}</span>`;
  row.innerHTML = when + (view === 'list' ? amount + bank + what : bank + what + amount) + `<input list=categories placeholder="category…" value="${esc(r.category)}"><button class=friend title="Settlement with a friend: kept out of spend and income">Friend</button>`;
  const input = row.querySelector('input');
  input.addEventListener('change', () => labelTxn(r, input.value.trim(), input));
  row.querySelector('button').addEventListener('click', () => labelTxn(r, 'Settlements/Friends', input));
  return row;
}
function renderCal() {
  const month = calMonth(); if (!month) return;
  const [y, mo] = month.split('-').map(Number), n = new Date(y, mo, 0).getDate(), lead = (new Date(y, mo - 1, 1).getDay() + 6) % 7;
  const by = {};
  DATA.filter(r => r.hash && r.transaction_date.startsWith(month) && r.status !== 'internal_transfer').forEach(r => (by[r.transaction_date] ||= []).push(r));
  const cells = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => `<div class=dow>${d}</div>`);
  for (let i = 0; i < lead; i++) cells.push('<div class="day empty"></div>');
  for (let d = 1; d <= n; d++) {
    const key = `${month}-${String(d).padStart(2, '0')}`, rows = by[key] || [];
    const todo = rows.filter(r => !r.category).length, spend = rows.reduce((a, r) => a + Math.min(parseFloat(r.amount) || 0, 0), 0), rec = rows.filter(r => r.frequency === 'Monthly').length;
    cells.push(`<div class="day ${rows.length ? '' : 'none'} ${key === calDay ? 'sel' : ''}" data-day=${key}><span class=n>${d}</span>${rows.length ? `<span class=out>${spend ? '−' + inr(-spend) : '—'}</span>${todo ? `<span class=todo>${todo} to label</span>` : '<span class=ok>✓ labelled</span>'}${rec ? `<span class=rec>↻ ${rec} recurring</span>` : ''}` : ''}</div>`);
  }
  $('p_grid').innerHTML = cells.join('');
  $('p_grid').querySelectorAll('[data-day]').forEach(c => c.onclick = () => { calDay = c.dataset.day; renderCal(); });
  const rows = by[calDay] || [];
  $('p_day').replaceChildren(...(calDay.startsWith(month) ? [el('div', 'sub', `${new Date(calDay).toLocaleDateString('en-IN', {weekday: 'long', day: 'numeric', month: 'long'})} · ${rows.length} transaction${rows.length === 1 ? '' : 's'} (transfers left out)`), ...rows.map(r => txnRow(r, 'cal'))] : []));
}
function setReviewView(v) {
  reviewView = localStorage.reviewView = v;
  document.querySelectorAll('[data-rv]').forEach(b => b.classList.toggle('on', b.dataset.rv === v));
  $('p_list').hidden = v !== 'list'; $('p_cal').hidden = v !== 'cal';
  if (v === 'cal') renderCal();
}
function fillReview() {
  const rows = payeeGroups($('p_month').value);
  $('review_n').textContent = rows.length ? (rows.length > 99 ? '99+' : rows.length) : '';
  $('p_list').replaceChildren(...(rows.length ? rows.slice(0, 300).map(e => {
    const grp = el('div', 'grp'), row = el('div', 'item');
    grp.append(row);
    row.innerHTML = `<span class=nm title="${esc(e.name)}"><i class=chev>▸</i>${esc(e.name)}</span><span>${e.n}</span><span>${e.total < 0 ? '−' : '+'}${Math.abs(e.total).toLocaleString('en-IN', {maximumFractionDigits: 0})}</span><span class=when title="Most recent payment">${esc(e.last.transaction_date.slice(5))}${e.last.time ? ' ' + esc(e.last.time) : ''}</span><span class=d title="${esc(e.like.description)}">${esc(e.like.description)}</span><input list=categories placeholder="category…"><button>Friend</button>`;
    const go = category => { if (category) openReview(e.name, category, e.like); };
    row.querySelector('input').addEventListener('change', ev => go(ev.target.value.trim()));
    row.querySelector('button').addEventListener('click', () => go('Settlements/Friends'));
    // Click the payee to see every payment: date, time, amount, bank and narration, newest first.
    row.querySelector('.nm').addEventListener('click', () => {
      const open = grp.querySelector('.det');
      if (open) { open.remove(); row.querySelector('.chev').textContent = '▸'; return; }
      const det = el('div', 'det');
      det.append(...[...e.rows].sort((a, b) => (b.transaction_date + (b.time || '')).localeCompare(a.transaction_date + (a.time || ''))).slice(0, 60).map(r => txnRow(r, 'list')));
      if (e.rows.length > 60) det.append(el('div', 'drow', `…and ${e.rows.length - 60} older`));
      grp.append(det); row.querySelector('.chev').textContent = '▾';
    });
    return grp;
  }) : [el('div', 'done', 'Nothing left to review for this month ✓')]));
}
// Every month with payee rows, newest first (done months stay, marked ✓); opens on the latest month with at least 20 such rows.
function fillReviewMonths(preferred) {
  const counts = {};
  DATA.filter(r => r.hash && r.counterparty && r.status !== 'internal_transfer').forEach(r => { const m = r.transaction_date.slice(0, 7); counts[m] = (counts[m] || 0) + (r.category ? 0 : 1); });
  const months = Object.keys(counts).sort().reverse(), keep = preferred ?? $('p_month').value;
  $('p_month').innerHTML = '<option value="">All months</option>' + months.map(m => `<option value="${m}">${m} ${counts[m] ? `(${counts[m]})` : '✓'}</option>`).join('');
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
$('p_month').addEventListener('change', () => { fillReview(); if (reviewView === 'cal') renderCal(); });
document.querySelectorAll('[data-rv]').forEach(b => b.addEventListener('click', () => setReviewView(b.dataset.rv)));
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
    closeReview(); render(); refreshReview();
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


// ---- Subscriptions screen ---------------------------------------------------------------------
const isSub = r => /subscri/i.test(r.category || '');
const addMonth = (iso, n) => { const d = new Date(iso + 'T00:00:00'); d.setMonth(d.getMonth() + n); return d.toISOString().slice(0, 10); };
const spendRows = () => DATA.filter(r => r.hash && r.status !== 'internal_transfer' && (parseFloat(r.amount) || 0) < 0);
const byDateDesc = (a, b) => (b.transaction_date + (b.time || '')).localeCompare(a.transaction_date + (a.time || ''));

function subscriptionGroups() {
  const latest = DATA.reduce((m, r) => r.transaction_date > m ? r.transaction_date : m, '');
  const g = new Map();
  spendRows().filter(r => isSub(r) || r.frequency === 'Monthly').forEach(r => {
    const key = r.counterparty || r.description.replace(/\\s+/g, ' ').slice(0, 28);
    const e = g.get(key) || {name: key, rows: [], sub: false}; e.rows.push(r); e.sub ||= isSub(r); g.set(key, e);
  });
  return [...g.values()].map(e => {
    e.rows.sort(byDateDesc);
    const last = e.rows[0], gap = (new Date(latest) - new Date(last.transaction_date)) / 864e5;
    return {...e, last, amount: -parseFloat(last.amount), next: addMonth(last.transaction_date, 1), active: gap <= 45, category: last.category || ''};
  }).sort((a, b) => b.active - a.active || b.amount - a.amount);
}

function renderSubs() {
  const groups = subscriptionGroups(), subs = groups.filter(e => e.sub), other = groups.filter(e => !e.sub);
  const monthly = list => list.filter(e => e.active).reduce((a, e) => a + e.amount, 0);
  const table = (list, empty) => list.length ? `<table class=tbl><tr><th>Payee</th><th>Category</th><th class=num>Latest</th><th class=num>Paid</th><th>Last paid</th><th>Next expected</th><th>Status</th></tr>${list.map((e, i) => `<tr class=r><td class=nm data-g="${esc(e.name)}"><i class=chev>▸</i>${esc(e.name)}</td><td>${esc(e.category) || '—'}</td><td class=num>₹${inr(e.amount)}</td><td class=num>${e.rows.length}×</td><td>${esc(e.last.transaction_date)}</td><td>${e.active ? esc(e.next) : '—'}</td><td><span class='pill ${e.active ? 'act' : 'old'}'>${e.active ? 'active' : 'stopped?'}</span></td></tr>`).join('')}</table>` : `<div class=note>${empty}</div>`;
  $('screen-subs').innerHTML = `<div class=m-head><h2 style="min-width:0">Subscriptions</h2></div>
    <div class=kpis>
      <div class='card kpi'><h3>Subscriptions / month</h3><div class=v>₹${inr(monthly(subs))}</div><div class=d>${subs.filter(e => e.active).length} active · labelled …/Subscriptions</div></div>
      <div class='card kpi'><h3>Per year</h3><div class=v>₹${inr(monthly(subs) * 12)}</div><div class=d>at today's amounts</div></div>
      <div class='card kpi'><h3>Other recurring / month</h3><div class=v>₹${inr(monthly(other))}</div><div class=d>${other.filter(e => e.active).length} active (rent, EMIs, bills…)</div></div>
      <div class='card kpi'><h3>Possibly stopped</h3><div class=v>${groups.filter(e => !e.active).length}</div><div class=d>no payment in 45+ days</div></div>
    </div>
    <div class=card><h3>Subscriptions</h3>${table(subs, 'Nothing is labelled as a subscription yet. Give a recurring payee a category ending in /Subscriptions.')}</div>
    <div class=card style="margin-top:12px"><h3>Other recurring payments (monthly, detected or labelled)</h3>${table(other, 'No other recurring payments detected.')}</div>
    <div class=note>A payment counts as recurring when it is labelled Monthly, or detected: same payee, similar amount, same day each month for 3+ months. "Stopped?" means nothing was paid for 45 days up to the latest statement. Click a payee for its payments.</div>`;
  $('screen-subs').querySelectorAll('td.nm').forEach(td => td.onclick = () => {
    const tr = td.parentElement, nxt = tr.nextElementSibling;
    if (nxt && nxt.classList.contains('sub2')) { while (tr.nextElementSibling?.classList.contains('sub2')) tr.nextElementSibling.remove(); td.querySelector('.chev').textContent = '▸'; return; }
    const e = groups.find(x => x.name === td.dataset.g); td.querySelector('.chev').textContent = '▾';
    e.rows.slice(0, 24).reverse().forEach(r => { const s = document.createElement('tr'); s.className = 'sub2'; s.innerHTML = `<td colspan=7>${esc(r.transaction_date)} ${esc(r.time || '')} · ₹${inr(-parseFloat(r.amount))} · ${esc(r.source_bank)}</td>`; tr.after(s); });
  });
}

// ---- Work claims: Work/* spend to file for reimbursement -----------------------------------------
let workFilter = localStorage.workFilter || 'todo';
const workRows = () => DATA.filter(r => r.hash && r.status !== 'internal_transfer' && /^Work\\//.test(r.category || '') && ((parseFloat(r.amount) || 0) < 0 || /^(HDFC_|UNI_)/.test(r.source_bank))).sort(byDateDesc);  // only spend is claimable (card refunds net off); Work/Income credits are not
const claimState = r => r.reimbursement || 'todo';
const claimAmt = r => -(parseFloat(r.amount) || 0);

function updateWorkBadge() { const n = workRows().filter(r => claimState(r) === 'todo').length; $('work_n').textContent = n ? n : ''; }

async function setClaim(r, value) {
  const res = await fetch('/annotate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({hash: r.hash, field: 'reimbursement', value: value === 'todo' ? '' : value})});
  if (!res.ok) throw new Error((await res.json()).error || res.status);
  r.reimbursement = value === 'todo' ? '' : value;
}

function claimsCsv(rows) {
  const q = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  return ['Date,Time,Payee,Category,Amount (INR),Bank,Narration', ...rows.map(r => [r.transaction_date, r.time, r.counterparty, r.category, claimAmt(r).toFixed(2), r.source_bank, r.description.replace(/\\s+/g, ' ')].map(q).join(','))].join('\\n');
}

function renderWork() {
  const all = workRows(), sum = st => all.filter(r => claimState(r) === st).reduce((a, r) => a + claimAmt(r), 0), n = st => all.filter(r => claimState(r) === st).length;
  const shown = workFilter === 'all' ? all : all.filter(r => claimState(r) === workFilter);
  $('screen-work').innerHTML = `<div class=m-head><h2 style="min-width:0">Work claims</h2></div>
    <div class=kpis>
      <div class='card kpi'><h3>To file</h3><div class='v ${n('todo') ? 'up' : ''}'>₹${inr(sum('todo'))}</div><div class=d>${n('todo')} transactions</div></div>
      <div class='card kpi'><h3>Filed, awaiting payback</h3><div class=v>₹${inr(sum('filed'))}</div><div class=d>${n('filed')} transactions</div></div>
      <div class='card kpi'><h3>Reimbursed</h3><div class='v down'>₹${inr(sum('reimbursed'))}</div><div class=d>${n('reimbursed')} transactions</div></div>
      <div class='card kpi'><h3>All Work/* spend</h3><div class=v>₹${inr(sum('todo') + sum('filed') + sum('reimbursed'))}</div><div class=d>${all.length} transactions</div></div>
    </div>
    <div class=tools><span class=sw>Show <select id=w_filter>${[['todo', 'To file'], ['filed', 'Filed'], ['reimbursed', 'Reimbursed'], ['all', 'All']].map(([v, l]) => `<option value=${v} ${v === workFilter ? 'selected' : ''}>${l}</option>`).join('')}</select></span>
      <button id=w_csv>Download these ${shown.length} as CSV</button><button class=alt id=w_file>Mark these ${shown.length} as filed</button></div>
    <div class=card>${shown.length ? `<table class=tbl><tr><th>Date</th><th>Time</th><th>Payee</th><th>Category</th><th class=num>Amount</th><th>Bank</th><th>Status</th><th style="width:22%">Note</th></tr>${shown.map((r, i) => `<tr class=r data-i=${i}><td>${esc(r.transaction_date)}</td><td>${esc(r.time) || '—'}</td><td title="${esc(r.description)}">${esc(r.counterparty || r.description.replace(/\\s+/g, ' ').slice(0, 30))}</td><td>${esc(r.category)}</td><td class=num>${claimAmt(r) < 0 ? '+' : ''}₹${inr(Math.abs(claimAmt(r)))}</td><td>${esc(r.source_bank)}</td><td><select>${[['todo', 'To file'], ['filed', 'Filed'], ['reimbursed', 'Reimbursed']].map(([v, l]) => `<option value=${v} ${v === claimState(r) ? 'selected' : ''}>${l}</option>`).join('')}</select></td><td><input value="${esc(r.notes)}" placeholder="invoice #, trip…"></td></tr>`).join('')}</table>` : `<div class=note>Nothing here. Label transactions with a Work/… category (Review tab) and they show up to claim.</div>`}</div>
    <div class=note>Work/* transactions, from the Review or Transactions tabs. Card refunds show as a negative claim. Status and notes are saved as you change them.</div>`;
  $('w_filter').onchange = e => { workFilter = localStorage.workFilter = e.target.value; renderWork(); };
  $('w_csv').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([claimsCsv(shown)], {type: 'text/csv'})); a.download = `work-claims-${new Date().toISOString().slice(0, 10)}.csv`; a.click(); };
  $('w_file').onclick = async () => {
    const todo = shown.filter(r => claimState(r) === 'todo');
    if (!todo.length || !confirm(`Mark ${todo.length} transactions (₹${inr(todo.reduce((a, r) => a + claimAmt(r), 0))}) as filed?`)) return;
    try { for (const r of todo) await setClaim(r, 'filed'); } catch (err) { alert(`Stopped: ${err.message}`); }
    renderWork(); updateWorkBadge();
  };
  $('screen-work').querySelectorAll('tr.r').forEach(tr => {
    const r = shown[+tr.dataset.i];
    tr.querySelector('select').onchange = async e => { try { await setClaim(r, e.target.value); renderWork(); updateWorkBadge(); } catch (err) { e.target.title = `Not saved: ${err.message}`; } };
    tr.querySelector('input').onchange = async e => {
      const res = await fetch('/annotate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({hash: r.hash, field: 'notes', value: e.target.value})});
      if (res.ok) r.notes = e.target.value.trim(); else e.target.title = 'Not saved';
    };
  });
}


// ---- Tasks: insights to act on or hand to an agent ---------------------------------------------
let TASKS = [];
async function postTask(body) {
  const res = await fetch('/task', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  if (!res.ok) throw new Error((await res.json()).error || res.status);
}
async function loadTasks() {
  const res = await fetch('/tasks'); TASKS = await res.json();
  const open = TASKS.filter(t => t.status === 'open' || t.status === 'doing').length;
  $('tasks_n').textContent = open || '';
  if (!$('screen-tasks').hidden) renderTasks();
}
function renderTasks() {
  const live = TASKS.filter(t => t.status === 'open' || t.status === 'doing'), fin = TASKS.filter(t => t.status === 'done' || t.status === 'dismissed');
  const row = (t, i) => `<div class="task p${t.priority} ${t.status === 'done' || t.status === 'dismissed' ? 'fin' : ''}" data-i=${i}><span class=bar1></span>
    <div><div class=tt>${esc(t.title)}</div><div class=td>${esc(t.detail)}</div>${t.prompt ? `<button class=cp>Copy agent prompt</button>` : ''}</div>
    <span><span class="pill ${t.owner}">${t.owner === 'agent' ? 'agent can do' : 'you'}</span></span>
    <select>${['open', 'doing', 'done', 'dismissed'].map(v => `<option value=${v} ${v === t.status ? 'selected' : ''}>${v}</option>`).join('')}</select>
    <input value="${esc(t.note)}" placeholder="note…"></div>`;
  $('screen-tasks').innerHTML = `<div class=m-head><h2 style="min-width:0">Tasks</h2></div>
    <div class=note style="margin:0 0 8px">Built from your data: bills, late fees, unlabelled spend, stale statements, claims. Tasks marked "agent can do" carry a prompt you can hand to an agent; it only reads and prepares. Nothing runs by itself.</div>
    <form class=addt id=t_form><input name=title placeholder="Add your own task…"><select name=owner><option value=you>you</option><option value=agent>agent can do</option></select><select name=priority><option value=1>high</option><option value=2 selected>normal</option><option value=3>low</option></select><button>Add</button></form>
    <div class=card>${live.length ? live.map(t => row(t, TASKS.indexOf(t))).join('') : '<div class=note>Nothing to do. ✓</div>'}</div>
    ${fin.length ? `<div class=card style="margin-top:12px"><h3>Done or dismissed (${fin.length})</h3>${fin.map(t => row(t, TASKS.indexOf(t))).join('')}</div>` : ''}`;
  $('t_form').onsubmit = async e => {
    e.preventDefault(); const f = new FormData(e.target);
    if (!String(f.get('title')).trim()) return;
    try { await postTask({title: f.get('title'), owner: f.get('owner'), priority: Number(f.get('priority'))}); await loadTasks(); } catch (err) { alert('Not saved: ' + err.message); }
  };
  $('screen-tasks').querySelectorAll('.task').forEach(el1 => {
    const t = TASKS[+el1.dataset.i];
    el1.querySelector('select').onchange = async e => { try { await postTask({id: t.id, status: e.target.value}); await loadTasks(); } catch (err) { e.target.title = 'Not saved: ' + err.message; } };
    el1.querySelector('input').onchange = async e => { try { await postTask({id: t.id, note: e.target.value}); t.note = e.target.value.trim(); } catch (err) { e.target.title = 'Not saved: ' + err.message; } };
    const cp = el1.querySelector('.cp');
    if (cp) cp.onclick = async () => { await navigator.clipboard.writeText(t.prompt); cp.textContent = 'Copied ✓'; };
  });
}

function showTab(tab) {
  localStorage.tab = tab;
  for (const [t, id] of Object.entries({month: 'screen-month', tx: 'screen-tx', review: 'screen-review', subs: 'screen-subs', work: 'screen-work', tasks: 'screen-tasks'})) $(id).hidden = tab !== t;
  document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
  if (tab === 'month') loadMonth(localStorage.analysisMonth);
  else if (tab === 'tasks') loadTasks();
  else if (tab === 'subs') renderSubs();
  else if (tab === 'work') renderWork();
  else if (tab === 'review') { if (!$('p_month').options.length) fillReviewMonths(); fillReview(); }
  else { setStickyOffsets(); render(); }
}
document.querySelectorAll('#tabs button').forEach(b => b.addEventListener('click', () => showTab(b.dataset.tab)));

init();
snapshotOpen(); fillReviewMonths(); fillReview(); setReviewView(reviewView); updateWorkBadge(); loadTasks();
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
                    .replace("{{DUES}}", _script_json(card_dues(settings, current_rows()) if settings else []))
                    .replace("{{GAPS}}", _script_json(statement_gaps(settings.paths.input) if settings else []))
                    .replace("{{SUGGESTIONS}}", _script_json(suggestions))
                )
                self._send(200, "text/html; charset=utf-8", html.encode())
            elif self.path == "/tasks" and settings:
                rows = current_rows()
                self._send_json(
                    200,
                    all_tasks(
                        rows,
                        card_dues(settings, rows),
                        statement_gaps(settings.paths.input),
                        date.today(),
                        settings.paths.tasks,
                        str(Path.cwd()),
                    ),
                )
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
            if self.path not in ("/unlock", "/annotate", "/accept", "/task") or settings is None:
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
            if self.path == "/task":
                self._task(settings)
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

        def _task(self, settings: Settings) -> None:
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if body.get("title"):
                    task_id = add_task(
                        settings.paths.tasks,
                        str(body["title"]),
                        str(body.get("detail", "")),
                        str(body.get("owner", "you")),
                        int(body.get("priority", 2)),
                    )
                    self._send_json(200, {"ok": True, "id": task_id})
                    return
                set_task(settings.paths.tasks, str(body["id"]), status=body.get("status"), note=body.get("note"))
            except (KeyError, ValueError) as exc:
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
