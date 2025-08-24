<script>
    import {currentYear} from "./stores/currentYear"
    import {csv} from "d3-fetch"
    import { tweened } from "svelte/motion";
    import { cubicOut } from "svelte/easing";
    // import { shapeTweens } from './stores/shapeTweens'

    let dataByYear = $state({});
    let topShapes = $state([]);
    let topStates = $state([]);
    let cumulativeData = $state({});
    let barOption = $state("year");

    // tweened values (one per shape) top 3 shapes
    const tweenShape1 = tweened(0, {
                        duration : 800,
                        easing : cubicOut
    });
    const tweenShape2 = tweened(0, {
                        duration : 800,
                        easing : cubicOut
    });
    const tweenShape3 = tweened(0, {
                        duration : 800,
                        easing : cubicOut
    });


    // now for states
    const tweenState1 = tweened(0, {
                        duration : 800,
                        easing : cubicOut
    });
    const tweenState2 = tweened(0, {
                        duration : 800,
                        easing : cubicOut
    });
    const tweenState3 = tweened(0, {
                        duration : 800,
                        easing : cubicOut
    });

    async function loadData() {
        const raw = await csv("/data/scrubbed.csv");

        // parse year from datetime
        raw.forEach(d => {
            d.year = new Date(d.datetime).getFullYear();
        });

        const byYear = {};


        for (const row of raw) {
            const year = row.year;
            if (!byYear[year]) {
                byYear[year] = {shapes : {}, states : {}, total : 0};
            }


            const shape = row.shape || 'unknown';
            byYear[year].shapes[shape] =(byYear[year].shapes[shape] || 0) + 1;
            
            // increment state count
            const state = row.state || 'unknown';
            byYear[year].states[state] = (byYear[year].states[state] || 0) + 1;
            
            
            // increment total
            byYear[year].total++;

            
        }


        const years = Object.keys(byYear).sort((a, b) => (+a) - (+b));

        let forCumulative = {};
        let cumulativeShapes = {};
        let cumulativeStates = {};
        let cumulativeTotal = 0;

        for (const year of years) {
            forCumulative[year] = { shapes: {}, states: {}, total: 0 };

            for (const [shape, count] of Object.entries(byYear[year].shapes)) {
                cumulativeShapes[shape] = (cumulativeShapes[shape] || 0) + count;
            }

            forCumulative[year].shapes = { ...cumulativeShapes };

            // states
            for (const [state, count] of Object.entries(byYear[year].states)) {
                cumulativeStates[state] = (cumulativeStates[state] || 0) + count;
            }
            forCumulative[year].states = { ...cumulativeStates };

            // total
            cumulativeTotal += byYear[year].total;
            forCumulative[year].total = cumulativeTotal;
        }

        cumulativeData = forCumulative;
        dataByYear = byYear;
    }

    loadData();


    // reactive -- compute top 3 shapes for current year
    $effect(() => {

        // this really should've been a function call X|
        if (dataByYear[$currentYear] && barOption === "year") {
            const yearData = dataByYear[$currentYear];

            const entries = Object.entries(yearData.shapes).map(([shape, count]) => ({
                shape, 
                count,
                proportion : count / yearData.total
            })).sort((a, b) => b.count - a.count).slice(0, 3);


            topShapes = entries;


            // already sorted by max prop
            tweenShape1.set(entries[0].proportion * 100);
            tweenShape2.set(entries[1].proportion * 100);
            tweenShape3.set(entries[2].proportion * 100);


            const stateEntries = Object.entries(yearData.states).map(([state, count]) => ({
                state, 
                count,
                proportion : count / yearData.total
            })).sort((a, b) => b.count - a.count).slice(0, 3);


            topStates = stateEntries;

            tweenState1.set(entries[0].proportion * 100);
            tweenState2.set(entries[1].proportion * 100);
            tweenState3.set(entries[2].proportion * 100);

        }

        if (cumulativeData[$currentYear] && barOption === "cumulative") {
            const cumData = cumulativeData[$currentYear];

            const entries = Object.entries(cumData.shapes).map(([shape, count]) => ({
                shape, 
                count,
                proportion : count / cumData.total
            })).sort((a, b) => b.count - a.count).slice(0, 3);


            topShapes = entries;

            // already sorted by max prop
            tweenShape1.set(entries[0].proportion * 100);
            tweenShape2.set(entries[1].proportion * 100);
            tweenShape3.set(entries[2].proportion * 100);


            const stateEntries = Object.entries(cumData.states).map(([state, count]) => ({
                state, 
                count,
                proportion : count / cumData.total
            })).sort((a, b) => b.count - a.count).slice(0, 3);


            topStates = stateEntries;

            tweenState1.set(entries[0].proportion * 100);
            tweenState2.set(entries[1].proportion * 100);
            tweenState3.set(entries[2].proportion * 100);

        }
    })

</script>
  
<main>
    <div id="bar-graphs-card">
        <div id="bar-graphs-title">
            <h2 style={"margin-bottom : 0"}>
                Composition of Reports
            </h2>

            <p>{$currentYear}</p>
        </div>

        <div id="selector-container">
            <select bind:value={barOption} id="bar-option-selector">
                <option value="year">By Year</option>
                <option value="cumulative">Cumulative</option>
            </select>
        </div>

        <p class="bars-title">Shape of UFO</p>
        <div id="actual-bar-graphs">
            {#each topShapes as d, i}

                <div class="bar-row">
                    <div class="label">{d.shape}</div>
                    <div class="bar-container">
                        <svg viewBox="0 0 100 18" preserveAspectRatio="none">
                            <rect x="0" y="0" width="100" height="18" fill="rgba(255, 255, 255, 0.1)"/>
                            <rect x="0" y="0"
                                height="18"
                                
                                fill="url(#grad)"
                                width={(i === 0) ? $tweenShape1 : ((i === 1) ? $tweenShape2 : $tweenShape3)} 
                            />
                        </svg>
                    </div>
                    <div class="value">{(d.proportion * 100).toFixed(1)}%</div>
                </div>

            {/each}
            <svg width="0" height="0">
                <defs>
                    <linearGradient id="grad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#095904"/>
                    <stop offset="100%" stop-color="#59cf74"/>
                    </linearGradient>
                </defs>
            </svg>
        </div>



        <!-- NOW FOR THE states -->
        <p class="bars-title">State of Sighting</p>

        <div id="actual-bar-graphs">

            {#each topStates as d, i}

                <div class="bar-row">
                    <div class="label">{d.state.toLowerCase() === "unknown" ? "No State" : d.state.toUpperCase()}</div>
                    <div class="bar-container">
                        <svg viewBox="0 0 100 18" preserveAspectRatio="none">
                            <rect x="0" y="0" width="100" height="18" fill="rgba(255, 255, 255, 0.1)"/>
                            <rect x="0" y="0"
                                height="18"
                                
                                fill="url(#grad-state)"
                                width={(i === 0) ? $tweenState1 : ((i === 1) ? $tweenState2 : $tweenState3)} 
                            />
                        </svg>
                    </div>
                    <div class="value">{(d.proportion * 100).toFixed(1)}%</div>
                </div>

            {/each}
            <svg width="0" height="0">
                <defs>
                    <linearGradient id="grad-state" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#b50021"/>
                    <stop offset="100%" stop-color="#eb5468"/>
                    </linearGradient>
                </defs>
            </svg>
        </div>
    </div>
</main>
  
<style>
    main {
        height : 80%;
        width : 25%;

        margin : 0;
        padding : 0;

        font-family: 'Arial', sans-serif;
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.8);
        color: white;
        border: 1px solid #333;
    }

    #bar-graphs-card {
        

        height : 100%;
        width : 100%;

        display: flex;
        flex-direction: column;
        gap : 10px;

    }

    #selector-container {

    }


    #bar-option-selector {
        padding : 8px;
        padding-left: 10px;
        padding-right: 10px;
        border-radius: 20px;
    }

    #bar-graphs-title {
        display : "flex";
        flex-direction : "column";
        align-items : "center";
        gap : 0;
    }

    #actual-bar-graphs {
        border : 1px solid rgba(226, 226, 226, 0.3);
        border-radius: 10px;
        padding : 8px;

        display: flex;
        flex-direction: column;
        gap : 12px;

        padding-top: 20px;
    }

    .label {
        width: 70px;
        text-transform: capitalize;
        font-size: 14px;
        flex-shrink: 0;
    }

    .bar-container {
        flex: 1;
        height: 18px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        overflow: hidden;

        width : 50%;

        outline : 1px solid white;

    }

    .bars-title {
        width : 100%;
        text-align: start;
        margin-bottom: 0;
    }

    .bar-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        width : 100%;
    }

    .value {
        width: 50px;
        font-size: 12px;
        text-align: right;
        flex-shrink: 0;
    }

</style>