import math

def calculate_stats(matches):
    total = len(matches)
    if total == 0:
        return {"total": 0, "win_rate": 0, "roi": 0, "total_profit": 0}

    wins = sum(1 for m in matches if m.get("result") == "WIN" or m.get("settlement") == "WIN")
    loses = sum(1 for m in matches if m.get("result") == "LOSE" or m.get("settlement") == "LOSE")
    total_profit = sum(m.get("profit", 0) for m in matches)
    total_stake = sum(m.get("stake", 50000) for m in matches)

    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (total_profit / total_stake * 100) if total_stake > 0 else 0

    # Wilson Score untuk Win Rate yang lebih akurat
    z = 1.96
    p = wins / total if total > 0 else 0
    denominator = 1 + z**2 / total
    centre = p + z**2 / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)
    wilson = (centre - margin) / denominator * 100 if total > 0 else 0

    return {
        "total": total,
        "wins": wins,
        "loses": loses,
        "win_rate": win_rate,
        "wilson": wilson,
        "roi": roi,
        "total_profit": total_profit,
    }
