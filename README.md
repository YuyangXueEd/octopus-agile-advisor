# 🐙⚡ Octopus Agile Advisor: a Claude Skill

A daily email that tells your household **when to run the washing machine, dishwasher, dryer, EV charger or gaming PC tomorrow** on the [Octopus Energy Agile](https://octopus.energy/smart/agile/) tariff. Claude writes it, using *your* appliances.

Most Agile tools give you a chart or the single cheapest slot. This one does the thinking a sensible flatmate would:

> **⚡ Tomorrow's electricity, Fri 27 Nov: washing after 21:00, nothing big 4–7pm**
>
> Tomorrow is about 8% dearer than today. Prices stay above 50p all day and hit 72p around 16:30, then drop back to 31–35p after 9pm.
>
> - **Washing machine: 21:00–23:00**, ~33.5p/kWh. 3am is the absolute cheapest, but only 2p cheaper, so it isn't worth a midnight wash. Saves ~38p vs running it at 4pm.
> - **Dishwasher: start at 20:30**, ~34.6p. Saves ~44p vs the peak.
> - **Gaming PC:** after 9pm costs about half the peak rate. Saves ~40p over a 3-hour session.
>
> **Avoid:** 16:00–19:00 (avg 70p).

It weighs *cheapest overall* against *cheapest while you're awake*, puts the savings in pence per run, flags negative-price slots first, mentions Octopus Tracker gas prices if you have them, and writes in any language (English by default).

## How it works

```
 scheduled task (daily, ~17:00)
        │
        ▼
 scripts/agile.py ──► Octopus public API (no account login or API key needed)
   • finds your region from your postcode
   • converts UTC → UK time (handles the clock changes)
   • finds the cheapest back-to-back window for each appliance
   • peak block, negative / very cheap slots, Tracker gas
        │  JSON
        ▼
 Claude: judgement + writing ──► Gmail ──► everyone in the house
```

The arithmetic lives in a small, dependency-free Python script, so the numbers are the same every day and the clock changes can't go wrong. The model only does what it's good at: deciding what's worth saying and saying it like a person.

## Requirements

- **Claude desktop app**: the daily email uses its scheduled tasks. Tasks run while the app is open; if it was closed at send time, the task runs when you next open it.
- **Gmail connected** in Claude, to send the email.
- **Python 3.8+** on your computer. Nothing to `pip install`.
- You're on **Agile Octopus** (import). On Go, Intelligent Octopus or Cosy the cheap hours are fixed, so a daily email adds little.

## Install

**Claude desktop / claude.ai:** download `octopus-agile-advisor.zip` from the [latest release](../../releases/latest), then go to **Settings → Capabilities → Skills → Upload skill**.

**Claude Code:** copy the folder into your skills directory:

```bash
git clone https://github.com/YuyangXueEd/octopus-agile-advisor.git
cp -r octopus-agile-advisor/octopus-agile-advisor ~/.claude/skills/
```

Then say something like *"Set up my Octopus Agile daily email"*. Claude will ask for:

1. the first half of your postcode (it works out your Agile region)
2. your gas tariff: fixed, Tracker, or none
3. the appliances you can shift, with sensible defaults you can edit
4. your awake hours, recipients, language and send time

It shows you a preview of tomorrow's email before scheduling anything.

## Try the script on its own

```bash
python octopus-agile-advisor/scripts/agile.py region "EH9"
python octopus-agile-advisor/scripts/agile.py analyse --config my-config.json
```

See [`references/config.md`](octopus-agile-advisor/references/config.md) for the config format.

## Privacy

Everything runs on your own computer. Prices come from Octopus's **public** API: no account login, API key or meter data is needed or sent. Your config (appliances, recipients) stays in `~/.octopus-agile-advisor/` on your machine.

## Alternatives and credits

Plenty of good Agile tools already exist. This project only adds the scheduled, emailed, judgement-based layer, with no Home Assistant, Docker or API key needed. If you want something else:

- **Home Assistant**: [BottlecapDave/HomeAssistant-OctopusEnergy](https://github.com/BottlecapDave/HomeAssistant-OctopusEnergy) and [Target Timeframes](https://github.com/BottlecapDave/HomeAssistant-TargetTimeframes) for automating devices directly.
- **Ask Claude on demand**: [octopus-mcp](https://github.com/mattoddie/octopus-mcp), an MCP server with a cheapest-time finder.
- **Terminal**: [gridhour](https://github.com/777dimas/gridhour), with price plus carbon timelines per job.
- **Push alerts**: [agile-octopus-telegram-notifications](https://github.com/lahatfield/agile-octopus-telegram-notifications).

## Roadmap / ideas welcome

- "Finish by" deadlines and split runs, e.g. *EV: 4h, done by 07:00*
- Carbon intensity from the [NESO API](https://carbonintensity.org.uk/) as a second "greenest time" score
- Octopus Power-Ups (free electricity sessions) and Saving Sessions
- Agile Outgoing (export) advice for solar and battery homes

PRs and issues are welcome.

## Not affiliated with Octopus Energy

This is an independent community project. Prices come from the public Octopus Energy API. Always check your own app or bill for the authoritative rate.

## License

MIT
