// SparshaGuard circuit model v0.3, JavaScript port of sg_model.py ("typical" values).
// Sources: see docs/parameter_sources.md
const SG = (() => {
  const EPS0 = 8.854e-12, pF = 1e-12, CM2 = 1e-4, TAU = 2 * Math.PI;
  const c = (re, im = 0) => ({ re, im });
  const add = (a, b) => c(a.re + b.re, a.im + b.im);
  const sub = (a, b) => c(a.re - b.re, a.im - b.im);
  const mul = (a, b) => c(a.re * b.re - a.im * b.im, a.re * b.im + a.im * b.re);
  const div = (a, b) => { const d = b.re * b.re + b.im * b.im; return c((a.re * b.re + a.im * b.im) / d, (a.im * b.re - a.re * b.im) / d); };
  const inv = (a) => div(c(1), a);
  const abs = (a) => Math.hypot(a.re, a.im);
  const Z0 = c(0);
  const yc = (w, C) => c(0, w * C);
  const zc = (w, C) => inv(yc(w, C));
  const plate = (er, area, gap) => EPS0 * er * area / gap;
  const gm = (a, b) => Math.sqrt(a * b);
  const mid = (a, b) => (a + b) / 2;

  // Goyal et al. 2022: dry metal electrode on skin, per cm^2, hyd 0 (dry) .. 1 (hydrated)
  const lerpLog = (a, b, h) => Math.exp(Math.log(a) + (Math.log(b) - Math.log(a)) * h);
  const cpeY = (q, w, a) => { const m = q * Math.pow(w, a); return c(m * Math.cos(a * Math.PI / 2), m * Math.sin(a * Math.PI / 2)); };
  function zSC(f, area, hyd, alpha) {            // stratum corneum: Rsc || CPE(Csc)
    const w = TAU * f;
    const rsc = lerpLog(6.4e6, 3.0e6, hyd) / area;
    const qsc = lerpLog(41e-9, 190e-9, hyd) * area;
    return inv(add(c(1 / rsc), cpeY(qsc, w, alpha)));
  }
  function zMetal(f, area, hyd, beta) {          // stainless-steel contact CPE
    const qc = lerpLog(114e-9, 114e-9 * 420 / 267, hyd) * area;
    return inv(cpeY(qc, TAU * f, beta));
  }
  const HIS = { hyd: 0.5, alpha: 0.9 };

  // from data/summary_stats.json (no-touch drift, % of full scale, p50 and p90)
  const DRIFT = { single: [0.112, 0.119], dual: [0.118, 0.145], dual_shield: [0.113, 0.123] };
  const TRIGGER = 0.3;      // % of full scale; chosen from the event-stream trade-off (fig 9)
  const NOISE = 0.112;      // % of full scale, per sweep point after averaging (ESP32 ADC)

  // Touché grid: 1 kHz + 17.5 kHz * k, k = 0..199
  const TOUCHE = Array.from({ length: 200 }, (_, k) => 1e3 + 17.5e3 * k);
  function logFreqs(n) { const out = []; const a = 3, b = Math.log10(3.5e6); for (let i = 0; i < n; i++) out.push(Math.pow(10, a + (b - a) * i / (n - 1))); return out; }

  function base(st) {
    const env = st.env, d = st.design;
    let cgb = plate(mid(1.5, 2.5), 10 * CM2, 3e-3);
    if (d !== "single") cgb += plate(3.0, 25 * CM2, 2.25e-3);
    if (d === "dual_shield") cgb *= 0.35;
    let cge = (d === "single" ? gm(0.4, 1.5) : gm(0.6, 2.0)) * pF;
    if (env === "car_seat") cge *= 1.65;
    const cgeFree = cge;
    if (st.bench) cge = 10e-9;
    const cbe = { street_shoes: 140, sandals: 170, barefoot_tile: 217.5, car_seat: 225 }[env];
    return {
      Rs: 10e3, L: 10e-3, Ctank: 104.5 * pF,
      elArea: 3, hyd: st.hyd, alpha: 0.9, beta: 0.55, Rbody: 350,
      C_GB: cgb, C_BE: cbe * pF, C_GE: cge, C_GE_free: cgeFree, C_AE: (140 + (env === "car_seat" ? 85 : 0)) * pF,
    };
  }

  function yOuterContact(w, f, design) {
    if (design === "single") return yc(w, plate(2.0, 4 * CM2, 4.5e-3));
    const area = 15;
    return inv(add(zSC(f, area, HIS.hyd, HIS.alpha), zc(w, plate(3.0, area * CM2, 62.5e-6))));
  }

  function branches(f, p, st, withEvent) {
    const w = TAU * f;
    const b = {
      Ysrc: inv(c(p.Rs, w * p.L)), Y_S0: yc(w, p.Ctank),
      Y_SB: inv(add(add(zMetal(f, p.elArea, p.hyd, p.beta), zSC(f, p.elArea, p.hyd, p.alpha)), c(p.Rbody))),
      Y_B0: yc(w, p.C_GB), Y_BE: yc(w, p.C_BE), Y_0E: yc(w, p.C_GE), Y_AE: yc(w, p.C_AE),
      Y_BA: Z0, Y_A0: Z0,
    };
    if (!withEvent) return b;
    const d = st.design;
    if (st.touch === "bystander") {
      b.Y_BA = yc(w, 30.5 * pF); b.Y_A0 = yc(w, p.C_GE_free * 0.055);
    } else if (st.touch === "person") {
      const area = 60;
      const skins = add(zSC(f, area, HIS.hyd, HIS.alpha), zSC(f, area, HIS.hyd, HIS.alpha));
      b.Y_BA = inv(st.bare ? skins : add(skins, zc(w, plate(3.15, area * CM2, st.clothMm * 1e-3))));
      if (st.loc === "wrist") b.Y_A0 = yOuterContact(w, f, d);
      else if (st.loc === "forearm") b.Y_A0 = yc(w, (d !== "single" ? 1.75 : 0.6) * pF);
      else b.Y_A0 = yc(w, p.C_GE_free * 0.11);
    } else if (st.touch === "self") {
      b.Y_B0 = add(b.Y_B0, inv(add(inv(yOuterContact(w, f, d)), c(500))));
    } else if (st.touch === "object") {
      const o = st.object;
      if (o === "railing_hand" || o === "railing_wrist") {
        b.Y_BE = add(b.Y_BE, inv(add(zSC(f, 30, HIS.hyd, HIS.alpha), zMetal(f, 30, HIS.hyd, 0.55))));
        if (o === "railing_wrist") b.Y_0E = add(b.Y_0E, yc(w, d === "single" ? plate(3.0, 2 * CM2, 2.25e-3) : plate(3.0, 6 * CM2, 62.5e-6)));
      } else if (o === "phone") {
        b.Y_BE = add(b.Y_BE, inv(add(zSC(f, 30, HIS.hyd, HIS.alpha), zc(w, 8 * pF))));
      } else if (o === "wood_table") {
        b.Y_0E = add(b.Y_0E, yc(w, 3 * pF)); b.Y_BE = add(b.Y_BE, yc(w, 12.5 * pF));
      } else if (o === "bag") {
        b.Y_BE = add(b.Y_BE, yc(w, 6 * pF));
      }
    }
    return b;
  }

  // 4x4 complex nodal solve, nodes S B A E, reference = watch ground
  function solve(b) {
    const neg = (a) => c(-a.re, -a.im);
    const M = [
      [add(add(b.Ysrc, b.Y_S0), b.Y_SB), neg(b.Y_SB), Z0, Z0],
      [neg(b.Y_SB), add(add(add(b.Y_SB, b.Y_B0), b.Y_BE), b.Y_BA), neg(b.Y_BA), neg(b.Y_BE)],
      [Z0, neg(b.Y_BA), add(add(b.Y_BA, b.Y_AE), b.Y_A0), neg(b.Y_AE)],
      [Z0, neg(b.Y_BE), neg(b.Y_AE), add(add(b.Y_BE, b.Y_AE), b.Y_0E)],
    ];
    const rhs = [b.Ysrc, Z0, Z0, Z0];
    const n = 4;
    for (let k = 0; k < n; k++) {
      let piv = k;
      for (let i = k + 1; i < n; i++) if (abs(M[i][k]) > abs(M[piv][k])) piv = i;
      [M[k], M[piv]] = [M[piv], M[k]]; [rhs[k], rhs[piv]] = [rhs[piv], rhs[k]];
      for (let i = k + 1; i < n; i++) {
        const fct = div(M[i][k], M[k][k]);
        for (let j = k; j < n; j++) M[i][j] = sub(M[i][j], mul(fct, M[k][j]));
        rhs[i] = sub(rhs[i], mul(fct, rhs[k]));
      }
    }
    const x = new Array(n);
    for (let i = n - 1; i >= 0; i--) {
      let s = rhs[i];
      for (let j = i + 1; j < n; j++) s = sub(s, mul(M[i][j], x[j]));
      x[i] = div(s, M[i][i]);
    }
    return x[0];
  }

  function sweepOn(st, F) {
    const p = base(st);
    const vb = [], ve = [];
    for (const f of F) {
      vb.push(solve(branches(f, p, st, false)));
      ve.push(solve(branches(f, p, st, true)));
    }
    return { F, vb, ve };
  }
  const sweep = (st, n) => sweepOn(st, logFreqs(n));

  function score(st) { // % of full scale, RMS amplitude change on the Touché grid
    const { vb, ve } = sweepOn(st, TOUCHE);
    let s = 0;
    for (let i = 0; i < vb.length; i++) s += Math.pow(abs(ve[i]) - abs(vb[i]), 2);
    return 100 * Math.sqrt(s / vb.length);
  }

  function skinOhmsAt(st, f) { return abs(add(zMetal(f, 3, st.hyd, 0.55), zSC(f, 3, st.hyd, 0.9))); }

  return { sweep, score, abs, div, sub, c, DRIFT, TRIGGER, NOISE, skinOhmsAt };
})();
if (typeof module !== "undefined") module.exports = SG;
