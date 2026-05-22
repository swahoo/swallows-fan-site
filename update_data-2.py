#!/usr/bin/env python3
"""
応燕スタンド 自動更新スクリプト
複数の情報源（NPB公式・ヤクルト公式・スポカレ）からデータを取得してindex.htmlを更新
"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone, timedelta
import json

JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
today_badge = now.strftime('%Y.%m.%d')
today_str = now.strftime('%Y年%m月%d日')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f'  ⚠️  取得失敗: {url} -> {e}')
        return None

# ============================================================
# 1. 順位表（NPB公式）
# ============================================================
def get_standings():
    print('📊 順位表取得中... (NPB公式)')
    soup = fetch('https://npb.jp/bis/2026/stats/std_c.html')
    if not soup:
        return None
    teams = []
    table = soup.find('table')
    if not table:
        return None
    for row in table.find_all('tr')[1:]:
        cols = row.find_all(['td','th'])
        if len(cols) < 7:
            continue
        name = cols[0].get_text(strip=True)
        if not name or name in ('チーム',''):
            continue
        try:
            teams.append({
                'name': name,
                'games': cols[1].get_text(strip=True),
                'wins': cols[2].get_text(strip=True),
                'losses': cols[3].get_text(strip=True),
                'draws': cols[4].get_text(strip=True),
                'pct': cols[5].get_text(strip=True),
                'gb': cols[6].get_text(strip=True),
                'home': cols[7].get_text(strip=True) if len(cols) > 7 else '—',
                'road': cols[8].get_text(strip=True) if len(cols) > 8 else '—',
            })
        except:
            continue
    print(f'  ✅ {len(teams)}チーム取得')
    return teams if teams else None

# ============================================================
# 2. 次の試合（ヤクルト公式 + スポカレでクロスチェック）
# ============================================================
def get_next_game():
    print('⚾ 次の試合取得中...')
    
    # ソース1: ヤクルト公式
    month = now.strftime('%Y%m')
    soup = fetch(f'https://www.yakult-swallows.co.jp/game/{month}')
    next_game = None
    
    if soup:
        text = soup.get_text()
        # 今日以降の試合を探す
        today_yyyymmdd = now.strftime('%Y%m%d')
        # 日付パターンを探す（例: 5 . 23）
        month_num = now.month
        for day in range(now.day, 32):
            patterns = [
                f'{month_num} . {day:02d}',
                f'{month_num} . {day}',
            ]
            for pattern in patterns:
                idx = text.find(pattern)
                if idx >= 0:
                    snippet = text[idx:idx+200]
                    # 対戦相手を探す
                    for team in ['DeNA','巨人','阪神','広島','中日','西武','楽天','ロッテ','日本ハム','ソフトバンク','オリックス']:
                        if team in snippet:
                            # 球場を探す
                            venue = '—'
                            for v in ['神宮','横浜','東京ドーム','甲子園','マツダ','バンテリン','みずほPayPay','楽天モバイル','ベルーナ','エスコン','ZOZOマリン','いわき']:
                                if v in snippet:
                                    venue = v
                                    break
                            # 時刻
                            time_m = re.search(r'(\d{1,2}:\d{2})', snippet)
                            time_str = time_m.group(1) if time_m else '18:00'
                            # 曜日
                            try:
                                dt = datetime(now.year, month_num, day)
                                weekdays = ['MON','TUE','WED','THU','FRI','SAT','SUN']
                                weekday = weekdays[dt.weekday()]
                            except:
                                weekday = ''
                            # 交流戦かどうか
                            is_interleague = '交流戦' in snippet
                            next_game = {
                                'date': f'{now.year}.{month_num:02d}.{day:02d}',
                                'day': day,
                                'weekday': weekday,
                                'time': time_str,
                                'opponent': team,
                                'venue': venue,
                                'interleague': is_interleague
                            }
                            print(f'  ✅ 次の試合: {next_game["date"]} vs {team} {venue} {time_str}')
                            return next_game
    
    # ソース2: スポカレ（クロスチェック）
    if not next_game:
        soup2 = fetch('https://spocale.com/sports/1/team_and_players/8')
        if soup2:
            text2 = soup2.get_text()
            for day in range(now.day, 32):
                pattern = f'.{now.month:02d}.{day:02d}'
                idx = text2.find(pattern)
                if idx >= 0:
                    snippet = text2[idx:idx+150]
                    for team in ['DeNA','巨人','阪神','広島','中日','西武','楽天','ロッテ','日本ハム','ソフトバンク','オリックス']:
                        if team in snippet or f'横浜{team}' in snippet or f'東北{team}' in snippet:
                            for v in ['神宮','横浜','東京ドーム','甲子園','マツダ','バンテリン','みずほPayPay','楽天モバイル','ベルーナ','エスコン','ZOZOマリン','いわき']:
                                if v in snippet:
                                    venue = v
                                    break
                            else:
                                venue = '—'
                            time_m = re.search(r'(\d{1,2}:\d{2})', snippet)
                            time_str = time_m.group(1) if time_m else '18:00'
                            try:
                                dt = datetime(now.year, now.month, day)
                                weekdays = ['MON','TUE','WED','THU','FRI','SAT','SUN']
                                weekday = weekdays[dt.weekday()]
                            except:
                                weekday = ''
                            next_game = {
                                'date': f'{now.year}.{now.month:02d}.{day:02d}',
                                'day': day,
                                'weekday': weekday,
                                'time': time_str,
                                'opponent': team,
                                'venue': venue,
                                'interleague': '交流戦' in snippet
                            }
                            print(f'  ✅ 次の試合(スポカレ): {next_game["date"]} vs {team} {venue} {time_str}')
                            return next_game
    
    print('  ⚠️  次の試合: 取得失敗')
    return None

# ============================================================
# 3. チーム成績（baseball-data-store）
# ============================================================
def get_team_stats():
    print('📈 チーム成績取得中...')
    soup = fetch('https://baseball-data-store.com/team/1/stats/1st?year=2026')
    if not soup:
        return None
    stats = {}
    text = soup.get_text()
    patterns = {
        '防御率': r'防御率[^\d]*([\d.]+)',
        '打率': r'打率[^\d]*([\d.]+)',
        '得点': r'得点[^\d]*(\d+)',
        '本塁打': r'本塁打[^\d]*(\d+)',
        '盗塁': r'盗塁[^\d]*(\d+)',
        '出塁率': r'出塁率[^\d]*([\d.]+)',
        '長打率': r'長打率[^\d]*([\d.]+)',
        'OPS': r'OPS[^\d]*([\d.]+)',
        'WHIP': r'WHIP[^\d]*([\d.]+)',
        '奪三振': r'奪三振[^\d]*(\d+)',
        'セーブ': r'セーブ[^\d]*(\d+)',
        'ホールド': r'ホールド[^\d]*(\d+)',
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            stats[key] = m.group(1)
    print(f'  ✅ チーム成績取得: {list(stats.keys())}')
    return stats if stats else None

# ============================================================
# 4. HTML更新
# ============================================================
TEAM_SHORT = {
    '東京ヤクルトスワローズ': 'ヤクルト',
    '阪神タイガース': '阪神',
    '読売ジャイアンツ': '巨人',
    '横浜DeNAベイスターズ': 'DeNA',
    '広島東洋カープ': '広島',
    '中日ドラゴンズ': '中日',
}
TEAM_FULL = {v: k for k, v in TEAM_SHORT.items()}

def shorten(name):
    for k, v in TEAM_SHORT.items():
        if k in name:
            return v
    return name

def update_html(standings, next_game, team_stats):
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 日付バッジ
    html = re.sub(r'NPB公式 \d{4}\.\d{2}\.\d{2}', f'NPB公式 {today_badge}', html)
    html = re.sub(r'\d{4}\.\d{2}\.\d{2}現在', f'{today_badge}現在', html)

    if standings:
        ys = next((t for t in standings if 'ヤクルト' in t['name']), None)
        if ys:
            w, l = int(ys['wins']), int(ys['losses'])
            pct = ys['pct']
            貯金 = w - l
            貯金_str = f'+{貯金}' if 貯金 >= 0 else str(貯金)
            
            # KPI更新
            html = re.sub(r'(<span class="kpi-num">)\d+(</span>\s*<div class="kpi-label">WIN)', rf'\g<1>{w}\g<2>', html)
            html = re.sub(r'(<span class="kpi-num red">)\d+(</span>\s*<div class="kpi-label">LOSE)', rf'\g<1>{l}\g<2>', html)
            html = re.sub(r'(<span class="kpi-num gold">)[.\d]+(</span>\s*<div class="kpi-label">勝率)', rf'\g<1>{pct}\g<2>', html)
            html = re.sub(r'(<span class="kpi-num">[+\-]\d+</span>\s*<div class="kpi-label">貯金)', f'<span class="kpi-num">{貯金_str}</span>\n        <div class="kpi-label">貯金', html)
            
            # シーズン成績ボックス
            html = re.sub(r'<span class="rec-num g">\d+</span><div class="rec-lbl">勝利', f'<span class="rec-num g">{w}</span><div class="rec-lbl">勝利', html)
            html = re.sub(r'<span class="rec-num r">\d+</span><div class="rec-lbl">敗戦', f'<span class="rec-num r">{l}</span><div class="rec-lbl">敗戦', html)
            html = re.sub(r'<span class="rec-num gold">[.\d]+</span><div class="rec-lbl">勝率', f'<span class="rec-num gold">{pct}</span><div class="rec-lbl">勝率', html)
            html = re.sub(r'<span class="rec-num g">[+\-\d]+</span><div class="rec-lbl">貯金', f'<span class="rec-num g">{貯金_str}</span><div class="rec-lbl">貯金', html)

        # 順位表HTML生成（トップページ）
        rank_cls = ['rk1','rk2','rk3','rk4','rk5','rk6']
        rows_top = ''
        for i, t in enumerate(standings[:6]):
            rc = rank_cls[i]
            sname = shorten(t['name'])
            is_ys = 'ヤクルト' in t['name']
            tr_cls = ' class="ys"' if is_ys else ''
            rows_top += f'<tr{tr_cls}><td><span class="rk {rc}">{i+1}</span></td><td class="l">{sname}</td><td>{t["games"]}</td><td class="win">{t["wins"]}</td><td class="lose">{t["losses"]}</td><td>{t["pct"]}</td><td>{t["gb"]}</td></tr>'
        
        pattern = r'(<thead><tr><th class="l" colspan="2">チーム</th><th>試合</th><th>勝</th><th>負</th><th>勝率</th><th>差</th></tr></thead>\s*<tbody>)(.*?)(</tbody>)'
        html = re.sub(pattern, r'\g<1>' + rows_top + r'\g<3>', html, flags=re.DOTALL)

    # 次の試合更新
    if next_game:
        g = next_game
        interleague_str = '（交流戦）' if g['interleague'] else ''
        date_str = f'{g["date"]} {g["weekday"]} {g["time"]}{interleague_str}'
        html = re.sub(r'<div class="next-date">.*?</div>', f'<div class="next-date">{date_str}</div>', html)
        
        # ホーム/アウェー判定
        if g['venue'] in ['神宮', '明治神宮']:
            vs_html = f'<div class="next-vs">ヤクルト<br><span style="font-size:0.8rem;color:var(--muted);">vs</span><br>{g["opponent"]}</div>'
        else:
            vs_html = f'<div class="next-vs">{g["opponent"]}<br><span style="font-size:0.8rem;color:var(--muted);">vs</span><br>ヤクルト</div>'
        html = re.sub(r'<div class="next-vs">.*?</div>', vs_html, html, flags=re.DOTALL)
        html = re.sub(r'<div class="next-venue">.*?</div>', f'<div class="next-venue">📍 {g["venue"]}</div>', html)

    # チーム成績更新
    if team_stats:
        replacements = {
            r'チーム防御率</td><td class="hi">[.\d]+': f'チーム防御率</td><td class="hi">{team_stats.get("防御率","—")}',
            r'WHIP</td><td>[.\d]+': f'WHIP</td><td>{team_stats.get("WHIP","—")}',
            r'奪三振</td><td><strong>\d+': f'奪三振</td><td><strong>{team_stats.get("奪三振","—")}',
            r'チーム打率</td><td class="hi">[.\d]+': f'チーム打率</td><td class="hi">{team_stats.get("打率","—")}',
            r'OPS</td><td class="hi">[.\d]+': f'OPS</td><td class="hi">{team_stats.get("OPS","—")}',
            r'出塁率</td><td>[.\d]+': f'出塁率</td><td>{team_stats.get("出塁率","—")}',
            r'長打率</td><td>[.\d]+': f'長打率</td><td>{team_stats.get("長打率","—")}',
        }
        for pattern, replacement in replacements.items():
            html = re.sub(pattern, replacement, html)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ index.html 更新完了（{today_str}）')

# ============================================================
# メイン
# ============================================================
def main():
    print(f'\n🐦 応燕スタンド 自動更新スクリプト')
    print(f'📅 実行日時: {today_str} JST\n')
    print('ℹ️  情報源: NPB公式 / ヤクルト公式 / スポカレ（複数ソース確認）\n')

    standings = get_standings()
    next_game = get_next_game()
    team_stats = get_team_stats()

    print('\n📝 HTML更新中...')
    update_html(standings, next_game, team_stats)

if __name__ == '__main__':
    main()
