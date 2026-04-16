## Smart Campus Intelligence — Insight Report (Template)

### Key findings (top 3–5)
- **Energy**: Identify buildings with consistently high daily kWh and peak kW, and the time windows they spike.
- **WiFi**: Identify APs/buildings with recurring congestion spikes (connected devices anomalies).
- **Mess**: Identify recurring peak hours with high wait times and high predicted peak probability.

### Cost-saving opportunities (simple scenario estimates)
- **Peak shaving**: If we reduce daily peak-hour consumption by \(X\%\) in top 2 buildings, expected weekly savings \(\approx\) \(0.01X \times\) weekly_kWh_top2.
- **Off-peak shifting**: Move non-critical loads (water heating, laundry, HVAC pre-cooling) to lower demand hours to reduce peak kW penalties.

### Evidence (what to screenshot from Tableau)
- `v_kpi_overview_daily`: last 30 days trend
- `v_peak_usage_by_hour`: hour-of-day heatmap (energy/WiFi/mess)
- `v_anomalies`: top anomalies table + timeline
- `v_forecast_electricity_daily`: forecast vs actual
- `v_peak_mess_hours_forecast`: next-hour peak probability
- `v_recommendations`: ranked actions with expected impact

### Recommended actions (from recommendation engine)
- **Class scheduling**: avoid ending large lectures immediately before peak mess windows; stagger section timings.
- **Energy saving**: tune HVAC/lighting schedules; switch off idle zones; shift non-critical loads.
- **Resource allocation**: add counters/staff during predicted mess peaks; prioritize maintenance in recurring anomaly buildings/AP zones.

### Limitations + next steps
- Replace simulated data with real campus logs.
- Add building-level occupancy proxies (from WiFi + attendance) for stronger forecasting.
- Add feedback loop: mark recommendation applied → measure impact.

