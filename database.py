import json
import os
from parser import compute_trading_day, format_iso_utc_and_wita

# REVISI: Mode baca saja, tidak menulis ke data/ lagi
# Biar repo baru tidak bengkak 3981 commit lagi

class TradingDatabase:
    def __init__(self, db_path=None):
        self.matches = []

    def get_all_matches(self):
        return self.matches

    def get_matches_by_day(self, trading_day):
        return [m for m in self.matches if m.get("trading_day") == trading_day]
