/* Simulatore di esposizione.
   Una foto reale, tre controlli in terzi di stop, istogramma calcolato dai pixel.
   Uso: <div class="sim" data-src="img.webp" data-f="4" data-t="0.001" data-iso="100" data-mm="17"
              data-start-f="8" data-start-t="0.004" data-start-iso="100" data-theme="dark|light" data-focus="0.5,0.45"></div> */
(function () {
  const F = [1.4,1.6,1.8,2,2.2,2.5,2.8,3.2,3.5,4,4.5,5,5.6,6.3,7.1,8,9,10,11,13,14,16,18,20,22];
  const T = [1/4000,1/3200,1/2500,1/2000,1/1600,1/1250,1/1000,1/800,1/640,1/500,1/400,1/320,1/250,1/200,1/160,1/125,1/100,1/80,1/60,1/50,1/40,1/30,1/25,1/20,1/15,1/13,1/10,1/8,1/6,1/5,1/4,0.3,0.4,0.5,0.6,0.8,1,1.3,1.6,2,2.5,3.2,4,5,6,8,10,13,15,20,25,30];
  const ISO = [100,125,160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500,3200,4000,5000,6400,8000,10000,12800,25600];
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const nearest = (arr, v) => arr.reduce((b, x, i) => Math.abs(Math.log2(x / v)) < Math.abs(Math.log2(arr[b] / v)) ? i : b, 0);
  const fmtT = t => t >= 0.3 ? (String(Math.round(t * 10) / 10).replace('.', ',') + ' s') : ('1/' + Math.round(1 / t));
  const fmtF = f => 'f/' + String(f).replace('.', ',');
  const ev = (f, t, iso) => Math.log2(f * f / t) - Math.log2(iso / 100);
  const fmtStops = s => {
    const r = Math.round(s * 3) / 3;
    if (Math.abs(r) < 0.05) return '0';
    const sign = r > 0 ? '+' : '−';
    return sign + (Math.round(Math.abs(r) * 10) / 10).toFixed(1).replace('.', ',');
  };

  // sRGB <-> lineare
  const toLin = new Float32Array(256);
  for (let i = 0; i < 256; i++) { const c = i / 255; toLin[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  const toSrgb = l => { l = Math.max(0, l); const c = l <= 0.0031308 ? l * 12.92 : 1.055 * Math.pow(l, 1 / 2.4) - 0.055; return Math.min(255, Math.round(c * 255)); };

  // sfocatura portabile: rimpicciolisci e ingrandisci (funziona anche dove ctx.filter non c'è)
  function blurInto(dst, src, r) {
    const ctx = dst.getContext('2d');
    if (r < 0.6) { ctx.drawImage(src, 0, 0, dst.width, dst.height); return; }
    const s = 1 + r / 1.6;
    const w = Math.max(2, Math.round(dst.width / s)), h = Math.max(2, Math.round(dst.height / s));
    const tmp = blurInto.tmp || (blurInto.tmp = document.createElement('canvas'));
    tmp.width = w; tmp.height = h;
    const t = tmp.getContext('2d'); t.imageSmoothingQuality = 'high';
    t.drawImage(src, 0, 0, w, h);
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(tmp, 0, 0, dst.width, dst.height);
  }

  function drawHisto(cv, data, color) {
    const bins = new Uint32Array(64);
    for (let i = 0; i < data.length; i += 16) {
      const y = 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
      bins[Math.min(63, y >> 2)]++;
    }
    const dpr = devicePixelRatio || 1;
    const w = cv.clientWidth * dpr, h = cv.clientHeight * dpr;
    if (cv.width !== w) { cv.width = w; cv.height = h; }
    const c = cv.getContext('2d');
    c.clearRect(0, 0, w, h);
    let max = 0; for (let i = 1; i < 63; i++) max = Math.max(max, bins[i]);
    max = Math.max(max, 1);
    c.fillStyle = color;
    const bw = w / 64;
    for (let i = 0; i < 64; i++) {
      const v = Math.min(1, bins[i] / max);
      c.fillRect(i * bw, h - v * h, bw + 0.5, v * h);
    }
    // segnali di clipping agli estremi
    const total = data.length / 16;
    c.fillStyle = '#e8644a';
    if (bins[0] / total > 0.02) c.fillRect(0, 0, 3 * dpr, h);
    if (bins[63] / total > 0.02) c.fillRect(w - 3 * dpr, 0, 3 * dpr, h);
  }
  window.drawHistoFromImage = function (img, cv, color) {
    const c = document.createElement('canvas'); c.width = 400; c.height = Math.round(400 * img.naturalHeight / img.naturalWidth);
    const x = c.getContext('2d'); x.drawImage(img, 0, 0, c.width, c.height);
    drawHisto(cv, x.getImageData(0, 0, c.width, c.height).data, color);
  };

  function build(el) {
    const d = el.dataset;
    const scene = ev(+d.f, +d.t, +d.iso);
    const mm = +(d.mm || 50) * 1.5; // focale equivalente APS-C
    const [fx, fy] = (d.focus || '0.5,0.5').split(',').map(Number);
    const theme = d.theme || 'dark';
    const idx = {
      f: nearest(F, +(d.startF || d.f)),
      t: nearest(T, +(d.startT || d.t)),
      iso: nearest(ISO, +(d.startIso || d.iso))
    };
    const start = { ...idx };
    const hColor = () => theme === 'light' ? (getComputedStyle(document.documentElement).getPropertyValue('--glacier').trim() || '#2b7a81') : 'rgba(255,255,255,.85)';

    const stage = el.querySelector('.sim-stage') || el;
    const canvas = document.createElement('canvas');
    canvas.className = 'photo';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', d.alt || 'Foto di esempio che cambia con i controlli');
    stage.prepend(canvas);

    const panel = el.querySelector('.controls');
    panel.classList.toggle('light', theme === 'light');
    panel.innerHTML = `
      <div class="dial"><label for="${el.id}-f">Diaframma</label><input id="${el.id}-f" type="range" min="0" max="${F.length - 1}" step="1"><output></output></div>
      <div class="dial"><label for="${el.id}-t">Tempo</label><input id="${el.id}-t" type="range" min="0" max="${T.length - 1}" step="1"><output></output></div>
      <div class="dial"><label for="${el.id}-iso">ISO</label><input id="${el.id}-iso" type="range" min="0" max="${ISO.length - 1}" step="1"><output></output></div>
      <canvas class="histo" aria-hidden="true"></canvas>
      <div class="readout"><span>Esposimetro <span class="meter" aria-live="polite"></span> stop</span><button class="reset" type="button">Esposizione corretta</button></div>
      <p class="notes"></p>`;
    const [inF, inT, inI] = panel.querySelectorAll('input');
    const outs = panel.querySelectorAll('output');
    const meter = panel.querySelector('.meter');
    const notes = panel.querySelector('.notes');
    const histo = panel.querySelector('.histo');
    inF.value = idx.f; inT.value = idx.t; inI.value = idx.iso;

    const img = new Image();
    img.decoding = 'async';
    img.src = d.src;
    let W = 0, H = 0, base, sharp, soft, out, noise, ctxOut, pending = false, intro = reduceMotion ? 0 : -4;

    img.onload = () => {
      W = Math.min(1200, img.naturalWidth); H = Math.round(W * img.naturalHeight / img.naturalWidth);
      canvas.width = W; canvas.height = H;
      const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
      base = mk(); base.getContext('2d').drawImage(img, 0, 0, W, H);
      sharp = mk(); soft = mk(); out = mk();
      ctxOut = canvas.getContext('2d', { willReadFrequently: true });
      noise = new Int8Array(W * H);
      for (let i = 0; i < noise.length; i++) { const g = (Math.random() + Math.random() + Math.random() - 1.5) * 2; noise[i] = Math.max(-127, Math.min(127, Math.round(g * 42))); }
      if (intro) {
        const t0 = performance.now();
        const step = now => {
          const p = Math.min(1, (now - t0) / 1400);
          intro = -4 * Math.pow(1 - p, 3);
          render();
          if (p < 1) requestAnimationFrame(step); else { intro = 0; render(); }
        };
        requestAnimationFrame(step);
      } else render();
    };

    function state() {
      const f = F[inF.value], t = T[inT.value], iso = ISO[inI.value];
      return { f, t, iso, stops: scene - ev(f, t, iso) };
    }

    function describe(s) {
      const bits = [];
      const st = Math.round(s.stops * 3) / 3;
      if (st >= 0.66) bits.push('Sovraesposta: le alte luci si bruciano.');
      else if (st <= -0.66) bits.push('Sottoesposta: le ombre si chiudono.');
      else bits.push('Esposizione corretta.');
      if (s.f <= 2.8) bits.push('Diaframma aperto, bordi sfocati.');
      else if (s.f >= 11) bits.push('Diaframma chiuso, tutto nitido.');
      if (s.t > 1 / mm) bits.push('Tempo lungo: a mano libera arriva il mosso.');
      else if (s.t <= 1 / 1000) bits.push('Tempo rapido: il movimento si congela.');
      if (s.iso >= 3200) bits.push('ISO alti: rumore visibile.');
      return bits.join(' ');
    }

    function render() {
      if (!W) return;
      const s = state();
      outs[0].textContent = fmtF(s.f);
      outs[1].textContent = fmtT(s.t);
      outs[2].textContent = s.iso;
      meter.textContent = fmtStops(s.stops);
      notes.textContent = describe(s);

      // profondità di campo: bordi sfocati con diaframma aperto
      const dof = s.f >= 8 ? 0 : Math.min(9, Math.pow(8 / s.f, 1.35) * 2.4 - 2.4);
      // mosso: oltre il tempo di sicurezza 1/focale equivalente
      const shake = s.t <= 1 / mm ? 0 : Math.min(12, (Math.log2(s.t * mm) + 1) * 1.7);

      const sc = sharp.getContext('2d');
      blurInto(sharp, base, shake);
      if (dof > 0.6) {
        blurInto(soft, sharp, dof + shake * 0.2);
        const oc = out.getContext('2d');
        oc.globalCompositeOperation = 'source-over';
        oc.drawImage(sharp, 0, 0);
        oc.globalCompositeOperation = 'destination-in';
        const g = oc.createRadialGradient(W * fx, H * fy, Math.min(W, H) * 0.14, W * fx, H * fy, Math.max(W, H) * 0.52);
        g.addColorStop(0, 'rgba(0,0,0,1)'); g.addColorStop(1, 'rgba(0,0,0,0)');
        oc.fillStyle = g; oc.fillRect(0, 0, W, H);
        oc.globalCompositeOperation = 'source-over';
        ctxOut.drawImage(soft, 0, 0);
        ctxOut.drawImage(out, 0, 0);
      } else {
        ctxOut.drawImage(sharp, 0, 0);
      }

      // esposizione in luce lineare + rumore ISO
      const gain = Math.pow(2, s.stops + intro);
      const lut = new Uint8ClampedArray(256);
      for (let i = 0; i < 256; i++) lut[i] = toSrgb(toLin[i] * gain);
      const nAmp = s.iso <= 200 ? 0 : Math.min(1.6, (Math.log2(s.iso / 100) - 1) * 0.26);
      const id = ctxOut.getImageData(0, 0, W, H), p = id.data;
      for (let i = 0, j = 0; i < p.length; i += 4, j++) {
        let r = lut[p[i]], g = lut[p[i + 1]], b = lut[p[i + 2]];
        if (nAmp) {
          const y = (r * 0.3 + g * 0.59 + b * 0.11) / 255;
          const n = noise[j] * nAmp * (1.25 - y);
          const nc = noise[(j * 7) % noise.length] * nAmp * 0.35;
          r += n + nc; g += n; b += n - nc;
        }
        p[i] = r; p[i + 1] = g; p[i + 2] = b;
      }
      ctxOut.putImageData(id, 0, 0);
      drawHisto(histo, p, hColor());
    }

    const schedule = () => { if (pending) return; pending = true; requestAnimationFrame(() => { pending = false; render(); }); };
    [inF, inT, inI].forEach(i => i.addEventListener('input', schedule));
    panel.querySelector('.reset').addEventListener('click', () => {
      // riporta a zero cambiando solo il tempo, come farebbe chi scatta in priorità di diaframma
      const s = state();
      const target = s.t * Math.pow(2, s.stops);
      inT.value = nearest(T, target);
      if (Math.abs(state().stops) > 0.2) { inT.value = start.t; inF.value = start.f; inI.value = start.iso; }
      schedule();
    });
    addEventListener('resize', () => W && drawHisto(histo, ctxOut.getImageData(0, 0, W, H).data, hColor()), { passive: true });
  }

  document.querySelectorAll('.sim').forEach(build);
})();
