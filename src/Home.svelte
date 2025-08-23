<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';

  let chartContainer;
  let svg, g;
  let width = 900;
  let height = 500;
  let margin = { top: 100, right: 30, bottom: 60, left: 100 };
  
  let allData = [];
  let dataLoaded = false;

  let data = [];
  
  let currentYearIndex = 0;
  let xScale, yScale, line, xAxis, yAxis;
  let path, dots, markers;
  let currentYear = 1940;
  let currentCount = 0;

  const historicalMarkers = [
    {
      label: 'Kenneth Arnold sighting (Jun 24, 1947)\n"flying saucers" enters pop culture',
      showAt: 1946.5,
      yHint: 'auto'
    },
    {
      label: 'Project Blue Book begins (1952)\nGovernment UFO investigation',
      showAt: 1952,
      yHint: 'auto'
    },
    {
      label: 'Betty & Barney Hill abduction (1961)\nFirst widely publicized case',
      showAt: 1961,
      yHint: 'auto'
    },
    {
      label: 'Project Blue Book ends (1969)\nGovernment concludes no evidence for alien UFOs',
      showAt: 1969,
      yHint: 'auto'
    },
    {
      label: 'Close Encounters film (1977)\nMainstream UFO interest',
      showAt: 1977,
      yHint: 'auto'
    },
    {
      label: 'X-Files premieres (1993)\nPop culture phenomenon',
      showAt: 1993,
      yHint: -40 
    },
    {
      label: 'Internet boom (late 1990s)\nEasy reporting & sharing',
      showAt: 1995,
      yHint: -10  
    },
    {
      label: 'Government file releases (2007-2010)\nUK, France declassify UFO documents',
      showAt: 2007,
      yHint: -35  
    },
    {
      label: 'Smartphone + YouTube era (2008-2011)\nInstant UFO video sharing explodes',
      showAt: 2008.5,
      yHint: -5  
    }
  ];

  onMount(async () => {
    await loadData();
    if (dataLoaded) {
      initChart();
      setupScrollListener();
    }
  });

  async function loadData() {
    try {
      const res = await fetch('/data/ufo_year_counts_all.json');
      if (!res.ok) throw new Error('fetch failed');
      allData = await res.json();
      
      // Filter data starting from 1940
      data = allData.filter(d => d.year >= 1940);
      
      if (data.length > 0) {
        currentYear = data[0].year;
        currentCount = data[0].count;
        dataLoaded = true;
      } else {
        console.error('No data found for years >= 1940');
      }
    } catch (error) {
      console.error('Error loading data:', error);
      // Fallback to hardcoded data if file loading fails
      allData = [
        { year: 1940, count: 0 }, { year: 1941, count: 1 }, { year: 1942, count: 2 }, 
        { year: 1943, count: 9 }, { year: 1944, count: 9 }, { year: 1945, count: 9 },
        { year: 1946, count: 10 }, { year: 1947, count: 37 }
      ];
      data = allData;
      currentYear = data[0].year;
      currentCount = data[0].count;
      dataLoaded = true;
    }
  }
  

  function initChart() {
    svg = d3.select(chartContainer)
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    g = svg.append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    updateScales();

    line = d3.line()
      .x(d => xScale(d.year))
      .y(d => yScale(d.count))
      .curve(d3.curveMonotoneX);

    xAxis = g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${height - margin.top - margin.bottom})`);

    yAxis = g.append('g')
      .attr('class', 'y-axis');

    svg.append('text')
      .attr('class', 'y-label')
      .attr('transform', 'rotate(-90)')
      .attr('y', 0 + margin.left - 60)
      .attr('x', 0 - (height / 2))
      .attr('dy', '1em')
      .style('text-anchor', 'middle')
      .style('font-size', '14px')
      .style('font-weight', 'bold')
      .style('fill', 'white')
      .text('Number of UFO Sightings');

    svg.append('text')
      .attr('class', 'x-label')
      .attr('transform', `translate(${width / 2}, ${height - 10})`)
      .style('text-anchor', 'middle')
      .style('font-size', '14px')
      .style('font-weight', 'bold')
      .style('fill', 'white')
      .text('Year');

    svg.append('text')
      .attr('class', 'title')
      .attr('x', width / 2)
      .attr('y', 30)
      .attr('text-anchor', 'middle')
      .style('font-size', '20px')
      .style('font-weight', 'bold')
      .style('fill', 'white');

    svg.append('text')
      .attr('class', 'current-year')
      .attr('x', width / 2)
      .attr('y', 50)
      .attr('text-anchor', 'middle')
      .style('font-size', '16px')
      .style('font-weight', 'normal')
      .style('fill', '#666');

    markers = g.append('g').attr('class', 'markers');

    path = g.append('path')
      .attr('class', 'line')
      .style('fill', 'none')
      .style('stroke', '#4CAF50')
      .style('stroke-width', 3);

    dots = g.append('g').attr('class', 'dots');

    svg.append('text')
      .attr('x', width - 20)
      .attr('y', height - 10)
      .attr('text-anchor', 'end')
      .style('font-size', '12px')
      .style('fill', '#999')
      .style('font-style', 'italic')
      .text('Scroll to advance through years');

    updateChart();
  }

  function updateScales() {
    const currentData = data.slice(0, currentYearIndex + 1);
    
    const startYear = 1940;
    const endYear = currentYear;
    
    xScale = d3.scaleLinear()
      .domain([startYear, endYear])
      .range([0, width - margin.left - margin.right]);

    const maxCount = Math.max(50, d3.max(currentData, d => d.count) * 1.1);
    
    yScale = d3.scaleLinear()
      .domain([0, maxCount])
      .range([height - margin.top - margin.bottom, 0]);
  }

  function updateMarkers() {
    const visibleMarkers = historicalMarkers.filter(marker => {
      return marker.showAt <= currentYear && (currentYear - marker.showAt) <= 15; // Fade after 15 years
    });

    const markerGroups = markers.selectAll('.marker-group')
      .data(visibleMarkers, d => d.showAt);

    markerGroups.exit()
      .transition()
      .duration(300)
      .style('opacity', 0)
      .remove();

    const enterGroups = markerGroups.enter()
      .append('g')
      .attr('class', 'marker-group')
      .style('opacity', 0);

    enterGroups.append('line')
      .attr('class', 'marker-line')
      .attr('x1', d => xScale(d.showAt))
      .attr('x2', d => xScale(d.showAt))
      .attr('y1', 0)
      .attr('y2', height - margin.top - margin.bottom)
      .style('stroke', '#ff6b6b')
      .style('stroke-width', 2)
      .style('stroke-dasharray', '5,5')
      .style('opacity', 0.7);

    enterGroups.each(function(d) {
      const group = d3.select(this);
      const lines = d.label.split('\n');
      const baseY = d.yHint === 'auto' ? -15 : d.yHint;
      
      lines.forEach((line, i) => {
        group.append('text')
          .attr('class', `marker-label-line marker-label-line-${i}`)
          .attr('x', xScale(d.showAt))
          .attr('y', baseY - (i * 12))
          .attr('text-anchor', 'middle')
          .style('font-size', i === 0 ? '10px' : '9px')
          .style('font-weight', i === 0 ? 'bold' : 'normal')
          .style('fill', i === 0 ? '#ff6b6b' : '#ffaa88')
          .text(line);
      });
    });

    enterGroups.append('circle')
      .attr('class', 'marker-dot')
      .attr('cx', d => xScale(d.showAt))
      .attr('cy', 0)
      .attr('r', 3)
      .style('fill', '#ff6b6b')
      .style('stroke', 'white')
      .style('stroke-width', 1);

    const allMarkers = markerGroups.merge(enterGroups);
    
    allMarkers.transition()
      .duration(300)
      .style('opacity', d => {
        const age = currentYear - d.showAt;
        if (age <= 3) return 1; 
        if (age <= 8) return 0.7; 
        return 0.4;
      });

    allMarkers.select('.marker-line')
      .transition()
      .duration(300)
      .attr('x1', d => xScale(d.showAt))
      .attr('x2', d => xScale(d.showAt));

    allMarkers.selectAll('.marker-label-line')
      .transition()
      .duration(300)
      .attr('x', d => xScale(d.showAt));

    allMarkers.select('.marker-dot')
      .transition()
      .duration(300)
      .attr('cx', d => xScale(d.showAt));

    enterGroups.transition()
      .delay(200)
      .duration(400)
      .style('opacity', 1);
  }

  function updateChart() {
    const currentData = data.slice(0, currentYearIndex + 1);
    
    updateScales();

    dots.selectAll('.dot')
      .transition()
      .duration(100)
      .style('opacity', 0);

    xAxis.transition()
      .duration(300)
      .call(d3.axisBottom(xScale).tickFormat(d3.format('d')));

    yAxis.transition()
      .duration(300)
      .call(d3.axisLeft(yScale));

    updateMarkers();

    line.x(d => xScale(d.year)).y(d => yScale(d.count));
    
    path.datum(currentData)
      .transition()
      .duration(300)
      .attr('d', line);

    setTimeout(() => {
      const dotSelection = dots.selectAll('.dot')
        .data(currentData, d => d.year);

      dotSelection.exit().remove();

      dotSelection.enter()
        .append('circle')
        .attr('class', 'dot')
        .attr('cx', d => xScale(d.year))
        .attr('cy', d => yScale(d.count))
        .attr('r', d => d.year === currentYear ? 6 : 4)
        .style('fill', d => d.year === currentYear ? '#FF5722' : '#2196F3')
        .style('stroke', 'white')
        .style('stroke-width', 2)
        .style('opacity', 0);

      dots.selectAll('.dot')
        .transition()
        .duration(200)
        .attr('cx', d => xScale(d.year))
        .attr('cy', d => yScale(d.count))
        .attr('r', d => d.year === currentYear ? 6 : 4)
        .style('fill', d => d.year === currentYear ? '#FF5722' : '#2196F3')
        .style('opacity', 1);
    }, 150);

    svg.select('.title')
      .text(`UFO Sightings: ${currentYear}`);
    
    svg.select('.current-year')
      .text(`${currentCount} sightings reported`);
  }

  function setupScrollListener() {
    let isScrolling = false;
    
    const handleScroll = (event) => {
      event.preventDefault();
      
      if (isScrolling) return;
      isScrolling = true;
      
      const oldIndex = currentYearIndex;
      
      if (event.deltaY > 0 && currentYearIndex < data.length - 1) {
        currentYearIndex++;
      } else if (event.deltaY < 0 && currentYearIndex > 0) {
        currentYearIndex--;
      }
      
      if (oldIndex !== currentYearIndex) {
        currentYear = data[currentYearIndex].year;
        currentCount = data[currentYearIndex].count;
        updateChart();
      }
      
      setTimeout(() => {
        isScrolling = false;
      }, 350);
    };

    chartContainer.addEventListener('wheel', handleScroll, { passive: false });
  }

  function resetToStart() {
    currentYearIndex = 0;
    currentYear = data[0].year;
    currentCount = data[0].count;
    updateChart();
  }

  function jumpToEnd() {
    currentYearIndex = data.length - 1;
    currentYear = data[currentYearIndex].year;
    currentCount = data[currentYearIndex].count;
    updateChart();
  }
</script>

<div class="chart-wrapper">
  <div class="controls">
    <div class="control-buttons">
      <button on:click={resetToStart} class="control-btn">Start (1940)</button>
      <button on:click={jumpToEnd} class="control-btn">End (2014)</button>
    </div>
    <div class="progress">
      <div class="progress-text">
        Year {currentYearIndex + 1} of {data.length}
      </div>
      <div class="progress-bar">
        <div class="progress-fill" style="width: {((currentYearIndex) / (data.length - 1)) * 100}%"></div>
      </div>
    </div>
  </div>
  <div bind:this={chartContainer} class="chart-container">
    {#if !dataLoaded}
      <div class="loading">
        <div class="loading-spinner"></div>
        <p>Loading UFO sightings data...</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .chart-wrapper {
    font-family: 'Arial', sans-serif;
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.8);
    color: white;
    border: 1px solid #333;
    height : 80%;

  }

  .controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 15px;
  }

  .control-buttons {
    display: flex;
    gap: 10px;
  }

  .control-btn {
    background: rgba(255,255,255,0.1);
    color: white;
    border: 1px solid rgba(255,255,255,0.2);
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.3s;
    backdrop-filter: blur(10px);
  }

  .control-btn:hover {
    background: rgba(255,255,255,0.2);
    border-color: rgba(255,255,255,0.4);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }

  .progress {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .progress-text {
    font-size: 12px;
    white-space: nowrap;
    color: #ccc;
  }

  .progress-bar {
    width: 200px;
    height: 6px;
    background: rgba(255,255,255,0.1);
    border-radius: 3px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.1);
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #00ff88, #00cc66);
    transition: width 0.3s ease;
    box-shadow: 0 0 10px rgba(0,255,136,0.3);
  }

  .chart-container {
    background: #0a0a0a;
    border-radius: 8px;
    box-shadow: inset 0 2px 10px rgba(0,0,0,0.8);
    cursor: grab;
    border: 1px solid #333;
  }

  .chart-container:active {
    cursor: grabbing;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 400px;
    color: #ccc;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #333;
    border-top: 3px solid #00ff88;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 15px;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  :global(.x-axis text, .y-axis text) {
    font-size: 11px;
    fill: #555;
    font-weight: 500;
  }

  :global(.x-axis .domain, .y-axis .domain) {
    stroke: #333;
    stroke-width: 1;
  }

  :global(.x-axis .tick line, .y-axis .tick line) {
    stroke: #ddd;
  }

  :global(.line) {
    filter: drop-shadow(0 2px 4px rgba(76, 175, 80, 0.3));
  }

  :global(.dot) {
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
    transition: all 0.3s ease;
  }

  :global(.marker-dot) {
    filter: drop-shadow(0 1px 3px rgba(255, 107, 107, 0.4));
  }

  :global(.marker-label-line) {
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.8));
  }

  @media (max-width: 768px) {
    .controls {
      flex-direction: column;
      align-items: stretch;
    }
    
    .progress {
      justify-content: center;
    }
    
    .progress-bar {
      width: 150px;
    }
  }
</style>