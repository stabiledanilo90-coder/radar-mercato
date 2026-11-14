/* Radar Mercato — app web (nessuna libreria esterna) */
'use strict';
const C = { up: '#3FB68B', dn: '#F26B76', acc: '#7C8CFF', vio: '#A78BFA', ora: '#F5A524', mut: '#9DA7B3', line: '#2A3340', txt: '#E8EDF2', bg: '#0E1116', surf2: '#1C232D' };
const $app = document.getElementById('app');
const cache = {};

/* ---------------- utilità ---------------- */
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const nf = (v, d) => v == null ? '—' : new Intl.NumberFormat('it-IT', { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
const prezzo = (v) => v == null ? '—' : nf(v, v >= 1000 ? 0 : v >= 10 ? 2 : v >= 1 ? 3 : 4) + ' $';
const pct = (v, d = 1) => v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + nf(Math.abs(v), d) + '%';
const quando = (iso) => {
  if (!iso) return '';
  const d = new Date(iso), s = (Date.now() - d) / 1000;
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))} min fa`;
  if (s < 86400) return `${Math.round(s / 3600)} ore fa`;
  return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
};
const ora = (iso) => iso ? new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }) : '—';
async function get(path) {
  try {
    const r = await fetch(`data/${path}?v=${Math.floor(Date.now() / 60000)}`);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}
function rng(seed) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

const IC = {
  home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
  news: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  check: '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
  back: '<path d="M15 18l-6-6 6-6"/>', chev: '<path d="M9 18l6-6-6-6"/>',
  up: '<path d="M12 19V5M5 12l7-7 7 7"/>', down: '<path d="M12 5v14M19 12l-7 7-7-7"/>',
  cal: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  doc: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
  whale: '<path d="M3 13c0 4 4 6 9 6s9-3 9-8c0-2 1-3 2-4-2 0-3 1-4 2-1-3-4-4-7-4-5 0-9 3-9 8z"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>', refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
};
const ic = (n, s = 20, c = 'currentColor') => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[n]}</svg>`;

const LIV = { rosso: ['Campanello di discesa', 'down'], arancio: ["Da tenere d'occhio", 'info'], grigio: ['Niente di forte', 'info'], verde: ['Campanello di salita', 'up'] };
const chip = (l) => `<span class="chip ${l}">${ic(LIV[l][1], 14)}${LIV[l][0]}</span>`;
const FONTE = { uff: ['Ufficiale', C.up, 'shield'], ag: ['Agenzia', C.acc, 'doc'], ag_dc: ['Agenzia · da confermare', C.ora, 'doc'], bal: ['Balene', C.acc, 'whale'] };
const TONO = { neg: ['Negativa', C.dn], pos: ['Positiva', C.up], ev: ['Evento', C.acc], unc: ['Impatto incerto', C.ora], neu: ['Neutra', C.mut] };

/* ---------------- navigazione ---------------- */
const NAV = [['#/', 'home', 'Panoramica'], ['#/titoli', 'list', 'Titoli'], ['#/notizie', 'news', 'Notizie e balene'], ['#/occasioni', 'target', 'Occasioni'], ['#/pagella', 'check', 'Pagella']];
function nav(active) {
  document.getElementById('nav-links').innerHTML = NAV.map(([h, i, l]) => `<a class="navl ${active === h ? 'on' : ''}" href="${h}" ${active === h ? 'aria-current="page"' : ''}>${ic(i)}<span>${l}</span></a>`).join('');
  document.getElementById('tabbar').innerHTML = NAV.map(([h, i, l]) => `<a class="${active === h ? 'on' : ''}" href="${h}" ${active === h ? 'aria-current="page"' : ''}>${ic(i, 22)}<span>${l.split(' ')[0]}</span></a>`).join('');
}
async function route() {
  const h = location.hash || '#/';
  const m = h.match(/^#\/t\/([A-Z0-9.-]+)(?:\/(\w+))?/i);
  try {
    if (m) { nav('#/titoli'); await viewTitolo(m[1].toUpperCase(), m[2]); }
    else if (h.startsWith('#/titoli')) { nav('#/titoli'); await viewPanoramica(true); }
    else if (h.startsWith('#/notizie')) { nav('#/notizie'); await viewNotizie(); }
    else if (h.startsWith('#/occasioni')) { nav('#/occasioni'); await viewOccasioni(); }
    else if (h.startsWith('#/pagella')) { nav('#/pagella'); await viewPagella(); }
    else { nav('#/'); await viewPanoramica(false); }
  } catch (e) { console.error(e); $app.innerHTML = `<div class="empty">Qualcosa è andato storto nel caricare la pagina. Riprova tra poco.</div>`; }
  $app.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);

/* ---------------- grafici ---------------- */
function spark(vals, color, w = 220, h = 46) {
  if (!vals || vals.length < 2) return '';
  const mn = Math.min(...vals), mx = Math.max(...vals), d = mx - mn || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1) * w).toFixed(1)},${(h - 3 - (v - mn) / d * (h - 6)).toFixed(1)}`).join(' ');
  return `<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><polygon points="0,${h} ${pts} ${w},${h}" fill="${color}" opacity=".1"/><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`;
}
function defs(u) {
  return `<defs><filter id="g${u}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="gs${u}" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="1.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="dots${u}" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".9" fill="${C.line}"/></pattern>
<linearGradient id="band${u}" x1="0" x2="1"><stop offset="0" stop-color="${C.vio}" stop-opacity=".3"/><stop offset="1" stop-color="${C.vio}" stop-opacity=".08"/></linearGradient>
<radialGradient id="halo${u}" cx=".75" cy=".5" r=".6"><stop offset="0" stop-color="${C.vio}" stop-opacity=".1"/><stop offset="1" stop-color="${C.vio}" stop-opacity="0"/></radialGradient></defs>`;
}
function particelle(points, delay, r, spread = 70) {
  return points.map(([x, y]) => {
    const a = r() * Math.PI * 2, rad = spread * (0.4 + 0.6 * r());
    return `<circle class="pt" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(0.8 + r() * 0.8).toFixed(2)}" fill="#DDD6FE" style="--dx:${(Math.cos(a) * rad).toFixed(0)}px;--dy:${(Math.sin(a) * rad).toFixed(0)}px;--d:${(delay + r() * 0.12).toFixed(3)}s"/>`;
  }).join('');
}
function assi(lo, hi, X0, X1, Y) {
  let g = '';
  for (let k = 0; k <= 4; k++) {
    const v = lo + (hi - lo) * k / 4, y = Y(v);
    g += `<line x1="${X0}" x2="${X1}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${C.line}" opacity=".6"/><text x="${X1 + 8}" y="${(y + 4).toFixed(1)}" fill="${C.mut}" font-size="12" font-family="Inter">${esc(prezzo(v).replace(' $', ''))}</text>`;
  }
  return g;
}
function graficoCandele(o, w = 760, h = 400) {
  const u = Math.random().toString(36).slice(2, 7), r = rng(o.storia.length * 7 + 3);
  const hist = o.storia, fut = o.candele, F = o.fascia, n = hist.length, m = fut.length, last = hist[n - 1][4];
  const vals = hist.flatMap((c) => [c[2], c[3]]).concat(F.p10, F.p90, fut.flatMap((c) => [c[1], c[2]]));
  let lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
  const L = 10, R = 70, T = 16, B = 30, pw = w - L - R, ph = h - T - B, cw = pw / (n + m);
  const X = (i) => L + cw * (i + 0.5), Y = (v) => T + (hi - v) / (hi - lo) * ph, bw = Math.max(cw * 0.6, 1.5);
  const xs = [X(n - 1), ...fut.map((_, i) => X(n + i))];
  const poly = (a, b) => [...xs.map((x, i) => `${x.toFixed(1)},${Y(i ? b[i - 1] : last).toFixed(1)}`), ...xs.slice().reverse().map((x, j) => { const i = xs.length - 1 - j; return `${x.toFixed(1)},${Y(i ? a[i - 1] : last).toFixed(1)}`; })].join(' ');
  let g = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Grafico a candele: storico e candele previste">${defs(u)}<rect width="${w}" height="${h}" fill="url(#dots${u})"/><rect width="${w}" height="${h}" fill="url(#halo${u})"/>`;
  g += assi(lo, hi, L, w - R, Y);
  g += `<polygon class="bandfade" points="${poly(F.p10, F.p90)}" fill="url(#band${u})"/><polygon class="bandfade" points="${poly(F.p25, F.p75)}" fill="url(#band${u})"/>`;
  for (const a of [F.p10, F.p90]) g += `<polyline class="bandfade" points="${xs.map((x, i) => `${x.toFixed(1)},${Y(i ? a[i - 1] : last).toFixed(1)}`).join(' ')}" fill="none" stroke="${C.vio}" stroke-dasharray="2 4" opacity=".7"/>`;
  const xt = X(n - 0.5);
  g += `<line x1="${xt}" x2="${xt}" y1="${T}" y2="${h - B}" stroke="${C.vio}" stroke-opacity=".5"/><text x="${xt - 6}" y="${h - 10}" text-anchor="end" fill="${C.mut}" font-size="12" font-family="Inter">oggi</text><text x="${xt + 6}" y="${h - 10}" fill="${C.vio}" font-size="12" font-family="Inter">${esc(o.label)}</text>`;
  hist.forEach((c, i) => {
    const col = c[4] >= c[1] ? C.up : C.dn, x = X(i), y1 = Math.min(Y(c[1]), Y(c[4])), y2 = Math.max(Y(c[1]), Y(c[4]));
    g += `<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${Y(c[2]).toFixed(1)}" y2="${Y(c[3]).toFixed(1)}" stroke="${col}" opacity=".75"/><rect x="${(x - bw / 2).toFixed(1)}" y="${y1.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(y2 - y1, 1).toFixed(1)}" fill="${col}" opacity=".85"/>`;
  });
  let pts = '', cand = `<g filter="url(#g${u})">`;
  const step = 0.55 / Math.max(m, 1);
  fut.forEach((c, i) => {
    const x = X(n + i), d = 0.15 + i * step, y1 = Math.min(Y(c[0]), Y(c[3])), hh = Math.max(Math.abs(Y(c[0]) - Y(c[3])), 1.5);
    const body = Array.from({ length: 9 }, () => [x + (r() - 0.5) * bw, y1 + r() * hh]);
    const wick = Array.from({ length: 4 }, () => [x, Y(c[1]) + r() * (Y(c[2]) - Y(c[1]))]);
    pts += particelle([...body, ...wick], d, r);
    const dc = (d + 0.38).toFixed(3), upc = c[3] >= c[0];
    cand += `<line class="fc" x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${Y(c[1]).toFixed(1)}" y2="${Y(c[2]).toFixed(1)}" stroke="${C.vio}" style="--d:${dc}s"/><rect class="fc" x="${(x - bw / 2).toFixed(1)}" y="${y1.toFixed(1)}" width="${bw.toFixed(1)}" height="${hh.toFixed(1)}" rx="1" fill="${upc ? C.vio : '#1B1530'}" stroke="#C4B5FD" style="--d:${dc}s"/>`;
  });
  g += `<circle class="pulse" cx="${X(n - 1).toFixed(1)}" cy="${Y(last).toFixed(1)}" r="4" fill="${C.vio}" filter="url(#gs${u})"/>`;
  return g + `<g filter="url(#gs${u})">${pts}</g>${cand}</g></svg>`;
}
function graficoAnno(o, w = 760, h = 400) {
  const u = Math.random().toString(36).slice(2, 7), r = rng(11);
  const st = o.storia.map((x) => x[1]), F = o.fascia, n = st.length, last = st[n - 1];
  const vals = st.concat(F.p10, F.p90); let lo = Math.min(...vals) * 0.95, hi = Math.max(...vals) * 1.04;
  const L = 10, R = 70, T = 16, B = 30, pw = w - L - R, ph = h - T - B, N = n + 52;
  const X = (i) => L + pw * i / (N - 1), Y = (v) => T + (hi - v) / (hi - lo) * ph;
  const xs = [X(n - 1), ...F.p50.map((_, i) => X(n + i))];
  let g = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Scenari a un anno">${defs(u)}<rect width="${w}" height="${h}" fill="url(#dots${u})"/><rect width="${w}" height="${h}" fill="url(#halo${u})"/>` + assi(lo, hi, L, w - R, Y);
  const band = [...xs.map((x, i) => `${x.toFixed(1)},${Y(i ? F.p90[i - 1] : last).toFixed(1)}`), ...xs.slice().reverse().map((x, j) => { const i = xs.length - 1 - j; return `${x.toFixed(1)},${Y(i ? F.p10[i - 1] : last).toFixed(1)}`; })].join(' ');
  g += `<polygon class="bandfade" points="${band}" fill="url(#band${u})"/><polyline points="${st.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ')}" fill="none" stroke="${C.txt}" stroke-width="1.8" opacity=".85"/>`;
  let pts = '';
  [[F.p90, 'ottimista', C.up], [F.p50, 'medio', C.vio], [F.p10, 'pessimista', C.dn]].forEach(([a, lab, col], j) => {
    const seq = [last, ...a];
    for (let k = 0; k < seq.length; k += 2) pts += particelle([[xs[k], Y(seq[k])]], 0.1 + k * 0.012, r, 50);
    g += `<polyline class="draw" pathLength="1" points="${xs.map((x, i) => `${x.toFixed(1)},${Y(seq[i]).toFixed(1)}`).join(' ')}" fill="none" stroke="${col}" stroke-width="2.2" filter="url(#g${u})" style="--d:${(0.35 + j * 0.08).toFixed(2)}s"/>`;
    g += `<text class="fc" x="${w - R - 4}" y="${(Y(a[a.length - 1]) - 8).toFixed(1)}" text-anchor="end" fill="${col}" font-size="13" font-weight="600" font-family="Inter" style="--d:.9s">${lab} ${esc(prezzo(a[a.length - 1]))}</text>`;
  });
  const xt = X(n - 1);
  return g + `<g filter="url(#gs${u})">${pts}</g><line x1="${xt}" x2="${xt}" y1="${T}" y2="${h - B}" stroke="${C.vio}" stroke-opacity=".5"/><circle class="pulse" cx="${xt}" cy="${Y(last)}" r="4" fill="${C.vio}" filter="url(#gs${u})"/><text x="${xt - 6}" y="${h - 10}" text-anchor="end" fill="${C.mut}" font-size="12" font-family="Inter">ultimi 2 anni</text><text x="${xt + 6}" y="${h - 10}" fill="${C.vio}" font-size="12" font-family="Inter">prossimi 12 mesi</text></svg>`;
}

/* ---------------- viste ---------------- */
function primiDati() {
  return `<div class="card empty"><h2>I primi dati sono in arrivo</h2><p class="sub">Il sistema sta facendo la prima analisi: le notizie arrivano in pochi minuti, le previsioni entro un'ora. Ricarica la pagina più tardi.</p></div>`;
}

async function viewPanoramica(soloTitoli) {
  const ov = await get('overview.json');
  if (!ov) { $app.innerHTML = `<h1>${soloTitoli ? 'Titoli' : 'Buongiorno'}</h1><br>` + primiDati(); return; }
  const forti = ov.titoli.filter((t) => ['rosso', 'verde', 'arancio'].includes(t.campanello?.livello)).sort((a, b) => ({ rosso: 0, verde: 1, arancio: 2 }[a.campanello.livello] - { rosso: 0, verde: 1, arancio: 2 }[b.campanello.livello])).slice(0, 4);
  const eventi = ov.titoli.flatMap((t) => (t.eventi || []).map((e) => ({ ...e, nome: t.nome }))).sort((a, b) => a.giorni - b.giorni);
  const saluto = new Date().getHours() < 13 ? 'Buongiorno' : new Date().getHours() < 18 ? 'Buon pomeriggio' : 'Buonasera';
  $app.innerHTML = `<div class="stack">
  <header class="row"><div><h1>${soloTitoli ? 'I tuoi titoli' : saluto}</h1><span class="sub">${new Date().toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })} · aggiornato alle ${ora(ov.aggiornato)}</span></div>
  <button class="btn" style="margin-left:auto" onclick="route()">${ic('refresh', 18)}Aggiorna</button></header>
  ${!soloTitoli && forti.length ? `<section class="alerts" aria-label="Campanelli">${forti.map((t) => {
    const l = t.campanello.livello, col = { rosso: C.dn, verde: C.up, arancio: C.ora }[l];
    return `<a class="alert ${l}" href="#/t/${t.id}"><div class="ic" style="background:${col}22">${ic(l === 'arancio' ? 'info' : 'bell', 22, col)}</div><div style="display:flex;flex-direction:column;gap:4px;min-width:0"><span class="k" style="color:${col}">${LIV[l][0]} · ${esc(t.nome)}</span><span class="t">${esc(t.campanello.principale || 'Notizie da guardare')}</span><span class="sub">${t.campanello.negative} negative · ${t.campanello.positive} positive nelle ultime 48 ore</span></div><span style="margin-left:auto;align-self:center;color:${C.mut}">${ic('chev')}</span></a>`;
  }).join('')}</section>` : ''}
  <section class="grid" aria-label="Titoli">${ov.titoli.map((t) => {
    const col = (t.var24 ?? 0) >= 0 ? C.up : C.dn, l = t.campanello?.livello || 'grigio';
    return `<a class="card tcard" href="#/t/${t.id}" aria-label="Apri ${esc(t.nome)}"><div class="row" style="gap:10px"><div class="logo">${esc(t.id)}</div><div style="display:flex;flex-direction:column"><b style="font-size:15px">${esc(t.nome)}</b><span class="sub" style="font-size:12px">${t.tipo === 'crypto' ? 'Crypto' : 'Azione'}</span></div><span style="margin-left:auto;color:${col};font-weight:600;display:inline-flex;align-items:center;gap:2px">${ic((t.var24 ?? 0) >= 0 ? 'up' : 'down', 14, col)}${pct(t.var24)}</span></div>
    <div class="price">${prezzo(t.prezzo)}</div>${spark(t.spark, col)}
    <div style="display:flex;flex-direction:column;gap:8px">${chip(l)}<span class="sub" style="font-size:13px;line-height:1.4">${esc(t.campanello?.principale || 'Nessuna notizia forte nelle ultime 48 ore')}</span></div></a>`;
  }).join('')}
  ${eventi.length ? `<div class="card" style="background:var(--surf2);border-style:dashed;display:flex;flex-direction:column;gap:10px"><b style="display:flex;align-items:center;gap:8px">${ic('cal', 18, C.acc)}Prossimi eventi</b>${eventi.map((e) => `<div><b style="font-size:14px">${new Date(e.data).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'numeric' })} · ${esc(e.nome)}</b><div class="sub" style="font-size:13px">${esc(e.testo)}</div></div>`).join('')}</div>` : ''}
  </section></div>`;
}

async function viewTitolo(id, scelta) {
  const [d, news, ov, btAll] = await Promise.all([get(`forecast/${id}.json`), get('news.json'), get('overview.json'), get('backtest.json')]);
  const q = ov?.titoli.find((t) => t.id === id) || {};
  const nome = d?.nome || q.nome || id;
  const ord = ['ore', 'giorni', 'settimane', 'anno'].filter((k) => d?.orizzonti?.[k]);
  const att = ord.includes(scelta) ? scelta : (ord.includes('giorni') ? 'giorni' : ord[0]);
  const o = d?.orizzonti?.[att];
  const col = (q.var24 ?? 0) >= 0 ? C.up : C.dn;
  const mieNews = (news?.notizie || []).filter((n) => n.titoli.includes(id)).slice(0, 6);
  const bt = btAll?.titoli?.[id]?.[att] || d?.backtest?.[att];
  const etich = { ore: 'Ore', giorni: 'Giorni', settimane: 'Settimane', anno: '1 anno' };
  let riass = '';
  if (o) {
    const R = o.riassunto, periodo = { ore: 'Nelle prossime 24 ore', giorni: 'Nelle prossime 4 settimane', settimane: 'Nei prossimi 3 mesi', anno: 'Tra 12 mesi' }[att];
    const extra = att === 'anno' ? `Non è una previsione: sono 5.000 anni simulati dalle oscillazioni degli ultimi ${nf(R.anni_usati, 0)} anni. In ${nf(R.prob_perdita, 0)} casi su 100 si finisce in perdita; il calo tipico dal picco durante l'anno è ${pct(R.calo_tipico, 0)}.`
      : `Scenari in salita: ${nf(R.prob_salita, 0)}%. ${R.prob_salita > 40 && R.prob_salita < 60 ? 'Praticamente metà e metà: nessuna direzione chiara.' : ''} ${(d.eventi || []).length ? 'Attenzione: in arrivo i conti del trimestre, il modello non li conosce.' : ''}`;
    riass = `<span class="label">In parole semplici</span><p class="plain">${periodo}, <b style="color:${C.vio}">8 scenari su 10</b> finiscono tra <b>${prezzo(R.p10)}</b> e <b>${prezzo(R.p90)}</b>.</p>
    <div class="trio"><div><span>Pessimista</span><span class="dn">${pct(R.var_p10, 0)}</span></div><div><span>Mediano</span><span>${pct(R.var_p50, 0)}</span></div><div><span>Ottimista</span><span class="up">${pct(R.var_p90, 0)}</span></div></div>
    <span class="sub" style="line-height:1.45">${extra}</span>`;
  }
  const fiducia = (() => {
    if (att === 'anno') return `<span class="label">Quanto fidarsi</span><span style="font-size:14px;line-height:1.45">Lo scenario a 1 anno non si può verificare in tempi brevi: usalo per capire <b>quanto può oscillare</b> il titolo, non dove andrà.</span>`;
    if (!bt || !bt.prove) return `<span class="label">Quanto fidarsi</span><span style="font-size:14px;line-height:1.45">Il test sul passato non è ancora stato fatto per questo orizzonte. Arriva con l'analisi della domenica.</span>`;
    const c = { verde: C.up, arancio: C.ora, grigio: C.mut }[bt.livello];
    return `<span class="label">Quanto fidarsi</span><div class="row" style="gap:8px;align-items:baseline"><span class="num" style="font-size:30px;color:${c}">${nf(bt.dir_ok, 0)}%</span><span class="sub">direzioni giuste su ${bt.prove} prove (± ${nf(bt.margine, 0)})</span></div>
    <div class="meter"><div style="width:${bt.dir_ok}%;background:${c}"></div><i></i></div><span style="font-size:14px;line-height:1.4"><b>${esc(bt.verdetto)}.</b> La linea bianca è il 50%: tirare a indovinare.</span>`;
  })();
  $app.innerHTML = `<div class="stack">
  <header class="dhead"><a class="back" href="#/titoli" aria-label="Torna ai titoli">${ic('back')}</a>
  <div style="display:flex;flex-direction:column;gap:2px"><div class="row" style="gap:10px;flex-wrap:wrap"><h1>${esc(nome)}</h1><span class="sub">${esc(id)}</span>${chip(q.campanello?.livello || 'grigio')}</div><span class="sub">Aggiornato ${quando(q.agg || d?.aggiornato)}</span></div>
  <div style="margin-left:auto;display:flex;flex-direction:column;align-items:flex-end"><span class="num" style="font-size:30px">${prezzo(q.prezzo)}</span><span style="color:${col};font-weight:600;display:inline-flex;align-items:center;gap:4px">${ic((q.var24 ?? 0) >= 0 ? 'up' : 'down', 14, col)}${pct(q.var24)} in 24 ore</span></div></header>
  ${!d ? primiDati() : `<div class="dbody">
   <section class="card chartcard" aria-label="Grafico e scenari"><div class="row" style="flex-wrap:wrap;gap:12px">
    <div class="seg" role="tablist" aria-label="Orizzonte">${ord.map((k) => `<button role="tab" aria-selected="${k === att}" onclick="location.hash='#/t/${id}/${k}'">${etich[k]}</button>`).join('')}</div>
    <div class="legend"><span><i class="sw" style="background:${C.vio}"></i>${att === 'anno' ? 'Scenari' : 'Candele previste'}</span><span><i class="sw" style="width:16px;background:rgba(167,139,250,.35)"></i>8 scenari su 10</span></div></div>
    <div class="chart">${o ? (att === 'anno' ? graficoAnno(o) : graficoCandele(o)) : ''}</div>
    <div class="note">${ic('info', 16)}Più la fascia viola è larga, meno il futuro è prevedibile. Guarda la fascia, non la singola candela.</div>
    ${(d.anomalie || []).length ? `<div class="note" style="color:${C.ora}">${ic('bell', 16, C.ora)}${d.anomalie.map((a) => esc(a.testo)).join(' · ')}</div>` : ''}
   </section>
   <aside class="aside">
    <div class="card" style="display:flex;flex-direction:column;gap:12px">${riass}</div>
    <a class="card" href="#/pagella" style="display:flex;flex-direction:column;gap:10px;color:var(--txt)">${fiducia}</a>
    <div class="card"><span class="label">Notizie · ultimi giorni</span>${mieNews.length ? mieNews.map(nItemBreve).join('') : `<p class="sub">Nessuna notizia dalle fonti verificate negli ultimi giorni.</p>`}</div>
   </aside></div>`}</div>`;
}
function tags(n) {
  const f = FONTE[n.livello] || FONTE.ag, t = TONO[n.tono] || TONO.neu;
  return `<span class="tag" style="color:${f[1]}">${ic(f[2], 12, f[1])}${f[0]}</span><span class="tag" style="color:${t[1]}">${t[0]}</span>`;
}
const nItemBreve = (n) => `<div class="nitem"><div class="row" style="gap:6px;flex-wrap:wrap">${tags(n)}</div><a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titolo)}</a><span class="sub" style="font-size:12px">${esc(n.fonte)} · ${quando(n.quando)}</span></div>`;

let filtroNews = 'tutte';
async function viewNotizie() {
  const [news, ov] = await Promise.all([get('news.json'), get('overview.json')]);
  const nomi = Object.fromEntries((ov?.titoli || []).map((t) => [t.id, t.nome]));
  const all = news?.notizie || [];
  const ok = (n) => filtroNews === 'tutte' || (filtroNews === 'forti' && n.imp >= 3) || (filtroNews === 'uff' && n.livello === 'uff') || (filtroNews === 'ag' && n.livello.startsWith('ag')) || (filtroNews === 'bal' && n.livello === 'bal');
  const lista = all.filter(ok);
  const F = [['tutte', 'Tutte'], ['forti', 'Solo importanti'], ['uff', 'Ufficiali'], ['ag', 'Agenzie'], ['bal', 'Balene']];
  const box = (icn, col, t, d, items) => `<div class="srcbox"><b style="display:flex;align-items:center;gap:8px">${ic(icn, 18, col)}${t}</b><span class="sub" style="font-size:13px;line-height:1.45">${d}</span><div class="pills">${items.map((x) => `<span>${x}</span>`).join('')}</div></div>`;
  $app.innerHTML = `<div class="nlayout"><section class="nlist" aria-label="Notizie">
   <header><h1>Notizie e balene</h1><span class="sub">Solo fonti verificate · aggiornato alle ${ora(news?.aggiornato)}</span></header>
   <div class="filters" role="group" aria-label="Filtra">${F.map(([k, l]) => `<button aria-pressed="${k === filtroNews}" onclick="filtroNews='${k}';viewNotizie()">${l}</button>`).join('')}</div>
   ${!news ? primiDati() : lista.length ? lista.slice(0, 80).map((n) => {
     const t = TONO[n.tono] || TONO.neu;
     return `<article class="card art"><div class="bar" style="background:${t[1]}"></div><div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:8px">
     <div class="row" style="gap:6px;flex-wrap:wrap">${tags(n)}${n.titoli.map((x) => `<a class="tag" style="color:var(--txt)" href="#/t/${x}">${esc(nomi[x] || x)}</a>`).join('')}<span class="sub" style="margin-left:auto;font-size:12px">${quando(n.quando)}</span></div>
     <a class="t" href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titolo)}</a>
     <div class="row" style="gap:10px;flex-wrap:wrap"><span class="sub" style="font-size:13px">${esc(n.fonte)}${n.dettaglio ? ' · ' + esc(n.dettaglio) : ''}</span><span class="sub" style="margin-left:auto;font-size:12px">Importanza</span><span class="imp" aria-label="Importanza ${n.imp} su 3">${[1, 2, 3].map((k) => `<i style="${k <= n.imp ? 'background:' + t[1] : ''}"></i>`).join('')}</span></div></div></article>`;
   }).join('') : `<div class="card empty">Nessuna notizia con questo filtro negli ultimi 7 giorni.</div>`}
  </section>
  <aside class="nsrc card" aria-label="Fonti"><span class="label">Da dove arrivano le notizie</span>
   ${box('shield', C.up, '1 · Fonti ufficiali', "Quello che l'azienda o il progetto dichiara davvero. Valgono più di tutto.", ['SEC: 8-K, 10-Q, 6-K', 'Siti ufficiali aziende', 'Cardano Foundation · IOG', 'Polkadot · Web3 Foundation'])}
   ${box('doc', C.ora, '2 · Grandi agenzie', 'Notizie verificate da giornalisti. Se citano fonti anonime sono segnate "da confermare".', ['Reuters', 'Bloomberg', 'AP', 'Financial Times', 'WSJ', 'CNBC', 'Il Sole 24 Ore'])}
   ${box('whale', C.acc, '3 · Balene', 'Cosa fanno i grandi soldi: chi compra e chi vende davvero.', ['Acquisti e vendite dei manager (Form 4)', 'Quote sopra il 5% (13D/13G)', 'Volumi anomali'])}
   <div class="srcbox" style="background:transparent;border:1px dashed var(--line)"><b style="display:flex;align-items:center;gap:8px">${ic('x', 18, C.dn)}Esclusi</b><span class="sub" style="font-size:13px">Social, forum, influencer, siti anonimi, gruppi Telegram.</span></div>
  </aside></div>`;
}

async function viewOccasioni() {
  const oc = await get('occasioni.json');
  const crit = [['Molte scommesse al ribasso', 'oltre il 20% delle azioni disponibili'], ['Difficile uscirne in fretta', 'più di 5 giorni di scambi per ricomprare'], ['Volumi in crescita', 'oltre 2 volte la media'], ['Conti migliori del prezzo', 'ricavi in crescita, valutazione bassa, cassa solida'], ['Balene in entrata', 'i manager comprano più di quanto vendono']];
  const studio = (c) => `https://claude.ai/new?q=${encodeURIComponent(`Studiamo insieme ${c.nome} (${c.simbolo}). Il mio radar lo segnala come possibile caso stile GameStop: ${c.perche} Verifica i dati su fonti ufficiali (SEC, comunicati), spiegami i rischi e dimmi se ha senso approfondire. Ricorda che non posso perdere capitale.`)}`;
  $app.innerHTML = `<div class="stack"><header><h1>Radar occasioni</h1><span class="sub">Titoli con caratteristiche simili a GameStop nel 2021. Sono idee da studiare, non da comprare.${oc ? ' · aggiornato ' + quando(oc.aggiornato) : ''}</span></header>
  <div class="warn" role="note">${ic('info', 22, C.ora)}<span>Per ogni GameStop ce ne sono molti che non esplodono mai o crollano dopo pochi giorni. <b>Mai più di una piccola parte del capitale, e solo dopo averla studiata insieme.</b></span></div>
  <div class="dbody"><aside class="card aside" style="max-width:340px"><span class="label">Cosa cerca il radar</span>${crit.map(([t, d]) => `<div class="row" style="align-items:flex-start;gap:10px">${ic('check', 16, C.acc)}<div><b style="font-size:14px">${t}</b><div class="sub" style="font-size:13px">${d}</div></div></div>`).join('')}<div class="note">Dati da Yahoo Finance e SEC. Niente segnalazioni dai social. Esclusi i titoli sotto i 150 milioni di valore, troppo facili da manipolare.</div></aside>
  <section style="flex:999 1 560px;min-width:0;display:flex;flex-direction:column;gap:14px">${!oc ? primiDati() : !oc.candidati.length ? `<div class="card empty">Oggi nessun titolo supera almeno 3 segnali su 5. Va bene così: meglio nessuna idea che un'idea debole.</div>` : oc.candidati.map((c) => `
   <article class="card" style="display:flex;flex-direction:column;gap:14px"><div class="row" style="flex-wrap:wrap;gap:10px"><span class="num" style="font-size:20px">${esc(c.nome)}</span><span class="tag">${esc(c.simbolo)}</span>${c.settore ? `<span class="sub">${esc(c.settore)}</span>` : ''}
   <div style="margin-left:auto" class="row"><span class="dots">${[0, 1, 2, 3, 4].map((i) => `<i class="${i < c.punti ? 'on' : ''}"></i>`).join('')}</span><span class="sub">${c.punti}/5 segnali</span></div></div>
   <div class="metrics"><div><span>Prezzo</span><span>${prezzo(c.prezzo)}</span></div><div><span>Scommesse al ribasso</span><span>${c.metriche['scommesse_ribasso_%'] == null ? '—' : nf(c.metriche['scommesse_ribasso_%'], 0) + '%'}</span></div><div><span>Giorni per ricomprare</span><span>${nf(c.metriche.giorni_per_ricomprare, 1)}</span></div><div><span>Volume</span><span>${c.metriche.volume_x == null ? '—' : nf(c.metriche.volume_x, 1) + 'x'}</span></div><div><span>Ultimo mese</span><span>${pct(c.metriche['var_1m_%'], 0)}</span></div></div>
   <span style="font-size:14px;line-height:1.45">${esc(c.perche)}</span>${c.rischi.length ? `<span style="font-size:14px;color:${C.ora}">Rischi: ${esc(c.rischi.join('; '))}.</span>` : ''}
   ${(c.notizie_ufficiali || []).length ? `<div>${c.notizie_ufficiali.map((n) => `<div class="nitem"><a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titolo)}</a><span class="sub" style="font-size:12px">SEC · ${quando(n.quando)}</span></div>`).join('')}</div>` : ''}
   <div class="row" style="flex-wrap:wrap;gap:10px"><a class="btn primary" href="${studio(c)}" target="_blank" rel="noopener">Studiamola insieme</a><a class="btn" href="https://finance.yahoo.com/quote/${encodeURIComponent(c.simbolo)}" target="_blank" rel="noopener">Vedi i dati</a></div></article>`).join('')}
  </section></div></div>`;
}

async function viewPagella() {
  const [p, ov] = await Promise.all([get('pagella.json'), get('overview.json')]);
  const nomi = Object.fromEntries((ov?.titoli || []).map((t) => [t.id, t.nome]));
  const giorni = p?.inizio_prova ? Math.floor((Date.now() - new Date(p.inizio_prova)) / 86400000) + 1 : 0;
  const cella = (x) => {
    if (!x) return '<span class="sub">—</span>';
    const reale = x.verificate ? `<div class="row" style="gap:6px;align-items:baseline"><span class="num" style="font-size:22px;color:${x.dir_ok >= 60 && x.verificate >= 30 ? C.up : x.dir_ok >= 55 ? C.ora : C.mut}">${nf(x.dir_ok, 0)}%</span><span class="sub" style="font-size:12px">su ${x.verificate} reali</span></div><div class="meter" style="height:8px"><div style="height:8px;width:${x.dir_ok}%;background:${x.dir_ok >= 55 ? C.ora : C.mut}"></div><i></i></div>` : `<span class="sub" style="font-size:13px">In attesa delle prime scadenze</span>`;
    const b = x.backtest ? `<div class="sub" style="font-size:12px;margin-top:6px">Test sul passato: ${nf(x.backtest.dir_ok, 0)}% su ${x.backtest.prove} · ${esc(x.backtest.verdetto)}</div>` : '';
    return `<div style="display:flex;flex-direction:column;gap:6px">${reale}${b}</div>`;
  };
  $app.innerHTML = `<div class="stack"><header><h1>Quanto ci ha preso davvero</h1><span class="sub">Ogni previsione viene salvata e confrontata con il prezzo reale alla scadenza. Nessun soldo investito.</span></header>
  ${!p ? primiDati() : `<section class="grid"><div class="card"><span class="sub">Periodo di prova</span><div class="num" style="font-size:26px">Giorno ${giorni} di 30</div><div class="meter" style="margin-top:10px"><div style="width:${Math.min(100, giorni / 30 * 100)}%;background:${C.acc}"></div></div></div>
   <div class="card"><span class="sub">Previsioni verificate</span><div class="num" style="font-size:26px">${p.verificate_totali}</div></div>
   <div class="card"><span class="sub">La realtà è caduta nella fascia viola</span><div class="num" style="font-size:26px">${p.in_banda_totale == null ? '—' : nf(p.in_banda_totale, 0) + '%'}</div><span class="sub" style="font-size:13px">dovrebbe essere vicino all'80%</span></div></section>
   <section class="card" style="overflow-x:auto"><table class="ptable"><thead><tr><th>Titolo</th><th>Ore</th><th>Giorni</th><th>Settimane</th></tr></thead><tbody>
   ${Object.entries(p.titoli).map(([t, o]) => `<tr><td><b>${esc(nomi[t] || t)}</b></td><td>${cella(o.ore)}</td><td>${cella(o.giorni)}</td><td>${cella(o.settimane)}</td></tr>`).join('')}</tbody></table></section>
   <div class="note" style="font-size:14px;line-height:1.5">${ic('info', 20, C.acc)}<span>La linea bianca è il 50%: tirare a indovinare. Un titolo diventa <b style="color:${C.up}">affidabile</b> solo sopra il 60% con almeno 30 previsioni reali. Sotto il 55% le sue previsioni vanno ignorate.</span></div>`}</div>`;
}

route();
setInterval(() => { if (!document.hidden && !location.hash.startsWith('#/t/')) route(); }, 5 * 60 * 1000);
