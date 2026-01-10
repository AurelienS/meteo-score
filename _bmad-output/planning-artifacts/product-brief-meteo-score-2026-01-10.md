---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "_bmad-output/analysis/brainstorming-session-2026-01-10.md"
  - "_bmad-output/planning-artifacts/research/technical-data-sources-planfoy-research-2026-01-10.md"
date: "2026-01-10"
author: "boss"
project_name: "meteo-score"
---

# Product Brief: meteo-score

## Executive Summary

MétéoScore is an open-source, data-driven platform that objectively evaluates weather forecast model accuracy for paragliding sites in France. By comparing forecast predictions against real-world observations from weather beacons and stations, MétéoScore eliminates guesswork and cognitive biases, helping paragliders identify which forecast model is most reliable for their specific flying location.

**Mission:** Educate the paragliding community through transparent, data-backed model comparisons, ultimately improving forecast accuracy across the industry.

**Approach:** Compare forecasts from multiple models (AROME, Meteo-Parapente, ICON-CH) against real observations (ROMMA, FFVL beacons) to quantify accuracy by site, revealing typical biases (e.g., "AROME overestimates wind by +10 km/h at Passy").

**Value Proposition:** Replace subjective preferences and aesthetic bias with objective data, enabling pilots to trust the right model for the right location.

---

## Core Vision

### Problem Statement

Paragliders face decision paralysis when choosing between dozens of contradictory weather forecast models. Without objective validation, pilots fall victim to cognitive biases:

- **Confirmation bias**: Choosing the forecast that supports what they want to do
- **Sunk cost fallacy**: Trusting paid models regardless of accuracy
- **Aesthetic bias**: Preferring visually appealing interfaces over data quality
- **Selective amnesia**: Forgetting when forecasts were wrong, remembering only when they were right

The result: suboptimal flying decisions based on hunches, peer pressure, or interface design rather than forecast reliability.

### Problem Impact

**For Paragliders:**
- Missed flying opportunities (canceling when conditions would have been good)
- Safety risks (flying when conditions are worse than predicted)
- Wasted time comparing 20+ models without clear guidance
- Financial waste on paid models that may not be the most accurate
- Frustration and decision fatigue

**For the Community:**
- Perpetuation of myths and subjective beliefs ("locals say X is better")
- No feedback loop to improve forecast models
- New pilots especially vulnerable without experience-based intuition

### Why Existing Solutions Fall Short

**Current Approaches:**
- Individual pilot experience (anecdotal, not scalable)
- Forum discussions (subjective opinions, no data)
- "Local knowledge" (varies, often contradictory)
- Trial and error (learning through mistakes)

**Critical Gaps:**
- **No objective validation**: No one compares forecasts to actual observations systematically
- **No site-specificity**: General claims about models without geographic granularity
- **No transparency**: Proprietary models with opaque methodologies
- **No memory**: Community forgets forecast failures, no long-term tracking

### Proposed Solution

MétéoScore creates an objective, data-driven reference tool that:

1. **Compares forecasts vs. reality**: Systematically matches forecast predictions (AROME, Meteo-Parapente, ICON-CH) against real observations from weather beacons (ROMMA, FFVL, PiouPiou stations)

2. **Quantifies accuracy by site**: Calculates mean absolute errors and identifies systematic biases for each model at specific paragliding sites

3. **Reveals actionable insights**: Not just abstract scores, but practical biases (e.g., "Model X overestimates wind by +15% at Site Y")

4. **Provides transparency**: Open-source code, public methodology, visible data sources

**MVP Scope:**
- 4-5 pilot sites in France (Passy Plaine Joux, Alps North/South, Mediterranean, Atlantic)
- 2-3 forecast models (AROME, Meteo-Parapente initially)
- Core parameters: Wind (speed + direction), Temperature
- Daily data collection: 4x/day forecasts, 6x/day observations

**Usage Model:**
A **reference tool**, not a daily engagement app. Pilots consult it when discovering a new site or validating their model preferences, then apply that knowledge going forward.

### Key Differentiators

**1. Objective Data Validation**
- First platform to systematically compare forecasts against real beacon observations
- No opinions, no aesthetics—pure quantitative accuracy metrics

**2. Site-Specific Granularity**
- Recognizes that model performance varies by location (valley vs. plateau, altitude, terrain)
- Provides actionable insights per flying site, not generic national averages

**3. Bias Characterization Over Scores**
- Reveals *how* models fail (systematic overestimation, underestimation) not just *that* they fail
- Enables mental correction: "Model says 25 km/h, but it overestimates by 10%, so expect ~23 km/h"

**4. Radical Transparency**
- Open-source codebase (GitHub)
- Public methodology documentation
- Verifiable data sources (all from public APIs/beacons)
- No commercial agenda—educational mission

**5. Community Impact**
- Creates feedback loop: underperforming models can improve
- Shifts community from subjective beliefs to data-driven decisions
- Elevates overall forecast quality across the industry

**6. Technical Foundation**
- Leveraging newly accessible data (Météo-France API free since 2024)
- Automated data pipeline (Python + PostgreSQL + Docker)
- Professional CI/CD and testing (quality without commercial pressure)

---

## Target Users

**Primary Users:** Paragliders of all levels—beginners, experienced pilots, local flyers, traveling pilots, recreational and competitive.

**Core Need:** Identify which weather forecast model is most reliable for their specific flying site to make better flight planning decisions.

**Usage Pattern:** Consult MétéoScore as a reference tool when discovering a new site or validating model preferences, then apply that knowledge for ongoing flight planning.

**Note:** This is a universal reference tool for the entire paragliding community. User segmentation is minimal—the value proposition (objective forecast accuracy data) is consistent across all pilot types.

---

## Success Metrics

### User Success Metrics

**Primary Success Outcome:**
Users can confidently answer: "Which forecast model should I trust for [specific site] and [specific parameter]?"

**Core User Value Indicators:**

1. **Actionable Model Comparison**
   - User identifies the most accurate model for their target site
   - User understands *why* a model performs better (e.g., "AROME predicts wind speed ±2 km/h better than Meteo-Parapente at Passy")
   - User can differentiate model strengths by parameter (wind speed vs. direction vs. temperature)

2. **Parameter-Specific Insights**
   - **MVP Phase:** Wind (speed + direction), Temperature
   - **Future Expansion:** Instability, cloud base, convective layer top, cloud top, precipitation

3. **Informed Decision Making**
   - User adjusts forecast interpretation based on known model biases
   - User selects appropriate model based on forecast horizon needs (6h, 48h, weekly)
   - User understands trade-offs between models (accuracy vs. forecast range)

**Behavioral Success Indicators:**
- User consults MétéoScore when discovering a new flying site
- User references MétéoScore insights in flight planning discussions
- User contributes feedback or suggests additional sites/models to compare

### Project Objectives

**Since MétéoScore is an open-source side project for education and community benefit, success is measured by impact and adoption rather than revenue:**

**Short-Term Objectives (3-6 months):**
- **MVP Validation:** Demonstrate statistical validity with 1-2 pilot sites, 2-3 models, core parameters (wind, temperature)
- **Data Pipeline Stability:** Automated daily collection of forecasts and observations with minimal manual intervention
- **Initial Community Feedback:** Early adopters validate that insights are actionable and accurate

**Medium-Term Objectives (6-12 months):**
- **Geographic Expansion:** Cover 10-15 paragliding sites across diverse French regions (Alps, Mediterranean, Atlantic, valleys, plateaus)
- **Model Diversity:** Include 4-5 forecast models to provide comprehensive comparisons
- **Parameter Expansion:** Add cloud-related parameters (base, top, convective layer) and instability metrics
- **Community Adoption:** MétéoScore becomes a recognized reference tool in French paragliding forums and schools

**Long-Term Vision (12+ months):**
- **Industry Impact:** Forecast model providers acknowledge MétéoScore findings and improve underperforming models
- **Cultural Shift:** Paragliding community bases model selection on objective data rather than subjective preferences
- **Open Contribution:** Community members contribute site suggestions, validate findings, and participate in methodology refinement
- **Recognition of Model Nuances:** Pilots understand that "best model" depends on site, parameter, and forecast horizon

### Key Performance Indicators

**Data Quality & Coverage KPIs:**
- **Site Coverage:** Number of active flying sites with sufficient observation data (Target MVP: 1-2 sites; 12-month: 10-15 sites)
- **Data Completeness:** % of expected forecast/observation data points successfully collected daily (Target: >90%)
- **Statistical Confidence:** Minimum sample size achieved per site-model-parameter combination (Target: 90+ days of data for initial conclusions)

**User Engagement KPIs:**
- **Adoption Rate:** Number of unique visitors consulting site comparisons (Leading indicator of community awareness)
- **Return Usage:** % of users who return after initial visit (Indicates sustained value perception)
- **Geographic Distribution:** Number of distinct regions represented by user queries (Indicates breadth of relevance)

**Impact & Insight KPIs:**
- **Model Differentiation:** % of site-parameter combinations where clear model performance differences emerge (Target: identify "winner" in >70% of cases)
- **Bias Characterization:** % of models with identified systematic biases (e.g., "AROME +10% wind overestimation") (Target: characterize bias for >80% of model-site pairs)
- **Community Validation:** Feedback from pilots confirming MétéoScore insights match real-world experience (Qualitative but critical)

**Operational KPIs:**
- **Pipeline Reliability:** % uptime of automated data collection (Target: 95%+)
- **Processing Latency:** Time lag between observation availability and updated site scores (Target: <24 hours)
- **Transparency:** All methodology, data sources, and calculations publicly documented and verifiable

**Strategic Success Indicator:**
The ultimate KPI: A pilot planning a flight at an unfamiliar site thinks, "Let me check MétéoScore first to see which model to trust here."

---

## MVP Scope

### Core Features

**Geographic Scope:**
- **Single Pilot Site:** Passy Plaine Joux / Varan (Haute-Savoie)
  - Validates approach on one well-instrumented site before scaling
  - Tests methodology against real-world paragliding conditions

**Forecast Models:**
- **2 Models:** AROME (Météo-France), Meteo-Parapente
  - Covers institutional vs. community-specialized models
  - Sufficient to demonstrate comparative analysis

**Parameters:**
- **Wind:** Speed (km/h) + Direction (degrees)
- **Temperature:** °C at site altitude
  - Core parameters that directly impact flight safety and decisions

**Data Pipeline:**
- **Automated Daily Collection:**
  - Forecast retrieval: 4x per day (00h, 06h, 12h, 18h UTC runs)
  - Observation retrieval: 6x per day from ROMMA/FFVL beacons
  - Scheduled tasks with error handling and retry logic
- **Data Storage:** TimescaleDB for time-series forecast/observation pairs
- **Progressive Accumulation:** Start collection immediately, build dataset over time (30-60-90 days)

**Analysis Engine:**
- **Statistical Calculations:**
  - Mean Absolute Error (MAE) per model, parameter, and forecast horizon
  - Systematic bias detection (overestimation/underestimation patterns)
  - Confidence intervals based on sample size
- **Minimum Data Requirements:** Flag results as "preliminary" until 30+ days, "validated" after 90+ days

**User Interface:**
- **Simple Web Interface:** Minimalist UX displaying:
  - Model comparison table (MAE by parameter)
  - Bias characterization ("AROME overestimates wind by +X km/h on average")
  - Data freshness indicators (last update, sample size)
  - Basic charts showing error distributions
- **Technology:** Static or simple server-rendered pages (no complex SPA)
- **Mobile-responsive:** Pilots check on phones in the field

**Transparency:**
- **Methodology Documentation:** Publicly visible explanation of calculations
- **Data Provenance:** Clear indication of observation and forecast sources
- **Open Source:** GitHub repository with code and documentation

### Out of Scope for MVP

**Explicitly deferred to post-MVP phases:**

- ❌ **Multi-Site Expansion:** Extending beyond Passy to 10-15 sites (Phase 2)
- ❌ **Advanced Parameters:** Instability, cloud base/top, convective layer height, precipitation (Phase 2+)
- ❌ **Additional Models:** ICON-CH, other models beyond AROME and Meteo-Parapente (Phase 2)
- ❌ **Historical Data Backfill:** Multi-year historical analysis (start fresh, accumulate prospectively)
- ❌ **Community Features:** User accounts, comments, site suggestions, voting (Phase 3)
- ❌ **Advanced Analytics:** Machine learning bias correction, ensemble predictions, forecast horizon optimization (Phase 3)
- ❌ **Interactive Dashboards:** Complex data visualizations, custom date ranges, downloadable reports (Phase 2)
- ❌ **API Access:** Public API for third-party integrations (Phase 3)
- ❌ **Alerts/Notifications:** Email or push notifications for model updates (Phase 3)

**Rationale:**
The MVP focuses on proving the core hypothesis: "Can we objectively compare forecast model accuracy using beacon observations?" Everything else is enhancement after validation.

### MVP Success Criteria

**The MVP is considered successful if, after 90 days of operation:**

1. **Technical Success:**
   - Data pipeline achieves >90% uptime and completeness
   - Sufficient data collected to calculate statistically meaningful MAE (90+ day sample)
   - Web interface successfully displays comparison results

2. **Analytical Success:**
   - Clear differentiation emerges between models (>20% MAE difference OR identified systematic bias >5%)
   - Results are reproducible and explainable with documented methodology
   - Confidence intervals narrow enough to make actionable recommendations

3. **User Validation Success:**
   - 5-10 paragliding pilots review results and confirm insights align with real-world experience
   - Pilots report findings are actionable ("I now know which model to trust for Passy")
   - No major methodological flaws identified by community feedback

4. **Go/No-Go Decision Point:**
   - **GO (scale to Phase 2):** If all success criteria met → expand to 4-5 sites, add ICON-CH model
   - **PIVOT:** If methodology issues emerge → refine approach before scaling
   - **NO-GO:** If no meaningful model differentiation OR data pipeline unreliable → reassess feasibility

### Future Vision

**If MétéoScore is wildly successful, in 2-3 years it becomes:**

**Phase 2: Geographic & Parameter Expansion (6-12 months)**
- **10-15 Sites:** Cover diverse French paragliding regions (Alps North/South, Mediterranean, Atlantic, valleys, plateaus)
- **4-5 Models:** Add ICON-CH, potentially regional models or other community favorites
- **Advanced Parameters:** Cloud base/top, convective layer height, instability indices, precipitation
- **Enhanced UX:** Interactive charts, historical trend views, site comparison tools

**Phase 3: Community Platform (12-24 months)**
- **User Contributions:** Pilots suggest new sites, validate findings, report anomalies
- **Regional Expansion:** Extend beyond France (Switzerland, Italy, Spain Alps)
- **Public API:** Enable third-party integrations (flight planning apps, weather aggregators)
- **Model Provider Engagement:** Collaborate with forecast providers to improve underperforming models

**Long-Term Vision (24+ months):**
- **Industry Standard:** MétéoScore becomes the authoritative reference for paragliding forecast validation
- **Cultural Shift:** Community broadly adopts data-driven model selection over subjective preferences
- **Feedback Loop:** Forecast model providers use MétéoScore insights to improve accuracy
- **Research Platform:** Academic researchers use MétéoScore dataset for weather model validation studies
- **Ecosystem Growth:** Flight schools integrate MétéoScore into pilot training, competitions reference it for fairness

**Ultimate Impact:**
Paragliding weather forecasting accuracy improves industry-wide because models are held accountable to objective, transparent performance metrics.

---
