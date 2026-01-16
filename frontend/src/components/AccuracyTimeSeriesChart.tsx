import type { Component } from 'solid-js';
import { createEffect, onMount, onCleanup, Show } from 'solid-js';
import * as d3 from 'd3';

/** Chart data point with Date object */
export interface ChartDataPoint {
  date: Date;
  mae: number;
}

/** Model time series data for chart */
export interface ModelTimeSeries {
  modelId: number;
  modelName: string;
  color: string;
  data: ChartDataPoint[];
}

/**
 * Props for AccuracyTimeSeriesChart component.
 * DO NOT destructure - access via props.x for Solid.js reactivity.
 */
export interface AccuracyTimeSeriesChartProps {
  models: ModelTimeSeries[];
  parameterUnit: string;
}

/** Chart configuration */
const CHART_CONFIG = {
  marginDesktop: { top: 20, right: 120, bottom: 40, left: 60 },
  marginMobile: { top: 20, right: 90, bottom: 40, left: 45 },
  height: 400,
  mobileBreakpoint: 640,
  hoverLineColor: '#9ca3af',
  legendMaxChars: 12,
};

/**
 * Get responsive margins based on container width.
 */
function getResponsiveMargins(containerWidth: number) {
  return containerWidth < CHART_CONFIG.mobileBreakpoint
    ? CHART_CONFIG.marginMobile
    : CHART_CONFIG.marginDesktop;
}

/**
 * Truncate text to fit legend on mobile screens.
 */
function truncateForLegend(text: string, isMobile: boolean): string {
  if (!isMobile || text.length <= CHART_CONFIG.legendMaxChars) {
    return text;
  }
  return text.slice(0, CHART_CONFIG.legendMaxChars - 1) + '…';
}

/**
 * Escape HTML entities to prevent XSS attacks.
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/** Model color palette */
const MODEL_COLORS: Record<string, string> = {
  'AROME': '#2563eb',
  'Meteo-Parapente': '#dc2626',
};

const DEFAULT_COLORS = ['#2563eb', '#dc2626', '#16a34a', '#ca8a04', '#7c3aed', '#db2777'];

/**
 * Get color for a model.
 */
export function getModelColor(modelName: string, index: number): string {
  return MODEL_COLORS[modelName] || DEFAULT_COLORS[index % DEFAULT_COLORS.length];
}

/**
 * D3.js time series chart component for accuracy evolution.
 * Shows MAE over time for multiple models with interactive tooltip.
 */
const AccuracyTimeSeriesChart: Component<AccuracyTimeSeriesChartProps> = (props) => {
  let svgRef: SVGSVGElement | undefined;
  let tooltipRef: d3.Selection<HTMLDivElement, unknown, HTMLElement, unknown> | null = null;

  const drawChart = () => {
    if (!svgRef || props.models.length === 0) return;

    // Clear previous chart
    d3.select(svgRef).selectAll('*').remove();

    const containerWidth = svgRef.clientWidth;
    const isMobile = containerWidth < CHART_CONFIG.mobileBreakpoint;
    const margin = getResponsiveMargins(containerWidth);
    const width = containerWidth - margin.left - margin.right;
    const height = CHART_CONFIG.height - margin.top - margin.bottom;

    if (width <= 0 || height <= 0) return;

    const svg = d3.select(svgRef)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Combine all data points for domain calculation
    const allDates = props.models.flatMap(m => m.data.map(d => d.date));
    const allMae = props.models.flatMap(m => m.data.map(d => d.mae));

    if (allDates.length === 0) return;

    // Scales
    const xExtent = d3.extent(allDates) as [Date, Date];
    const xScale = d3.scaleTime()
      .domain(xExtent)
      .range([0, width]);

    const yMax = d3.max(allMae) || 10;
    const yScale = d3.scaleLinear()
      .domain([0, yMax * 1.1]) // Add 10% padding
      .nice()
      .range([height, 0]);

    // Grid lines
    svg.append('g')
      .attr('class', 'grid')
      .attr('opacity', 0.1)
      .call(
        d3.axisLeft(yScale)
          .tickSize(-width)
          .tickFormat(() => '')
      );

    // X Axis
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(
        d3.axisBottom(xScale)
          .ticks(6)
          .tickFormat((d: Date | d3.NumberValue) => d3.timeFormat('%b %d')(d as Date))
      )
      .selectAll('text')
      .attr('class', 'text-xs fill-gray-600');

    // Y Axis
    svg.append('g')
      .call(d3.axisLeft(yScale).ticks(6))
      .selectAll('text')
      .attr('class', 'text-xs fill-gray-600');

    // Y-axis label
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -margin.left + 15)
      .attr('x', -height / 2)
      .attr('text-anchor', 'middle')
      .attr('class', 'text-sm fill-gray-600')
      .text(`MAE (${props.parameterUnit})`);

    // Line generator
    const line = d3.line<ChartDataPoint>()
      .x((d: ChartDataPoint) => xScale(d.date))
      .y((d: ChartDataPoint) => yScale(d.mae))
      .curve(d3.curveMonotoneX);

    // Draw lines for each model
    props.models.forEach(model => {
      if (model.data.length === 0) return;

      svg.append('path')
        .datum(model.data)
        .attr('fill', 'none')
        .attr('stroke', model.color)
        .attr('stroke-width', 2)
        .attr('d', line);
    });

    // Legend
    const legendG = svg.append('g')
      .attr('transform', `translate(${width + 10}, 0)`);

    props.models.forEach((model, i) => {
      const legendY = i * 22;

      legendG.append('line')
        .attr('x1', 0)
        .attr('x2', 20)
        .attr('y1', legendY + 10)
        .attr('y2', legendY + 10)
        .attr('stroke', model.color)
        .attr('stroke-width', 2);

      legendG.append('text')
        .attr('x', 25)
        .attr('y', legendY + 14)
        .attr('class', 'text-xs fill-gray-700')
        .text(truncateForLegend(model.modelName, isMobile));
    });

    // Interactive overlay for tooltip
    const overlay = svg.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'transparent')
      .style('cursor', 'crosshair');

    // Vertical line for hover indicator
    const hoverLine = svg.append('line')
      .attr('stroke', CHART_CONFIG.hoverLineColor)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4')
      .attr('y1', 0)
      .attr('y2', height)
      .style('opacity', 0);

    overlay
      .on('mousemove', function(event: MouseEvent) {
        if (!tooltipRef) return;

        const [mx] = d3.pointer(event);
        const date = xScale.invert(mx);

        // Show hover line
        hoverLine
          .attr('x1', mx)
          .attr('x2', mx)
          .style('opacity', 1);

        // Find closest data points for each model
        const values = props.models.map(m => {
          if (m.data.length === 0) return null;

          const closest = m.data.reduce((prev, curr) =>
            Math.abs(curr.date.getTime() - date.getTime()) <
            Math.abs(prev.date.getTime() - date.getTime()) ? curr : prev
          );
          return { model: m, point: closest };
        }).filter(Boolean) as { model: ModelTimeSeries; point: ChartDataPoint }[];

        if (values.length === 0) return;

        // Escape user-provided data to prevent XSS
        const safeUnit = escapeHtml(props.parameterUnit);

        tooltipRef
          .style('opacity', '1')
          .style('left', `${event.pageX + 15}px`)
          .style('top', `${event.pageY - 10}px`)
          .html(`
            <div class="font-semibold mb-1 text-gray-900">${d3.timeFormat('%b %d, %Y')(date)}</div>
            ${values.map(v => {
              const safeName = escapeHtml(v.model.modelName);
              return `<div class="flex items-center gap-2">
                <span class="w-3 h-0.5 inline-block" style="background-color: ${v.model.color}"></span>
                <span style="color: ${v.model.color}">${safeName}:</span>
                <span class="font-medium">${v.point.mae.toFixed(1)} ${safeUnit}</span>
              </div>`;
            }).join('')}
          `);
      })
      .on('mouseout', () => {
        tooltipRef?.style('opacity', '0');
        hoverLine.style('opacity', 0);
      });
  };

  onMount(() => {
    // Create tooltip element
    tooltipRef = d3.select('body')
      .append('div')
      .attr('class', 'fixed bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm shadow-lg pointer-events-none z-50')
      .style('opacity', '0');

    // Initial draw
    drawChart();

    // Resize observer for responsiveness
    const observer = new ResizeObserver(() => {
      drawChart();
    });

    if (svgRef) {
      observer.observe(svgRef);
    }

    onCleanup(() => {
      observer.disconnect();
      tooltipRef?.remove();
    });
  });

  // Redraw when props change
  createEffect(() => {
    // Access props to track them (use void to suppress unused warnings)
    void props.models;
    void props.parameterUnit;
    drawChart();
  });

  return (
    <div class="bg-white rounded-lg shadow-sm">
      <h3 class="text-base md:text-lg font-semibold text-gray-900 p-4 md:p-6 pb-2">
        Accuracy Evolution Over Time
      </h3>

      {/* Empty state */}
      <Show when={props.models.length === 0}>
        <div class="p-6 pt-2">
          <div class="bg-gray-50 rounded-lg p-8 text-center">
            <p class="text-gray-500">No time series data available</p>
          </div>
        </div>
      </Show>

      {/* Chart */}
      <Show when={props.models.length > 0}>
        <div class="px-4 md:px-6 pb-4 md:pb-6">
          <svg
            ref={svgRef!}
            class="w-full"
            style={{ height: `${CHART_CONFIG.height}px` }}
            role="img"
            aria-label="Line chart showing model accuracy over time"
          />
        </div>
      </Show>
    </div>
  );
};

export default AccuracyTimeSeriesChart;
