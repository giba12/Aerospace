// Browser port of the simulator's maths: Euler truth, seeded noisy sensor, 2-state Kalman filter.
// It mirrors src/dynamics.cpp, src/sensor.cpp and src/kalman.cpp. The random numbers differ from the
// C++ program (std::normal_distribution is implementation-defined), so live runs give similar,
// not identical, figures. Fed the C++ run's own readings, it reproduces the C++ estimates.
const SimEngine = (() => {
  function mulberry32(a) {
    return () => {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function normalSource(seed) {
    const u = mulberry32(seed >>> 0);
    return () => {
      let a = u(); if (a < 1e-12) a = 1e-12;
      return Math.sqrt(-2 * Math.log(a)) * Math.cos(2 * Math.PI * u());
    };
  }
  const mul = (A, B) => [A[0]*B[0] + A[1]*B[2], A[0]*B[1] + A[1]*B[3], A[2]*B[0] + A[3]*B[2], A[2]*B[1] + A[3]*B[3]];
  const tr = (A) => [A[0], A[2], A[1], A[3]];
  const add = (A, B) => A.map((v, i) => v + B[i]);

  // p: { steps, dt, x0, v0, accel, every, sigma, seed, q, r, p0pos, p0vel }
  // fixedMeas: optional array (null = no reading) that replaces the sensor, to replay recorded readings.
  function simulate(p, fixedMeas) {
    const n = p.steps + 1;
    const out = {
      n, t: new Float64Array(n), pos: new Float64Array(n), vel: new Float64Array(n),
      meas: new Float64Array(n).fill(NaN), est: new Float64Array(n).fill(NaN),
      evel: new Float64Array(n).fill(NaN), evar: new Float64Array(n).fill(NaN),
      kind: new Uint8Array(n), // 0 = no estimate yet, 1 = predict only, 2 = predict + update (or first reading)
    };
    const normal = normalSource(p.seed);
    let pos = p.x0, vel = p.v0;
    let x = null, P = null;
    for (let k = 0; k < n; k++) {
      if (k > 0) { pos = pos + vel * p.dt; vel = vel + p.accel * p.dt; }
      out.t[k] = k * p.dt; out.pos[k] = pos; out.vel[k] = vel;
      let z = NaN;
      if (fixedMeas) { if (fixedMeas[k] != null) z = fixedMeas[k]; }
      else if (k % p.every === 0) z = pos + p.sigma * normal();
      out.meas[k] = z;
      if (!x) {
        if (!isNaN(z)) { x = [z, 0]; P = [p.p0pos, 0, 0, p.p0vel]; out.kind[k] = 2; }
      } else {
        const dt = p.dt, dt2 = dt * dt, dt3 = dt2 * dt;
        const F = [1, dt, 0, 1];
        x = [x[0] + dt * x[1], x[1]];
        P = add(mul(mul(F, P), tr(F)), [p.q * dt3 / 3, p.q * dt2 / 2, p.q * dt2 / 2, p.q * dt]);
        out.kind[k] = 1;
        if (!isNaN(z)) {
          const S = P[0] + p.r, K = [P[0] / S, P[2] / S], y = z - x[0];
          x = [x[0] + K[0] * y, x[1] + K[1] * y];
          const IKH = [1 - K[0], 0, -K[1], 1];
          const KK = [K[0]*K[0]*p.r, K[0]*K[1]*p.r, K[1]*K[0]*p.r, K[1]*K[1]*p.r];
          P = add(mul(mul(IKH, P), tr(IKH)), KK);
          out.kind[k] = 2;
        }
      }
      if (x) { out.est[k] = x[0]; out.evel[k] = x[1]; out.evar[k] = P[0]; }
    }
    return out;
  }

  // Running metrics over steps 0..k, taken at the steps that have a reading (as analyze.py does).
  function metricsUpTo(s, k) {
    let n = 0, sm = 0, se = 0, sv = 0, inside = 0;
    for (let i = 0; i <= k; i++) {
      if (isNaN(s.meas[i]) || isNaN(s.est[i])) continue;
      n++;
      const em = s.meas[i] - s.pos[i], ee = s.est[i] - s.pos[i], ev = s.evel[i] - s.vel[i];
      sm += em * em; se += ee * ee; sv += ev * ev;
      if (Math.abs(ee) <= 2 * Math.sqrt(s.evar[i])) inside++;
    }
    if (!n) return null;
    const rm = Math.sqrt(sm / n), re = Math.sqrt(se / n);
    return { n, rmseMeas: rm, rmseEst: re, rmseVel: Math.sqrt(sv / n), ratio: rm > 0 ? re / rm : NaN, coverage: inside / n };
  }

  return { simulate, metricsUpTo };
})();
if (typeof module !== 'undefined') module.exports = SimEngine;
