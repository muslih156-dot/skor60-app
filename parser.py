from datetime import datetime, timezone, timedelta

WITA = timezone(timedelta(hours=8))

def compute_trading_day(dt=None):
    # Trading day WITA: jam 00:00 - 23:59 WITA
    if dt is None:
        dt = datetime.now(WITA)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=WITA)
    return dt.astimezone(WITA).strftime("%Y-%m-%d")

def format_iso_utc_and_wita(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_wita = dt.astimezone(WITA)
        return dt.isoformat(), dt_wita.strftime("%Y-%m-%d %H:%M WITA")
    except:
        return iso_str, iso_str

def parse_match_status(raw_status):
    s = str(raw_status).lower()
    if "live" in s or "1h" in s or "2h" in s:
        return "LIVE"
    if "ft" in s or "finished" in s or "full" in s:
        return "FT"
    return "SCHEDULED"

def parse_match_clock(raw_clock):
    try:
        return int(str(raw_clock).replace("'", "").strip())
    except:
        return 0

def parse_score(raw_score):
    try:
        parts = str(raw_score).split("-")
        return int(parts[0]), int(parts[1])
    except:
        return 0, 0

def detect_candidate(match):
    # Deteksi kandidat menit 60
    minute = parse_match_clock(match.get("minute", 0))
    status = parse_match_status(match.get("status", ""))
    if status == "LIVE" and 55 <= minute <= 65:
        return True
    return False
