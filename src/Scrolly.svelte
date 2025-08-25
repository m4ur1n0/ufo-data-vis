<script>


    import { onMount, onDestroy } from 'svelte';
    import { csv } from 'd3-fetch';
    import { scaleLinear, scaleBand, scaleLog } from 'd3-scale';
    import { tweened } from 'svelte/motion';
    import { cubicInOut } from 'svelte/easing';
    import { interpolate } from 'd3-interpolate';
    import { max } from 'd3-array';

    let value = $state(0);                 // current step index (0..7)
    const nsteps = 8;
    const steps = Array.from({ length: nsteps }, (_, i) => i);
    const copy = [
        "Over 80,000 reports across a century — here's the shape of the data.",
        'A century in the sky: reports rise dramatically in the 1990s. We Cannot be completely sure why that is. Some theories suggest that people became more aware about random things in the sky with the release of the X-Files TV show in 1993, while others suggest that the end of the Cold War in 1991 led to more people looking up at the sky. The truth is probably a combination of both along with many other circumstantial factors.',
        'When do sightings happen? Summer evenings dominate. This could be because people are more likely to be outside and looking at the sky during warm summer evenings, or alternatively, aliens like warm weather.',
        "Where they're seen: the dataset is primarily focused on the US . There are some hotspots within the US — hotspots in CA, WA, FL, TX.",
        'What people report: unexplicable light is the primary vision; triangles, fireballs, and discs are not as typical as one may assume.',
        'How long it lasted: Typically minutes, but there are some reports that last hours. Longer sightings tend to be of lights or circles, while triangles and other shapes tend to be seen for briefer periods.',
        'Human moments: what do the viewers, the witnesses, the hunters and the observers have to say?',
        "Ultimately, what this does — and doesn't — mean."
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
            // Pick the step with the largest intersection ratio
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

    // Data load & precompute
    // ---------------------------------------------------------------------
    const DATA_URL = '/data/scrubbed.csv';
    const gridStep = 0.75; // degrees — used both for binning and for screen cell size

    // datetime parser for "MM/DD/YYYY HH:mm[:ss]" strings
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

    // Helpers to for markup
    function smallTrendPoints(series) {
        if (!series || !series.length) return '';
        const years = series.map(d => d.year);
        const xS = scaleLinear().domain([Math.min(...years), Math.max(...years)]).range([0, smallW()]);
        const yS = shapeYScale(series);
        return series.map(d => `${xS(d.year)},${yS(d.count)}`).join(' ');
    }

    function sparkPoints(data, xKey, yKey, w, h, xDomain = null) {
        if (!data || !data.length) return '';
        const xs = data.map(d => +d[xKey]);
        const ys = data.map(d => +d[yKey]);
        const xmin = xDomain ? xDomain[0] : Math.min(...xs);
        const xmax = xDomain ? xDomain[1] : Math.max(...xs);
        const ymax = Math.max(1, Math.max(...ys));
        const _x = scaleLinear().domain([xmin, xmax]).range([0, w]);
        const _y = scaleLinear().domain([0, ymax]).nice().range([h, 0]);
        return data.map(d => `${_x(+d[xKey])},${_y(+d[yKey])}`).join(' ');
    }

    // Projection & cell size helpers (equirectangular)
    const projX = (lon) => (lon + 180) / 360 * innerW();
    const projY = (lat) => (90 - lat) / 180 * innerH();
    const cellW = () => (gridStep / 360) * innerW();
    const cellH = () => (gridStep / 180) * innerH();

    // Aggregates used across scenes
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
    let comments     = $state([]);  // curated snippets

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
            const m = dt.getMonth();
            const h = dt.getHours();

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
                const gkey = `${gy}|${gx}`;
                gridMap.set(gkey, (gridMap.get(gkey) || 0) + 1);
            }

            const shape = shapeKey(r.shape);
            shapeMap.set(shape, (shapeMap.get(shape) || 0) + 1);
            if (!shapeYear.has(shape)) shapeYear.set(shape, new Map());
            const sy = shapeYear.get(shape);
            sy.set(y, (sy.get(y) || 0) + 1);

            const ds = +r['duration (seconds)'];
            if (Number.isFinite(ds)) {
                const dd = Math.min(qMax, Math.max(qMin, ds));
                durs.push(dd);
            }

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

        yearCounts = Array.from(ymap.entries())
            .sort((a, b) => a[0] - b[0])
            .map(([year, count]) => ({ year, count }));

        monthHour  = mh;
        monthTotals= mt;
        hourTotals = ht;

        stateCountsUS = Array.from(stateMap.entries())
            .sort((a,b) => b[1] - a[1])
            .map(([state, count]) => ({ state, count }));

        gridBins = Array.from(gridMap.entries()).map(([key, count]) => {
            const [gy, gx] = key.split('|').map(Number);
            const lon = gx * gridStep - 180 + gridStep / 2;
            const lat = gy * gridStep - 90  + gridStep / 2;
            return { lon, lat, count };
        }).sort((a,b) => a.lon - b.lon || a.lat - b.lat);

        const K = 5;
        const topShapes = Array.from(shapeMap.entries())
            .sort((a,b) => b[1] - a[1])
            .slice(0, K)
            .map(([s]) => s);
        shapeTopK = topShapes;

        const trends = {};
        for (const s of topShapes) {
            const mp = shapeYear.get(s) || new Map();
            const years = Array.from(mp.entries())
                .sort((a,b)=> a[0] - b[0])
                .map(([year, count]) => ({ year, count }));
            trends[s] = years;
        }
        shapeTrends = trends;

        if (durs.length === 0) {
            durQuantiles = { p50: null, p75: null, p90: null, p99: null };
            ecdf = [];
        } else {
            durs.sort((a,b)=> a - b);
            const q = (p) => durs[Math.floor((durs.length - 1) * p)];
            durQuantiles = { p50: q(0.50), p75: q(0.75), p90: q(0.90), p99: q(0.99) };

            const logMin = Math.log10(qMin), logMax = Math.log10(qMax);
            const edges = Array.from({ length: nBins + 1 }, (_, i) =>
                Math.pow(10, logMin + (logMax - logMin) * i / nBins)
            );
            const points = [];
            let di = 0;
            for (let b = 1; b < edges.length; b++) {
                const hi = edges[b];
                while (di < durs.length && durs[di] <= hi) di++;
                points.push({ xSec: hi, p: di / durs.length });
            }
            ecdf = points;
        }

        const wanted = [
            (r) => r.month>=5 && r.month<=8 && r.hour>=21 && r.hour<=23,
            (r) => r.shape==='triangle',
            (r) => r.shape==='fireball' && (r.dur||0) >= 600,
            (r) => r.shape==='light' && (r.dur||0) <= 120,
            (r) => r.shape==='circle',
            (r) => true
        ];
        const picked = [];
        for (const want of wanted) {
            const hit = snippets.find(want);
            if (hit) picked.push(hit);
        }
        comments = picked.slice(0, 6);

        computeYearScales();
        computeHeatScales();
        computeMapMax();
        retargetSceneTweens();
    });

    // Dimensions & scale
    // ---------------------------------------------------------------------
    let width = 980, height = 600; // SVG logical size; scaled by CSS
    const margin = { top: 28, right: 28, bottom: 42, left: 58 };
    const innerW = () => width - margin.left - margin.right;
    const innerH = () => height - margin.top - margin.bottom;

    // Scene 1: year scales
    let xYear, yCount;
    function computeYearScales() {
        if (!yearCounts.length) return;
        const years = yearCounts.map(d => d.year);
        const cmax = max(yearCounts, d => d.count) || 1;
        xYear = scaleLinear().domain([Math.min(...years), Math.max(...years)]).range([0, innerW()]);
        yCount = scaleLinear().domain([0, cmax]).nice().range([innerH(), 0]);
    }

    // Scene 2: heatmap scales
    const hours = Array.from({ length: 24 }, (_, i) => i);
    const months = Array.from({ length: 12 }, (_, i) => i);
    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    let xHourBand = scaleBand().domain(hours).range([0, innerW()]).padding(0.05);
    let yMonthBand = scaleBand().domain(months).range([0, innerH()]).padding(0.08);
    let heatMax = 1;
    function computeHeatScales() {
        if (!monthHour.length) return;
        heatMax = 1;
        for (let m=0;m<12;m++) for (let h=0;h<24;h++) heatMax = Math.max(heatMax, monthHour[m][h]);
    }
    function heatColor(v) {
        // Dark-mode ramp: deep navy → bright cyan
        const t = Math.sqrt(Math.min(1, v / heatMax));
        return interpolate('#0b1220', '#22d3ee')(t);
    }

    // Scene 3: map color scaling
    let mapMax = 1;
    function computeMapMax() {
        mapMax = 1;
        for (const b of gridBins) mapMax = Math.max(mapMax, b.count);
    }
    function mapColor(v) {
        const t = Math.sqrt(Math.min(1, v / mapMax));
        return interpolate('#0b1220', '#22d3ee')(t);
    }

    // Scene 4: small multiples Y scale (per panel)
    function shapeYScale(series) {
        const ymax = max(series, d=>d.count) || 1;
        return scaleLinear().domain([0, ymax]).nice().range([smallH, 0]);
    }

    // Scene 5: ECDF scales
    const durMin = 1, durMax = 4 * 3600;
    let xDur = scaleLog().domain([durMin, durMax]).range([0, innerW()]).clamp(true);
    let yECDF = scaleLinear().domain([0,1]).range([innerH(), 0]);

    // Animation Sec
    // ---------------------------------------------------------------------
    const sceneTweens = Array.from({length:8}, (_,i)=> tweened(i===0?1:0, { duration: 450, easing: cubicInOut }));
    let s = $state(Array(8).fill(0)); // array of current opacities for scenes
    const unsubs = sceneTweens.map((tw, i) => tw.subscribe(v => s[i] = v));

    // Scene 1 clip reveal tween target → mirrored to plain var via $state
    const clipW = tweened(0, { duration: 900, easing: cubicInOut });
    let clipWidth = $state(0);
    const unsubClip = clipW.subscribe(v => clipWidth = v);

    // Scene 2 heat opacity tween
    const heatOpacity = tweened(0, { duration: 600, easing: cubicInOut });
    let heatA = $state(0);
    const unsubHeat = heatOpacity.subscribe(v => heatA = v);

    // Scene 0 counter tween
    const counter = tweened(0, { duration: 800, easing: cubicInOut });
    let countVal = $state(0);
    const unsubC = counter.subscribe(v => countVal = Math.round(v));

    onDestroy(() => {
        unsubs.forEach(u=>u());
        unsubClip(); unsubHeat(); unsubC();
        if (observer) observer.disconnect();
    });

    function retargetSceneTweens() {
        computeYearScales();
        computeHeatScales();
        computeMapMax();

        // Dark mode spec: hide non-active scenes completely
        for (let i=0;i<8;i++) sceneTweens[i].set(i === value ? 1 : 0);

        if (value === 0) {
            if (totalReports) counter.set(totalReports, { duration: 900 });
            clipW.set(0);
            heatOpacity.set(0);
        } else if (value === 1) {
            if (yearCounts.length) clipW.set(innerW());
            heatOpacity.set(0);
        } else if (value === 2) {
            heatOpacity.set(1);
        }
    }

    // ---------------------------------------------------------------------
    // Misc helpers
    // ---------------------------------------------------------------------
    const fmtInt = (n) => n?.toLocaleString?.('en-US') ?? '—';
    const fmtMinSec = (s) => {
        if (!s || !Number.isFinite(s)) return '—';
        const m = Math.floor(s/60), r = Math.round(s%60);
        if (m===0) return `${r}s`; if (r===0) return `${m}m`; return `${m}m ${r}s`;
    };

    // Small-multiples layout
    const smallCols = 1;
    const smallW = () => (innerW() - 24) / smallCols;
    const smallH = 120;
</script>

<div class="container">
    <!-- Sticky graphic area -->
    <div class="sticky">
        <svg {width} {height} role="img" aria-label="UFO scrollytelling visuals">
            <defs>
                <clipPath id="scene1Clip">
                    <rect x={0} y={0} width={clipWidth} height={innerH()} />
                </clipPath>
            </defs>
            <g transform={`translate(${margin.left},${margin.top})`}>

                <!-- Scene 0 -->
                <g style={`opacity:${s[0]}`}> 
                    <text x={innerW()/2} y={34} text-anchor="middle" class="kpi">
                        {fmtInt(countVal)} reports
                    </text>
                    <g transform="translate(0,60)">
                        {#if yearCounts.length}
                            {#key yearCounts}
                                <g>
                                    <g transform="translate(0,0)">
                                        <text class="mini-title" x={0} y={-8}>per year</text>
                                        <svg class="spark" width={innerW()/3 - 12} height={70} viewBox={`0 0 ${innerW()/3 - 12} 70`}>
                                            <polyline fill="none" stroke="var(--ink)" stroke-width="1.5"
                                                points={sparkPoints(yearCounts, 'year', 'count', innerW()/3 - 12, 70)} />
                                        </svg>
                                    </g>
                                    <g transform={`translate(0,${innerH()/3})`}>
                                        <text class="mini-title" x={0} y={-8}>by month</text>
                                        <svg class="spark" width={innerW()/3 - 12} height={70} viewBox={`0 0 ${innerW()/3 - 12} 70`}>
                                            <polyline fill="none" stroke="var(--ink)" stroke-width="1.5"
                                                points={sparkPoints(monthTotals.map((c,i)=>({x:i+1,y:c})), 'x', 'y', innerW()/3 - 12, 70, [1,12])} />
                                        </svg>
                                    </g>
                                    <g transform={`translate(0,${2*innerH()/3})`}>
                                        <text class="mini-title" x={0} y={-8}>by hour</text>
                                        <svg class="spark" width={innerW()/3 - 12} height={70} viewBox={`0 0 ${innerW()/3 - 12} 70`}>
                                            <polyline fill="none" stroke="var(--ink)" stroke-width="1.5"
                                                points={sparkPoints(hourTotals.map((c,i)=>({x:i,y:c})), 'x', 'y', innerW()/3 - 12, 70, [0,23])} />
                                        </svg>
                                    </g>
                                </g>
                            {/key}
                        {/if}
                    </g>
                </g>

                <!-- Scene 1-->
                <g style={`opacity:${s[1]}`}> 
                    {#if yearCounts.length}
                        {#key yearCounts}
                        <g>
                            <g transform="translate(0,0)">
                                <g class="axis">
                                    <!-- clearer axes -->
                                    <line class="axis-line" x1={0} y1={innerH()} x2={innerW()} y2={innerH()} />
                                    <line class="axis-line" x1={0} y1={0} x2={0} y2={innerH()} />
                                    <text x={0} y={innerH()+28} class="axis-label">Year</text>
                                    <text x={-40} y={-10} class="axis-label" transform="rotate(-90)">Reports</text>
                                </g>
                                <g clip-path="url(#scene1Clip)">
                                    <polyline
                                        fill="none" stroke="var(--ink)" stroke-width="2"
                                        points={yearCounts.map(d=>`${xYear?.(d.year)},${yCount?.(d.count)}`).join(' ')}
                                    />
                                    <polygon
                                        fill="var(--ink)" fill-opacity="0.15"
                                        points={`0,${innerH()} ` + yearCounts.map(d=>`${xYear?.(d.year)},${yCount?.(d.count)}`).join(' ') + ` ${innerW()},${innerH()}`}
                                    />
                                </g>
                            </g>
                        </g>
                        {/key}
                    {/if}
                </g>

                <!-- Scene 2: Month -->
                <g style={`opacity:${s[2]}`}> 
                    {#if monthHour.length}
                        <g>
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
                            <!-- left month labels -->
                            {#each months as m}
                                <text class="tick" x={-8} y={yMonthBand(m)+yMonthBand.bandwidth()/2} text-anchor="end" dominant-baseline="middle">{monthNames[m]}</text>
                            {/each}
                            <!-- bottom hour labels -->
                            {#each hours as h}
                                {#if h % 3 === 0}
                                    <text class="tick" x={xHourBand(h)+xHourBand.bandwidth()/2} y={innerH()+18} text-anchor="middle">{h}</text>
                                {/if}
                            {/each}
                            <!-- border box to clarify axes bounds -->
                            <rect class="axis-border" x={0} y={0} width={innerW()} height={innerH()} fill="none" />
                        </g>
                    {/if}
                </g>

                <!-- Scene 3 top states -->
                <g style={`opacity:${s[3]}`}> 
                    {#if gridBins.length}
                        <g>
                            {#each gridBins as b}
                                <rect
                                    x={projX(b.lon) - cellW()}
                                    y={projY(b.lat) - cellH()}
                                    width={cellW()*2}
                                    height={cellH()*2}
                                    fill={mapColor(b.count)}
                                    opacity={0.95}
                                    rx="1" ry="1"
                                    transform={'scale(3)'}
                                />
                            {/each}
                            {#each stateCountsUS.slice(0,6) as sU, i}
                                <text class="mini-title" x={8} y={14 + i*14}>{sU.state}: {fmtInt(sU.count)}</text>
                            {/each}
                        </g>
                    {/if}
                </g>

                <!-- Scene 4 Shapes -->
                <g style={`opacity:${s[4]}`}> 
                    {#if Object.keys(shapeTrends).length}
                        <g>
                            {#each shapeTopK as shape, i}
                                {@const col = i % smallCols}
                                {@const row = Math.floor(i / smallCols)}
                                {@const x0 = col * (smallW() + 12)}
                                {@const y0 = row * (smallH + 28)}
                                {@const series = shapeTrends[shape] || []}
                                <g transform={`translate(${x0},${y0})`}>
                                    <text class="mini-title" x={0} y={-6}>{shape}</text>
                                    {#if series.length}
                                        <polyline fill="none" stroke="var(--ink)" stroke-opacity="0.9" stroke-width="1.6"
                                            points={smallTrendPoints(series)} />
                                        <line x1={0} y1={smallH} x2={smallW()} y2={smallH} stroke="var(--gridline)" stroke-width="1" />
                                    {/if}
                                </g>
                            {/each}
                        </g>
                    {/if}
                </g>

                <!-- Scene 5 -->
                <g style={`opacity:${s[5]}`}> 
                    {#if ecdf.length}
                        <g>
                            <g class="axis">
                                <line class="axis-line" x1={0} y1={innerH()} x2={innerW()} y2={innerH()} />
                                <line class="axis-line" x1={0} y1={0} x2={0} y2={innerH()} />
                            </g>
                            <polyline fill="none" stroke="var(--ink)" stroke-width="2"
                                points={ecdf.map(d=>`${xDur(d.xSec)},${yECDF(d.p)}`).join(' ')}
                            />
                            <g>
                                {#if durQuantiles.p50 != null}<line x1={xDur(durQuantiles.p50)} y1={0} x2={xDur(durQuantiles.p50)} y2={innerH()} stroke="var(--gridline)" stroke-dasharray="4,4" />{/if}
                                {#if durQuantiles.p75 != null}<line x1={xDur(durQuantiles.p75)} y1={0} x2={xDur(durQuantiles.p75)} y2={innerH()} stroke="var(--gridline)" stroke-dasharray="4,4" />{/if}
                                {#if durQuantiles.p90 != null}<line x1={xDur(durQuantiles.p90)} y1={0} x2={xDur(durQuantiles.p90)} y2={innerH()} stroke="var(--gridline)" stroke-dasharray="4,4" />{/if}
                                {#if durQuantiles.p99 != null}<line x1={xDur(durQuantiles.p99)} y1={0} x2={xDur(durQuantiles.p99)} y2={innerH()} stroke="var(--gridline)" stroke-dasharray="4,4" />{/if}
                                {#if durQuantiles.p50 != null}<text class="tick" x={xDur(durQuantiles.p50)} y={-6} text-anchor="middle">50% ≈ {fmtMinSec(durQuantiles.p50)}</text>{/if}
                                {#if durQuantiles.p75 != null}<text class="tick" x={xDur(durQuantiles.p75)} y={-6} text-anchor="middle">75% ≈ {fmtMinSec(durQuantiles.p75)}</text>{/if}
                                {#if durQuantiles.p90 != null}<text class="tick" x={xDur(durQuantiles.p90)} y={-6} text-anchor="middle">90% ≈ {fmtMinSec(durQuantiles.p90)}</text>{/if}
                                {#if durQuantiles.p99 != null}<text class="tick" x={xDur(durQuantiles.p99)} y={-6} text-anchor="middle">99% ≈ {fmtMinSec(durQuantiles.p99)}</text>{/if}
                            </g>
                            <text class="axis-label" x={innerW()/2} y={innerH()+28} text-anchor="middle">Duration (log scale, seconds)</text>
                            <text class="axis-label" x={-40} y={-10} transform="rotate(-90)">Fraction of sightings</text>
                        </g>
                    {/if}
                </g>

                <!-- Scene 6: commentary -->
                <g style={`opacity:${s[6]}`}> 
                    {#if comments.length}
                        <g>
                            {#each comments as c, i}
                                {@const y = i * 86}
                                <g transform={`translate(0,${y})`}>
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

                <!-- Scene 7 -->
                <g style={`opacity:${s[7]}`}> 
                    <g>
                        <text class="finale-title" x={innerW()/2} y={40} text-anchor="middle">So, what does this mean?</text>
                        <foreignObject x="0" y="70" width={innerW()} height={innerH()-70}>
                            <div xmlns="http://www.w3.org/1999/xhtml" class="finale">
                                <ul>
                                    <li><strong>Self-reported data.</strong> Peaks reflect reporting behavior as much as phenomena (internet era, media cycles).</li>
                                    <li><strong>Human rhythms.</strong> Summer nights dominate; people outside looking up.</li>
                                    <li><strong>Descriptions evolve.</strong> “Light” is evergreen; “fireball/triangle” surge later.</li>
                                    <li><strong>Most sightings are brief.</strong> Minutes, not hours.</li>
                                </ul>
                                <p class="fine">Dataset: UFO reports (1906–2014). Counts compressed visually for clarity. This is pattern-finding, not proof.</p>
                            </div>
                        </foreignObject>
                    </g>
                </g>

            </g>
        </svg>
    </div>

    <!-- Stepping -->
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
    :global(:root){
        --bg: #0b0f10;
        --fg: #f8fafc;
        --muted: #94a3b8;
        --ink: #22d3ee;        /* primary accent (cyan) */
        --card-bg: #111827;     /* slate-900 */
        --card-border: #334155; /* slate-700 */
        --axis: #e2e8f0;        /* light text for labels */
        --tick: #cbd5e1;        /* lighter ticks */
        --chip: #f1f5f9;
        --comment: #e2e8f0;
        --finale-fg: #f8fafc;
        --gridline: #334155;    /* subtle grid/guide lines */
        --axis-line: #cbd5e1;   /* stronger axis baseline */
        --shadow: rgba(0,0,0,.6);
    }

    :global(body){
        background: var(--bg);
        color: var(--fg);
    }

    .container{ display:flex; gap:2rem; align-items:flex-start; background:var(--bg); color:var(--fg); }
    .sticky{ position:sticky; top:1.25rem; flex:1 1 60%; }
    .scrolly{ flex:1 1 40%; }
    .steps{ position:relative; }
    .step{ min-height:65vh; display:flex; align-items:center; opacity:.6; transition:opacity .2s ease; }
    .step.active{ opacity:1; }
    .step-content{ background:var(--card-bg); border:1px solid var(--card-border); border-radius:12px; padding:1rem 1.25rem; box-shadow:0 2px 8px var(--shadow); }
    .spacer{ height:35vh; }

    .kpi{ font: 700 28px/1.2 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; fill:var(--fg); }
    .mini-title{ font: 600 11px/1 system-ui, sans-serif; fill:var(--axis); }
    .tick{ font: 11px/1 system-ui, sans-serif; fill:var(--tick); }
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

    svg{ width:100%; height:auto; max-height:80vh; background:var(--bg); }
    .spark{ width:100%; height:auto; }

    /* Axis visuals */
    .axis-label{ font: 12px/1 system-ui, sans-serif; fill: var(--axis); }
    .axis-line{ stroke: var(--axis-line); stroke-width: 1.25; shape-rendering: crispEdges; }
    .axis-border{ stroke: var(--axis-line); stroke-width: 1; shape-rendering: crispEdges; }

    @media (max-width: 980px){
        .container{ flex-direction:column-reverse; }
        .sticky{ width:96%; margin:0 auto; }
    }

    @media (prefers-reduced-motion: reduce){
        *{ transition:none !important; }
    }
</style>
