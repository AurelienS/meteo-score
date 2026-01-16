# Story 4.5: Accuracy Time Series Chart (D3.js)

Status: ready-for-dev

## Story

As a user,
I want to see how model accuracy evolves over time,
So that I can understand if recent performance differs from historical trends.

## Acceptance Criteria

1. **AC1: AccuracyTimeSeriesChart Component** - D3.js-based line chart showing MAE over time
2. **AC2: Multi-model Support** - Display multiple colored lines (one per model)
3. **AC3: Interactive Tooltip** - Show values on hover with date and model MAE
4. **AC4: Axes and Labels** - Proper X (date) and Y (MAE) axes with labels
5. **AC5: Legend** - Model names with color indicators
6. **AC6: Responsive** - Resizes on window change, mobile-friendly
7. **AC7: Empty State** - Message when no time series data available
8. **AC8: API Integration** - Fetch time series data from backend
9. **AC9: TypeScript** - No compilation errors, proper typing

## Tasks / Subtasks

- [ ] Task 1: Add API types and fetch function (AC: 8, 9)
  - [ ] 1.1: Add `TimeSeriesDataPoint` interface to `frontend/src/lib/types.ts`
  - [ ] 1.2: Add `TimeSeriesAccuracyResponse` interface to `frontend/src/lib/types.ts`
  - [ ] 1.3: Add `fetchAccuracyTimeSeries(siteId, modelId, parameterId)` to `frontend/src/lib/api.ts`

- [ ] Task 2: Create AccuracyTimeSeriesChart component (AC: 1, 2, 4, 5, 7, 9)
  - [ ] 2.1: Create `frontend/src/components/AccuracyTimeSeriesChart.tsx`
  - [ ] 2.2: Define component props interface
  - [ ] 2.3: Set up SVG ref and D3 chart structure
  - [ ] 2.4: Implement scales (scaleTime, scaleLinear)
  - [ ] 2.5: Draw axes with proper formatting
  - [ ] 2.6: Draw multi-line chart with d3.line()
  - [ ] 2.7: Add legend at right side
  - [ ] 2.8: Add empty state handling

- [ ] Task 3: Add interactivity (AC: 3)
  - [ ] 3.1: Create tooltip div with positioning
  - [ ] 3.2: Add mousemove handler for hover detection
  - [ ] 3.3: Find closest data point to cursor
  - [ ] 3.4: Display tooltip with date and all model values
  - [ ] 3.5: Clean up tooltip on unmount

- [ ] Task 4: Make responsive (AC: 6)
  - [ ] 4.1: Use ResizeObserver or window resize listener
  - [ ] 4.2: Redraw chart on size change
  - [ ] 4.3: Adjust margins for mobile

- [ ] Task 5: Integrate into Home page (AC: 8)
  - [ ] 5.1: Import AccuracyTimeSeriesChart in Home.tsx
  - [ ] 5.2: Add time series signals and fetch logic
  - [ ] 5.3: Fetch data for each model when selections change
  - [ ] 5.4: Render chart below bias cards

- [ ] Task 6: Verification (AC: 9)
  - [ ] 6.1: Run `npm run type-check` - no errors
  - [ ] 6.2: Run `npm run lint` - no warnings
  - [ ] 6.3: Manual test with sample data

## Dev Notes

### Backend API Endpoint

**Endpoint:** `GET /api/v1/analysis/sites/{site_id}/accuracy/timeseries`

**Query Parameters:**
- `modelId` (required): Model identifier
- `parameterId` (required): Weather parameter identifier
- `granularity` (optional): "daily" | "weekly" | "monthly" (default: "daily")
- `startDate` (optional): Start of date range (ISO 8601)
- `endDate` (optional): End of date range (ISO 8601)

**Response Schema (camelCase JSON):**
```typescript
interface TimeSeriesAccuracyResponse {
  siteId: number;
  siteName: string;
  modelId: number;
  modelName: string;
  parameterId: number;
  parameterName: string;
  granularity: string;
  dataPoints: TimeSeriesDataPoint[];
}

interface TimeSeriesDataPoint {
  bucket: string;  // ISO 8601 date
  mae: number;
  bias: number;
  sampleSize: number;
}
```

**Note:** The API returns data for ONE model at a time. To show multiple models, make parallel requests for each model.

### D3.js Integration with Solid.js

**CRITICAL: D3 manages its own DOM inside the SVG ref. Do NOT mix Solid.js reactive rendering with D3.**

```tsx
// Correct pattern: Let D3 manage SVG internals
let svgRef: SVGSVGElement | undefined;

onMount(() => {
  drawChart();
});

// Redraw when data changes
createEffect(() => {
  // Access reactive props to track them
  const _ = props.models;
  drawChart();
});

const drawChart = () => {
  if (!svgRef) return;

  // Clear previous chart
  d3.select(svgRef).selectAll('*').remove();

  // Draw new chart...
};
```

### Chart Configuration

```typescript
const CHART_CONFIG = {
  margin: { top: 20, right: 120, bottom: 40, left: 60 },
  height: 400,
  colors: ['#2563eb', '#dc2626', '#16a34a', '#ca8a04'], // blue, red, green, yellow
};
```

### Model Colors

Assign consistent colors to models:
```typescript
const MODEL_COLORS: Record<string, string> = {
  'AROME': '#2563eb',       // blue
  'Meteo-Parapente': '#dc2626', // red
  'Default': '#6b7280',     // gray
};

function getModelColor(modelName: string, index: number): string {
  return MODEL_COLORS[modelName] || CHART_CONFIG.colors[index % CHART_CONFIG.colors.length];
}
```

### Data Transformation

Transform API responses into chart-ready format:
```typescript
interface ChartDataPoint {
  date: Date;
  mae: number;
}

interface ModelTimeSeries {
  modelId: number;
  modelName: string;
  color: string;
  data: ChartDataPoint[];
}

function transformApiResponse(
  response: TimeSeriesAccuracyResponse,
  color: string
): ModelTimeSeries {
  return {
    modelId: response.modelId,
    modelName: response.modelName,
    color,
    data: response.dataPoints.map(dp => ({
      date: new Date(dp.bucket),
      mae: dp.mae,
    })),
  };
}
```

### D3 Chart Structure

```tsx
const drawChart = () => {
  if (!svgRef || props.models.length === 0) return;

  // Clear
  d3.select(svgRef).selectAll('*').remove();

  const width = svgRef.clientWidth - margin.left - margin.right;
  const height = CHART_CONFIG.height - margin.top - margin.bottom;

  const svg = d3.select(svgRef)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  // Combine all data points for domain calculation
  const allDates = props.models.flatMap(m => m.data.map(d => d.date));
  const allMae = props.models.flatMap(m => m.data.map(d => d.mae));

  // Scales
  const xScale = d3.scaleTime()
    .domain(d3.extent(allDates) as [Date, Date])
    .range([0, width]);

  const yScale = d3.scaleLinear()
    .domain([0, d3.max(allMae) || 10])
    .nice()
    .range([height, 0]);

  // Axes
  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale).ticks(6).tickFormat(d3.timeFormat('%b %d')));

  svg.append('g')
    .call(d3.axisLeft(yScale).ticks(6));

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
    .x(d => xScale(d.date))
    .y(d => yScale(d.mae))
    .curve(d3.curveMonotoneX);

  // Draw lines
  props.models.forEach(model => {
    svg.append('path')
      .datum(model.data)
      .attr('fill', 'none')
      .attr('stroke', model.color)
      .attr('stroke-width', 2)
      .attr('d', line);
  });

  // Legend
  props.models.forEach((model, i) => {
    const legendY = i * 20;

    svg.append('line')
      .attr('x1', width + 10)
      .attr('x2', width + 30)
      .attr('y1', legendY + 10)
      .attr('y2', legendY + 10)
      .attr('stroke', model.color)
      .attr('stroke-width', 2);

    svg.append('text')
      .attr('x', width + 35)
      .attr('y', legendY + 14)
      .attr('class', 'text-xs fill-gray-700')
      .text(model.modelName);
  });
};
```

### Tooltip Implementation

```tsx
// Create tooltip once, outside of drawChart
let tooltip: d3.Selection<HTMLDivElement, unknown, HTMLElement, any> | null = null;

onMount(() => {
  tooltip = d3.select('body')
    .append('div')
    .attr('class', 'fixed bg-white border border-gray-300 rounded px-3 py-2 text-sm shadow-lg pointer-events-none opacity-0 z-50');
});

onCleanup(() => {
  tooltip?.remove();
});

// In drawChart, add overlay for mouse events
svg.append('rect')
  .attr('width', width)
  .attr('height', height)
  .attr('fill', 'transparent')
  .on('mousemove', function(event) {
    if (!tooltip) return;

    const [mx] = d3.pointer(event);
    const date = xScale.invert(mx);

    // Find closest data points for each model
    const values = props.models.map(m => {
      const closest = m.data.reduce((prev, curr) =>
        Math.abs(curr.date.getTime() - date.getTime()) <
        Math.abs(prev.date.getTime() - date.getTime()) ? curr : prev
      );
      return { model: m, point: closest };
    });

    tooltip
      .style('opacity', '1')
      .style('left', `${event.pageX + 15}px`)
      .style('top', `${event.pageY - 10}px`)
      .html(`
        <div class="font-semibold mb-1">${d3.timeFormat('%b %d, %Y')(date)}</div>
        ${values.map(v =>
          `<div style="color: ${v.model.color}">${v.model.modelName}: ${v.point.mae.toFixed(1)}</div>`
        ).join('')}
      `);
  })
  .on('mouseout', () => {
    tooltip?.style('opacity', '0');
  });
```

### API Integration in Home.tsx

```tsx
// New signals for time series
const [timeSeriesData, setTimeSeriesData] = createSignal<ModelTimeSeries[]>([]);
const [isLoadingTimeSeries, setIsLoadingTimeSeries] = createSignal(false);

// Fetch time series for all models
const loadTimeSeriesData = async (siteId: number, parameterId: number, models: ModelAccuracyMetrics[]) => {
  if (!siteId || !parameterId || models.length === 0) {
    setTimeSeriesData([]);
    return;
  }

  setIsLoadingTimeSeries(true);

  try {
    // Fetch in parallel for all models
    const responses = await Promise.all(
      models.map(model =>
        fetchAccuracyTimeSeries(siteId, model.modelId, parameterId)
      )
    );

    // Transform to chart format
    const chartData = responses.map((response, index) =>
      transformApiResponse(response, getModelColor(response.modelName, index))
    );

    setTimeSeriesData(chartData);
  } catch (err) {
    console.error('Failed to load time series:', err);
    setTimeSeriesData([]);
  } finally {
    setIsLoadingTimeSeries(false);
  }
};

// Effect to load time series after accuracy data loads
createEffect(() => {
  const data = accuracyData();
  if (data && data.models.length > 0) {
    loadTimeSeriesData(data.siteId, data.parameterId, data.models);
  }
});
```

### Solid.js Patterns (CRITICAL)

**Refs in Solid.js:**
```tsx
let svgRef: SVGSVGElement | undefined;

// In JSX - use ref callback
<svg ref={svgRef!} class="w-full" style={{ height: '400px' }} />
```

**Effect dependencies:**
```tsx
createEffect(() => {
  // Access props to track them
  const models = props.models;
  if (models.length > 0) {
    drawChart();
  }
});
```

**Cleanup:**
```tsx
import { onCleanup } from 'solid-js';

onCleanup(() => {
  tooltip?.remove();
  // Clean up resize listener if used
});
```

### Responsive Handling

```tsx
// Option 1: ResizeObserver (preferred)
onMount(() => {
  const observer = new ResizeObserver(() => {
    drawChart();
  });

  if (svgRef) {
    observer.observe(svgRef);
  }

  onCleanup(() => observer.disconnect());
});

// Option 2: Window resize with debounce
import { createSignal, onCleanup } from 'solid-js';

const [windowWidth, setWindowWidth] = createSignal(window.innerWidth);

onMount(() => {
  let timeout: number;
  const handleResize = () => {
    clearTimeout(timeout);
    timeout = window.setTimeout(() => {
      setWindowWidth(window.innerWidth);
    }, 150);
  };

  window.addEventListener('resize', handleResize);
  onCleanup(() => window.removeEventListener('resize', handleResize));
});

createEffect(() => {
  windowWidth(); // Track window width
  drawChart();
});
```

### Empty State

```tsx
<Show when={props.models.length === 0}>
  <div class="bg-gray-50 rounded-lg p-8 text-center">
    <p class="text-gray-500">No time series data available</p>
  </div>
</Show>

<Show when={props.models.length > 0}>
  <svg ref={svgRef!} class="w-full" style={{ height: '400px' }} />
</Show>
```

### File Structure

```
frontend/src/
├── components/
│   ├── AccuracyTimeSeriesChart.tsx  # NEW
│   ├── BiasCharacterizationCard.tsx
│   ├── ModelComparisonTable.tsx
│   └── ...
├── pages/
│   └── Home.tsx                     # MODIFY (add time series section)
└── lib/
    ├── api.ts                       # MODIFY (add fetchAccuracyTimeSeries)
    └── types.ts                     # MODIFY (add time series types)
```

### D3.js Types

D3 is already installed. For TypeScript support:
```bash
npm install --save-dev @types/d3
```

If not already installed, check package.json first.

### Previous Story Context

From Stories 4-3 and 4-4:
- `accuracyData` signal contains model list with modelId
- `selectedParameterUnit()` helper for unit display
- Show callback pattern: `<Show when={...}>{(data) => ...}</Show>`
- Proper Solid.js patterns established

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.5]
- [Source: _bmad-output/project-context.md#Solid.js-Patterns]
- [Source: backend/api/routes/analysis.py - Time series endpoint]
- [Source: backend/api/schemas/analysis.py - TimeSeriesAccuracyResponse]
- [D3.js Documentation: https://d3js.org/]

## Change Log

- 2026-01-16: Story created with comprehensive context for dev agent
