#!/usr/bin/env python3
"""Price helper for the octopus-agile-advisor skill.

Does the deterministic part of the job (fetching Octopus Agile prices, converting
UTC to UK time, finding the cheapest run window for each appliance) so the model
only has to do the judgement and the writing. Standard library only, so it runs on
any machine with Python 3.8+ and nothing to install.

Usage:
  python agile.py region EH9                 # postcode -> Agile region letter
  python agile.py analyse --config FILE      # JSON analysis for the daily email
  python agile.py analyse --config FILE --wait-minutes 9   # poll if not published yet
"""
import argparse
import json
import math
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://api.octopus.energy/v1"
HEADERS = {"User-Agent": "octopus-agile-advisor/1.0"}
DEFAULT_CONFIG = os.path.join(os.path.expanduser("~"), ".octopus-agile-advisor", "config.json")

REGION_NAMES = {
    "A": "Eastern England", "B": "East Midlands", "C": "London",
    "D": "Merseyside and North Wales", "E": "West Midlands", "F": "North Eastern England",
    "G": "North Western England", "H": "Southern England", "J": "South Eastern England",
    "K": "South Wales", "L": "South Western England", "M": "Yorkshire",
    "N": "South Scotland", "P": "North Scotland",
}


# ---------------------------------------------------------------- HTTP helpers

def _ssl_context():
    try:
        import certifi  # optional; fixes Pythons that ship without root certificates
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


def _get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
            return json.load(resp)
    except urllib.error.URLError as exc:
        # Some Pythons (python.org builds on macOS, MSYS2 on Windows) can't verify
        # HTTPS out of the box. The system curl uses the OS certificate store, so
        # fall back to it rather than make the user fix their Python install.
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc) or not shutil.which("curl"):
            raise
        raw = subprocess.run(["curl", "-sSf", "--max-time", "30", "-A", HEADERS["User-Agent"], url],
                             check=True, capture_output=True).stdout
        return json.loads(raw)


def _get_all(url, params=None):
    data = _get(url, params)
    rows = list(data.get("results", []))
    while data.get("next"):
        data = _get(data["next"])
        rows.extend(data.get("results", []))
    return rows


# ------------------------------------------------------------------ UK time
# Implemented by hand rather than with zoneinfo: Windows Pythons often ship
# without the IANA database, and the UK rule is simple and fixed by law.

def _last_sunday(year, month):
    last = (date(year, month + 1, 1) - timedelta(days=1)) if month < 12 else date(year, 12, 31)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def _uk_offset(utc_dt):
    y = utc_dt.year
    bst_start = datetime.combine(_last_sunday(y, 3), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    bst_end = datetime.combine(_last_sunday(y, 10), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    return timedelta(hours=1) if bst_start <= utc_dt < bst_end else timedelta(0)


def to_uk(utc_dt):
    return (utc_dt + _uk_offset(utc_dt)).replace(tzinfo=None)


def uk_midnight_as_utc(d):
    guess = datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)
    return guess - _uk_offset(guess)


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ Octopus

def region_for_postcode(postcode):
    res = _get(f"{API}/industry/grid-supply-points/", {"postcode": postcode.strip().upper()})["results"]
    return res[0]["group_id"].lstrip("_") if res else None


def current_agile_product():
    products = _get_all(f"{API}/products/", {"brand": "OCTOPUS_ENERGY", "is_variable": "true", "page_size": 100})
    agile = [p for p in products
             if p["code"].startswith("AGILE-") and "OUTGOING" not in p["code"]
             and p.get("direction", "IMPORT") == "IMPORT"]
    if not agile:
        raise RuntimeError("No Agile import product is listed on the Octopus API right now.")
    agile.sort(key=lambda p: p.get("available_from") or "")
    return agile[-1]["code"]


def fetch_unit_rates(kind, product, region, start_utc, end_utc):
    prefix = "E" if kind == "electricity" else "G"
    tariff = f"{prefix}-1R-{product}-{region}"
    rows = _get_all(
        f"{API}/products/{product}/{kind}-tariffs/{tariff}/standard-unit-rates/",
        {"period_from": _iso(start_utc), "period_to": _iso(end_utc), "page_size": 1500},
    )
    out = []
    for r in rows:
        s = _parse(r["valid_from"])
        e = _parse(r["valid_to"]) if r.get("valid_to") else s + timedelta(minutes=30)
        out.append({"start": s, "end": e, "p": round(float(r["value_inc_vat"]), 2)})
    out.sort(key=lambda x: x["start"])
    return out


# ----------------------------------------------------------------- analysis

def _hhmm(utc_dt):
    return to_uk(utc_dt).strftime("%H:%M")


def _label(utc_dt, today):
    local = to_uk(utc_dt)
    day = {today: "today", today + timedelta(days=1): "tomorrow"}.get(local.date(), local.strftime("%a %d %b"))
    return f"{day} {local.strftime('%H:%M')}"


def _minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _stats(slots):
    if not slots:
        return None
    lo = min(slots, key=lambda s: s["p"])
    hi = max(slots, key=lambda s: s["p"])
    return {
        "avg_p": round(sum(s["p"] for s in slots) / len(slots), 2),
        "min_p": lo["p"], "min_at": _hhmm(lo["start"]),
        "max_p": hi["p"], "max_at": _hhmm(hi["start"]),
        "slots": len(slots),
    }


def _windows(slots, n):
    """Every run of n back-to-back half-hour slots, with its average price."""
    for i in range(len(slots) - n + 1):
        run = slots[i:i + n]
        if all(run[k]["end"] == run[k + 1]["start"] for k in range(n - 1)):
            yield run, sum(s["p"] for s in run) / n


def _in_awake(run, awake_from, awake_to):
    start_local, end_local = to_uk(run[0]["start"]), to_uk(run[-1]["end"])
    start_min = start_local.hour * 60 + start_local.minute
    end_min = end_local.hour * 60 + end_local.minute
    if end_local.date() != start_local.date():
        end_min += 1440  # finishes at/after midnight
    return start_min >= awake_from and end_min <= awake_to


def _describe(run, avg, kwh, today):
    return {
        "start": _label(run[0]["start"], today),
        "end": _hhmm(run[-1]["end"]),
        "avg_p": round(avg, 2),
        "cost_p": round(avg * kwh, 1),
    }


def analyse_appliances(horizon, appliances, awake, today):
    awake_from, awake_to = _minutes(awake[0]), _minutes(awake[1])
    out = []
    for a in appliances:
        hours = float(a["hours"])
        kwh = float(a["kwh"]) if a.get("kwh") is not None else float(a["kw"]) * hours
        n = max(1, math.ceil(hours * 2 - 1e-9))
        wins = list(_windows(horizon, n))
        if not wins:
            out.append({"name": a["name"], "error": "not enough published slots for this run length"})
            continue
        best = min(wins, key=lambda w: w[1])
        worst = max(wins, key=lambda w: w[1])
        awake_wins = [w for w in wins if _in_awake(w[0], awake_from, awake_to)]
        best_awake = min(awake_wins, key=lambda w: w[1]) if awake_wins else None
        entry = {
            "name": a["name"], "hours": hours, "kwh": round(kwh, 2),
            "note": a.get("note", ""),
            "best_any_time": _describe(*best, kwh, today),
            "best_awake": _describe(*best_awake, kwh, today) if best_awake else None,
            "worst": _describe(*worst, kwh, today),
            "saving_vs_worst_p": round((worst[1] - best[1]) * kwh, 1),
        }
        if best_awake:
            entry["awake_premium_p"] = round((best_awake[1] - best[1]) * kwh, 1)
            entry["saving_awake_vs_worst_p"] = round((worst[1] - best_awake[1]) * kwh, 1)
        out.append(entry)
    return out


def hourly_table(slots, today):
    buckets = {}
    for s in slots:
        local = to_uk(s["start"])
        key = (local.date(), local.hour)
        buckets.setdefault(key, []).append(s["p"])
    rows = [{"hour": f"{h:02d}:00", "day": "today" if d == today else "tomorrow", "avg_p": round(sum(v) / len(v), 2)}
            for (d, h), v in sorted(buckets.items())]
    ranked = sorted(rows, key=lambda r: r["avg_p"])
    k = max(1, len(rows) // 6)
    cheap = {id(r) for r in ranked[:k]}
    dear = {id(r) for r in ranked[-k:]}
    for r in rows:
        r["tag"] = "cheapest" if id(r) in cheap else "priciest" if id(r) in dear else ""
    return rows


def gas_info(cfg, region, today):
    gas = cfg.get("gas") or {"type": "none"}
    kind = gas.get("type", "none")
    if kind == "fixed":
        return {"type": "fixed", "unit_p": gas.get("unit_rate_p"), "standing_p": gas.get("standing_charge_p")}
    if kind == "tracker":
        code = gas["tracker_product_code"]
        try:
            rates = fetch_unit_rates("gas", code, region, uk_midnight_as_utc(today),
                                     uk_midnight_as_utc(today + timedelta(days=2)))
        except Exception as exc:  # report, don't crash the electricity analysis
            return {"type": "tracker", "error": f"could not fetch Tracker gas prices: {exc}"}
        by_day = {}
        for r in rates:
            by_day[to_uk(r["start"]).date()] = r["p"]
        return {"type": "tracker", "product": code,
                "today_p": by_day.get(today), "tomorrow_p": by_day.get(today + timedelta(days=1))}
    return {"type": "none"}


def analyse(cfg, now_utc=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    region = cfg["region"].upper()
    product = cfg.get("agile_product") or current_agile_product()
    today = to_uk(now_utc).date()
    tomorrow = today + timedelta(days=1)

    slots = fetch_unit_rates("electricity", product, region, uk_midnight_as_utc(today),
                             uk_midnight_as_utc(today + timedelta(days=2)))
    if not slots:
        # A retired product or a wrong region returns HTTP 200 with no rows, which
        # would otherwise look like "prices not published yet" forever.
        raise RuntimeError(f"No prices at all for {product} region {region} today. The product may be "
                           f"retired or the region wrong; set 'agile_product'/'region' in the config.")
    today_slots = [s for s in slots if to_uk(s["start"]).date() == today]
    tomorrow_slots = [s for s in slots if to_uk(s["start"]).date() == tomorrow]
    horizon = [s for s in slots if s["start"] >= now_utc]

    cheap_threshold = float(cfg.get("very_cheap_threshold_p", 15))
    alerts = [{"at": _label(s["start"], today), "p": s["p"], "kind": "negative" if s["p"] <= 0 else "very_cheap"}
              for s in horizon if s["p"] < cheap_threshold]

    peak = None
    if len(tomorrow_slots) >= 6:
        run, avg = max(_windows(tomorrow_slots, 6), key=lambda w: w[1])
        peak = {"from": _hhmm(run[0]["start"]), "to": _hhmm(run[-1]["end"]), "avg_p": round(avg, 2),
                "max_p": max(s["p"] for s in run)}

    t_stats, y_stats = _stats(tomorrow_slots), _stats(today_slots)
    change = None
    if t_stats and y_stats:
        change = round((t_stats["avg_p"] - y_stats["avg_p"]) / y_stats["avg_p"] * 100, 1)

    last_end = slots[-1]["end"] if slots else None
    return {
        "generated_at_uk": to_uk(now_utc).strftime("%Y-%m-%d %H:%M"),
        "region": region, "region_name": REGION_NAMES.get(region, region), "agile_product": product,
        "tomorrow": tomorrow.isoformat(), "tomorrow_weekday": tomorrow.strftime("%A"),
        "tomorrow_published": len(tomorrow_slots) >= 40,
        "published_until_uk": _label(last_end, today) if last_end else None,
        "stats": {"tomorrow": t_stats, "today": y_stats, "tomorrow_vs_today_pct": change},
        "peak_3h_tomorrow": peak,
        "alerts": alerts,
        "appliances": analyse_appliances(horizon, cfg.get("appliances", []),
                                         cfg.get("awake_hours", ["07:00", "23:00"]), today),
        "hourly": hourly_table(tomorrow_slots, today),
        "gas": gas_info(cfg, region, today),
        "language": cfg.get("language", "English"),
        "recipients": cfg.get("recipients", []),
    }


# ---------------------------------------------------------------------- CLI

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("region", help="look up the Agile region letter for a postcode")
    r.add_argument("postcode")
    a = sub.add_parser("analyse", help="print the JSON analysis used to write the daily email")
    a.add_argument("--config", default=DEFAULT_CONFIG)
    a.add_argument("--wait-minutes", type=float, default=0,
                   help="if tomorrow's prices are not out yet, re-check every 3 minutes for up to this long")
    a.add_argument("--now", help="pretend it is this UTC time (ISO 8601), for testing")
    args = ap.parse_args()

    if args.cmd == "region":
        letter = region_for_postcode(args.postcode)
        print(json.dumps({"postcode": args.postcode, "region": letter,
                          "region_name": REGION_NAMES.get(letter or "", None)}))
        return 0 if letter else 1

    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    now = _parse(args.now) if args.now else None
    deadline = time.time() + args.wait_minutes * 60
    while True:
        result = analyse(cfg, now)
        if result["tomorrow_published"] or time.time() + 180 > deadline:
            break
        time.sleep(180)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (urllib.error.URLError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "code", None) or getattr(exc, "returncode", None)
        print(json.dumps({"error": "Could not fetch prices from the Octopus API "
                                   f"({detail or exc}). A 404 usually means a wrong region letter "
                                   "or a retired product code in the config; otherwise check the "
                                   "internet connection."}))
        sys.exit(2)
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(2)
