(function (root) {
  const DAY = 86400000, YEAR = 365.25 * DAY;
  const MON = {jan:0,feb:1,mar:2,apr:3,may:4,jun:5,jul:6,aug:7,sep:8,oct:9,nov:10,dec:11};

  function parseDate(s) {
    if (s == null) return NaN;
    s = String(s).trim().replace(/^"|"$/g, '');
    let m;
    if ((m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/))) return Date.UTC(+m[1], +m[2] - 1, +m[3]);
    if ((m = s.match(/^(\d{1,2})[-\/. ](\d{1,2})[-\/. ](\d{4})$/))) return Date.UTC(+m[3], +m[2] - 1, +m[1]);
    if ((m = s.match(/^(\d{1,2})[-\/ ]([A-Za-z]{3,9})[-\/ ,]+(\d{4})$/))) { const mo = MON[m[2].slice(0, 3).toLowerCase()]; if (mo != null) return Date.UTC(+m[3], mo, +m[1]); }
    if ((m = s.match(/^([A-Za-z]{3,9}) (\d{1,2}),? (\d{4})$/))) { const mo = MON[m[1].slice(0, 3).toLowerCase()]; if (mo != null) return Date.UTC(+m[3], mo, +m[2]); }
    return NaN;
  }
  const toNum = s => { const v = parseFloat(String(s).replace(/[",\s]/g, '')); return isFinite(v) ? v : NaN; };

  function finish(points) {
    const byT = new Map();
    for (const p of points) if (isFinite(p.t) && isFinite(p.nav) && p.nav > 0) byT.set(p.t, p.nav);
    return [...byT].sort((a, b) => a[0] - b[0]).map(([t, nav]) => ({t, nav}));
  }

  // Returns [{code, name, source, points:[{t,nav}]}]
  function parseFile(text, fileName) {
    text = text.replace(/^﻿/, '');
    const trimmed = text.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      const j = JSON.parse(trimmed);
      const arr = Array.isArray(j) ? j : [j];
      return arr.filter(o => o && Array.isArray(o.data)).map(o => ({
        code: String(o.meta?.scheme_code ?? fileName), name: o.meta?.scheme_name || fileName,
        source: 'mfapi JSON', points: finish(o.data.map(d => ({t: parseDate(d.date), nav: toNum(d.nav)})))
      })).filter(s => s.points.length > 1);
    }
    const lines = text.split(/\r?\n/);
    // AMFI semicolon format
    const hIdx = lines.findIndex(l => l.includes(';') && /scheme code/i.test(l) && /net asset value/i.test(l));
    if (hIdx >= 0) {
      const h = lines[hIdx].split(';').map(x => x.trim().toLowerCase());
      const ci = h.findIndex(x => x.startsWith('scheme code')), ni = h.findIndex(x => x.startsWith('scheme name')),
            vi = h.findIndex(x => x.startsWith('net asset value')), di = h.findIndex(x => x === 'date' || x.endsWith('date'));
      const map = new Map();
      for (let k = hIdx + 1; k < lines.length; k++) {
        const f = lines[k].split(';'); if (f.length < h.length - 1 || !/^\d+$/.test((f[ci] || '').trim())) continue;
        const code = f[ci].trim(); let s = map.get(code);
        if (!s) { s = {code, name: (f[ni] || code).trim(), source: 'AMFI NAV file', raw: []}; map.set(code, s); }
        s.raw.push({t: parseDate(f[di]), nav: toNum(f[vi])});
      }
      return [...map.values()].map(s => ({code: s.code, name: s.name, source: s.source, points: finish(s.raw)})).filter(s => s.points.length > 1);
    }
    // generic CSV/TSV with a date column and a nav/close/value column
    const delim = (lines[0].match(/\t/g) || []).length > (lines[0].match(/,/g) || []).length ? '\t' : ',';
    const split = l => { const out = []; let cur = '', q = false;
      for (const ch of l) { if (ch === '"') q = !q; else if (ch === delim && !q) { out.push(cur.trim()); cur = ''; } else cur += ch; }
      out.push(cur.trim()); return out; };
    const head = split(lines[0]).map(x => x.toLowerCase());
    const di = head.findIndex(x => x.includes('date'));
    let vi = head.findIndex(x => /\bnav\b|net asset value/.test(x));
    if (vi < 0) vi = head.findIndex(x => x === 'close' || x.includes('close'));
    if (vi < 0) vi = head.findIndex(x => /total\s*returns?\s*index|\btri\b/.test(x));
    if (vi < 0) vi = head.findIndex(x => x.includes('value') || x.includes('price'));
    if (di < 0 || vi < 0) throw new Error('Could not find a date column and a NAV/close column in ' + fileName);
    const pts = lines.slice(1).filter(l => l.trim()).map(l => { const f = split(l); return {t: parseDate(f[di]), nav: toNum(f[vi])}; });
    // name: an "Index Name"/"Scheme Name" column if present, else the file name without its date range,
    // so yearly downloads of the same index merge into one series
    const nmI = head.findIndex(x => x === 'index name' || x === 'scheme name' || x === 'name');
    const fromCol = nmI >= 0 ? (split(lines[1] || '')[nmI] || '').trim() : '';
    const base = fileName.replace(/\.(csv|tsv|txt)$/i, '')
      .replace(/_Historical_[A-Z_]+_?\d{8}to\d{8}$/i, '').replace(/[_-]\d{8}[_-]\d{8}$/, '').replace(/[_-]+$/, '');
    const name = fromCol || base;
    const out = finish(pts);
    return out.length > 1 ? [{code: name, name, source: 'CSV file', points: out}] : [];
  }

  // ---------- series helpers
  function idxAtOrBefore(pts, t) { let lo = 0, hi = pts.length - 1, r = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (pts[m].t <= t) { r = m; lo = m + 1; } else hi = m - 1; } return r; }
  function navAt(pts, t) { const i = idxAtOrBefore(pts, t); return i < 0 ? null : pts[i].nav; }
  function shiftYears(t, y) { const d = new Date(t); const r = Date.UTC(d.getUTCFullYear() + Math.trunc(y), d.getUTCMonth() + Math.round((y % 1) * 12), d.getUTCDate()); return r; }
  function shiftMonths(t, mo) { const d = new Date(t); return Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + mo, d.getUTCDate()); }
  const cagr = (a, b, years) => Math.pow(b / a, 1 / years) - 1;

  // window: {start, end} timestamps. slice inclusive
  function slice(pts, start, end) { return pts.filter(p => p.t >= start && p.t <= end); }

  const PERIODS = [['1M', 0, 1], ['3M', 0, 3], ['6M', 0, 6], ['1Y', 1, 0], ['3Y', 3, 0], ['5Y', 5, 0], ['7Y', 7, 0], ['10Y', 10, 0]];
  function trailing(pts, asOf) {
    const end = asOf ?? pts[pts.length - 1].t, endNav = navAt(pts, end), out = {};
    for (const [k, y, mo] of PERIODS) {
      const st = y ? shiftYears(end, -y) : shiftMonths(end, -mo);
      if (st < pts[0].t) { out[k] = null; continue; }
      const a = navAt(pts, st);
      out[k] = y >= 1 ? cagr(a, endNav, y) : endNav / a - 1;
    }
    const yrs = (end - pts[0].t) / YEAR;
    out.SI = yrs >= 1 ? cagr(pts[0].nav, endNav, yrs) : endNav / pts[0].nav - 1;
    out.siYears = yrs;
    return out;
  }

  function periodicReturns(pts) { const r = []; for (let i = 1; i < pts.length; i++) r.push({t: pts[i].t, r: pts[i].nav / pts[i - 1].nav - 1}); return r; }
  const mean = a => a.reduce((s, x) => s + x, 0) / a.length;
  const stdev = a => { const m = mean(a); return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1)); };

  // risk over a window; rf annual decimal
  // freq 'monthly' (factsheet convention) uses month-end NAVs for volatility/Sharpe/Sortino; drawdown always uses every NAV
  function risk(ptsAll, start, end, rf, freq = 'daily') {
    const pts = slice(ptsAll, start, end);
    if (pts.length < 20) return null;
    const years = (pts[pts.length - 1].t - pts[0].t) / YEAR;
    const basis = freq === 'monthly' ? [pts[0], ...monthEnd(pts).filter(p => p.t > pts[0].t)] : pts;
    if (basis.length < 13 && freq === 'monthly') return null;
    const rets = periodicReturns(basis).map(x => x.r);
    const ppy = freq === 'monthly' ? 12 : rets.length / years;   // monthly: 12 by convention; daily: observed count (≈ 245-250)
    const vol = stdev(rets) * Math.sqrt(ppy);
    const annRet = cagr(pts[0].nav, pts[pts.length - 1].nav, years);
    const rfp = Math.pow(1 + rf, 1 / ppy) - 1;
    const dd = Math.sqrt(rets.reduce((s, x) => s + Math.min(0, x - rfp) ** 2, 0) / rets.length) * Math.sqrt(ppy);
    // drawdown
    let peak = pts[0].nav, peakT = pts[0].t, mdd = 0, troughT = pts[0].t, mddPeakT = pts[0].t;
    for (const p of pts) { if (p.nav > peak) { peak = p.nav; peakT = p.t; } const d = p.nav / peak - 1; if (d < mdd) { mdd = d; troughT = p.t; mddPeakT = peakT; } }
    let recoverT = null; const pk = navAt(pts, mddPeakT);
    for (const p of pts) if (p.t > troughT && p.nav >= pk) { recoverT = p.t; break; }
    return {years, annRet, vol, sharpe: (annRet - rf) / vol, sortino: dd > 0 ? (annRet - rf) / dd : null, maxDD: mdd, ddPeakT: mddPeakT, ddTroughT: troughT, ddRecoverT: recoverT, obs: pts.length, ppy};
  }

  function drawdownSeries(pts) { let peak = -Infinity; return pts.map(p => { peak = Math.max(peak, p.nav); return {t: p.t, v: p.nav / peak - 1}; }); }

  // rolling N-year CAGR at every observation; thinned to ~weekly for charting via `step`
  function rolling(pts, years, step = 1) {
    const out = []; const first = pts[0].t;
    for (let i = 0; i < pts.length; i += step) {
      const p = pts[i], st = shiftYears(p.t, -years); if (st < first) continue;
      const a = navAt(pts, st); out.push({t: p.t, v: years >= 1 ? cagr(a, p.nav, years) : p.nav / a - 1});
    }
    return out;
  }
  function quantile(sorted, q) { if (!sorted.length) return null; const pos = (sorted.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos); return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo); }
  function rollingStats(series, threshold) {
    if (!series.length) return null;
    const v = series.map(x => x.v).sort((a, b) => a - b);
    return {n: v.length, min: v[0], p25: quantile(v, .25), median: quantile(v, .5), p75: quantile(v, .75), max: v[v.length - 1], mean: mean(v),
            pctNeg: v.filter(x => x < 0).length / v.length, pctAbove: v.filter(x => x >= threshold).length / v.length};
  }

  function calendarYears(pts) {
    const out = []; const y0 = new Date(pts[0].t).getUTCFullYear(), y1 = new Date(pts[pts.length - 1].t).getUTCFullYear();
    for (let y = y0; y <= y1; y++) {
      const endI = idxAtOrBefore(pts, Date.UTC(y, 11, 31)); const startI = idxAtOrBefore(pts, Date.UTC(y - 1, 11, 31));
      const partial = startI < 0 || y === y1;
      const a = startI < 0 ? pts[0].nav : pts[startI].nav; const b = pts[endI].nav;
      out.push({year: y, r: b / a - 1, partial});
    }
    return out;
  }

  // align two series on common dates
  function align(a, b, start, end) {
    const mb = new Map(b.filter(p => p.t >= start && p.t <= end).map(p => [p.t, p.nav]));
    return a.filter(p => p.t >= start && p.t <= end && mb.has(p.t)).map(p => ({t: p.t, a: p.nav, b: mb.get(p.t)}));
  }
  function monthEnd(pts) { const m = new Map(); for (const p of pts) { const d = new Date(p.t); m.set(d.getUTCFullYear() * 12 + d.getUTCMonth(), p); } return [...m.values()]; }
  function correlation(x, y) { const mx = mean(x), my = mean(y); let sxy = 0, sxx = 0, syy = 0; for (let i = 0; i < x.length; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; } return sxy / Math.sqrt(sxx * syy); }

  // fund vs benchmark on common dates; daily for corr/TE, monthly for beta/capture
  function versus(fund, bench, start, end, rf) {
    const al = align(fund, bench, start, end); if (al.length < 30) return null;
    const ra = [], rb = []; for (let i = 1; i < al.length; i++) { ra.push(al[i].a / al[i - 1].a - 1); rb.push(al[i].b / al[i - 1].b - 1); }
    const years = (al[al.length - 1].t - al[0].t) / YEAR, ppy = ra.length / years;
    const corr = correlation(ra, rb);
    const diff = ra.map((x, i) => x - rb[i]); const te = stdev(diff) * Math.sqrt(ppy);
    const fa = cagr(al[0].a, al[al.length - 1].a, years), fb = cagr(al[0].b, al[al.length - 1].b, years);
    const me = monthEnd(al.map(p => ({t: p.t, nav: 0, a: p.a, b: p.b})));
    const ma = [], mb = []; for (let i = 1; i < me.length; i++) { ma.push(me[i].a / me[i - 1].a - 1); mb.push(me[i].b / me[i - 1].b - 1); }
    let beta = null, alpha = null, up = null, down = null;
    if (ma.length >= 12) {
      const mbm = mean(mb), mam = mean(ma); let cov = 0, vb = 0; for (let i = 0; i < ma.length; i++) { cov += (ma[i] - mam) * (mb[i] - mbm); vb += (mb[i] - mbm) ** 2; }
      beta = cov / vb; alpha = fa - (rf + beta * (fb - rf));
      const geo = arr => arr.length ? Math.pow(arr.reduce((s, x) => s * (1 + x), 1), 1 / arr.length) - 1 : null;
      const upI = mb.map((x, i) => x > 0 ? i : -1).filter(i => i >= 0), dnI = mb.map((x, i) => x < 0 ? i : -1).filter(i => i >= 0);
      if (upI.length) up = geo(upI.map(i => ma[i])) / geo(upI.map(i => mb[i]));
      if (dnI.length) down = geo(dnI.map(i => ma[i])) / geo(dnI.map(i => mb[i]));
    }
    return {years, corr, te, ir: te > 0 ? (fa - fb) / te : null, excess: fa - fb, beta, alpha, upCapture: up, downCapture: down, months: ma.length};
  }

  // ---------- calculators (all rates annual decimals; monthly rate is the effective equivalent)
  const mrate = r => Math.pow(1 + r, 1 / 12) - 1;
  // SIP at start of each month, step-up applied each 12 months
  function sip({monthly, rate, years, stepUp = 0, lumpsum = 0}) {
    const i = mrate(rate), n = Math.round(years * 12); let val = lumpsum, inv = lumpsum, amt = monthly; const rows = [];
    for (let m = 0; m < n; m++) {
      if (m > 0 && m % 12 === 0) amt *= (1 + stepUp);
      val += amt; inv += amt; val *= (1 + i);
      if ((m + 1) % 12 === 0 || m === n - 1) rows.push({year: (m + 1) / 12, invested: inv, value: val, sipAmount: amt});
    }
    return {invested: inv, value: val, gain: val - inv, rows};
  }
  // future value of ₹1 starting monthly SIP with step-up (start-of-month)
  const sipFactor = (rate, years, stepUp) => sip({monthly: 1, rate, years, stepUp}).value;
  function goal({target, inflation, years, rate, existing = 0, stepUp = 0}) {
    const fv = target * Math.pow(1 + inflation, years); const existingFV = existing * Math.pow(1 + rate, years);
    const gap = Math.max(0, fv - existingFV);
    return {futureCost: fv, existingFV, gap, monthlySIP: gap / sipFactor(rate, years, stepUp), lumpsumToday: gap / Math.pow(1 + rate, years)};
  }
  function retirement({monthlyExpense, age, retireAge, lifeAge, inflation, preRate, postRate, existing = 0, stepUp = 0}) {
    const yrsTo = retireAge - age, yrsIn = lifeAge - retireAge;
    const firstExpense = monthlyExpense * Math.pow(1 + inflation, yrsTo);
    const ip = mrate(postRate); let corpus = 0;
    for (let m = 0; m < yrsIn * 12; m++) corpus += firstExpense * Math.pow(1 + inflation, Math.floor(m / 12)) / Math.pow(1 + ip, m);
    const existingFV = existing * Math.pow(1 + preRate, yrsTo); const gap = Math.max(0, corpus - existingFV);
    return {yearsToRetire: yrsTo, yearsInRetirement: yrsIn, firstMonthlyExpense: firstExpense, corpus, existingFV, gap, monthlySIP: yrsTo > 0 ? gap / sipFactor(preRate, yrsTo, stepUp) : null};
  }
  // SWP: withdrawal at start of month, then growth
  function swp({corpus, withdrawal, rate, years, increase = 0}) {
    const i = mrate(rate); let bal = corpus, w = withdrawal, total = 0, depletedMonth = null; const rows = [{month: 0, balance: corpus}];
    for (let m = 0; m < years * 12; m++) {
      if (m > 0 && m % 12 === 0) w *= (1 + increase);
      const take = Math.min(w, bal); bal -= take; total += take; bal *= (1 + i);
      if (bal <= 0.5 && depletedMonth == null) { depletedMonth = m + 1; bal = 0; }
      rows.push({month: m + 1, balance: bal});
    }
    return {endBalance: bal, totalWithdrawn: total, depletedMonth, rows};
  }
  // XIRR: flows [{t, amount}] (investments negative)
  function xirr(flows) {
    if (flows.length < 2 || !flows.some(f => f.amount < 0) || !flows.some(f => f.amount > 0)) return null;
    const t0 = Math.min(...flows.map(f => f.t));
    const f = r => flows.reduce((s, x) => s + x.amount / Math.pow(1 + r, (x.t - t0) / (365 * DAY)), 0);
    let lo = -0.9999, hi = 10, flo = f(lo), fhi = f(hi);
    if (flo * fhi > 0) return null;
    for (let k = 0; k < 200; k++) { const mid = (lo + hi) / 2, fm = f(mid); if (Math.abs(fm) < 1e-9) return mid; if (flo * fm < 0) { hi = mid; fhi = fm; } else { lo = mid; flo = fm; } }
    return (lo + hi) / 2;
  }
  // Equity-oriented MF capital gains (rates editable)
  function equityTax({buyT, sellT, buyValue, sellValue, stcgRate, ltcgRate, exemption, cess}) {
    const gain = sellValue - buyValue; const months = (new Date(sellT).getUTCFullYear() - new Date(buyT).getUTCFullYear()) * 12 + new Date(sellT).getUTCMonth() - new Date(buyT).getUTCMonth() - (new Date(sellT).getUTCDate() <= new Date(buyT).getUTCDate() ? 1 : 0);
    const longTerm = months >= 12;
    let taxable = gain, rate = longTerm ? ltcgRate : stcgRate;
    if (gain <= 0) return {gain, longTerm, taxable: 0, tax: 0, rate, months};
    if (longTerm) taxable = Math.max(0, gain - exemption);
    const tax = taxable * rate * (1 + cess);
    return {gain, longTerm, taxable, tax, rate, months, net: sellValue - tax};
  }

  const api = {parseDate, parseFile, navAt, trailing, risk, drawdownSeries, rolling, rollingStats, calendarYears, versus, sip, goal, retirement, swp, xirr, equityTax, shiftYears, shiftMonths, YEAR, DAY, monthEnd};
  if (typeof module !== 'undefined') module.exports = api; else root.FW = api;
})(typeof window !== 'undefined' ? window : globalThis);
