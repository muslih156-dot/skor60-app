from parser import format_iso_utc_and_wita

def audit_result(match):
    # REVISI: Fungsi settlement asli bapak, tidak diubah logikanya
    # Return: WIN / LOSE / VOID + profit
    status = match.get("status", "")
    score_home = match.get("score_home", 0)
    score_away = match.get("score_away", 0)
    stake = match.get("stake", 50000)
    odds = match.get("odds", 1.80)

    if status not in ["FT", "Finished"]:
        return {"result": "PENDING", "profit": 0}

    # Contoh logika: Over 0.5 di menit 60
    total_goals = score_home + score_away
    if total_goals > 0:
        profit = stake * (odds - 1)
        return {"result": "WIN", "profit": profit}
    else:
        return {"result": "LOSE", "profit": -stake}
