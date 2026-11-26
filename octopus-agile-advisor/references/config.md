# config.json

Saved at `~/.octopus-agile-advisor/config.json` and read fresh on every daily run, so editing it changes tomorrow's email without touching the scheduled task.

```json
{
  "region": "N",
  "awake_hours": ["07:00", "23:00"],
  "appliances": [
    {"name": "Washing machine", "hours": 2, "kwh": 1.0},
    {"name": "Dishwasher", "hours": 2.5, "kwh": 1.0, "note": "has delay-start"},
    {"name": "Gaming PC", "hours": 3, "kw": 0.35}
  ],
  "gas": {"type": "fixed", "unit_rate_p": 7.87, "standing_charge_p": 28.93},
  "language": "English",
  "recipients": ["me@example.com", "flatmate@example.com"],
  "send_time": "17:00"
}
```

| Field | Meaning |
|---|---|
| `region` | Agile region letter (A–P), from `agile.py region <postcode>`. |
| `awake_hours` | `[from, to]` in 24-hour UK time. Windows must start and finish inside it to count as the "awake" option. Use `"24:00"` to allow running until midnight. |
| `appliances[]` | `name`, `hours` (run length), and either `kwh` (per run) or `kw` (power). An optional `note` is passed through to help the wording, e.g. "has delay-start" or "noisy spin". |
| `gas.type` | `"fixed"` (optional `unit_rate_p`, `standing_charge_p`), `"tracker"` (needs `tracker_product_code`, e.g. `"SILVER-25-09-02"`), or `"none"`. |
| `language` | Language for the whole email. Default `"English"`. |
| `recipients` | Email addresses that get the daily email. |
| `send_time` | Kept for reference. The actual time is set on the scheduled task. |
| `very_cheap_threshold_p` | Optional, default `15`. Slots below this price (and all negative ones) appear in `alerts`. |
| `agile_product` | Optional. Pins a specific Agile product code. If left out, the newest one is found automatically. |
