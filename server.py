#!/usr/bin/env python3
"""横浜イベント検索 - 会場サイトスクレイピング版（Playwright対応）"""

import concurrent.futures
import html as html_mod
import http.server
import json
import math
import os
import re
import socketserver
import ssl
import urllib.parse
import urllib.request
from datetime import date, datetime

PORT = 8080


# =============================================
# 横浜主要会場のキュレーションデータ
# =============================================

YOKOHAMA_VENUES = [
    {
        "name": "Kアリーナ横浜",
        "lat": 35.4617,
        "lng": 139.6319,
        "type": "arena",
        "capacity": 20000,
        "schedule_urls": [
            "https://k-arena.com/schedule/",
        ],
        "js_rendered": True,
    },
    {
        "name": "ぴあアリーナMM",
        "lat": 35.4575,
        "lng": 139.6350,
        "type": "arena",
        "capacity": 10000,
        "schedule_urls": [
            "https://pia-arena-mm.jp/event/",
        ],
    },
    {
        "name": "横浜アリーナ",
        "lat": 35.5094,
        "lng": 139.6172,
        "type": "arena",
        "capacity": 17000,
        "schedule_urls": [
            "https://www.yokohama-arena.co.jp/event/",
        ],
        "js_rendered": True,
    },
    {
        "name": "横浜スタジアム",
        "lat": 35.4434,
        "lng": 139.6401,
        "type": "stadium",
        "capacity": 34046,
        "schedule_urls": [
            "https://www.baystars.co.jp/game/schedule/",
        ],
    },
    {
        "name": "日産スタジアム",
        "lat": 35.5103,
        "lng": 139.6064,
        "type": "stadium",
        "capacity": 72327,
        "schedule_urls": [
            "https://www.nissan-stadium.jp/",
        ],
    },
    {
        "name": "横浜みなとみらいホール",
        "lat": 35.4535,
        "lng": 139.6384,
        "type": "hall",
        "capacity": 2020,
        "schedule_urls": [
            "https://yokohama-minatomiraihall.jp/concert/index.html",
        ],
        "js_rendered": True,
    },
    {
        "name": "横浜赤レンガ倉庫",
        "lat": 35.4530,
        "lng": 139.6436,
        "type": "hall",
        "capacity": 0,
        "schedule_urls": [
            "https://www.yokohama-akarenga.jp/event/",
        ],
    },
    {
        "name": "横浜関内ホール",
        "lat": 35.4447,
        "lng": 139.6365,
        "type": "hall",
        "capacity": 1106,
        "schedule_urls": [
            "https://www.kannaihall.jp/schedule/",
        ],
    },
    {
        "name": "横浜にぎわい座",
        "lat": 35.4430,
        "lng": 139.6372,
        "type": "hall",
        "capacity": 392,
        "schedule_urls": [
            "https://nigiwaiza.yafjp.org/perform/",
        ],
    },
    {
        "name": "KAAT神奈川芸術劇場",
        "lat": 35.4476,
        "lng": 139.6486,
        "type": "hall",
        "capacity": 1270,
        "schedule_urls": [
            "https://www.kaat.jp/calendar/",
        ],
        "js_rendered": True,
    },
    {
        "name": "パシフィコ横浜",
        "lat": 35.4582,
        "lng": 139.6372,
        "type": "hall",
        "capacity": 5002,
        "schedule_urls": [
            "https://www.pacifico.co.jp/eventInfo",
        ],
        "js_rendered": True,
    },
    {
        "name": "神奈川県立音楽堂",
        "lat": 35.4474,
        "lng": 139.6327,
        "type": "hall",
        "capacity": 1106,
        "schedule_urls": [
            "https://www.kanagawa-ongakudo.com/event/",
        ],
    },
    {
        "name": "横浜ベイホール",
        "lat": 35.4605,
        "lng": 139.6480,
        "type": "livehouse",
        "capacity": 700,
        "schedule_urls": [
            "https://bayhall.jp/schedule/",
        ],
    },
    {
        "name": "F.A.D YOKOHAMA",
        "lat": 35.4430,
        "lng": 139.6380,
        "type": "livehouse",
        "capacity": 250,
        "schedule_urls": [
            "http://www.fad-music.com/fad/?page_id=3",
        ],
    },
    {
        "name": "横浜ランドマークホール",
        "lat": 35.4555,
        "lng": 139.6324,
        "type": "hall",
        "capacity": 500,
        "schedule_urls": [
            "https://landmarkhall.jp/schedule/",
        ],
    },
    {
        "name": "神奈川県民ホール",
        "lat": 35.4477,
        "lng": 139.6505,
        "type": "hall",
        "capacity": 2493,
        "schedule_urls": [
            "https://www.kanagawa-kenminhall.com/event/",
        ],
        "note": "2025年3月末に休館",
    },
]


# =============================================
# HTML取得ユーティリティ
# =============================================

def fetch_html_playwright(url, timeout=20):
    """PlaywrightでJSレンダリング後のHTMLを取得"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "ja,en;q=0.9"})
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            # 追加で少し待機（非同期データ読み込み対応）
            page.wait_for_timeout(1500)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"    [Playwright] エラー: {url} - {e}")
        return None


def fetch_html(url, timeout=10):
    """URLからHTMLを取得"""
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        req.add_header("Accept", "text/html,application/xhtml+xml,*/*")
        req.add_header("Accept-Language", "ja,en;q=0.9")
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            content_type = resp.headers.get("Content-Type", "")
            encoding = "utf-8"
            if "charset=" in content_type:
                encoding = content_type.split("charset=")[-1].strip().split(";")[0]
            raw = resp.read(512_000)
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                return raw.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    [Fetch] エラー: {url} - {e}")
        return None


def clean_text(s):
    """文字列の空白・記号を整理"""
    s = html_mod.unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def guess_genre(title):
    """タイトルからジャンルを推定"""
    t = title.upper()
    if any(w in t for w in ['VS', 'ＶＳ', 'リーグ', '対 ', '試合', 'BASEBALL', 'SOCCER', 'FOOTBALL']):
        return "スポーツ"
    if any(w in t for w in ['TOUR', 'LIVE', 'ライブ', 'CONCERT', 'コンサート', 'ツアー', 'FES', 'フェス', 'FESTIVAL']):
        return "ライブ"
    if any(w in t for w in ['交響楽', 'オーケストラ', 'リサイタル', 'ピアノ', 'オルガン', 'クラシック', 'ORCHESTRA', 'SYMPHONY']):
        return "クラシック"
    if any(w in t for w in ['落語', '演芸', '寄席', '漫才', '講談', 'お笑い']):
        return "演芸"
    if any(w in t for w in ['ミュージカル', '演劇', '舞台', '芝居', 'シアター', 'THEATER', 'MUSICAL']):
        return "舞台"
    if any(w in t for w in ['展覧', 'EXHIBITION', 'アート展', '博覧']):
        return "展示"
    return "イベント"


# =============================================
# 会場ごとの専用パーサー
# =============================================

def parse_pia_arena_mm(html, url, target_date=None):
    """ぴあアリーナMM: event-list__date + event-list__detail 構造"""
    today = target_date or date.today()
    today_str = f"{today.month:02d}.{today.day:02d}"  # "04.01"
    events = []

    # <a class="event-list" href="..."> ブロックを全て抽出
    blocks = re.findall(
        r'<a\s+class="event-list"\s+href="([^"]+)">(.*?)</a>',
        html, re.DOTALL
    )
    for href, block in blocks:
        # 日付チェック
        date_m = re.search(r'<p>(\d{2}\.\d{2})</p>', block)
        if not date_m or date_m.group(1) != today_str:
            continue
        # PRIVATEスキップ
        if 'PRIVATE' in block.upper():
            continue

        # タイトル: <h3> または <p> in event-list__detail
        h3 = re.search(r'<h3[^>]*>([^<]+)</h3>', block)
        p_title = re.search(r'class="title"[^>]*>.*?<h3[^>]*>([^<]+)</h3>.*?<p>([^<]+)</p>', block, re.DOTALL)

        artist = clean_text(h3.group(1)) if h3 else ""
        subtitle = clean_text(p_title.group(2)) if p_title else ""

        title = subtitle if subtitle else artist
        if not title:
            continue

        # 時間
        time_m = re.search(r'(?:OPEN|開場)[^\d]*(\d{1,2})[:\uff1a](\d{2})', block, re.IGNORECASE)
        start_m = re.search(r'(?:START|開演)[^\d]*(\d{1,2})[:\uff1a](\d{2})', block, re.IGNORECASE)
        time_str = ""
        if start_m:
            time_str = f"{int(start_m.group(1)):02d}:{start_m.group(2)}"
        elif time_m:
            time_str = f"{int(time_m.group(1)):02d}:{time_m.group(2)}"

        # 詳細URL（相対パスを絶対パスに）
        if href.startswith("http"):
            detail_url = href
        else:
            base = url.rsplit("/", 1)[0]
            detail_url = base + "/" + href.lstrip("/")

        events.append({
            "title": title,
            "time": time_str or "時間未定",
            "genre": guess_genre(title),
            "url": detail_url,
        })

    return events


def parse_k_arena(html, url, target_date=None):
    """Kアリーナ横浜: 2026.MM.DD.Www. 形式"""
    today = target_date or date.today()
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    today_str = today.strftime(f"%Y.%m.%d.{weekdays[today.weekday()]}.")
    events = []

    # スケジュールアイテムを抽出（日付パターンで分割）
    # Kアリーナは "2026.04.01.Wed." 形式
    pattern = re.escape(today_str)
    sections = re.split(r'(?=\d{4}\.\d{2}\.\d{2}\.\w{3}\.)', html)
    for section in sections:
        if not section.startswith(today_str):
            continue
        # イベントタイトルを探す（h2, h3, strong, class="title" など）
        titles = re.findall(r'<(?:h[23]|strong|p)[^>]*class="[^"]*(?:title|name|event)[^"]*"[^>]*>([^<]{3,100})</(?:h[23]|strong|p)>', section)
        if not titles:
            titles = re.findall(r'<(?:h[23]|strong)[^>]*>([^<]{3,100})</(?:h[23]|strong)>', section)

        # OPEN/START時間
        start_m = re.search(r'START\s*(\d{1,2})[:\uff1a](\d{2})', section, re.IGNORECASE)
        time_str = f"{int(start_m.group(1)):02d}:{start_m.group(2)}" if start_m else "時間未定"

        for t in titles[:3]:
            t = clean_text(t)
            if len(t) >= 2 and 'PRIVATE' not in t.upper():
                events.append({
                    "title": t,
                    "time": time_str,
                    "genre": guess_genre(t),
                    "url": url,
                })
    return events


def parse_generic_by_date(html, url, target_date=None):
    """汎用パーサー: 指定日付付近のイベント情報を抽出"""
    today = target_date or date.today()
    weekdays_ja = ['月', '火', '水', '木', '金', '土', '日']
    wd = weekdays_ja[today.weekday()]

    # 日付パターン候補（優先度順）
    date_pats = [
        today.strftime("%Y年%-m月%-d日"),
        today.strftime("%Y年%m月%d日"),
        today.strftime("%-m月%-d日") + f"（{wd}）",
        today.strftime("%-m月%-d日") + f"({wd})",
        today.strftime("%-m月%-d日"),
        today.strftime("%m月%d日"),
        today.strftime("%Y/%m/%d"),
        today.strftime("%Y.%m.%d"),
        f"{today.month:02d}/{today.day:02d}",
        f"{today.month}/{today.day}",
    ]

    events = []
    # ノイズ除去
    html_clean = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)           # HTMLコメント除去
    html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)
    html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)
    html_clean = re.sub(r'<select[^>]*>.*?</select>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)  # selectメニュー除去

    for dpat in date_pats:
        idx = 0
        while True:
            pos = html_clean.find(dpat, idx)
            if pos == -1:
                break
            idx = pos + len(dpat)

            # 日付の後500文字のHTMLを取得してタグ除去
            chunk = html_clean[pos:pos + 600]
            text = re.sub(r'<[^>]+>', ' ', chunk)
            text = html_mod.unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()

            # 日付部分を除去して残りからタイトルを抽出
            text = text.replace(dpat, '').strip()
            text = re.sub(r'^[\s\-\|/・:：(（）)]+', '', text).strip()

            # 時間を抽出
            start_m = re.search(r'(?:開演|START)\s*(\d{1,2})[:\uff1a](\d{2})', text, re.IGNORECASE)
            open_m = re.search(r'(?:開場|OPEN)\s*(\d{1,2})[:\uff1a](\d{2})', text, re.IGNORECASE)
            time_str = ""
            if start_m:
                time_str = f"{int(start_m.group(1)):02d}:{start_m.group(2)}"
            elif open_m:
                time_str = f"{int(open_m.group(1)):02d}:{open_m.group(2)}"

            # タイトル候補（最初の意味ある部分）
            text = re.sub(r'\d{1,2}[:\uff1a]\d{2}', '', text)
            text = re.sub(r'(?:開演|開場|START|OPEN|CLOSE|前売|当日|全席|指定)[^\s]*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'[\d,]+円', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            text = re.sub(r'^[\s\-\|/・:：（()）,\.]+', '', text).strip()

            if not text or len(text) < 3:
                continue

            title = text[:100].split('　')[0].split('  ')[0].strip()
            if len(title) < 2 or 'PRIVATE' in title.upper():
                continue
            if re.match(r'^[\d\s/\.\-]+$', title):
                continue

            if not any(e["title"] == title for e in events):
                events.append({
                    "title": title,
                    "time": time_str or "時間未定",
                    "genre": guess_genre(title),
                    "url": url,
                })

            if len(events) >= 8:
                break
        if len(events) >= 8:
            break

    return events


def parse_yokohama_stadium(html, url, target_date=None):
    """横浜スタジアム: Yahoo Baseballから横浜DeNA試合情報を取得"""
    today = target_date or date.today()
    today_str = f"{today.month}月{today.day}日"  # "4月1日"
    events = []

    # 今日のセクションを探す
    pos = html.find(today_str)
    if pos == -1:
        return []

    section = html[pos:pos + 3000]

    # 全試合を抽出
    items = re.findall(r'<li class="bb-scoreList__item">(.*?)</li>', section, re.DOTALL)
    for item in items:
        # チーム名
        teams = re.findall(r'bb-scoreList__teamName[^>]*>([^<]+)<', item)
        if len(teams) < 2:
            continue

        home, away = teams[0].strip(), teams[1].strip()

        # 横浜DeNAが含まれる試合のみ
        if 'DeNA' not in home and 'DeNA' not in away and '横浜' not in home and '横浜' not in away:
            continue

        # 横浜スタジアムで行われるか（ホームゲーム = DeNAがホーム）
        is_home = 'DeNA' in home or '横浜' in home

        # 試合時刻
        time_m = re.search(r'centerScore[^>]*>(\d{2}:\d{2})<', item)
        time_str = time_m.group(1) if time_m else "時間未定"

        if is_home:
            title = f"横浜DeNA vs {away}"
            venue_note = "横浜スタジアム"
        else:
            title = f"横浜DeNA @ {home}（ビジター）"
            venue_note = ""
            # ビジターゲームはスキップ（横浜スタジアムではない）
            continue

        # 詳細URL
        link_m = re.search(r'href="(https://baseball\.yahoo\.co\.jp/npb/game/[^"]+)"', item)
        detail_url = link_m.group(1) if link_m else url

        events.append({
            "title": title,
            "time": time_str,
            "genre": "スポーツ",
            "url": detail_url,
        })

    return events


def parse_yokohama_arena(html, url, target_date=None):
    """横浜アリーナ: テーブル形式の日程から指定日のイベントを抽出"""
    today = target_date or date.today()
    today_label = f"{today.day}({['月','火','水','木','金','土','日'][today.weekday()]})"  # "1(水)"

    events = []
    # スクリプト・スタイル除去
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)

    # テーブル行を探す: 日付セル + イベント名セル
    # 「1(水) 設営日」「2(木) 平成フラミンゴ ...」形式
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', clean, re.DOTALL | re.IGNORECASE)
    for row in rows:
        text = re.sub(r'<[^>]+>', ' ', row)
        text = html_mod.unescape(re.sub(r'\s+', ' ', text)).strip()

        if not text.startswith(today_label):
            continue

        # 設営日・撤去日・休館日はスキップ
        if any(w in text for w in ['設営', '撤去', '休館', '準備']):
            continue

        # テキストから日付を除いてイベント名を抽出
        content = text[len(today_label):].strip()

        # 時間を抽出
        start_m = re.search(r'開演[：:\s]*(\d{1,2})[:\uff1a](\d{2})', content)
        open_m  = re.search(r'開場[：:\s]*(\d{1,2})[:\uff1a](\d{2})', content)
        time_str = ""
        if start_m:
            time_str = f"{int(start_m.group(1)):02d}:{start_m.group(2)}"
        elif open_m:
            time_str = f"{int(open_m.group(1)):02d}:{open_m.group(2)}"

        # イベント名: 時間・電話番号・主催者を除いた最初の部分
        title = re.sub(r'\d{1,2}[:\uff1a]\d{2}', ' ', content)
        title = re.sub(r'開[演場][：:]\s*\d+:\d+', ' ', title)
        title = re.sub(r'終演[：:]\s*\d+:\d+', ' ', title)
        title = re.sub(r'\d{2,4}-\d{4}-\d{4}', ' ', title)  # 電話番号
        title = re.sub(r'（平日[^）]*）', ' ', title)
        title = title.split('　')[0].split('  ')[0].strip()
        title = re.sub(r'\s+', ' ', title).strip()

        if title and len(title) >= 2 and not re.match(r'^[\d\s]+$', title):
            events.append({
                "title": title,
                "time": time_str or "時間未定",
                "genre": guess_genre(title),
                "url": url,
            })

    return events


def parse_nigiwaiza(html, url, target_date=None):
    """横浜にぎわい座: perform_list_inner_date_in + perform_inner_title 構造"""
    today = target_date or date.today()
    today_str = f"{today.month}/{today.day:02d}"  # "4/01"
    events = []

    # 各公演ブロック: <div class="perform_list_inner"> ... </div>
    blocks = re.findall(r'<div class="perform_list_inner">(.*?)</div>\s*</div>\s*</li>', html, re.DOTALL)
    for block in blocks:
        # 日付チェック
        date_m = re.search(r'class="perform_list_inner_date_in"[^>]*>\s*(\d+)/(\d+)', block)
        if not date_m:
            continue
        m, d = int(date_m.group(1)), int(date_m.group(2))
        if m != today.month or d != today.day:
            continue

        # タイトル: <p class="perform_inner_title"><a href="...">タイトル</a></p>
        title_m = re.search(r'class="perform_inner_title"[^>]*>\s*<a[^>]*>([^<]+)</a>', block)
        if not title_m:
            continue
        title = clean_text(title_m.group(1))
        if not title:
            continue

        # 時間: <p class="perform_inner_date">14:00開演...
        time_m = re.search(r'class="perform_inner_date"[^>]*>([^<]+)', block)
        time_str = ""
        if time_m:
            hm = re.search(r'(\d{1,2}):(\d{2})開演', time_m.group(1))
            if not hm:
                hm = re.search(r'(\d{1,2}):(\d{2})', time_m.group(1))
            if hm:
                time_str = f"{int(hm.group(1)):02d}:{hm.group(2)}"

        href_m = re.search(r'href="(https://nigiwaiza\.yafjp\.org/perform/archives/[^"]+)"', block)
        detail_url = href_m.group(1) if href_m else url

        events.append({
            "title": title,
            "time": time_str or "時間未定",
            "genre": guess_genre(title),
            "url": detail_url,
        })

    return events


def parse_bayhall(html, url, target_date=None):
    """横浜ベイホール: <div class="date">DD<span>Dow</span></div> 構造 (WordPress)"""
    today = target_date or date.today()
    weekdays_en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    today_day = f"{today.day:02d}"    # "01"
    today_dow = weekdays_en[today.weekday()]  # "Wed"
    events = []

    blocks = re.findall(
        r'<a\s+href="(https://bayhall\.jp/schedule/[^"]+)"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )
    for href, block in blocks:
        # <div class="date">01<span>Wed</span></div>
        date_m = re.search(r'class="date">(\d{2})<span>([A-Za-z]{3})</span>', block)
        if not date_m:
            continue
        if date_m.group(1) != today_day or date_m.group(2) != today_dow:
            continue

        title_m = re.search(r'<h3[^>]*>([^<]+)</h3>', block)
        if not title_m:
            continue
        title = clean_text(title_m.group(1))
        if not title or len(title) < 2:
            continue

        events.append({
            "title": title,
            "time": "時間未定",
            "genre": guess_genre(title),
            "url": href,
        })

    return events


def parse_landmarkhall(html, url, target_date=None):
    """横浜ランドマークホール: <dl><span>YYYY.M.D</span>...<dd>タイトル</dd></dl> 形式"""
    today = target_date or date.today()
    today_str = f"{today.year}.{today.month}.{today.day}"  # "2026.4.1"
    events = []

    # <dl id="post..."> ブロック内のスケジュール/URLを取得
    dl_blocks = re.findall(r'<dl[^>]*>(.*?)</dl>', html, re.DOTALL)
    for block in dl_blocks:
        # 日付チェック
        date_m = re.search(r'<span[^>]*>(\d{4}\.\d+\.\d+)</span>', block)
        if not date_m or date_m.group(1) != today_str:
            continue

        # URL
        href_m = re.search(r'href="(https://landmarkhall\.jp/schedule/[^"]+)"', block)
        if not href_m:
            continue
        href = href_m.group(1)

        # タイトル: <dd>タイトル</dd>
        title_m = re.search(r'<dd>([^<]+)</dd>', block)
        if not title_m:
            continue
        title = clean_text(title_m.group(1))
        if title == "Reserved":
            title = "詳細未定"
        if not title or len(title) < 2:
            continue

        events.append({
            "title": title,
            "time": "時間未定",
            "genre": guess_genre(title),
            "url": href,
        })

    return events


# パーサー登録: 会場名 -> (パーサー関数, URL)
VENUE_PARSERS = {
    "ぴあアリーナMM": (parse_pia_arena_mm, None),
    "Kアリーナ横浜": (parse_k_arena, None),
    "横浜スタジアム": (parse_yokohama_stadium, "https://baseball.yahoo.co.jp/npb/teams/3/schedule"),
    "横浜アリーナ": (parse_yokohama_arena, None),
    "横浜にぎわい座": (parse_nigiwaiza, None),
    "横浜ベイホール": (parse_bayhall, None),
    "横浜ランドマークホール": (parse_landmarkhall, None),
}


def scrape_venue(venue, target_date=None):
    """1つの会場のスケジュールページをスクレイピング"""
    venue_name = venue["name"]
    events = []
    fetch_failed = False
    parser_entry = VENUE_PARSERS.get(venue_name)

    if parser_entry:
        parser_fn, override_url = parser_entry
        # 横浜スタジアム: 月が違う場合はYahoo Baseball URLに月パラメータを付与
        if override_url and "baseball.yahoo.co.jp" in override_url and target_date:
            override_url = f"https://baseball.yahoo.co.jp/npb/teams/3/schedule?month={target_date.strftime('%Y%m')}"
        urls = [override_url] if override_url else venue.get("schedule_urls", [])
    else:
        parser_fn = parse_generic_by_date
        urls = venue.get("schedule_urls", [])

    use_playwright = venue.get("js_rendered", False)

    for url in urls:
        if use_playwright:
            print(f"  [PW] {venue_name} 取得中...")
            html = fetch_html_playwright(url)
        else:
            html = fetch_html(url)

        if not html:
            fetch_failed = True
            continue
        found = parser_fn(html, url, target_date)
        status = f"✓ {len(found)}件" if found else "- 0件"
        print(f"  {status} {venue_name} ({url.split('/')[2]})")
        events.extend(found)
        if events:
            break

    result = {
        "name": venue_name,
        "lat": venue["lat"],
        "lng": venue["lng"],
        "type": venue["type"],
        "capacity": venue["capacity"],
        "website": venue["schedule_urls"][0] if venue.get("schedule_urls") else "",
        "events": events[:10],
        # status: "ok" | "no_events" | "js_rendered" | "fetch_failed"
        "status": (
            "ok" if events else
            "js_rendered" if venue.get("js_rendered") else
            "fetch_failed" if fetch_failed else
            "no_events"
        ),
    }
    if venue.get("note"):
        result["note"] = venue["note"]
    return result


def scrape_all_venues(target_date=None, venue_names=None):
    """全会場（または指定会場）をスクレイピング（静的は並列、Playwrightは逐次）"""
    target_date = target_date or date.today()

    all_venues = YOKOHAMA_VENUES
    if venue_names:
        all_venues = [v for v in YOKOHAMA_VENUES if v["name"] in venue_names]

    print(f"\n{'='*50}")
    print(f"[Scrape] {len(all_venues)}会場 ({target_date.isoformat()}) をスクレイピング中...")

    static_venues = [v for v in all_venues if not v.get("js_rendered")]
    pw_venues     = [v for v in all_venues if v.get("js_rendered")]

    results = []

    # 静的サイトは並列
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(scrape_venue, v, target_date): v for v in static_venues}
        for future in concurrent.futures.as_completed(futures, timeout=30):
            try:
                results.append(future.result())
            except Exception as e:
                v = futures[future]
                print(f"  ✗ {v['name']}: エラー - {e}")
                results.append(_empty_venue(v))

    # Playwright対応サイトは逐次（ブラウザ競合を避ける）
    for v in pw_venues:
        try:
            results.append(scrape_venue(v, target_date))
        except Exception as e:
            print(f"  ✗ {v['name']}: エラー - {e}")
            results.append(_empty_venue(v))

    total = sum(len(v["events"]) for v in results)
    with_events = sum(1 for v in results if v["events"])
    print(f"[Scrape] 完了: {with_events}/{len(results)}会場, {total}件のイベント")
    return results


def _empty_venue(v):
    return {
        "name": v["name"], "lat": v["lat"], "lng": v["lng"],
        "type": v["type"], "capacity": v["capacity"],
        "website": v["schedule_urls"][0] if v.get("schedule_urls") else "",
        "events": [], "status": "fetch_failed",
    }


# =============================================
# HTTPハンドラ
# =============================================

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/venues":
            params = urllib.parse.parse_qs(parsed.query)

            # 日付パラメータ: ?date=2026-04-05
            date_str = params.get("date", [None])[0]
            try:
                target_date = date.fromisoformat(date_str) if date_str else date.today()
            except ValueError:
                target_date = date.today()

            # 会場フィルター: ?venues=ぴあアリーナMM,横浜にぎわい座
            venues_param = params.get("venues", [""])[0]
            venue_names = set(venues_param.split(",")) if venues_param else None

            venues = scrape_all_venues(target_date, venue_names)

            # イベントありを先に、距離順（みなとみらい中心点からの距離）
            center_lat, center_lng = 35.4555, 139.6380
            for v in venues:
                v["distance"] = round(
                    math.sqrt((v["lat"] - center_lat)**2 + (v["lng"] - center_lng)**2) * 111,
                    1
                )

            # イベントあり → なし、その中で距離順
            venues.sort(key=lambda x: (0 if x["events"] else 1, x["distance"]))

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(venues, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    today = date.today()
    print(f"🎵 横浜イベント検索サーバー起動中: http://localhost:{PORT}")
    print(f"   対象日: {today.isoformat()} ({['月','火','水','木','金','土','日'][today.weekday()]})")
    print(f"   登録会場: {len(YOKOHAMA_VENUES)}会場")
    for v in YOKOHAMA_VENUES:
        print(f"     - {v['name']}")
    class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True

    server = ThreadedHTTPServer(("", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました")
