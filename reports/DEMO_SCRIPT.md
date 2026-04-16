## Demo video script (4–6 minutes)

### 0:00–0:30 — Hook (Problem + stakes)
- “Campuses generate huge daily data (attendance, WiFi, electricity, mess logs), but it’s often siloed.”
- “Result: energy waste, overcrowding, and inefficient resource allocation.”

### 0:30–1:30 — Dashboard overview (Tableau)
- Open Tableau “Campus Overview”.
- Show KPIs from `v_kpi_overview_daily` (energy, average connected devices, total mess entries, average wait).
- Show trend: “We can immediately see when demand rises/falls.”

### 1:30–2:30 — Peaks + patterns
- Open “Peak Usage by Hour” (heatmap using `v_peak_usage_by_hour`).
- Point out:
  - peak electricity hours
  - peak WiFi congestion windows
  - peak mess rush hours

### 2:30–3:30 — Anomalies (operational alerts)
- Open anomalies view (`v_anomalies`).
- Explain: “We detect unusual spikes in electricity and WiFi usage — potential faults, sudden crowds, or misconfiguration.”
- Show 1–2 anomaly examples and drill down by entity.

### 3:30–4:30 — Predictions (decision support)
- Electricity forecast (`v_forecast_electricity_daily`): “Here’s tomorrow’s forecasted kWh by building.”
- Peak mess hour prediction (`v_peak_mess_hours_forecast`): “Next hour peak probability is high for Mess X.”

### 4:30–5:40 — Recommendations (actionable + practical)
- Open recommendations (`v_recommendations`).
- Walk through 3 categories:
  - **Energy**: “Shift non-critical loads / tune HVAC during low-demand”
  - **Schedule**: “Stagger class ending times to reduce rush”
  - **Resource allocation**: “Add counters/staff during predicted peaks”

### 5:40–6:00 — Impact + close
- “This system turns raw operational data into insights + predictions + actions.”
- “Expected impact: improved efficiency, reduced costs, and better student/admin experience.”

