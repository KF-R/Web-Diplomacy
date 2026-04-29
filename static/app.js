let STATE = null;

const $ = (id) => document.getElementById(id);

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: {'Content-Type': 'application/json'},
    ...opts
  });
  let data;
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok || data.ok === false) {
    const msg = (data.errors || [res.statusText]).join('\n');
    throw new Error(msg);
  }
  return data;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function powerName(p) {
  return (STATE && STATE.power_names && STATE.power_names[p]) || p;
}

function unitLoc(u) {
  if (u.type === 'F' && u.coast === 's' && ['Bul','Spa','Stp'].includes(u.loc)) return u.loc.toUpperCase();
  return u.loc;
}

function unitOrderText(u) {
  return `${u.type} ${unitLoc(u)}`;
}

function unitSvgId(u) {
  const suffix = u.type === 'F' && u.coast === 's' ? 's' : '';
  return `${u.loc}_pos_${u.type}${suffix}`;
}

function attrJson(value) {
  return encodeURIComponent(JSON.stringify(value || []));
}

function decodeAttrJson(value) {
  try { return JSON.parse(decodeURIComponent(value || '%5B%5D')); }
  catch { return []; }
}

function optionHtml(values, selected = '') {
  return values.map(v => `<option value="${escapeHtml(v)}" ${v === selected ? 'selected' : ''}>${escapeHtml(v)}</option>`).join('');
}

function refreshBuildLocation(row) {
  const typeSel = row.querySelector('[data-field="type"]');
  const locSel = row.querySelector('[data-field="loc"]');
  if (!typeSel || !locSel) return;
  const choices = decodeAttrJson(typeSel.value === 'F' ? locSel.dataset.sitesF : locSel.dataset.sitesA);
  const oldValue = locSel.value;
  const selected = choices.includes(oldValue) ? oldValue : (choices[0] || '');
  locSel.innerHTML = optionHtml(choices, selected);
}

function reloadBoard() {
  $('boardObject').data = '/board.svg?t=' + Date.now();
}

async function loadState() {
  const res = await fetch('/api/state');
  STATE = await res.json();
  render();
}

function render() {
  $('subhead').textContent = `${STATE.summary.turn} · ${STATE.summary.phase}`;
  $('phaseBadge').textContent = `${STATE.summary.turn} · ${STATE.summary.phase}`;
  $('ordersText').value = STATE.orders_text || '';
  $('ctrlLand').checked = !!(STATE.settings && STATE.settings.colour_controlled_land);

  const hideOrderButtons = STATE.phase === 'RETREAT' || STATE.phase === 'ADJUSTMENT';
  $('ordersActions').classList.toggle('hidden', hideOrderButtons);

  renderCounts();
  renderUnits();
  renderCenters();
  renderLogs();
  renderRetreats();
  renderAdjustments();
  renderHistory();
  installBoardUnitClickHandlers();
}

function renderCounts() {
  const rows = [['Power','Units','SCs']];
  const porder = ['ah','en','fr','de','it','ru','tu'];
  for (const p of porder) {
    const c = STATE.summary.counts[p];
    rows.push([powerName(p), c.units, c.centers]);
  }
  $('counts').innerHTML = rows.map((r,i) => `<tr>${r.map(x => i ? `<td>${escapeHtml(x)}</td>` : `<th>${escapeHtml(x)}</th>`).join('')}</tr>`).join('');
}

function renderUnits() {
  const groups = {};
  for (const u of STATE.units) {
    (groups[u.power] ||= []).push(u);
  }
  const porder = ['ah','en','fr','de','it','ru','tu'];
  $('units').innerHTML = porder.map(p => {
    const list = groups[p] || [];
    return `<div class="power-${p}"><strong>${escapeHtml(powerName(p))}</strong>${
      list.map(u => {
        const orderText = unitOrderText(u);
        return `<button class="unit unit-click" type="button" data-order-power="${escapeHtml(u.power)}" data-order-unit="${escapeHtml(orderText)}" title="Add ${escapeHtml(orderText)} to ${escapeHtml(powerName(u.power))} orders">
          <span>${escapeHtml(orderText)}</span><small>${escapeHtml(u.id)}</small>
        </button>`;
      }).join('')
    }</div>`;
  }).join('');
}

function renderCenters() {
  const groups = {};
  for (const [sc,p] of Object.entries(STATE.centers)) {
    (groups[p] ||= []).push(sc);
  }
  const porder = ['ah','en','fr','de','it','ru','tu','in'];
  $('centers').innerHTML = porder.map(p => {
    const list = (groups[p] || []).sort();
    if (!list.length) return '';
    return `<p><strong>${escapeHtml(powerName(p))}</strong><br>${list.map(x => `<span class="badge">${escapeHtml(x)}</span>`).join(' ')}</p>`;
  }).join('');
}

function renderLogs() {
  const logs = STATE.logs || [];
  if (!logs.length) {
    $('logs').textContent = 'No resolution logs yet.';
    return;
  }
  $('logs').textContent = logs.slice().reverse().map(l => `# ${l.turn} · ${l.created}\n${l.text}`).join('\n\n');
}

function renderRetreats() {
  const panel = $('retreatPanel');
  const retreats = STATE.pending_retreats || [];
  panel.classList.toggle('hidden', STATE.phase !== 'RETREAT' || !retreats.length);
  if (!retreats.length) {
    $('retreats').innerHTML = '';
    return;
  }
  $('retreats').innerHTML = retreats.map(r => {
    const u = r.unit;
    const options = ['DISBAND', ...(r.options || [])];
    return `<div class="retreat-block">
      <strong>${escapeHtml(powerName(u.power))} ${escapeHtml(u.type)} ${escapeHtml(r.from)}</strong>
      <p class="hint">Dislodged by attack from ${escapeHtml(r.attacker_from)}</p>
      <select data-retreat="${escapeHtml(u.id)}">
        ${options.map(o => `<option value="${escapeHtml(o)}">${escapeHtml(o)}</option>`).join('')}
      </select>
    </div>`;
  }).join('');
}

function renderAdjustments() {
  const panel = $('adjustPanel');
  const pending = STATE.pending_adjustments || {};
  const keys = Object.keys(pending);
  panel.classList.toggle('hidden', STATE.phase !== 'ADJUSTMENT' || !keys.length);
  if (!keys.length) {
    $('adjustments').innerHTML = '';
    return;
  }

  const ownedUnits = {};
  for (const u of STATE.units) (ownedUnits[u.power] ||= []).push(u);

  $('adjustments').innerHTML = keys.map(p => {
    const adj = pending[p];
    if (adj.type === 'build') {
      const rows = [];
      const sitesA = (adj.build_sites && adj.build_sites.A) || adj.sites || [];
      const sitesF = (adj.build_sites && adj.build_sites.F) || adj.sites || [];
      for (let i=0; i<adj.count; i++) {
        rows.push(`<div class="row build-row">
          <select data-build-power="${escapeHtml(p)}" data-build-index="${i}" data-field="type" onchange="refreshBuildLocation(this.closest('.build-row'))">
            <option>A</option><option>F</option>
          </select>
          <select data-build-power="${escapeHtml(p)}" data-build-index="${i}" data-field="loc" data-sites-a="${attrJson(sitesA)}" data-sites-f="${attrJson(sitesF)}">
            ${optionHtml(sitesA)}
          </select>
        </div>`);
      }
      return `<div class="adjust-block"><strong>${escapeHtml(powerName(p))} builds ${adj.count}</strong>${rows.join('')}</div>`;
    }
    const units = ownedUnits[p] || [];
    return `<div class="adjust-block"><strong>${escapeHtml(powerName(p))} disbands ${adj.count}</strong>
      <p class="hint">Select at least ${adj.count}; if fewer are selected, the server applies deterministic fallback.</p>
      ${units.map(u => `<label class="badge"><input type="checkbox" data-disband="${escapeHtml(u.id)}"> ${escapeHtml(unitOrderText(u))}</label>`).join(' ')}
    </div>`;
  }).join('');
}

async function renderHistory() {
  const res = await fetch('/api/history');
  const data = await res.json();
  const items = data.items || [];
  $('history').innerHTML = items.slice().reverse().map(h => `
    <div class="history-row">
      <strong>${escapeHtml(h.label)}</strong> <span class="hint">${escapeHtml(h.created)}</span><br>
      <a href="/history/${encodeURIComponent(h.id)}/board.svg" target="_blank">board</a> ·
      <a href="/history/${encodeURIComponent(h.id)}/orders.md" target="_blank">orders</a> ·
      <a href="/history/${encodeURIComponent(h.id)}/log.md" target="_blank">log</a> ·
      <a href="/history/${encodeURIComponent(h.id)}/state.json" target="_blank">state</a>
    </div>`).join('') || '<p class="hint">No snapshots yet.</p>';
}

function powerAliases(power) {
  const canonical = powerName(power);
  const aliases = {
    ah: ['Austria-Hungary', 'Austria', 'AH'],
    en: ['England', 'Britain', 'Great Britain', 'EN'],
    fr: ['France', 'FR'],
    de: ['Germany', 'DE'],
    it: ['Italy', 'IT'],
    ru: ['Russia', 'RU'],
    tu: ['Turkey', 'Ottoman', 'TU']
  }[power] || [canonical, power];
  return Array.from(new Set([canonical, ...aliases]));
}

function lineMatchesPower(line, power) {
  const trimmed = line.trimStart();
  return powerAliases(power).some(name => {
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`^${escaped}\\s*:`, 'i').test(trimmed);
  });
}

function findPowerLine(lines, power) {
  for (let i = 0; i < lines.length; i++) {
    if (lineMatchesPower(lines[i], power)) return i;
  }
  return -1;
}

function firstOrderLineIndex(lines) {
  const powers = ['ah','en','fr','de','it','ru','tu'];
  for (let i = 0; i < lines.length; i++) {
    if (powers.some(p => lineMatchesPower(lines[i], p))) return i;
  }
  return -1;
}

function textPositionForLine(lines, lineIndex, offsetInLine = 0) {
  let pos = 0;
  for (let i = 0; i < lineIndex; i++) pos += lines[i].length + 1;
  return pos + offsetInLine;
}

function unitJoinerPrefix(text) {
  if (/,\s*$/.test(text)) return /\s$/.test(text) ? '' : ' ';
  if (/\s[CS]\s*$/i.test(text)) return /\s$/.test(text) ? '' : ' ';
  return null;
}

function lineEndsWithOrderJoiner(text) {
  return unitJoinerPrefix(text) !== null;
}

function currentLineContext(textarea) {
  const value = textarea.value.replace(/\r\n/g, '\n');
  const caret = textarea.selectionStart ?? value.length;
  const lineStart = value.lastIndexOf('\n', Math.max(0, caret - 1)) + 1;
  let lineEnd = value.indexOf('\n', caret);
  if (lineEnd < 0) lineEnd = value.length;
  return {
    value,
    caret,
    lineStart,
    lineEnd,
    beforeCaret: value.slice(lineStart, caret),
    afterCaret: value.slice(caret, lineEnd),
  };
}

function insertTextAtCaret(text) {
  const textarea = $('ordersText');
  const value = textarea.value;
  const start = textarea.selectionStart ?? value.length;
  const end = textarea.selectionEnd ?? start;
  textarea.value = value.slice(0, start) + text + value.slice(end);
  const caret = start + text.length;
  textarea.focus();
  textarea.setSelectionRange(caret, caret);
}

function tryAppendUnitAtActiveJoiner(unitText) {
  const textarea = $('ordersText');
  const ctx = currentLineContext(textarea);
  const prefix = unitJoinerPrefix(ctx.beforeCaret);
  if (prefix === null) return false;

  const insertText = prefix + unitText;
  textarea.value = ctx.value.slice(0, ctx.caret) + insertText + ctx.value.slice(ctx.caret);
  const caret = ctx.caret + insertText.length;
  textarea.focus();
  textarea.setSelectionRange(caret, caret);
  return true;
}

function appendUnitToOrderLine(line, unitText) {
  if (!/:/.test(line)) return `${line.trimEnd()}: ${unitText}`;
  if (/:\s*$/.test(line)) return `${line.trimEnd()} ${unitText}`;
  const prefix = unitJoinerPrefix(line);
  if (prefix !== null) return `${line}${prefix}${unitText}`;
  return `${line.trimEnd()}, ${unitText}`;
}

function addUnitToOrders(power, unitText) {
  if (tryAppendUnitAtActiveJoiner(unitText)) return;

  const textarea = $('ordersText');
  const original = textarea.value.replace(/\r\n/g, '\n');
  let lines = original.length ? original.split('\n') : [];
  const prefix = `${powerName(power)}:`;
  let lineIndex = findPowerLine(lines, power);

  if (lineIndex < 0) {
    const newLine = `${prefix} ${unitText}`;
    if (!lines.length || (lines.length === 1 && !lines[0].trim())) {
      const header = STATE && STATE.summary && STATE.summary.turn
        ? STATE.summary.turn.toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
        : '';
      lines = header ? [header, newLine] : [newLine];
      lineIndex = lines.length - 1;
    } else {
      const insertAt = Math.max(firstOrderLineIndex(lines), 0);
      if (firstOrderLineIndex(lines) >= 0) {
        let lastCountryLine = insertAt;
        for (let i = insertAt; i < lines.length; i++) {
          if (['ah','en','fr','de','it','ru','tu'].some(p => lineMatchesPower(lines[i], p))) lastCountryLine = i;
        }
        lines.splice(lastCountryLine + 1, 0, newLine);
        lineIndex = lastCountryLine + 1;
      } else {
        if (lines[lines.length - 1].trim()) lines.push(newLine);
        else lines[lines.length - 1] = newLine;
        lineIndex = lines.length - 1;
      }
    }
    textarea.value = lines.join('\n');
    const caret = textPositionForLine(lines, lineIndex, lines[lineIndex].length);
    textarea.focus();
    textarea.setSelectionRange(caret, caret);
    return;
  }

  let line = lines[lineIndex];
  const duplicatePattern = new RegExp(`(^|[:,]\\s*)${unitText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?=\\s*(?:,|$|[-–]))`, 'i');
  const duplicateMatch = line.match(duplicatePattern);
  if (duplicateMatch) {
    textarea.value = lines.join('\n');
    const startInLine = duplicateMatch.index + duplicateMatch[1].length;
    const start = textPositionForLine(lines, lineIndex, startInLine);
    textarea.focus();
    textarea.setSelectionRange(start, start + unitText.length);
    return;
  }

  line = appendUnitToOrderLine(line, unitText);
  lines[lineIndex] = line;
  textarea.value = lines.join('\n');
  const caret = textPositionForLine(lines, lineIndex, line.length);
  textarea.focus();
  textarea.setSelectionRange(caret, caret);
}

function installBoardUnitClickHandlers() {
  const obj = $('boardObject');
  if (!obj || !STATE || !STATE.units) return;
  const doc = obj.contentDocument;
  if (!doc) return;

  if (!doc.getElementById('diplomacy-click-style')) {
    const style = doc.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.id = 'diplomacy-click-style';
    style.textContent = `
      use.clickable-unit { cursor: pointer; pointer-events: visiblePainted; }
      use.clickable-unit:hover { filter: drop-shadow(0 0 5px rgba(255,255,255,.95)) drop-shadow(0 0 4px rgba(0,0,0,.65)); }
      use.clickable-unit.unit-click-flash { filter: drop-shadow(0 0 7px rgba(255,255,255,1)) drop-shadow(0 0 7px rgba(20,70,110,.9)); }
    `;
    const svg = doc.querySelector('svg');
    (svg || doc.documentElement).appendChild(style);
  }

  const bySvgId = new Map();
  for (const u of STATE.units) bySvgId.set(unitSvgId(u), u);

  doc.querySelectorAll('use.clickable-unit').forEach(el => {
    el.classList.remove('clickable-unit');
    el.onclick = null;
  });

  for (const [svgId, u] of bySvgId.entries()) {
    const el = doc.getElementById(svgId);
    if (!el) continue;
    const cls = el.getAttribute('class') || '';
    if (!/\bunit_[a-z]{2}\b/.test(cls) || /\bunoccupied\b/.test(cls)) continue;
    el.classList.add('clickable-unit');
    el.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      addUnitToOrders(u.power, unitOrderText(u));
      el.classList.add('unit-click-flash');
      setTimeout(() => el.classList.remove('unit-click-flash'), 220);
    };
  }
}

async function validateOrders() {
  const text = $('ordersText').value;
  try {
    const data = await api('/api/orders', {method:'POST', body: JSON.stringify({orders_text: text})});
    $('parseOut').textContent = data.errors.length ? data.errors.join('\n') : data.orders.map(o => `✓ ${o.raw}`).join('\n');
    STATE = data.state;
    render();
  } catch (e) {
    $('parseOut').textContent = e.message;
  }
}

async function resolveOrders() {
  const text = $('ordersText').value;
  try {
    const data = await api('/api/resolve', {method:'POST', body: JSON.stringify({orders_text: text})});
    $('parseOut').textContent = data.log;
    STATE = data.state;
    reloadBoard();
    render();
  } catch (e) {
    $('parseOut').textContent = e.message;
  }
}

async function submitRetreats() {
  const decisions = {};
  document.querySelectorAll('[data-retreat]').forEach(sel => {
    decisions[sel.dataset.retreat] = sel.value;
  });
  try {
    const data = await api('/api/retreats', {method:'POST', body: JSON.stringify({decisions})});
    $('parseOut').textContent = data.log;
    STATE = data.state;
    reloadBoard();
    render();
  } catch (e) {
    $('parseOut').textContent = e.message;
  }
}

async function submitAdjustments() {
  const builds = [];
  const tmp = {};
  document.querySelectorAll('[data-build-power]').forEach(el => {
    const key = `${el.dataset.buildPower}:${el.dataset.buildIndex}`;
    tmp[key] ||= {power: el.dataset.buildPower};
    tmp[key][el.dataset.field] = el.value;
  });
  for (const b of Object.values(tmp)) builds.push(b);

  const disbands = Array.from(document.querySelectorAll('[data-disband]:checked')).map(x => x.dataset.disband);

  try {
    const data = await api('/api/adjustments', {method:'POST', body: JSON.stringify({builds, disbands})});
    $('parseOut').textContent = data.log;
    STATE = data.state;
    reloadBoard();
    render();
  } catch (e) {
    $('parseOut').textContent = e.message;
  }
}

$('units').addEventListener('click', (event) => {
  const button = event.target.closest('[data-order-power][data-order-unit]');
  if (!button) return;
  addUnitToOrders(button.dataset.orderPower, button.dataset.orderUnit);
});

$('boardObject').addEventListener('load', installBoardUnitClickHandlers);
$('btnInsertSupport').addEventListener('click', () => insertTextAtCaret(' S '));
$('btnInsertConvoy').addEventListener('click', () => insertTextAtCaret(' C '));
$('btnParse').addEventListener('click', validateOrders);
$('btnResolve').addEventListener('click', resolveOrders);
$('btnRetreats').addEventListener('click', submitRetreats);
$('btnAdjustments').addEventListener('click', submitAdjustments);
$('btnWriting').addEventListener('click', async () => {
  const data = await api('/api/phase/writing', {method:'POST', body:'{}'});
  STATE = data.state; render();
});
$('btnNew').addEventListener('click', async () => {
  if (!confirm('Start a fresh game and overwrite current state?')) return;
  const data = await api('/api/new-game', {method:'POST', body:'{}'});
  STATE = data.state; reloadBoard(); render();
});
$('ctrlLand').addEventListener('change', async (e) => {
  const data = await api('/api/settings', {method:'POST', body: JSON.stringify({colour_controlled_land: e.target.checked})});
  STATE = data.state; reloadBoard(); render();
});

loadState().then(reloadBoard);
