#!/usr/bin/env python3
"""
横浜イベント情報スクレイパー
実行すると events.json を出力する。
GitHub Actions から毎日自動実行される。
"""

import json
import math
from datetime import date, datetime, timezone, timedelta

from server import scrape_all_venues

CENTER_LAT, CENTER_LNG = 35.4555, 139.6380
JST = timezone(timedelta(hours=9))

def main():
    now_jst = datetime.now(JST)
    target_date = now_jst.date()
    print(f"[scrape.py] {target_date.isoformat()} のイベントを取得中... (JST: {now_jst.strftime('%Y-%m-%d %H:%M')})")

    venues = scrape_all_venues(target_date)

    # 距離計算・ソート
    for v in venues:
        v["distance"] = round(
            math.sqrt((v["lat"] - CENTER_LAT)**2 + (v["lng"] - CENTER_LNG)**2) * 111, 1
        )
    venues.sort(key=lambda x: (0 if x["events"] else 1, x["distance"]))

    output = {
        "date": target_date.isoformat(),
        "scraped_at": now_jst.strftime("%Y-%m-%dT%H:%M"),
        "venues": venues,
    }

    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_events = sum(len(v["events"]) for v in venues)
    venues_with_events = sum(1 for v in venues if v["events"])
    print(f"[scrape.py] 完了: {venues_with_events}/{len(venues)}会場, {total_events}件 → events.json")

if __name__ == "__main__":
    main()
