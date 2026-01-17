# MétéoScore Methodology

This document describes the technical methodology used by MétéoScore to compare weather forecast accuracy.

## Overview

MétéoScore compares weather forecasts from multiple models against actual observations from weather beacons to measure prediction accuracy.

## Data Sources

### Forecast Models
- **AROME** (Météo-France): High-resolution model covering France
- **Meteo-Parapente**: Specialized model for outdoor activities

### Observation Sources
- **ROMMA**: Regional weather beacon network
- **FFVL**: French Free Flight Federation beacon network

## Accuracy Metrics

### Mean Absolute Error (MAE)
The primary metric used to compare forecast accuracy:

```
MAE = (1/n) × Σ|forecast - observed|
```

### Bias
Indicates systematic over/under prediction:
- Positive bias: Model tends to overestimate
- Negative bias: Model tends to underestimate

## Methodology Details

1. **Data Collection**: Automated collection 4x daily for forecasts, 6x daily for observations
2. **Matching**: Forecasts are matched to observations by timestamp, location, and parameter
3. **Calculation**: Deviations computed for each matched pair
4. **Aggregation**: Statistics aggregated daily, weekly, and monthly using TimescaleDB continuous aggregates
5. **Visualization**: Results displayed with confidence indicators based on sample size

## Limitations

- Accuracy varies by location, time of day, and weather conditions
- Sample sizes may be limited for recent data
- Beacon observations have their own measurement uncertainties

## More Information

For detailed implementation, see the [source code](https://github.com/AurelienS/meteo-score).

For questions or feedback, please [open an issue](https://github.com/AurelienS/meteo-score/issues).
