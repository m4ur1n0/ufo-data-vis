<script>
    /*
        UFO Scrolly-Telly — Dark Mode (final pass), Svelte 5, SSR-safe
        =================================================================================================
        WHAT THIS IMPLEMENTATION DOES:
          • Keeps dark palette, typography, and sticky layout.
          • Preserves your opacity model EXACTLY: active scene = 1, others = 0 (no trail).
          • Adds axes (with tick marks + labels) to every charted scene (0,1,2,4,5).
          • Scene 3 (US map): NO axes/gridlines; enlarged via <g transform="scale(...)">; info card below.
          • Scene 4: two-column small multiples; each panel has labeled axes and ticks.
          • Scene 6: cards reliably render (>=6) with safe XHTML <foreignObject>.

        SVELTE 5 COMPLIANCE:
          • No {@const} inside plain elements; all “local constants” are hoisted to <script> helpers.
          • Scales that are reassigned are declared via $state(...) to avoid non_reactive_update diagnostics.

        FILES:
          - Component: labs/src/routes/c-lab1/Home.svelte
          - Data:      /data/scrubbed.csv (served via your symlink)
    */

    // ————————————————————————————————————————————————————————————————————————————————
    // Imports
    // ————————————————————————————————————————————————————————————————————————————————
    import { onMount, onDestroy } from 'svelte';
    import { csv } from 'd3-fetch';
    import { scaleLinear, scaleBand, scaleLog } from 'd3-scale';
    import { tweened } from 'svelte/motion';
    import { cubicInOut } from 'svelte/easing';
    import { interpolate } from 'd3-interpolate';
    import { max } from 'd3-array';

    // ————————————————————————————————————————————————————————————————————————————————
    // Scroll driver (unchanged behavior)
    // ————————————————————————————————————————————————————————————————————————————————
    let value = $state(0);                 // current scene index (0..7)
    const nsteps = 8;
    const steps = Array.from({ length: nsteps }, (_, i) => i);
    const copy = [
        // Scene 0
        "Over 80,000 UFO reports have been logged across more than a century. Each point of light is a moment when someone looked up, saw something they could not explain, and chose to record it. This is not proof, but it is human testimony — vast in number, uneven in distribution, and brimming with patterns waiting to be uncovered.",

        // Scene 1
        "Viewed across time, a striking rhythm emerges. Sightings remain relatively quiet for decades, only to surge in the mid-20th century and again in the 1990s. The Cold War skies, the dawn of mass media, the rise of the internet — all coincide with sharp climbs in reports. Are we seeing more phenomena, or simply more eyes willing to report?",

        // Scene 2
        "The clock and calendar tell their own story. Sightings cluster in the summer months, and evenings dominate — when more people are outdoors, gazing upward. Midnight holds fewer mysteries than twilight. Yet the regularity is uncanny: as if whatever people see is tethered not just to the sky, but to human rhythms of time and season.",

        // Scene 3
        "Where do these encounters unfold? The United States leads by far, with dense hotspots across California, Washington, Florida, and Texas. The map glows with concentrations of sightings, but geography alone cannot explain why. Culture, infrastructure, and belief all play roles — and still, the clusters feel like more than coincidence.",

        // Scene 4
        "Descriptions evolve. For decades, most reports were of simple 'lights' in the sky. Later, triangles and fireballs surged into prominence, matching popular imagery of UFOs. Circles and unknown shapes persist as well. The language people choose reflects both what they believe they saw, and what the culture around them makes imaginable.",

        // Scene 5
        "How long do these encounters last? The vast majority vanish within minutes — fleeting glimmers, sudden motions, momentary lights. But a rare few stretch far longer, lasting hours. These outliers pull at the edges of credibility: are they exaggerations, errors, or extraordinary events? The durations trace the line between the mundane and the mysterious.",

        // Scene 6
        "Within the numbers lie human voices. Short notes from witnesses capture the unease of the moment: a glow above a quiet road, a triangle hovering soundlessly, a burst of fire that lingered too long. These fragments are raw and personal, ordinary people struggling to put words to the extraordinary.",

        // Scene 7
        "What does it all mean? Patterns abound: seasonal rhythms, cultural echoes, sudden surges in reporting. But patterns are not proof. This dataset offers no certainty, only clues — threads of mystery woven into everyday life. To study it is to glimpse not only the unknown in the skies, but the hopes, fears, and imaginations of those watching from below."
    ];


    let container;
    let nodes = [];
    let observer;
    let root = null, top = 0, bottom = 0, increments = 80;
    let threshold = [];

    function updateObserver() {
        if (observer) observer.disconnect();
        const opts = { root, rootMargin: `${top}px 0px ${bottom}px 0px`, threshold };
        const ratios = new Map();

        observer = new IntersectionObserver((entries) => {
            for (const e of entries) {
                const idx = nodes.indexOf(e.target);
                if (idx !== -1) ratios.set(idx, e.intersectionRatio);
            }
            // Choose the step with the largest visible intersection ratio
            let bestIdx = value, best = -1;
            for (const [idx, r] of ratios) if (r > best) { best = r; bestIdx = idx; }
            value = bestIdx;
            retargetSceneTweens();
        }, opts);

        nodes.forEach((n) => observer.observe(n));
    }

    onMount(() => {
        threshold = Array.from({ length: increments + 1 }, (_, i) => i / increments);
        nodes = Array.from(container?.querySelectorAll(':scope > .step') ?? []);
        updateObserver();
    });

    // ————————————————————————————————————————————————————————————————————————————————
    // Data load & precompute (logic unchanged; presentation improves below)
    // ————————————————————————————————————————————————————————————————————————————————
    const DATA_URL = '/data/scrubbed.csv';
    const gridStep = 0.75; // degrees — used both for binning and for screen cell size

    // LOCAL datetime parser for "MM/DD/YYYY HH:mm[:ss]"
    function parseLocal(dtStr) {
        if (!dtStr) return null;
        const [datePart, timePart = '00:00'] = String(dtStr).trim().split(/\s+/);
        const md = datePart.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
        if (!md) return null;
        const mm = +md[1], dd = +md[2], yyyy = +md[3];
        const mt = timePart.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
        if (!mt) return null;
        const HH = +mt[1], MM = +mt[2], SS = mt[3] ? +mt[3] : 0;
        if (mm < 1 || mm > 12 || dd < 1 || dd > 31 || HH < 0 || HH > 23 || MM < 0 || MM > 59 || SS < 0 || SS > 59) return null;
        return new Date(yyyy, mm - 1, dd, HH, MM, SS); // local time
    }

    // ————————————————————————————————————————————————————————————————————————————————
    // Small helpers for Scene 0 (sparks) — axis ticks & polyline points
    // NOTE: We avoid {@const} in markup; all sizing is computed here.
    // ————————————————————————————————————————————————————————————————————————————————
    const SPARK_H = 110;               // total spark SVG height
    const SPARK_TOP = 8;               // top padding inside spark plot area
    const SPARK_PLOT = 88;             // plot height (leaves room for x labels)
    const sparkW = () => innerW() / 3 - 12;
    const sparkBASE = () => SPARK_TOP + SPARK_PLOT; // y pixel for bottom axis inside spark

    // Build spark polyline points for generic data arrays
    function sparkPoints(data, xKey, yKey, w, plotH, xDomain = null) {
        if (!data || !data.length) return '';
        const xs = data.map(d => +d[xKey]);
        const ys = data.map(d => +d[yKey]);
        const xmin = xDomain ? xDomain[0] : Math.min(...xs);
        const xmax = xDomain ? xDomain[1] : Math.max(...xs);
        const ymax = Math.max(1, Math.max(...ys));
        const _x = scaleLinear().domain([xmin, xmax]).range([0, w]);
        const _y = scaleLinear().domain([0, ymax]).nice().range([plotH, 0]);
        return data.map(d => `${_x(+d[xKey])},${_y(+d[yKey])}`).join(' ');
    }
    // X ticks for years: decade/5y/2y depending on span
    function sparkYearTicks(w) {
        if (!yearCounts.length) return [];
        const ys = yearCounts.map(d => d.year);
        const xmin = Math.min(...ys), xmax = Math.max(...ys);
        const span = xmax - xmin;
        const step = span >= 80 ? 10 : span >= 40 ? 5 : 2;
        const sx = scaleLinear().domain([xmin, xmax]).range([0, w]);
        const ticks = [];
        for (let y = Math.ceil(xmin / step) * step; y <= xmax; y += step) {
            ticks.push({ x: sx(y), label: y });
        }
        return ticks;
    }
    // X ticks for months: numeric 1..12
    function sparkMonthTicks(w) {
        const sx = scaleLinear().domain([1, 12]).range([0, w]);
        return Array.from({ length: 12 }, (_, i) => {
            const m = i + 1;
            return { x: sx(m), label: m };
        });
    }
    // X ticks for hours: every 4 from 0..24
    function sparkHourTicks(w) {
        const sx = scaleLinear().domain([0, 23]).range([0, w]);
        const out = [];
        for (let h = 0; h <= 23; h += 4) out.push({ x: sx(h), label: h });
        return out;
    }
    // Y ticks for sparks: compute from values, return [{y,label}] in pixel space relative to TOP
    function sparkYTicksFromValues(vals, plotH, nticks = 3) {
        const vmax = Math.max(1, ...vals);
        const sy = scaleLinear().domain([0, vmax]).nice().range([plotH, 0]);
        return sy.ticks(nticks).map(t => ({ y: SPARK_TOP + sy(t), label: Math.round(t).toLocaleString('en-US') }));
    }

    // ————————————————————————————————————————————————————————————————————————————————
    // Map helpers (Scene 3). We scale the group instead of recomputing geometry.
    // ————————————————————————————————————————————————————————————————————————————————
    const projX = (lon) => (lon + 180) / 360 * innerW();      // x in [0..innerW()]
    const projY = (lat) => (90 - lat) / 180 * innerH();       // y in [0..innerH()]
    const cellW = () => (gridStep / 360) * innerW();
    const cellH = () => (gridStep / 180) * innerH();

    // Map scale so that: (scaled map height) + gap + card height <= innerH()
    const mapCardH = 108;
    const mapCardGap = 14;

    // ————————————————————————————————————————————————————————————————————————————————
    // Scene 4 helpers — two-column panel layout + per-panel axes/ticks
    // ————————————————————————————————————————————————————————————————————————————————
    const panelGutter = 16;                // horizontal gap between two columns
    const panelW = () => (innerW() - panelGutter) / 2; // width per panel
    const panelH = 180;                    // height per panel (enough for ticks + labels)
    const rowGap = 18;

    function panelX(i) { return (i % 2 === 0) ? 0 : (panelW() + panelGutter); }
    function panelY(i) { return Math.floor(i / 2) * (panelH + rowGap); }

    // Build line points for a panel, and tick arrays for axes
    function panelScales(series) {
        if (!series || !series.length) {
            return { points: '', xticks: [], yticks: [], xmin: 0, xmax: 1 };
        }
        const years = series.map(d => d.year);
        const xmin = Math.min(...years), xmax = Math.max(...years);
        const sx = scaleLinear().domain([xmin, xmax]).range([0, panelW()]);
        const ymax = Math.max(1, max(series, d => d.count) || 1);
        const sy = scaleLinear().domain([0, ymax]).nice().range([panelH - 24, 0]); // leave 24px for bottom labels

        const points = series.map(d => `${sx(d.year)},${sy(d.count)}`).join(' ');

        // X ticks at min / mid / max years
        const mid = Math.round((xmin + xmax) / 2);
        const xticks = [xmin, mid, xmax].map(v => ({ x: sx(v), label: v }));

        // Y ticks (0..ymax "nice"), ~3 labels
        const yticks = sy.ticks(3).map(v => ({ y: sy(v), label: Math.round(v).toLocaleString('en-US') }));

        return { points, xticks, yticks, xmin, xmax };
    }

    // ————————————————————————————————————————————————————————————————————————————————
    // Aggregates (unchanged logic)
    // ————————————————————————————————————————————————————————————————————————————————
    let totalReports = 0;
    let yearCounts   = $state([]);  // [{year, count}]
    let monthHour    = $state([]);  // 12x24
    let monthTotals  = $state([]);  // [12]
    let hourTotals   = $state([]);  // [24]
    let stateCountsUS= $state([]);  // [{state,count}]
    let gridBins     = $state([]);  // [{lon,lat,count}]
    let shapeTopK    = $state([]);  // ['light','triangle',...]
    let shapeTrends  = $state({});  // { shape: [{year,count}] }
    let durQuantiles = $state({});  // { p50,p75,p90,p99 } (seconds)
    let ecdf         = $state([]);  // [{xSec, p}]
    let comments     = $state([]);  // curated snippets (cards)

    onMount(async () => {
        const rows = await csv(DATA_URL);

        const qMin = 1, qMax = 4 * 3600;
        const nBins = 60;
        const shapeKey = (s) => (s || 'unknown').toLowerCase().trim();
        const up = (s) => (s || '').toUpperCase().trim();

        const ymap = new Map();
        const mh = Array.from({ length: 12 }, () => Array(24).fill(0));
        const mt = Array(12).fill(0);
        const ht = Array(24).fill(0);

        const stateMap = new Map();
        const gridMap = new Map();

        const shapeMap = new Map();
        const shapeYear = new Map();

        const durs = [];
        const snippets = [];

        let good = 0;
        for (const r of rows) {
            const dt = r.datetime ? parseLocal(r.datetime) : null;
            if (!dt || isNaN(+dt)) continue;

            const y = dt.getFullYear();
            const m = dt.getMonth();   // 0..11 (local)
            const h = dt.getHours();   // 0..23 (local)

            if (Number.isFinite(y)) ymap.set(y, (ymap.get(y) || 0) + 1);
            if (m >= 0 && m < 12 && h >= 0 && h < 24) {
                mh[m][h]++; mt[m]++; ht[h]++;
            }

            const country = up(r.country);
            const st = up(r.state);
            const lat = +r.latitude;
            const lon = +r.longitude;

            if (country === 'US' && Number.isFinite(lat) && Number.isFinite(lon)
                && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
                stateMap.set(st, (stateMap.get(st) || 0) + 1);
                const gx = Math.floor((lon + 180) / gridStep);
                const gy = Math.floor((lat + 90) / gridStep);
                gridMap.set(`${gy}|${gx}`, (gridMap.get(`${gy}|${gx}`) || 0) + 1);
            }

            const shape = shapeKey(r.shape);
            shapeMap.set(shape, (shapeMap.get(shape) || 0) + 1);
            if (!shapeYear.has(shape)) shapeYear.set(shape, new Map());
            const sy = shapeYear.get(shape);
            sy.set(y, (sy.get(y) || 0) + 1);

            const ds = +r['duration (seconds)'];
            if (Number.isFinite(ds)) durs.push(Math.min(qMax, Math.max(qMin, ds)));

            if (r.comments && r.comments.trim()) {
                snippets.push({
                    ts: dt.toISOString(),
                    city: r.city || '',
                    state: st || (country !== 'US' ? country : ''),
                    shape,
                    dur: Number.isFinite(ds) ? ds : null,
                    month: m,
                    hour: h,
                    text: r.comments.trim().slice(0, 240)
                });
            }

            good++;
        }

        totalReports = good;

        yearCounts = Array.from(ymap.entries()).sort((a,b)=>a[0]-b[0]).map(([year,count])=>({year,count}));
        monthHour  = mh; monthTotals = mt; hourTotals = ht;

        stateCountsUS = Array.from(stateMap.entries()).sort((a,b)=>b[1]-a[1]).map(([state,count])=>({state,count}));

        gridBins = Array.from(gridMap.entries()).map(([key, count]) => {
            const [gy, gx] = key.split('|').map(Number);
            const lon = gx * gridStep - 180 + gridStep/2;
            const lat = gy * gridStep - 90  + gridStep/2;
            return { lon, lat, count };
        }).sort((a,b)=> a.lon - b.lon || a.lat - b.lat);

        const K = 5;
        const topShapes = Array.from(shapeMap.entries()).sort((a,b)=>b[1]-a[1]).slice(0,K).map(([s])=>s);
        shapeTopK = topShapes;
        const trends = {};
        for (const s of topShapes) {
            const mp = shapeYear.get(s) || new Map();
            trends[s] = Array.from(mp.entries()).sort((a,b)=>a[0]-b[0]).map(([year,count])=>({year,count}));
        }
        shapeTrends = trends;

        if (durs.length === 0) {
            durQuantiles = { p50:null,p75:null,p90:null,p99:null };
            ecdf = [];
        } else {
            durs.sort((a,b)=>a-b);
            const q = (p) => durs[Math.floor((durs.length-1)*p)];
            durQuantiles = { p50:q(0.50), p75:q(0.75), p90:q(0.90), p99:q(0.99) };
            const logMin = Math.log10(qMin), logMax = Math.log10(qMax);
            const edges = Array.from({length:nBins+1}, (_,i)=> Math.pow(10, logMin + (logMax-logMin)*i/nBins));
            let di = 0, pts = [];
            for (let b=1; b<edges.length; b++) {
                const hi = edges[b];
                while (di < durs.length && durs[di] <= hi) di++;
                pts.push({ xSec: hi, p: di / durs.length });
            }
            ecdf = pts;
        }

        // Scene 6: Loosened selection — ensure 6 cards
        const wanted = [
            (r) => r.month>=5 && r.month<=8 && r.hour>=20 && r.hour<=23,  // summer nights
            (r) => r.shape==='triangle',
            (r) => r.shape==='fireball' && (r.dur||0) >= 300,
            (r) => r.shape==='light',
            (r) => r.shape==='circle',
            (r) => true
        ];
        const picks = [];
        const seen = new Set();
        const keyOf = (r) => `${r.ts}|${r.city}|${r.state}`;
        for (const want of wanted) {
            for (const r of snippets) {
                const k = keyOf(r);
                if (want(r) && !seen.has(k)) { picks.push(r); seen.add(k); }
                if (picks.length >= 6) break;
            }
            if (picks.length >= 6) break;
        }
        if (picks.length < 6) {
            for (const r of snippets) {
                const k = keyOf(r);
                if (!seen.has(k)) { picks.push(r); seen.add(k); }
                if (picks.length >= 6) break;
            }
        }
        while (picks.length < 6) {
            picks.push({ ts: new Date(0).toISOString(), city: '', state: '', shape: '—', dur: null, month: null, hour: null, text: '(no comment available)' });
        }
        comments = picks.slice(0, 6);

        // Compute scales & kick tweens
        computeYearScales();
        computeHeatScales();
        computeMapMax();
        retargetSceneTweens();
    });

    // ————————————————————————————————————————————————————————————————————————————————
    // Dimensions & scales (responsive)
    // ————————————————————————————————————————————————————————————————————————————————
    let width = 980, height = 600; // SVG logical size; scaled by CSS
    const margin = { top: 28, right: 28, bottom: 42, left: 58 };
    const innerW = () => width - margin.left - margin.right;
    const innerH = () => height - margin.top - margin.bottom;

    // Scene 1: year scales — reactive to satisfy Svelte 5 diagnostics
    let xYear = $state(null);
    let yCount = $state(null);
    function computeYearScales() {
        if (!yearCounts.length) return;
        const years = yearCounts.map(d => d.year);
        const cmax = max(yearCounts, d => d.count) || 1;
        xYear = scaleLinear().domain([Math.min(...years), Math.max(...years)]).range([0, innerW()]);
        yCount = scaleLinear().domain([0, cmax]).nice().range([innerH(), 0]);
    }
    // Scene 1 tick helpers
    function yearTicks() {
        if (!xYear || !yearCounts.length) return [];
        const minY = Math.min(...yearCounts.map(d=>d.year));
        const maxY = Math.max(...yearCounts.map(d=>d.year));
        const span = maxY - minY;
        const step = span >= 80 ? 10 : span >= 40 ? 5 : 2;
        const out = [];
        for (let y = Math.ceil(minY/step)*step; y <= maxY; y += step) out.push(y);
        return out;
    }
    function countTicks() {
        return yCount ? yCount.ticks(5) : [];
    }

    // Scene 2: heatmap scales
    const hours = Array.from({ length: 24 }, (_, i) => i);
    const months = Array.from({ length: 12 }, (_, i) => i); // 0..11
    let xHourBand = scaleBand().domain(hours).range([0, innerW()]).padding(0.05);
    let yMonthBand = scaleBand().domain(months).range([0, innerH()]).padding(0.08);
    let heatMax = 1;
    function computeHeatScales() {
        if (!monthHour.length) return;
        heatMax = 1;
        for (let m=0;m<12;m++) for (let h=0;h<24;h++) heatMax = Math.max(heatMax, monthHour[m][h]);
    }
    function heatColor(v) {
        const t = Math.sqrt(Math.min(1, v / heatMax));
        return interpolate('#0b1220', '#22d3ee')(t); // dark navy → bright cyan
    }

    // Scene 3: map scaling
    let mapMax = 1;
    function computeMapMax() {
        mapMax = 1;
        for (const b of gridBins) mapMax = Math.max(mapMax, b.count);
    }
    function mapColor(v) {
        const t = Math.sqrt(Math.min(1, v / mapMax));
        return interpolate('#0b1220', '#22d3ee')(t);
    }

    // Scene 5: ECDF scales + tick helpers
    const durMin = 1, durMax = 4 * 3600;
    let xDur = scaleLog().domain([durMin, durMax]).range([0, innerW()]).clamp(true);
    let yECDF = scaleLinear().domain([0,1]).range([innerH(), 0]);
    function durationTicks() {
        const vals = [1, 10, 60, 600, 3600, 7200, 14400];
        const labels = new Map([[1,'1s'],[10,'10s'],[60,'1m'],[600,'10m'],[3600,'1h'],[7200,'2h'],[14400,'4h']]);
        return vals.map(v => ({ v, label: labels.get(v) }));
    }
    function fracTicks() {
        return [0, 0.25, 0.5, 0.75, 1];
    }

    // ————————————————————————————————————————————————————————————————————————————————
    // Animation (opacity model preserved: active=1, others=0)
    // ————————————————————————————————————————————————————————————————————————————————
    const sceneTweens = Array.from({length:8}, (_,i)=> tweened(i===0?1:0, { duration: 450, easing: cubicInOut }));
    let s = $state(Array(8).fill(0));
    const unsubs = sceneTweens.map((tw, i) => tw.subscribe(v => s[i] = v));

    const clipW = tweened(0, { duration: 900, easing: cubicInOut });
    let clipWidth = $state(0);  const unsubClip = clipW.subscribe(v => clipWidth = v);

    const heatOpacity = tweened(0, { duration: 600, easing: cubicInOut });
    let heatA = $state(0);      const unsubHeat = heatOpacity.subscribe(v => heatA = v);

    const counter = tweened(0, { duration: 800, easing: cubicInOut });
    let countVal = $state(0);   const unsubC = counter.subscribe(v => countVal = Math.round(v));

    onDestroy(() => {
        unsubs.forEach(u=>u());
        unsubClip(); unsubHeat(); unsubC();
        if (observer) observer.disconnect();
    });

    function retargetSceneTweens() {
        computeYearScales(); computeHeatScales(); computeMapMax();
        for (let i=0;i<8;i++) sceneTweens[i].set(i === value ? 1 : 0);
        if (value === 0) { if (totalReports) counter.set(totalReports, { duration: 900 }); clipW.set(0); heatOpacity.set(0); }
        else if (value === 1) { if (yearCounts.length) clipW.set(innerW()); heatOpacity.set(0); }
        else if (value === 2) { heatOpacity.set(1); }
    }

    // ————————————————————————————————————————————————————————————————————————————————
    // Misc display helpers
    // ————————————————————————————————————————————————————————————————————————————————
    const fmtInt = (n) => n?.toLocaleString?.('en-US') ?? '—';
    const fmtMinSec = (s) => {
        if (!s || !Number.isFinite(s)) return '—';
        const m = Math.floor(s/60), r = Math.round(s%60);
        if (m===0) return `${r}s`; if (r===0) return `${m}m`; return `${m}m ${r}s`;
    };
</script>

<div class="container">
    <!-- Sticky graphic area (left) -->
    <div class="sticky">
        <svg {width} {height} role="img" aria-label="UFO scrollytelling visuals">
            <defs>
                <!-- Clip for Scene 1 'reveal' (unchanged reveal logic) -->
                <clipPath id="scene1Clip">
                    <rect x={0} y={0} width={clipWidth} height={innerH()} />
                </clipPath>
            </defs>

            <g transform={`translate(${margin.left},${margin.top})`}>

                <!-- ===================================================================================
                     Scene 0: KPI + enlarged sparklines with full axes (ticks + labels)
                     =================================================================================== -->
                <g style={`opacity:${s[0]}`}> 
                    <text x={innerW()/2} y={28} text-anchor="middle" class="kpi">
                        {fmtInt(countVal)} reports
                    </text>

                    <g transform="translate(0,48)">
                        {#if yearCounts.length}
                            {#key yearCounts}
                                <g>
                                    <!-- Spark 1: per year -->
                                    <g transform={`translate(${innerW()/6},0) scale(2.05)`}>
                                        <text class="mini-title" x={0} y={-10}>per year</text>
                                        <svg class="spark" width={sparkW()} height={SPARK_H} viewBox={`0 0 ${sparkW()} ${SPARK_H}`}>
                                            <!-- Frame + axes -->
                                            <rect class="spark-frame" x="0" y="0" width={sparkW()} height={SPARK_H} />
                                            <line class="spark-axis" x1="0" y1={sparkBASE()} x2={sparkW()} y2={sparkBASE()} />
                                            <line class="spark-axis" x1="0" y1={SPARK_TOP} x2="0" y2={sparkBASE()} />

                                            <!-- X ticks (years) -->
                                            {#each sparkYearTicks(sparkW()) as t}
                                                <line class="spark-tick" x1={t.x} y1={sparkBASE()} x2={t.x} y2={sparkBASE()-6} />
                                                <text class="spark-tick-label" x={t.x} y={sparkBASE()+14} text-anchor="middle">{t.label}</text>
                                            {/each}
                                            <!-- Y ticks from counts -->
                                            {#each sparkYTicksFromValues(yearCounts.map(d=>d.count), SPARK_PLOT, 3) as ty}
                                                <line class="spark-tick" x1="-6" y1={ty.y} x2="0" y2={ty.y} />
                                                <text class="spark-tick-label" x="-8" y={ty.y} text-anchor="end" dominant-baseline="middle">{ty.label}</text>
                                            {/each}

                                            <!-- Series (translated into plot area) -->
                                            <g transform={`translate(0,${SPARK_TOP})`}>
                                                <polyline fill="none" stroke="var(--ink)" stroke-width="1.7"
                                                    points={sparkPoints(yearCounts, 'year', 'count', sparkW(), SPARK_PLOT)} />
                                            </g>

                                            <!-- Axis labels -->
                                            <text class="axis-micro" x={sparkW()/2} y={sparkBASE()+28} text-anchor="middle">Year</text>
                                            <text class="axis-micro" x="-34" y={(SPARK_TOP + sparkBASE())/2}
                                                  transform={`rotate(-90 -34 ${(SPARK_TOP + sparkBASE())/2})`}
                                                  text-anchor="middle">Reports</text>
                                        </svg>
                                    </g>

                                    <!-- Spark 2: by month (1..12 numeric) -->
                                    <g transform={`translate(150,${innerH()/2})`}>
                                        <text class="mini-title" x={0} y={-10}>by month</text>
                                        <svg class="spark" width={sparkW()} height={SPARK_H} viewBox={`0 0 ${sparkW()} ${SPARK_H}`}>
                                            <rect class="spark-frame" x="0" y="0" width={sparkW()} height={SPARK_H} />
                                            <line class="spark-axis" x1="0" y1={sparkBASE()} x2={sparkW()} y2={sparkBASE()} />
                                            <line class="spark-axis" x1="0" y1={SPARK_TOP} x2="0" y2={sparkBASE()} />

                                            {#each sparkMonthTicks(sparkW()) as t}
                                                <line class="spark-tick" x1={t.x} y1={sparkBASE()} x2={t.x} y2={sparkBASE()-6} />
                                                <text class="spark-tick-label" x={t.x} y={sparkBASE()+14} text-anchor="middle">{t.label}</text>
                                            {/each}
                                            {#each sparkYTicksFromValues(monthTotals, SPARK_PLOT, 3) as ty}
                                                <line class="spark-tick" x1="-6" y1={ty.y} x2="0" y2={ty.y} />
                                                <text class="spark-tick-label" x="-8" y={ty.y} text-anchor="end" dominant-baseline="middle">{ty.label}</text>
                                            {/each}

                                            <g transform={`translate(0,${SPARK_TOP})`}>
                                                <polyline fill="none" stroke="var(--ink)" stroke-width="1.7"
                                                    points={sparkPoints(monthTotals.map((c,i)=>({x:i+1,y:c})), 'x', 'y', sparkW(), SPARK_PLOT, [1,12])} />
                                            </g>

                                            <text class="axis-micro" x={sparkW()/2} y={sparkBASE()+28} text-anchor="middle">Month</text>
                                            <text class="axis-micro" x="-34" y={(SPARK_TOP + sparkBASE())/2}
                                                  transform={`rotate(-90 -34 ${(SPARK_TOP + sparkBASE())/2})`}
                                                  text-anchor="middle">Reports</text>
                                        </svg>
                                    </g>

                                    <!-- Spark 3: by hour (0..23; ticks every 4 hours) -->
                                    <g transform={`translate(${innerW()/2},${innerH()/2})`}>
                                        <text class="mini-title" x={0} y={-10}>by hour</text>
                                        <svg class="spark" width={sparkW()} height={SPARK_H} viewBox={`0 0 ${sparkW()} ${SPARK_H}`}>
                                            <rect class="spark-frame" x="0" y="0" width={sparkW()} height={SPARK_H} />
                                            <line class="spark-axis" x1="0" y1={sparkBASE()} x2={sparkW()} y2={sparkBASE()} />
                                            <line class="spark-axis" x1="0" y1={SPARK_TOP} x2="0" y2={sparkBASE()} />

                                            {#each sparkHourTicks(sparkW()) as t}
                                                <line class="spark-tick" x1={t.x} y1={sparkBASE()} x2={t.x} y2={sparkBASE()-6} />
                                                <text class="spark-tick-label" x={t.x} y={sparkBASE()+14} text-anchor="middle">{t.label}</text>
                                            {/each}
                                            {#each sparkYTicksFromValues(hourTotals, SPARK_PLOT, 3) as ty}
                                                <line class="spark-tick" x1="-6" y1={ty.y} x2="0" y2={ty.y} />
                                                <text class="spark-tick-label" x="-8" y={ty.y} text-anchor="end" dominant-baseline="middle">{ty.label}</text>
                                            {/each}

                                            <g transform={`translate(0,${SPARK_TOP})`}>
                                                <polyline fill="none" stroke="var(--ink)" stroke-width="1.7"
                                                    points={sparkPoints(hourTotals.map((c,i)=>({x:i,y:c})), 'x', 'y', sparkW(), SPARK_PLOT, [0,23])} />
                                            </g>

                                            <text class="axis-micro" x={sparkW()/2} y={sparkBASE()+28} text-anchor="middle">Hour</text>
                                            <text class="axis-micro" x="-34" y={(SPARK_TOP + sparkBASE())/2}
                                                  transform={`rotate(-90 -34 ${(SPARK_TOP + sparkBASE())/2})`}
                                                  text-anchor="middle">Reports</text>
                                        </svg>
                                    </g>
                                </g>
                            {/key}
                        {/if}
                    </g>
                </g>

                <!-- ===================================================================================
                     Scene 1: Timeline (axes + gridlines; reactive scales; reveal clip)
                     =================================================================================== -->
                <g style={`opacity:${s[1]}`}> 
                    {#if yearCounts.length}
                        {#key yearCounts}
                            <g>
                                <!-- Axes -->
                                <g class="axis">
                                    <!-- X baseline -->
                                    <line class="axis-line" x1={0} y1={innerH()} x2={innerW()} y2={innerH()} />
                                    {#each yearTicks() as y}
                                        <g transform={`translate(${xYear(y)},0)`}>
                                            <line class="tick-line" y1={innerH()} y2={innerH()+6} />
                                            <text class="tick" y={innerH()+20} text-anchor="middle">{y}</text>
                                        </g>
                                    {/each}
                                    <!-- Y baseline -->
                                    <line class="axis-line" x1={0} y1={0} x2={0} y2={innerH()} />
                                    {#each countTicks() as c}
                                        <g transform={`translate(0,${yCount(c)})`}>
                                            <line class="tick-line" x1={-6} x2={0} />
                                            <text class="tick" x={-10} text-anchor="end" dominant-baseline="middle">{Math.round(c)}</text>
                                            <line class="gridline" x1={0} x2={innerW()} y1={0} y2={0} />
                                        </g>
                                    {/each}
                                    <text class="axis-label" x={innerW()/2} y={innerH()+32} text-anchor="middle">Year</text>
                                    <text class="axis-label" x={-40} y={-10} transform="rotate(-90)">Reports</text>
                                </g>

                                <!-- Series (clipped by reveal) -->
                                <g clip-path="url(#scene1Clip)">
                                    <polyline
                                        fill="none" stroke="var(--ink)" stroke-width="2"
                                        points={yearCounts.map(d=>`${xYear(d.year)},${yCount(d.count)}`).join(' ')}
                                    />
                                    <polygon
                                        fill="var(--ink)" fill-opacity="0.15"
                                        points={`0,${innerH()} ` + yearCounts.map(d=>`${xYear(d.year)},${yCount(d.count)}`).join(' ') + ` ${innerW()},${innerH()}`}
                                    />
                                </g>
                            </g>
                        {/key}
                    {/if}
                </g>

                <!-- ===================================================================================
                     Scene 2: Month×Hour Heatmap — full axes (labels + ticks)
                     =================================================================================== -->
                <g style={`opacity:${s[2]}`}> 
                    {#if monthHour.length}
                        <g>
                            <!-- Heat cells -->
                            {#each months as m}
                                {#each hours as h}
                                    <rect
                                        x={xHourBand(h)}
                                        y={yMonthBand(m)}
                                        width={xHourBand.bandwidth()}
                                        height={yMonthBand.bandwidth()}
                                        fill={heatColor(monthHour[m][h])}
                                        opacity={heatA}
                                        rx="2" ry="2"
                                    />
                                {/each}
                            {/each}

                            <!-- Left Y axis baseline + ticks (months numeric 1..12) -->
                            <line class="axis-line" x1={0} y1={0} x2={0} y2={innerH()} />
                            {#each months as m}
                                <g transform={`translate(0,${yMonthBand(m)+yMonthBand.bandwidth()/2})`}>
                                    <line class="tick-line" x1={-6} x2={0} />
                                    <text class="tick" x={-10} text-anchor="end" dominant-baseline="middle">{m+1}</text>
                                </g>
                            {/each}
                            <text class="axis-label" x={-46} y={innerH()/2} transform="rotate(-90 -46 ${innerH()/2})" text-anchor="middle">Month</text>

                            <!-- Bottom X axis baseline + ticks every 4 hours -->
                            <line class="axis-line" x1={0} y1={innerH()} x2={innerW()} y2={innerH()} />
                            {#each hours as h}
                                {#if h % 4 === 0}
                                    <g transform={`translate(${xHourBand(h)+xHourBand.bandwidth()/2},0)`}>
                                        <line class="tick-line" y1={innerH()} y2={innerH()+6} />
                                        <text class="tick" y={innerH()+20} text-anchor="middle">{h}</text>
                                    </g>
                                {/if}
                            {/each}
                            <text class="axis-label" x={innerW()/2} y={innerH()+36} text-anchor="middle">Hour of day</text>
                        </g>
                    {/if}
                </g>

                <!-- ===================================================================================
                     Scene 3: US grid heat — bigger via SCALE; info panel BELOW (NO axes/grids)
                     =================================================================================== -->
                <g style={`opacity:${s[3]}`}> 
                    {#if gridBins.length}
                        <g>
                            <!-- Scaled map group: scale about (0,0) within inner plot area -->
                            <g transform= 'scale(6) translate(-140,-100)'>
                                {#each gridBins as b}
                                    <rect
                                        x={projX(b.lon) - cellW()/2}
                                        y={projY(b.lat) - cellH()/2}
                                        width={cellW()}
                                        height={cellH()}
                                        fill={mapColor(b.count)}
                                        opacity={0.95}
                                        rx="1" ry="1"
                                    />
                                {/each}
                            </g>

                            <g transform={`translate(0,0)`}>
                                <rect x={0} y={0} width={innerW()} height={mapCardH} rx="10" fill="var(--card-bg)" stroke="var(--card-border)" />
                                <text class="mini-title" x={12} y={20}>Top states (US)</text>
                                {#each stateCountsUS.slice(0,6) as sU, i}
                                    <text class="chip" x={12 + (i<3 ? 0 : innerW()/2)} y={44 + (i%3)*22}>{sU.state}: {fmtInt(sU.count)}</text>
                                {/each}
                            </g>
                        </g>
                    {/if}
                </g>

                <!-- ===================================================================================
                     Scene 4: Two-column small multiples — each panel has labeled axes + ticks
                     =================================================================================== -->
                <g style={`opacity:${s[4]}`}> 
                    {#if Object.keys(shapeTrends).length}
                        <g>
                            {#each shapeTopK as shape, i}
                                <!-- Panel frame & axes -->
<g transform={`translate(${panelX(i) + (i % 2 === 1 ? 10 : 0)},${panelY(i)}) scale(.9)`}>                                    <text class="panel-title" x={0} y={-6}>{shape}</text>

                                    <!-- Panel plot area (padding for bottom labels is baked into scales) -->
                                    <rect class="panel-frame" x={0} y={0} width={panelW()} height={panelH} rx="6" />

                                    {#if (shapeTrends[shape] || []).length}
                                        {#key shape}
                                            {#await Promise.resolve(panelScales(shapeTrends[shape])) then S}
                                                <!-- Axes baselines -->
                                                <line class="axis-line" x1={0} y1={panelH-24} x2={panelW()} y2={panelH-24} />
                                                <line class="axis-line" x1={0} y1={0} x2={0} y2={panelH-24} />

                                                <!-- X ticks (min/mid/max years) -->
                                                {#each S.xticks as t}
                                                    <line class="tick-line" x1={t.x} y1={panelH-24} x2={t.x} y2={panelH-24+6} />
                                                    <text class="tick" x={t.x} y={panelH-24+20} text-anchor="middle">{t.label}</text>
                                                {/each}

                                                <!-- Y ticks (~3 nice ticks) -->
                                                {#each S.yticks as t}
                                                    <line class="tick-line" x1={-6} y1={t.y} x2={0} y2={t.y} />
                                                    <text class="tick" x={-10} y={t.y} text-anchor="end" dominant-baseline="middle">{t.label}</text>
                                                {/each}

                                                <!-- Series polyline -->
                                                <polyline fill="none" stroke="var(--ink)" stroke-opacity="0.95" stroke-width="1.8"
                                                    points={S.points} />

                                                <!-- Axis labels -->
                                                <text class="axis-micro" x={panelW()/2} y={panelH+15} text-anchor="middle">Year</text>
                                                <text class="axis-micro" x={-40} y={(panelH-24)/2}
                                                      transform={`rotate(-90 -40 ${(panelH-24)/2})`}
                                                      text-anchor="middle">Reports</text>
                                            {/await}
                                        {/key}
                                    {/if}
                                </g>
                            {/each}
                        </g>
                    {/if}
                </g>

                <!-- ===================================================================================
                     Scene 5: ECDF — full axes + ticks + faint gridlines (as requested)
                     =================================================================================== -->
                <g style={`opacity:${s[5]}`}> 
                    {#if ecdf.length}
                        <g>
                            <!-- Baselines -->
                            <line x1={0} y1={innerH()} x2={innerW()} y2={innerH()} class="axis-line" />
                            <line x1={0} y1={0} x2={0} y2={innerH()} class="axis-line" />

                            <!-- X ticks -->
                            {#each durationTicks() as t}
                                <g transform={`translate(${xDur(t.v)},0)`}>
                                    <line y1={innerH()} y2={innerH()+6} class="tick-line"/>
                                    <text class="tick" y={innerH()+20} text-anchor="middle">{t.label}</text>
                                    <line x1={0} y1={0} x2={0} y2={innerH()} class="gridline"/>
                                </g>
                            {/each}

                            <!-- Y ticks -->
                            {#each fracTicks() as f}
                                <g transform={`translate(0,${yECDF(f)})`}>
                                    <line x1={-6} x2={0} class="tick-line"/>
                                    <text class="tick" x={-10} text-anchor="end" dominant-baseline="middle">{Math.round(f*100)}%</text>
                                    <line x1={0} x2={innerW()} y1={0} y2={0} class="gridline"/>
                                </g>
                            {/each}

                            <!-- ECDF curve -->
                            <polyline fill="none" stroke="var(--ink)" stroke-width="2"
                                points={ecdf.map(d=>`${xDur(d.xSec)},${yECDF(d.p)}`).join(' ')}
                            />

                            <!-- Quantile markers -->
                            <g>
                                {#if durQuantiles.p50 != null}<line x1={xDur(durQuantiles.p50)} y1={0} x2={xDur(durQuantiles.p50)} y2={innerH()} class="quantile"/>{/if}
                                {#if durQuantiles.p75 != null}<line x1={xDur(durQuantiles.p75)} y1={0} x2={xDur(durQuantiles.p75)} y2={innerH()} class="quantile"/>{/if}
                                {#if durQuantiles.p90 != null}<line x1={xDur(durQuantiles.p90)} y1={0} x2={xDur(durQuantiles.p90)} y2={innerH()} class="quantile"/>{/if}
                                {#if durQuantiles.p99 != null}<line x1={xDur(durQuantiles.p99)} y1={0} x2={xDur(durQuantiles.p99)} y2={innerH()} class="quantile"/>{/if}
                                {#if durQuantiles.p50 != null}<text class="tick" x={xDur(durQuantiles.p50)} y={-6} text-anchor="middle">50% ≈ {fmtMinSec(durQuantiles.p50)}</text>{/if}
                                {#if durQuantiles.p75 != null}<text class="tick" x={xDur(durQuantiles.p75)} y={-6} text-anchor="middle">75% ≈ {fmtMinSec(durQuantiles.p75)}</text>{/if}
                                {#if durQuantiles.p90 != null}<text class="tick" x={xDur(durQuantiles.p90)} y={-6} text-anchor="middle">90% ≈ {fmtMinSec(durQuantiles.p90)}</text>{/if}
                                {#if durQuantiles.p99 != null}<text class="tick" x={xDur(durQuantiles.p99)} y={-6} text-anchor="middle">99% ≈ {fmtMinSec(durQuantiles.p99)}</text>{/if}
                            </g>

                            <!-- Labels -->
                            <text class="axis-label" x={innerW()/2} y={innerH()+36} text-anchor="middle">Duration (log scale)</text>
                            <text class="axis-label" x={-50} y={-10} transform="rotate(-90)">Fraction of sightings</text>
                        </g>
                    {/if}
                </g>

                <!-- ===================================================================================
                     Scene 6: Cards — always 6, dark-safe, XHTML foreignObject
                     =================================================================================== -->
                <g style={`opacity:${s[6]}`}> 
                    {#if comments.length}
                        <g>
                            {#each comments as c, i}
                                <g transform={`translate(0,${i * 86})`}>
                                    <rect x={0} y={0} width={innerW()} height={78} rx="10" fill="var(--card-bg)" stroke="var(--card-border)" />
                                    <text class="chip" x={12} y={22}>{c.city}{c.state ? ', '+c.state : ''}</text>
                                    <text class="chip" x={12} y={40}>shape: {c.shape}</text>
                                    <text class="chip" x={12} y={58}>duration: {fmtMinSec(c.dur)}</text>
                                    <foreignObject x="220" y="10" width={innerW()-230} height={58}>
                                        <div xmlns="http://www.w3.org/1999/xhtml" class="comment-html">{c.text}</div>
                                    </foreignObject>
                                </g>
                            {/each}
                        </g>
                    {/if}
                </g>

                <!-- ===================================================================================
                     Scene 7: Finale (unchanged content; dark-mode typography)
                     =================================================================================== -->
                <g style={`opacity:${s[7]}`}> 
                    <g>
                        <text class="finale-title" x={innerW()/2} y={40} text-anchor="middle">So… what should we actually take from this?</text>
                        <foreignObject x="0" y="70" width={innerW()} height={innerH()-70}>
                            <div xmlns="http://www.w3.org/1999/xhtml" class="finale">
                                <p>
                                    This is a record of human encounters with the sky — self-reported, uneven, and large enough to show repeatable structure.
                                    Treat it like you would any signal from the real world: interesting, imperfect, and worth testing.
                                </p>

                                <ul>
                                    <li><strong>It’s human data.</strong> Peaks track access and attention as much as phenomena (more media, more internet, more reporting).</li>
                                    <li><strong>Time matters.</strong> Summer evenings dominate — when people are outside, skies are clearer, and the horizon invites stories.</li>
                                    <li><strong>Language shifts.</strong> “Light” never leaves the stage; “triangle” and “fireball” arrive later, echoing culture and tech imagery.</li>
                                    <li><strong>Most events are brief.</strong> Minutes, not hours. The long tails exist, but they’re rare and fragile.</li>
                                    <li><strong>Place concentrates.</strong> U.S. hotspots cluster where people, infrastructure, and attention also cluster.</li>
                                </ul>

                                <p><strong>What this is not:</strong> proof of cause, physics, or origin. These patterns explain reporting, not necessarily what was in the sky.</p>

                                <p><strong>If we kept pushing, here’s what we’d test next:</strong></p>
                                <ul>
                                    <li>Normalize by <em>population, light pollution, cloud cover, and weekend/holiday effects</em> to see what survives.</li>
                                    <li>De-duplicate likely multi-witness events and separate <em>first-hand</em> from <em>second-hand</em> reports.</li>
                                    <li>Compare shape trends against <em>media timelines</em> and <em>technology adoption</em> (satellites, drones, re-entries).</li>
                                    <li>Flag true anomalies with a simple <em>expected vs. observed</em> model across time, place, and description.</li>
                                </ul>

                                <p>
                                    In the end, the data gives us posture, not certainty: be skeptical, be curious, and keep looking up.
                                    The mystery isn’t only in the sky — it’s in how we notice, remember, and choose to tell the story.
                                </p>

                                <p class="fine">Dataset: UFO reports (1906–2014). Counts visually compressed for clarity. Patterns ≠ proof; they’re hypotheses that deserve testing.</p>
                            </div>
                        </foreignObject>
                    </g>
                </g>
            </g>
        </svg>
    </div>

    <!-- Steps (right column) -->
    <div class="scrolly">
        <div class="steps" bind:this={container}>
            {#each steps as step, i}
                <div class={value === i ? 'step active' : 'step'}>
                    <div class="step-content">{copy[i]}</div>
                </div>
            {/each}
            <div class="spacer" aria-hidden="true"></div>
        </div>
    </div>
</div>

<style>
    /* ===============================================================================================
       Dark tokens — one source of truth (axes + labels share these)
       =============================================================================================== */
    :global(:root){
        --bg: #0b0f10;
        --fg: #f8fafc;
        --muted: #94a3b8;
        --ink: #22d3ee;
        --card-bg: #111827;
        --card-border: #334155;
        --axis: #e2e8f0;
        --tick: #cbd5e1;
        --chip: #f1f5f9;
        --comment: #e2e8f0;
        --finale-fg: #f8fafc;
        --gridline: #334155;
        --axis-line: #cbd5e1;
        --frame: #1f2937;
        --shadow: rgba(0,0,0,.6);
    }

    :global(body){
        background: var(--bg);
        color: var(--fg);
    }

    /* Layout */
    .container{ display:flex; gap:2rem; align-items:flex-start; background:var(--bg); color:var(--fg); }
    .sticky{ position:sticky; top:1.25rem; flex:1 1 60%; }
    .scrolly{ flex:1 1 40%; }
    .steps{ position:relative; }
    .step{ min-height:65vh; display:flex; align-items:center; opacity:.6; transition:opacity .2s ease; }
    .step.active{ opacity:1; }
    .step-content{ background:var(--card-bg); border:1px solid var(--card-border); border-radius:12px; padding:1rem 1.25rem; box-shadow:0 2px 8px var(--shadow); }
    .spacer{ height:35vh; }

    /* Typography */
    .kpi{ font: 700 28px/1.2 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; fill:var(--fg); }
    .mini-title{ font: 600 11px/1 system-ui, sans-serif; fill:var(--axis); }
    .panel-title{ font: 600 12px/1 system-ui, sans-serif; fill: var(--axis); }
    .tick{ font: 11px/1 system-ui, sans-serif; fill:var(--tick); }
    .axis-label{ font: 12px/1 system-ui, sans-serif; fill: var(--axis); }
    .axis-micro{ font: 11px/1 system-ui, sans-serif; fill: var(--tick); }
    .chip{ font: 12px/1.2 system-ui, sans-serif; fill:var(--chip); }

    .comment-html{
        font: 13px/1.4 system-ui, sans-serif;
        color:var(--comment);
        overflow:hidden;
        display:-webkit-box;
        -webkit-line-clamp:3;
        -webkit-box-orient:vertical;
        line-clamp:3;
    }

    .finale-title{ font: 700 22px/1.2 system-ui, sans-serif; fill:var(--finale-fg); }
    .finale{ font: 14px/1.5 system-ui, sans-serif; color:var(--finale-fg); }
    .finale ul{ margin:0 0 12px 1.2rem; }
    .fine{ font-size:12px; color:var(--muted); margin-top:8px; }

    /* SVG surface */
    svg{ width:100%; height:auto; max-height:80vh; background:var(--bg); }
    .spark{ width:100%; height:auto; }

    /* Generic axis furniture */
    .axis-line{ stroke: var(--axis-line); stroke-width: 1.25; shape-rendering: crispEdges; }
    .tick-line{ stroke: var(--axis-line); stroke-width: 1; shape-rendering: crispEdges; }
    .gridline{ stroke: var(--gridline); stroke-width: 1; opacity: .6; shape-rendering: crispEdges; }
    .quantile{ stroke: var(--gridline); stroke-dasharray: 4,4; }

    /* Spark styling */
    .spark-frame{ fill: none; stroke: var(--frame); stroke-width: 1; shape-rendering: crispEdges; }
    .spark-axis{ stroke: var(--axis-line); stroke-width: 1; shape-rendering: crispEdges; }
    .spark-tick{ stroke: var(--axis-line); stroke-width: 1; }
    .spark-tick-label{ font: 10px/1 system-ui, sans-serif; fill: var(--tick); }

    /* Scene 4 panels */
    .panel-frame{ fill: transparent; stroke: var(--frame); stroke-width: 1; }

    @media (max-width: 980px){
        .container{ flex-direction:column-reverse; }
        .sticky{ width:96%; margin:0 auto; }
    }

    @media (prefers-reduced-motion: reduce){
        *{ transition:none !important; }
    }
</style>
