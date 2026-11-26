# Common shiftable appliances: defaults

Offer these during setup as a starting point, and let the person correct them: their own machine's eco programme may be much longer or use far less energy. Only appliances someone would actually move in time belong in the config.

`hours` is how long one run lasts, which sets the window length. Energy goes in `kwh` (per run) or `kw` (power while running; the script multiplies it by `hours`). For each appliance also ask whether it has **delay-start or a timer** (`delay_start`) and whether **someone has to be there** (`attended`). The "timer" and "attended" columns below are the usual answers, but check with the person.

| Appliance | hours | energy | timer | attended | Notes for the email |
|---|---|---|---|---|---|
| Washing machine (40°C) | 2 | 1.0 kWh | usually | no | Most have delay-start. Avoid suggesting runs that finish in the middle of the night unless the saving is real: wet clothes sit. |
| Washing machine (eco) | 3 | 0.6 kWh | usually | no | Eco programmes run longer but use less, so shifting saves less per run. |
| Tumble dryer (condenser/vented) | 2 | 4.5 kWh | often | no | The biggest win in most homes. Worth a clear recommendation. |
| Heat-pump tumble dryer | 3 | 1.5 kWh | often | no |  |
| Dishwasher | 2.5 | 1.0 kWh | usually | no | Delay-start is very common. "Start it before bed" works well. |
| Immersion heater (hot water) | 2 | 3 kW | timer/switch | no | Only if the water is heated electrically. Many people can put it on a timer. |
| EV charging (granny lead) | 4 | 2.3 kW | car app | no | Ask for their charger's power and typical hours. |
| EV charging (7 kW wallbox) | 4 | 7 kW | charger app | no | Large savings. Agile users often charge overnight on the cheapest block. |
| Home battery (grid charge) | 3 | 3 kW | app | no | Only if they charge from the grid manually. |
| Electric heater / oil radiator | 2 | 2 kW | sometimes | no | Pre-heat a room in a cheap slot. |
| Dehumidifier | 4 | 0.3 kW | sometimes | no |  |
| Bread maker / slow cooker | 4 | 0.2 kW | usually | no | Usually not worth mentioning: savings are tiny. |
| Gaming PC (under load) | 3 | 0.35 kW | no | **yes** | A 650 W power supply rarely draws 650 W. Gaming typically uses 250–450 W. |
| Laptop charging | 2 | 0.06 kW | smart plug | no | Savings are pennies. One line at most. |

## Things that are not worth including

- Fridge, freezer: always on.
- Kettle, microwave, hob, lights, TV: short or not movable.
- Gas boilers, gas hobs: not affected by electricity prices.
