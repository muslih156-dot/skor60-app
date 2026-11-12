import requests
import json

# SUDAH DIBETULIN SESUAI USERNAME BAPAK
OLD_REPO_RAW = "https://raw.githubusercontent.com/muslih156-dot/skor60/main/data/matches.json"

def load_matches_from_old_repo():
    try:
        r = requests.get(OLD_REPO_RAW, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                return data.get("matches", []) or data.get("data", []) or []
            return data
        return []
    except Exception as e:
        print(f"Gagal load data lama: {e}")
        return []
