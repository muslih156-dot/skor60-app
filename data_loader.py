"""
data_loader.py - BACA DARI REPO LAMA skor60
Menggabungkan matches.json (200 terbaru) + semua arsip harian
data/archive/daily/*.json biar totalnya nggak mentok 200 lagi.
Dedup by match_id, jadi kalau ada yang dobel, cuma dihitung 1x.
Kalau arsip gagal dibaca, fallback ke matches.json aja biar dashboard tetep jalan.
"""

import json
import urllib.request
import urllib.error

OLD_REPO = "muslih156-dot/skor60"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{OLD_REPO}/{BRANCH}/"
API_BASE = f"https://api.github.com/repos/{OLD_REPO}/contents/"

def _fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "skor60-app"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def _extract_matches(data):
    # Format bisa 2 macam: {"matches": [...]} atau langsung [...]
    if isinstance(data, dict):
        if isinstance(data.get("matches"), list):
            return data["matches"]
        # format arsip kadang {"total_records":..., "records":[...]}
        for k in ("records", "data", "items"):
            if isinstance(data.get(k), list):
                return data[k]
        return []
    if isinstance(data, list):
        return data
    return []

def load_matches_from_old_repo():
    # 1. Ambil yang utama dulu (200 terbaru)
    merged = {}
    try:
        main_data = _fetch_json(RAW_BASE + "data/matches.json")
        for m in _extract_matches(main_data):
            mid = str(m.get("match_id") or m.get("id") or f"{m.get('home_team')}-{m.get('away_team')}-{m.get('detected_at_utc')}")
            merged[mid] = m
    except Exception as e:
        print(f"[data_loader] gagal baca matches.json: {e}")

    # 2. Ambil daftar arsip harian via GitHub API
    try:
        listing = _fetch_json(API_BASE + "data/archive/daily?ref=" + BRANCH)
        if isinstance(listing, list):
            for item in listing:
                name = item.get("name", "")
                if not name.endswith(".json"):
                    continue
                try:
                    arch_data = _fetch_json(item.get("download_url"))
                    for m in _extract_matches(arch_data):
                        mid = str(m.get("match_id") or m.get("id") or f"{m.get('home_team')}-{m.get('away_team')}-{m.get('detected_at_utc')}")
                        # Kalau sudah ada di matches.json, jangan timpa (yang di matches.json lebih baru)
                        if mid not in merged:
                            merged[mid] = m
                except Exception:
                    continue
    except Exception as e:
        print(f"[data_loader] gagal baca arsip: {e}")

    # 3. Urutkan by detected_at_utc / trading_day biar yang terbaru di atas
    records = list(merged.values())
    records.sort(key=lambda x: str(x.get("detected_at_utc") or x.get("trading_day") or ""), reverse=True)
    print(f"[data_loader] total gabungan: {len(records)} (200 utama + arsip)")
    return records

def load_scan_metadata():
    try:
        data = _fetch_json(RAW_BASE + "data/scan_meta.json")
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"scan_timestamp_wita": "DARI REPO LAMA skor60", "source_status": "LOADED_FROM_OLD_REPO + ARCHIVE"}
