#!/usr/bin/env python3
"""
stats.py — Genera el informe HTML interactivo a partir de la base de datos

Uso:
    python3 stats.py                        # genera informe.html
    python3 stats.py --output mi_informe.html
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv  # type: ignore

load_dotenv()

DB_PATH     = Path(os.getenv("DB_PATH", "ejercicios.db")).expanduser()
OUTPUT_HTML = Path(os.getenv("OUTPUT_HTML", "informe.html")).expanduser()


def load_data(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute("""
        SELECT * FROM actividades
        WHERE fecha != ''
        ORDER BY fecha DESC, hora_inicio DESC
    """)
    return [dict(row) for row in cur.fetchall()]


def generate_html(actividades: list[dict], output: Path):
    data_json = json.dumps(actividades, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TicWatch — Ejercicios</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,600;1,9..40,300&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════
   VARIABLES Y RESET
═══════════════════════════════════════════════ */
:root {{
  --bg:          #0d0f14;
  --bg2:         #13161e;
  --bg3:         #1a1e29;
  --border:      #252938;
  --text:        #c8cfe0;
  --text-dim:    #5a6080;
  --text-bright: #e8ecf5;
  --accent:      #4f8ef7;
  --accent2:     #7c5cf5;
  --green:       #36d986;
  --orange:      #f59c36;
  --red:         #f75f5f;
  --cyan:        #36c9d9;
  --font-mono:   'DM Mono', monospace;
  --font-sans:   'DM Sans', sans-serif;
  --radius:      10px;
  --radius-lg:   16px;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 15px; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  min-height: 100vh;
  padding: 0;
}}

/* ═══════════════════════════════════════════════
   LAYOUT
═══════════════════════════════════════════════ */
.app {{
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px 80px;
}}

header {{
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 36px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}}
header h1 {{
  font-family: var(--font-mono);
  font-size: 1.4rem;
  font-weight: 500;
  color: var(--accent);
  letter-spacing: -.02em;
}}
header .subtitle {{
  font-size: .85rem;
  color: var(--text-dim);
  font-family: var(--font-mono);
}}

/* ═══════════════════════════════════════════════
   CONTROLES DE FILTRO
═══════════════════════════════════════════════ */
.controls {{
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 28px;
  padding: 16px 20px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}}
.controls label {{
  font-size: .78rem;
  color: var(--text-dim);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-right: 4px;
}}
.controls input[type=date],
.controls select {{
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-bright);
  font-family: var(--font-mono);
  font-size: .85rem;
  padding: 6px 10px;
  cursor: pointer;
  transition: border-color .2s;
}}
.controls input[type=date]:hover,
.controls select:hover {{
  border-color: var(--accent);
}}
.btn-group {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}}
.btn {{
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: .78rem;
  padding: 6px 12px;
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
}}
.btn:hover, .btn.active {{
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}}
.sep {{ width: 1px; background: var(--border); align-self: stretch; margin: 0 4px; }}

/* ═══════════════════════════════════════════════
   TARJETAS DE RESUMEN + CALENDARIO (layout conjunto)
═══════════════════════════════════════════════ */
.top-layout {{
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 14px;
  align-items: start;
  margin-bottom: 28px;
}}
.summary-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}}
@media (max-width: 750px) {{
  .summary-grid {{
    grid-template-columns: repeat(2, 1fr);
  }}
}}
@media (max-width: 750px) {{
  .top-layout {{
    grid-template-columns: 1fr;
  }}
  .calendar-wrap {{
    display: block !important;
    width: 100% !important;
  }}
  .cal-grid {{
    grid-template-columns: repeat(7, 1fr) !important;
    width: 100%;
  }}
  .cal-day {{
    min-width: unset !important;
    max-width: unset !important;
  }}
}}
.card {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 18px 16px;
  position: relative;
  overflow: hidden;
  transition: border-color .2s, transform .15s;
}}
.card:hover {{ border-color: var(--accent); transform: translateY(-1px); }}
.card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--card-accent, var(--accent));
}}
.card-label {{
  font-size: .72rem;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--text-dim);
  margin-bottom: 10px;
}}
.card-value {{
  font-size: 2rem;
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--text-bright);
  line-height: 1;
}}
.card-unit {{
  font-size: .75rem;
  color: var(--text-dim);
  font-family: var(--font-mono);
  margin-top: 4px;
}}
.card-pct {{
  font-size: .72rem;
  color: var(--text-dim);
  font-family: var(--font-mono);
  margin-top: 6px;
  opacity: .6;
}}

/* ═══════════════════════════════════════════════
   CALENDARIO
═══════════════════════════════════════════════ */
.section-title {{
  font-family: var(--font-mono);
  font-size: .8rem;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--text-dim);
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.section-title::after {{
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}}

.calendar-wrap {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 20px 16px;
  display: inline-block;
  vertical-align: top;
}}
.cal-nav {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  width: 100%;
}}
.cal-nav h2 {{
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-bright);
  flex: 1;
  text-align: center;
}}
.cal-nav button {{
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 1rem;
  width: 32px; height: 32px;
  cursor: pointer;
  transition: all .15s;
  display: flex; align-items: center; justify-content: center;
}}
.cal-nav button:hover {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

.cal-grid {{
  display: grid;
  grid-template-columns: repeat(7, 38px);
  gap: 4px;
}}
.cal-day-name {{
  text-align: center;
  font-family: var(--font-mono);
  font-size: .7rem;
  color: var(--text-dim);
  text-transform: uppercase;
  padding: 4px 0 8px;
  letter-spacing: .06em;
}}
.cal-day {{
  aspect-ratio: 1;
  border-radius: 5px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: default;
  font-family: var(--font-mono);
  font-size: .68rem;
  color: var(--text-dim);
  position: relative;
  transition: all .15s;
  min-width: 24px;
  max-width: 40px;
}}
.cal-day.empty {{ background: transparent; }}
.cal-day.today {{
  border: 1px solid var(--accent);
  color: var(--accent);
}}
.cal-day.has-activity {{
  cursor: pointer;
  color: var(--text-bright);
}}
.cal-day.has-activity:hover {{
  transform: scale(1.08);
  z-index: 10;
}}

/* Intensidad: minutos de ejercicio ese día */
.cal-day[data-intensity="1"]  {{ background: #1a3a2a; }}
.cal-day[data-intensity="2"]  {{ background: #1e4a34; }}
.cal-day[data-intensity="3"]  {{ background: #225c3e; }}
.cal-day[data-intensity="4"]  {{ background: #277048; }}
.cal-day[data-intensity="5"]  {{ background: #2c8454; }}
.cal-day[data-intensity="6"]  {{ background: #31a060; }}
.cal-day[data-intensity="7"]  {{ background: #36ba6c; }}
.cal-day[data-intensity="8"]  {{ background: #36d986; }}
.cal-day[data-intensity="1"] .cal-min,
.cal-day[data-intensity="2"] .cal-min,
.cal-day[data-intensity="3"] .cal-min {{ color: #4a9a6a; font-size: .58rem; }}
.cal-day[data-intensity="4"] .cal-min,
.cal-day[data-intensity="5"] .cal-min {{ color: #80d0a0; font-size: .58rem; }}
.cal-day[data-intensity="6"] .cal-min,
.cal-day[data-intensity="7"] .cal-min,
.cal-day[data-intensity="8"] .cal-min {{ color: #b0f0d0; font-size: .58rem; }}
.cal-min {{ font-size: .58rem; line-height: 1; margin-top: 2px; }}

/* Tooltip del día */
.cal-tooltip {{
  display: none;
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  white-space: nowrap;
  z-index: 100;
  font-size: .78rem;
  color: var(--text-bright);
  pointer-events: none;
  box-shadow: 0 8px 24px rgba(0,0,0,.5);
  min-width: 160px;
  text-align: left;
}}
.cal-day:hover .cal-tooltip {{ display: block; }}

/* ═══════════════════════════════════════════════
   TABLA DE ACTIVIDADES
═══════════════════════════════════════════════ */
.table-wrap {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 28px;
}}
.table-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}}
.table-header h3 {{
  font-family: var(--font-mono);
  font-size: .85rem;
  font-weight: 500;
  color: var(--text-bright);
}}
.table-count {{
  font-family: var(--font-mono);
  font-size: .78rem;
  color: var(--text-dim);
}}

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: .83rem;
}}
thead th {{
  background: var(--bg3);
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: .7rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}}
thead th:hover {{ color: var(--accent); }}
thead th.sorted {{ color: var(--accent); }}
thead th .sort-icon {{ margin-left: 4px; opacity: .5; }}
thead th.sorted .sort-icon {{ opacity: 1; }}

tbody tr {{
  border-bottom: 1px solid var(--border);
  transition: background .1s;
}}
tbody tr:last-child {{ border-bottom: none; }}
tbody tr:hover {{ background: var(--bg3); }}
tbody td {{
  padding: 11px 14px;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: .82rem;
  white-space: nowrap;
}}
.td-date {{ color: var(--text-dim); }}
.td-type {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
}}
.type-dot {{
  width: 7px; height: 7px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}}
.td-dur {{ color: var(--green); }}
.td-cal {{ color: var(--orange); }}
.td-fc  {{ color: var(--red); }}
.td-dist {{ color: var(--cyan); }}

.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: .72rem;
  font-family: var(--font-mono);
}}

/* ═══════════════════════════════════════════════
   GRÁFICO DE BARRAS MENSUAL
═══════════════════════════════════════════════ */
.chart-wrap {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 28px;
}}
.bar-chart {{
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 140px;
  padding: 0 4px;
}}
.bar-col {{
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  cursor: default;
}}
.bar-fill {{
  width: 100%;
  border-radius: 4px 4px 0 0;
  background: var(--accent);
  min-height: 2px;
  transition: opacity .2s;
  position: relative;
}}
.bar-fill:hover {{ opacity: .8; }}
.bar-label {{
  font-family: var(--font-mono);
  font-size: .65rem;
  color: var(--text-dim);
  text-align: center;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  line-height: 1;
  padding: 2px 0;
}}
.bar-val {{
  font-family: var(--font-mono);
  font-size: .65rem;
  color: var(--text-dim);
  position: absolute;
  top: -16px;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
}}

/* ═══════════════════════════════════════════════
   RESPONSIVE
═══════════════════════════════════════════════ */
@media (max-width: 700px) {{
  .app {{ padding: 16px 12px 60px; }}
  .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .controls {{ gap: 8px; }}
  table {{ font-size: .75rem; }}
  tbody td {{ padding: 9px 8px; }}
  .cal-day {{ min-width: 28px; font-size: .72rem; }}
}}
</style>
</head>
<body>
<div class="app">

  <header>
    <h1>⌚ TicWatch Analyzer</h1>
    <span class="subtitle">— registro de actividad física</span>
  </header>

  <!-- CONTROLES -->
  <div class="controls">
    <div class="btn-group" id="period-btns">
      <button class="btn" onclick="setPeriod(7)">7d</button>
      <button class="btn" onclick="setPeriod(30)">30d</button>
      <button class="btn" onclick="setPeriod(90)">3m</button>
      <button class="btn" onclick="setPeriod(365)">1a</button>
      <button class="btn active" onclick="setPeriod(0)">todo</button>
    </div>
    <div class="sep"></div>
    <label>Desde</label>
    <input type="date" id="date-from" onchange="applyFilters()">
    <label>Hasta</label>
    <input type="date" id="date-to"   onchange="applyFilters()">
    <div class="sep"></div>
    <label>Tipo</label>
    <select id="filter-type" onchange="applyFilters()">
      <option value="">Todos</option>
    </select>
  </div>

  <!-- TARJETAS + CALENDARIO -->
  <div class="top-layout">
    <div class="summary-grid" id="summary-grid"></div>
    <div class="calendar-wrap">
      <div class="section-title">Calendario</div>
      <div class="cal-nav">
        <button onclick="calNav(-1)">&#8249;</button>
        <h2 id="cal-title"></h2>
        <button onclick="calNav(1)">&#8250;</button>
      </div>
      <div class="cal-grid" id="cal-grid"></div>
    </div>
  </div>

  <!-- GRÁFICO MENSUAL -->
  <div class="chart-wrap">
    <div class="section-title">Minutos por mes</div>
    <div class="bar-chart" id="bar-chart"></div>
  </div>

  <!-- TABLA -->
  <div class="table-wrap">
    <div class="table-header">
      <h3>Actividades</h3>
      <span class="table-count" id="table-count"></span>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead>
          <tr>
            <th onclick="sortTable('fecha')"        class="sorted" id="th-fecha">   Fecha <span class="sort-icon">↓</span></th>
            <th onclick="sortTable('hora_inicio')"  id="th-hora_inicio">  Hora <span class="sort-icon">↕</span></th>
            <th onclick="sortTable('tipo_actividad')" id="th-tipo_actividad">Tipo <span class="sort-icon">↕</span></th>
            <th onclick="sortTable('duracion_seg')" id="th-duracion_seg"> Duración <span class="sort-icon">↕</span></th>
            <th onclick="sortTable('distancia_m')"  id="th-distancia_m">  Dist. <span class="sort-icon">↕</span></th>
            <th onclick="sortTable('velocidad_media')" id="th-velocidad_media"> Vel. <span class="sort-icon">↕</span></th>
            <th onclick="sortTable('calorias')"     id="th-calorias">     Kcal <span class="sort-icon">↕</span></th>
            <th onclick="sortTable('fc_media')"     id="th-fc_media">     FC med. <span class="sort-icon">↕</span></th>
            <th onclick="sortTable('fc_max')"       id="th-fc_max">       FC máx <span class="sort-icon">↕</span></th>
          </tr>
        </thead>
        <tbody id="activity-table"></tbody>
      </table>
    </div>
  </div>

</div>

<script>
// ═══════════════════════════════════════════════
// DATOS
// ═══════════════════════════════════════════════
const ALL_DATA = {data_json};

// ═══════════════════════════════════════════════
// ESTADO
// ═══════════════════════════════════════════════
let filtered = [...ALL_DATA];
let sortKey  = 'fecha';
let sortAsc  = false;
let calYear, calMonth;

const TYPE_COLORS = {{}};
const PALETTE = ['#4f8ef7','#7c5cf5','#36d986','#f59c36','#f75f5f','#36c9d9',
                 '#f7a64f','#9bf75f','#f75fa0','#5ff7e8','#c4f75f','#f75f5f'];

// ═══════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════
function tipoMostrado(d) {{
  const t = d.tipo_actividad || 'Desconocido';
  if (t === 'Otro') return d.distancia_m ? 'Correr en cinta' : 'Ej. de Fuerza';
  return t;
}}

// ═══════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════
function init() {{
  // Tipos únicos usando el nombre mostrado (con "Otro" ya corregido)
  const tiposSet = [...new Set(ALL_DATA.map(d => tipoMostrado(d)).filter(Boolean))].sort();
  // Colores por nombre mostrado
  tiposSet.forEach((t, i) => {{ TYPE_COLORS[t] = PALETTE[i % PALETTE.length]; }});
  const sel = document.getElementById('filter-type');
  tiposSet.forEach(t => {{
    const opt = document.createElement('option');
    opt.value = t; opt.textContent = t;
    sel.appendChild(opt);
  }});

  // Calendario: mes más reciente con datos
  const fechas = ALL_DATA.map(d => d.fecha).filter(Boolean).sort();
  const ultima = fechas[fechas.length - 1] || new Date().toISOString().slice(0,7);
  const [y, m] = ultima.split('-').map(Number);
  calYear  = y;
  calMonth = m;

  applyFilters();
}}

// ═══════════════════════════════════════════════
// FILTROS
// ═══════════════════════════════════════════════
function setPeriod(days) {{
  document.querySelectorAll('#period-btns .btn').forEach(b => b.classList.remove('active'));
  event.currentTarget.classList.add('active');

  if (days === 0) {{
    document.getElementById('date-from').value = '';
    document.getElementById('date-to').value   = '';
  }} else {{
    const to   = new Date();
    const from = new Date();
    from.setDate(from.getDate() - days);
    document.getElementById('date-from').value = from.toISOString().slice(0,10);
    document.getElementById('date-to').value   = to.toISOString().slice(0,10);
  }}
  applyFilters();
}}

function applyFilters() {{
  const from = document.getElementById('date-from').value;
  const to   = document.getElementById('date-to').value;
  const tipo = document.getElementById('filter-type').value;

  filtered = ALL_DATA.filter(d => {{
    if (from && d.fecha < from) return false;
    if (to   && d.fecha > to)   return false;
    if (tipo && tipoMostrado(d) !== tipo) return false;
    return true;
  }});

  sortData();
  renderSummary();
  renderBarChart();
  renderCalendar();
  renderTable();
}}

// ═══════════════════════════════════════════════
// ORDENACIÓN
// ═══════════════════════════════════════════════
function sortTable(key) {{
  if (sortKey === key) sortAsc = !sortAsc;
  else {{ sortKey = key; sortAsc = false; }}

  document.querySelectorAll('thead th').forEach(th => {{
    th.classList.remove('sorted');
    th.querySelector('.sort-icon').textContent = '↕';
  }});
  const th = document.getElementById('th-' + key);
  if (th) {{
    th.classList.add('sorted');
    th.querySelector('.sort-icon').textContent = sortAsc ? '↑' : '↓';
  }}
  sortData();
  renderTable();
}}

function sortData() {{
  filtered.sort((a, b) => {{
    let va = a[sortKey] ?? '', vb = b[sortKey] ?? '';
    if (typeof va === 'number' && typeof vb === 'number')
      return sortAsc ? va - vb : vb - va;
    va = String(va); vb = String(vb);
    return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
  }});
}}

// ═══════════════════════════════════════════════
// RESUMEN
// ═══════════════════════════════════════════════
function renderSummary() {{
  const totalSeg = filtered.reduce((s,d) => s + (d.duracion_seg||0), 0);
  const totalCal = filtered.reduce((s,d) => s + (d.calorias||0), 0);
  const fcArr    = filtered.filter(d => d.fc_media).map(d => d.fc_media);
  const fcMedia  = fcArr.length ? Math.round(fcArr.reduce((a,b)=>a+b,0)/fcArr.length) : null;
  const distArr  = filtered.filter(d => d.distancia_m).reduce((s,d)=>s+(d.distancia_m||0),0);
  const nDias    = new Set(filtered.map(d=>d.fecha)).size;
  const nSesiones= filtered.length;
  const durMedia  = nSesiones ? Math.round(totalSeg / nSesiones / 60) : 0;

  // % de días activos sobre el período seleccionado
  let pctDias = '';
  const from = document.getElementById('date-from').value;
  const to   = document.getElementById('date-to').value;
  if (nDias > 0) {{
    let totalDiasPeriodo = 0;
    if (from && to) {{
      const d1 = new Date(from), d2 = new Date(to);
      totalDiasPeriodo = Math.round((d2 - d1) / 86400000) + 1;
    }} else {{
      // Sin filtro: días entre primera y última actividad
      const fechas = filtered.map(d=>d.fecha).filter(Boolean).sort();
      if (fechas.length >= 2) {{
        const d1 = new Date(fechas[0]), d2 = new Date(fechas[fechas.length-1]);
        totalDiasPeriodo = Math.round((d2 - d1) / 86400000) + 1;
      }}
    }}
    if (totalDiasPeriodo > 0) {{
      const pct = Math.round(nDias / totalDiasPeriodo * 100);
      pctDias = `${{pct}}% de ${{totalDiasPeriodo}} días`;
    }}
  }}

  // Racha máxima de días consecutivos con actividad
  let rachaMax = 0;
  if (filtered.length > 0) {{
    const diasSet = [...new Set(filtered.map(d=>d.fecha).filter(Boolean))].sort();
    let racha = 1;
    for (let i = 1; i < diasSet.length; i++) {{
      const prev = new Date(diasSet[i-1]);
      const curr = new Date(diasSet[i]);
      const diff = Math.round((curr - prev) / 86400000);
      if (diff === 1) {{
        racha++;
        rachaMax = Math.max(rachaMax, racha);
      }} else {{
        racha = 1;
      }}
    }}
    rachaMax = Math.max(rachaMax, 1);
  }}

  const h = Math.floor(totalSeg / 3600);
  const m = Math.floor((totalSeg % 3600) / 60);
  const durStr = h > 0 ? `${{h}}h${{m.toString().padStart(2,'0')}}'` : `${{m}}'`;

  const grid = document.getElementById('summary-grid');
  grid.innerHTML = `
    <div class="card" style="--card-accent:var(--accent)">
      <div class="card-label">Sesiones</div>
      <div class="card-value">${{nSesiones}}</div>
      <div class="card-unit">actividades</div>
    </div>
    <div class="card" style="--card-accent:var(--accent2)">
      <div class="card-label">Días activos</div>
      <div class="card-value">${{nDias}}</div>
      <div class="card-unit">días con ejercicio</div>
      ${{pctDias ? `<div class="card-pct">${{pctDias}}</div>` : ''}}
    </div>
    <div class="card" style="--card-accent:var(--green)">
      <div class="card-label">Tiempo total</div>
      <div class="card-value">${{durStr}}</div>
      <div class="card-unit">horas y minutos</div>
    </div>
    <div class="card" style="--card-accent:var(--cyan)">
      <div class="card-label">Duración med.</div>
      <div class="card-value">${{durMedia}}</div>
      <div class="card-unit">min por sesión</div>
    </div>
    <div class="card" style="--card-accent:var(--orange)">
      <div class="card-label">Calorías</div>
      <div class="card-value">${{totalCal>0 ? totalCal.toLocaleString('es') : '—'}}</div>
      <div class="card-unit">kcal totales</div>
    </div>
    <div class="card" style="--card-accent:var(--red)">
      <div class="card-label">FC media</div>
      <div class="card-value">${{fcMedia ? fcMedia+'bpm' : '—'}}</div>
      <div class="card-unit">latidos por min</div>
    </div>
    <div class="card" style="--card-accent:var(--accent)">
      <div class="card-label">Distancia</div>
      <div class="card-value">${{distArr>0 ? (distArr/1000).toFixed(1)+'km' : '—'}}</div>
      <div class="card-unit">kilómetros totales</div>
    </div>
    <div class="card" style="--card-accent:var(--green)">
      <div class="card-label">Racha máxima</div>
      <div class="card-value">${{rachaMax || '—'}}</div>
      <div class="card-unit">días consecutivos</div>
    </div>
  `;
}}

// ═══════════════════════════════════════════════
// GRÁFICO DE BARRAS
// ═══════════════════════════════════════════════
function renderBarChart() {{
  // Agrupar por mes: YYYY-MM
  const byMonth = {{}};
  filtered.forEach(d => {{
    const mes = (d.fecha||'').slice(0,7);
    if (!mes) return;
    byMonth[mes] = (byMonth[mes]||0) + Math.round((d.duracion_seg||0)/60);
  }});

  const meses = Object.keys(byMonth).sort();
  if (!meses.length) {{
    document.getElementById('bar-chart').innerHTML = '<div style="color:var(--text-dim);font-family:var(--font-mono);font-size:.8rem;padding:40px;margin:auto">Sin datos en el período</div>';
    return;
  }}

  const maxVal = Math.max(...Object.values(byMonth));
  const MESES_ES = ['','Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];

  const bars = meses.map(mes => {{
    const [y, mo] = mes.split('-');
    const label = `${{MESES_ES[+mo]}} ${{y.slice(2)}}`;
    const val   = byMonth[mes];
    const pct   = maxVal > 0 ? (val / maxVal * 100) : 0;
    const h     = Math.max(2, pct * 1.2);
    const hStr  = val >= 60 ? `${{Math.floor(val/60)}}h${{(val%60).toString().padStart(2,'0')}}m` : `${{val}}m`;
    return `
      <div class="bar-col" title="${{label}}: ${{hStr}}">
        <div class="bar-fill" style="height:${{h}}px; background: linear-gradient(to top, var(--accent), var(--accent2))">
          <span class="bar-val">${{hStr}}</span>
        </div>
        <div class="bar-label">${{label}}</div>
      </div>`;
  }});

  document.getElementById('bar-chart').innerHTML = bars.join('');
}}

// ═══════════════════════════════════════════════
// CALENDARIO
// ═══════════════════════════════════════════════
function calNav(dir) {{
  calMonth += dir;
  if (calMonth > 12) {{ calMonth = 1;  calYear++; }}
  if (calMonth <  1) {{ calMonth = 12; calYear--; }}
  renderCalendar();
}}

function renderCalendar() {{
  const MESES_ES = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
                   'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
  const DIAS_ES  = ['Lu','Ma','Mi','Ju','Vi','Sá','Do'];

  document.getElementById('cal-title').textContent = `${{MESES_ES[calMonth]}} ${{calYear}}`;

  // Mapa: fecha → lista de actividades
  const byDay = {{}};
  ALL_DATA.forEach(d => {{ // siempre todo el historial para el calendario
    const f = d.fecha;
    if (!f) return;
    if (!byDay[f]) byDay[f] = [];
    byDay[f].push(d);
  }});

  const firstDay = new Date(calYear, calMonth-1, 1);
  const lastDay  = new Date(calYear, calMonth,   0);
  // Lunes=0 … Domingo=6
  let startOffset = (firstDay.getDay() + 6) % 7;

  let html = DIAS_ES.map(d => `<div class="cal-day-name">${{d}}</div>`).join('');

  // Celdas vacías iniciales
  for (let i = 0; i < startOffset; i++)
    html += '<div class="cal-day empty"></div>';

  const today = new Date().toISOString().slice(0,10);

  for (let day = 1; day <= lastDay.getDate(); day++) {{
    const fecha = `${{calYear}}-${{String(calMonth).padStart(2,'0')}}-${{String(day).padStart(2,'0')}}`;
    const acts  = byDay[fecha] || [];
    const totalMin = Math.round(acts.reduce((s,a)=>s+(a.duracion_seg||0), 0) / 60);
    const totalCal = acts.reduce((s,a)=>s+(a.calorias||0),0);

    // Intensidad 0-8 según minutos
    let intensity = 0;
    if (totalMin >   0) intensity = 1;
    if (totalMin >  15) intensity = 2;
    if (totalMin >  30) intensity = 3;
    if (totalMin >  45) intensity = 4;
    if (totalMin >  60) intensity = 5;
    if (totalMin >  90) intensity = 6;
    if (totalMin > 120) intensity = 7;
    if (totalMin > 180) intensity = 8;

    const cls   = [
      'cal-day',
      acts.length ? 'has-activity' : '',
      fecha === today ? 'today' : ''
    ].filter(Boolean).join(' ');

    let tooltip = '';
    if (acts.length) {{
      const rows = acts.map(a => {{
        const min = Math.round((a.duracion_seg||0)/60);
        const cal = a.calorias ? ` · ${{a.calorias}} kcal` : '';
        const fc  = a.fc_media ? ` · ${{a.fc_media}} bpm` : '';
        return `• ${{tipoMostrado(a)}} ${{min}}min${{cal}}${{fc}}`;
      }}).join('<br>');
      tooltip = `<div class="cal-tooltip"><strong>${{fecha}}</strong><br>${{rows}}</div>`;
    }}

    const minStr = totalMin > 0 ? `<span class="cal-min">${{totalMin}}'</span>` : '';

    html += `<div class="${{cls}}" data-intensity="${{intensity}}" title="">${{day}}${{minStr}}${{tooltip}}</div>`;
  }}

  document.getElementById('cal-grid').innerHTML = html;
}}

// ═══════════════════════════════════════════════
// TABLA
// ═══════════════════════════════════════════════
function renderTable() {{
  document.getElementById('table-count').textContent =
    `${{filtered.length}} actividad${{filtered.length !== 1 ? 'es' : ''}}`;

  const rows = filtered.map(d => {{
    const min  = Math.round((d.duracion_seg||0) / 60);
    const h    = Math.floor(min/60);
    const m    = min % 60;
    const durStr = h > 0 ? `${{h}}h ${{m.toString().padStart(2,'0')}}'` : `${{m}}'`;
    const dist = d.distancia_m ? (d.distancia_m/1000).toFixed(2)+'km' : '—';
    const cal  = d.calorias ? d.calorias.toLocaleString('es') : '—';
    const fc   = d.fc_media ? d.fc_media+'bpm' : '—';
    const fcx  = d.fc_max   ? d.fc_max+'bpm'   : '—';

    // Velocidad media: solo si hay distancia Y duración
    let vel = '—';
    if (d.distancia_m && d.duracion_seg > 0) {{
      const kmh = (d.distancia_m / 1000) / (d.duracion_seg / 3600);
      vel = kmh.toFixed(1) + ' km/h';
    }}

    // Tipo de actividad con corrección para "Otro"
    const tipo = tipoMostrado(d);
    const col  = TYPE_COLORS[tipo] || 'var(--accent)';

    // Formatear fecha como DD-MM-AAAA
    const fechaFmt = d.fecha
      ? d.fecha.slice(8,10) + '-' + d.fecha.slice(5,7) + '-' + d.fecha.slice(0,4)
      : '—';

    return `<tr>
      <td class="td-date">${{fechaFmt}}</td>
      <td class="td-date">${{d.hora_inicio||'—'}}${{d.hora_fin ? '–'+d.hora_fin : ''}}</td>
      <td><span class="td-type"><span class="type-dot" style="background:${{col}}"></span>${{tipo}}</span></td>
      <td class="td-dur">${{durStr}}</td>
      <td class="td-dist">${{dist}}</td>
      <td class="td-dist">${{vel}}</td>
      <td class="td-cal">${{cal}}</td>
      <td class="td-fc">${{fc}}</td>
      <td class="td-fc">${{fcx}}</td>
    </tr>`;
  }}).join('');

  document.getElementById('activity-table').innerHTML = rows ||
    '<tr><td colspan="9" style="text-align:center;color:var(--text-dim);padding:32px;font-family:var(--font-mono)">Sin actividades en el período seleccionado</td></tr>';
}}

// Arrancar
init();
</script>
</body>
</html>"""

    output.write_text(html, encoding="utf-8")
    print(f"✅ Informe generado: {output.resolve()}")
    print(f"   Ábrelo con:  xdg-open {output}  (o directamente en Firefox/Edge)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_HTML)
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"❌ No existe {DB_PATH}. Ejecuta primero: python3 parse.py")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    actividades = load_data(conn)
    conn.close()

    if not actividades:
        print("⚠️  La base de datos está vacía. Ejecuta: python3 parse.py")
        sys.exit(1)

    print(f"📊 Generando informe con {len(actividades)} actividades...")
    generate_html(actividades, args.output)


if __name__ == "__main__":
    main()
