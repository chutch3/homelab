/* wall.js — FIBER Throne Room client */

// ---- layout engine ----
function layoutWall() {
  const wall = document.getElementById('wall');
  if (!wall) return;
  const tiles = wall.querySelectorAll('.tile');
  const n = tiles.length;
  if (!n) return;
  const W = wall.clientWidth, H = wall.clientHeight, g = 12;
  let best = {c: 1, r: n, s: -1};
  for (let c = 1; c <= n; c++) {
    const r = Math.ceil(n / c), tw = (W - g * (c - 1)) / c, th = (H - g * (r - 1)) / r;
    const ar = tw / th, pen = (ar > 2.6 || ar < 0.5) ? 0.5 : 1, s = Math.min(tw, th) * pen;
    if (s > best.s) best = {c, r, s};
  }
  wall.style.gridTemplateColumns = `repeat(${best.c},minmax(0,1fr))`;
  wall.style.gridTemplateRows = `repeat(${best.r},minmax(0,1fr))`;
}

window.addEventListener('resize', layoutWall);
document.addEventListener('DOMContentLoaded', layoutWall);

// ---- SSE live updates ----
function startSSE() {
  const es = new EventSource('events');
  es.onmessage = function(e) {
    try {
      const msg = JSON.parse(e.data);
      if (msg.type === 'tile' && msg.service) {
        const el = document.getElementById('tile-' + msg.service);
        if (el) updateTile(el, msg.html);
      } else if (msg.type === 'summary') {
        const summary = document.getElementById('summary');
        if (summary) summary.innerHTML = msg.html;
      }
    } catch (err) {
      console.warn('SSE parse error', err);
    }
  };
  es.onerror = function() {
    // Reconnect after 3s on error
    es.close();
    setTimeout(startSSE, 3000);
  };
}

// Apply a fresh tile render. A straining tile is re-pushed every ~2s; replacing the
// whole node restarts its CSS animations (the tile's rise-in flash and the strainbar's
// sweep), which reads as flashing + a resetting progress bar. So when the status class
// is unchanged, sync only the live text in place and leave the node — and its running
// animations — intact. Fall back to a full swap only on an actual status transition.
function updateTile(el, html) {
  const tmp = document.createElement('template');
  tmp.innerHTML = html.trim();
  const fresh = tmp.content.firstElementChild;
  if (!fresh) return;
  if (el.className === fresh.className) {
    const oldLabel = el.querySelector('[data-strain]');
    const newLabel = fresh.querySelector('[data-strain]');
    if (oldLabel && newLabel) oldLabel.textContent = newLabel.textContent;
    const oldFoot = el.querySelectorAll('.foot span');
    const newFoot = fresh.querySelectorAll('.foot span');
    newFoot.forEach((n, i) => { if (oldFoot[i]) oldFoot[i].textContent = n.textContent; });
  } else {
    el.replaceWith(fresh);
    layoutWall();
  }
}

document.addEventListener('DOMContentLoaded', startSSE);

// ---- drawer helpers ----
function openDrawer(service, engine, status, badge) {
  const css = {
    clean: '--clean', straining: '--strain', pinched: '--pinched',
    constipated: '--constipated', clogged: '--clogged', misconfigured: '--misconfig'
  };
  const nm = document.getElementById('d_nm');
  const eng = document.getElementById('d_eng');
  const b = document.getElementById('d_badge');
  if (nm) nm.textContent = service;
  if (eng) eng.textContent = engine;
  if (b) {
    b.className = 'dbadge';
    const cssVar = css[status] || '--ink';
    b.style.color = `var(${cssVar})`;
    b.style.borderColor = `var(${cssVar})`;
    b.textContent = badge;
  }
  document.getElementById('drawer').classList.add('on');
  document.getElementById('scrim').classList.add('on');
}

function closeD() {
  document.getElementById('drawer').classList.remove('on');
  document.getElementById('scrim').classList.remove('on');
}

// ---- modal ----
let _okCallback = null;
function ask(title, msg, ok, danger) {
  document.getElementById('m_title').textContent = title;
  document.getElementById('m_msg').innerHTML = msg;
  const btn = document.getElementById('m_ok');
  btn.className = 'btn' + (danger ? ' danger' : '');
  btn.textContent = 'Confirm';
  _okCallback = ok;
  document.getElementById('modal').classList.add('on');
}
function closeModal() {
  document.getElementById('modal').classList.remove('on');
  _okCallback = null;
}
document.addEventListener('DOMContentLoaded', function() {
  const okBtn = document.getElementById('m_ok');
  if (okBtn) okBtn.onclick = function() { if (_okCallback) _okCallback(); closeModal(); };
});

function confirmFlushAll(e) {
  if (e) e.preventDefault();
  const tiles = document.querySelectorAll('#wall .tile');
  const n = tiles.length;
  ask('Courtesy Flush all',
    `Dump all <b>${n}</b> healthy stalls? <span class="warn">Runs a few at a time (concurrency cap).</span>`,
    function() {
      htmx.ajax('POST', 'flush-all', {target: '#summary', swap: 'innerHTML'});
      toast('Queued ' + n + ' flushes');
    });
  return false;
}

// ---- add-DB helper ----
function labelBlock(service) {
  return `deploy:\n  labels:\n    - "fiber.enable=true"\n    - "fiber.engine=postgres"\n    - "fiber.dbname=\${DB_NAME}"\n    - "fiber.user=\${DB_USER}"\n    - "fiber.secret=${service || '<swarm-secret>'}_db_password"\n    - "fiber.schedule=0 3 * * *"\n    - "fiber.app=<app-service>"`;
}

function openAdd() {
  ask('Add a database',
    `Add to the DB <b>service</b>'s <b>deploy.labels</b>, redeploy, then <span class="warn">grant the named secret to the Fiber stack.</span><div class="codeblock" style="margin-top:8px">${labelBlock(null)}</div>`,
    function() {
      if (navigator.clipboard) navigator.clipboard.writeText(labelBlock(null));
      toast('Labels copied');
    });
  const btn = document.getElementById('m_ok');
  if (btn) btn.textContent = 'Copy labels';
}

// ---- clipboard copy ----
function copy(el) {
  const blk = el.closest('.sub').nextElementSibling.textContent;
  if (navigator.clipboard) navigator.clipboard.writeText(blk);
  el.textContent = 'copied ✓';
  setTimeout(() => el.textContent = 'copy ▣', 1200);
}

// ---- toast ----
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('on');
  setTimeout(() => t.classList.remove('on'), 1700);
}

// ---- keyboard ----
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') { closeD(); closeModal(); }
  if (e.key === 'Enter' || e.key === ' ') {
    const el = e.target;
    if (el && el.classList && el.classList.contains('tile')) {
      e.preventDefault();
      htmx.trigger(el, 'click');
    }
  }
});

// ---- reduce-effects toggle ----
document.addEventListener('DOMContentLoaded', function() {
  const calm = document.getElementById('calm');
  if (calm) {
    calm.addEventListener('change', function() {
      document.body.classList.toggle('calm', this.checked);
    });
  }
});
