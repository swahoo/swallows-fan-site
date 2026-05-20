#!/usr/bin/env python3
"""
燕の巣 — 東京ヤクルトスワローズ ファンサイト 自動更新スクリプト
毎日NPB公式からデータを取得してindex.htmlを更新する
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone, timedelta, date
import json

JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
today = now.strftime('%Y/%m/%d')
today_badge = now.strftime('%Y.%m.%d')
today_str = now.strftime('%Y年%m月%d日')
today_date = now.date()

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; SwallowsFanSite/1.0)'}

def fetch(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        return BeautifulSoup(res.text, 'html.parser')
    except Exception as e:
        print(f'  ⚠️  取得失敗: {url} -> {e}')
        return None

# ============================================================
# 1. セ・リーグ順位表
# ============================================================
def get_standings():
    print('📊 順位表取得中...')
    soup = fetch('https://npb.jp/bis/2026/stats/std_c.html')
    if not soup:
        return None
    teams = []
    table = soup.find('table')
    if not table:
        return None
    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 8:
            teams.append({
                'name': cols[1].get_text(strip=True),
                'games': cols[2].get_text(strip=True),
                'wins': cols[3].get_text(strip=True),
                'losses': cols[4].get_text(strip=True),
                'draws': cols[5].get_text(strip=True),
                'pct': cols[6].get_text(strip=True),
                'gb': cols[7].get_text(strip=True),
            })
    return teams if teams else None

def build_standings_rows(teams):
    """順位表の行HTMLを生成（トップページ用・簡易版）"""
    rank_class = ['rk1','rk2','rk3','rk4','rk5','rk6']
    name_map = {
        'ヤクルト': 'ヤクルト', '阪神': '阪神', '巨人': '巨人', '読売': '巨人',
        'DeNA': 'DeNA', '横浜': 'DeNA', '広島': '広島', '中日': '中日'
    }
    html = ''
    for i, t in enumerate(teams[:6]):
        rank = i + 1
        rc = rank_class[i] if i < 6 else 'rk4'
        name = t['name']
        for k, v in name_map.items():
            if k in name:
                name = v
                break
        is_ys = 'ヤクルト' in t['name']
        tr = ' class="ys"' if is_ys else ''
        html += f'<tr{tr}><td><span class="rk {rc}">{rank}</span></td><td class="l">{name}</td><td>{t["games"]}</td><td class="win">{t["wins"]}</td><td class="lose">{t["losses"]}</td><td>{t["pct"]}</td><td>{t["gb"]}</td></tr>'
    return html

def build_standings_rows_detail(teams):
    """順位タブ用詳細版（ホーム/ロード含む）"""
    rank_class = ['rk1','rk2','rk3','rk4','rk5','rk6']
    full_names = {
        'ヤクルト': 'ヤクルト', '阪神': '阪神タイガース', '巨人': '巨人ジャイアンツ',
        '読売': '巨人ジャイアンツ', 'DeNA': '横浜DeNAベイスターズ', '横浜': '横浜DeNAベイスターズ',
        '広島': '広島東洋カープ', '中日': '中日ドラゴンズ'
    }
    html = ''
    for i, t in enumerate(teams[:6]):
        rank = i + 1
        rc = rank_class[i] if i < 6 else 'rk4'
        name = t['name']
        full = name
        for k, v in full_names.items():
            if k in name:
                full = v
                break
        is_ys = 'ヤクルト' in t['name']
        tr = ' class="ys"' if is_ys else ''
        html += f'<tr{tr}><td><span class="rk {rc}">{rank}</span></td><td class="l">{full}</td><td>{t["games"]}</td><td class="win">{t["wins"]}</td><td class="lose">{t["losses"]}</td><td>{t["draws"]}</td><td>{t["pct"]}</td><td>{t["gb"]}</td><td>—</td><td>—</td></tr>'
    return html

# ============================================================
# 2. 試合結果（月別）
# ============================================================
def get_game_results():
    """全月の試合結果を取得して月別集計"""
    print('📅 試合結果取得中...')
    month_urls = {
        '3・4月': 'https://npb.jp/bis/teams/results_s_04.html',
        '5月': 'https://npb.jp/bis/teams/results_s_05.html',
        '6月': 'https://npb.jp/bis/teams/results_s_06.html',
        '7月': 'https://npb.jp/bis/teams/results_s_07.html',
        '8月': 'https://npb.jp/bis/teams/results_s_08.html',
        '9月': 'https://npb.jp/bis/teams/results_s_09.html',
    }

    monthly = {}
    season_total = {'wins': 0, 'losses': 0, 'draws': 0, 'runs': 0, 'runs_against': 0, 'games': 0}
    today_game = None
    next_game = None

    for month_name, url in month_urls.items():
        soup = fetch(url)
        if not soup:
            continue

        wins = losses = draws = runs = runs_against = 0
        rows = []

        table = soup.find('table')
        if not table:
            continue

        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) < 8:
                continue
            score_text = cols[6].get_text(strip=True) if len(cols) > 6 else ''
            result = cols[7].get_text(strip=True) if len(cols) > 7 else ''
            date_text = cols[0].get_text(strip=True) if cols else ''
            opponent = cols[1].get_text(strip=True) if len(cols) > 1 else ''
            stadium = cols[3].get_text(strip=True) if len(cols) > 3 else ''

            if not score_text or '-' not in score_text:
                # 未消化試合かも
                # 今日の試合チェック
                if date_text and opponent:
                    rows.append({'date': date_text, 'opponent': opponent, 'stadium': stadium, 'score': '', 'result': ''})
                continue

            parts = score_text.split('-')
            if len(parts) == 2:
                try:
                    r = int(parts[0].strip())
                    ra = int(parts[1].strip())
                    runs += r
                    runs_against += ra
                    if result == '○':
                        wins += 1
                    elif result == '●':
                        losses += 1
                    elif result == '△':
                        draws += 1
                    rows.append({'date': date_text, 'opponent': opponent, 'stadium': stadium,
                                 'score': score_text, 'result': result})
                except:
                    pass

        games = wins + losses + draws
        if games > 0:
            pct = wins / (wins + losses) if (wins + losses) > 0 else 0
            monthly[month_name] = {
                'games': games, 'wins': wins, 'losses': losses, 'draws': draws,
                'pct': f'{pct:.3f}', 'runs': runs, 'runs_against': runs_against
            }
            season_total['wins'] += wins
            season_total['losses'] += losses
            season_total['draws'] += draws
            season_total['runs'] += runs
            season_total['runs_against'] += runs_against
            season_total['games'] += games

    return monthly, season_total

# ============================================================
# 3. 今日の試合
# ============================================================
def get_today_game():
    print('⚾ 今日の試合取得中...')
    soup = fetch('https://npb.jp/scores/')
    if not soup:
        return None

    today_fmt = now.strftime('%-m/%-d')  # e.g. "5/19"
    games_info = []

    for link in soup.find_all('a', href=True):
        text = link.get_text(strip=True)
        href = link.get('href', '')
        if 'scores/2026' in href and 's-' in href or '-s-' in href:
            games_info.append({'text': text, 'href': href})

    return games_info

# ============================================================
# 4. チーム成績（baseball-data-store）
# ============================================================
def get_team_stats():
    print('📈 チーム成績取得中...')
    soup = fetch('https://baseball-data-store.com/team/1/stats/1st?year=2026')
    if not soup:
        return None

    stats = {}
    text = soup.get_text()

    patterns = {
        '防御率': r'防御率\s*([\d.]+)',
        '打率': r'打率\s*([\d.]+)',
        '得点': r'得点\s*(\d+)',
        '本塁打': r'本塁打\s*(\d+)',
        '盗塁': r'盗塁\s*(\d+)',
        '出塁率': r'出塁率\s*([\d.]+)',
        '長打率': r'長打率\s*([\d.]+)',
        'OPS': r'OPS\s*([\d.]+)',
        'WHIP': r'WHIP\s*([\d.]+)',
        '奪三振': r'奪三振\s*(\d+)',
        'セーブ': r'セーブ\s*(\d+)',
        'ホールド': r'ホールド\s*(\d+)',
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            stats[key] = m.group(1)

    return stats if stats else None

# ============================================================
# 5. HTML更新
# ============================================================
def update_html(standings, monthly, season, team_stats):
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # --- 日付バッジ更新 ---
    html = re.sub(r'NPB公式 \d{4}\.\d{2}\.\d{2}', f'NPB公式 {today_badge}', html)
    html = re.sub(r'NPB \d{4}\.\d{2}\.\d{2}', f'NPB {today_badge}', html)
    html = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日現在', f'{today_str}現在', html)
    html = re.sub(r'5/18現在', f'{today_badge}現在', html)

    # --- 順位表更新（トップページ簡易版）---
    if standings:
        rows_simple = build_standings_rows(standings)
        # トップの簡易順位表を置換
        pattern = r'(<thead><tr><th class="l" colspan="2">チーム</th><th>試合</th><th>勝</th><th>負</th><th>勝率</th><th>差</th></tr></thead>\s*<tbody>)(.*?)(</tbody>)'
        replacement = r'\g<1>' + rows_simple + r'\g<3>'
        html = re.sub(pattern, replacement, html, flags=re.DOTALL)

        # ヒーローのKPI（勝数・敗数・勝率・貯金）
        total_wins = sum(int(t['wins']) for t in standings[:6] if t['name'] and 'ヤクルト' in t['name']) or None
        ys = next((t for t in standings if 'ヤクルト' in t['name']), None)
        if ys:
            w, l = int(ys['wins']), int(ys['losses'])
            貯金 = w - l
            html = re.sub(r'<span class="kpi-num">\d+</span>\s*<div class="kpi-label">WIN', f'<span class="kpi-num">{w}</span>\n        <div class="kpi-label">WIN', html)
            html = re.sub(r'<span class="kpi-num red">\d+</span>\s*<div class="kpi-label">LOSE', f'<span class="kpi-num red">{l}</span>\n        <div class="kpi-label">LOSE', html)
            html = re.sub(r'<span class="kpi-num gold">[.\d]+</span>\s*<div class="kpi-label">勝率', f'<span class="kpi-num gold">{ys["pct"]}</span>\n        <div class="kpi-label">勝率', html)
            貯金_str = f'+{貯金}' if 貯金 >= 0 else str(貯金)
            html = re.sub(r'<span class="kpi-num">[+\-\d]+</span>\s*<div class="kpi-label">貯金', f'<span class="kpi-num">{貯金_str}</span>\n        <div class="kpi-label">貯金', html)

            # シーズン成績ボックス
            html = re.sub(r'<span class="rec-num g">\d+</span><div class="rec-lbl">勝利', f'<span class="rec-num g">{w}</span><div class="rec-lbl">勝利', html)
            html = re.sub(r'<span class="rec-num r">\d+</span><div class="rec-lbl">敗戦', f'<span class="rec-num r">{l}</span><div class="rec-lbl">敗戦', html)
            html = re.sub(r'<span class="rec-num gold">[.\d]+</span><div class="rec-lbl">勝率', f'<span class="rec-num gold">{ys["pct"]}</span><div class="rec-lbl">勝率', html)
            html = re.sub(r'<span class="rec-num g">[+\-\d]+</span><div class="rec-lbl">貯金', f'<span class="rec-num g">{貯金_str}</span><div class="rec-lbl">貯金', html)

    # --- 月別成績更新 ---
    if monthly:
        rows_html = ''
        total_w = total_l = total_d = total_r = total_ra = total_g = 0
        for mname, m in monthly.items():
            rows_html += f'<tr><td class="l">{mname}</td><td>{m["games"]}</td><td class="win">{m["wins"]}</td><td class="lose">{m["losses"]}</td><td>{m["draws"]}</td><td>{m["pct"]}</td><td>{m["runs"]}</td><td>{m["runs_against"]}</td></tr>'
            total_w += m['wins']
            total_l += m['losses']
            total_d += m['draws']
            total_r += m['runs']
            total_ra += m['runs_against']
            total_g += m['games']
        total_pct = f'{total_w/(total_w+total_l):.3f}' if (total_w+total_l) > 0 else '.000'
        rows_html += f'<tr class="ys"><td class="l">合計</td><td>{total_g}</td><td class="win">{total_w}</td><td class="lose">{total_l}</td><td>{total_d}</td><td>{total_pct}</td><td>{total_r}</td><td>{total_ra}</td></tr>'

        pattern = r'(<thead><tr><th class="l">月</th>.*?</thead>\s*<tbody>)(.*?)(</tbody>)'
        replacement = r'\g<1>' + rows_html + r'\g<3>'
        html = re.sub(pattern, replacement, html, flags=re.DOTALL)

    # --- チーム成績更新 ---
    if team_stats:
        replacements = {
            r'チーム防御率</td><td class="hi">[.\d]+': f'チーム防御率</td><td class="hi">{team_stats.get("防御率", "—")}',
            r'WHIP</td><td>[.\d]+': f'WHIP</td><td>{team_stats.get("WHIP", "—")}',
            r'奪三振</td><td><strong>\d+': f'奪三振</td><td><strong>{team_stats.get("奪三振", "—")}',
            r'セーブ</td><td>\d+': f'セーブ</td><td>{team_stats.get("セーブ", "—")}',
            r'ホールド</td><td>\d+': f'ホールド</td><td>{team_stats.get("ホールド", "—")}',
            r'チーム打率</td><td class="hi">[.\d]+': f'チーム打率</td><td class="hi">{team_stats.get("打率", "—")}',
            r'本塁打</td><td><strong>\d+': f'本塁打</td><td><strong>{team_stats.get("本塁打", "—")}',
            r'盗塁</td><td><strong>\d+': f'盗塁</td><td><strong>{team_stats.get("盗塁", "—")}',
            r'出塁率</td><td>[.\d]+': f'出塁率</td><td>{team_stats.get("出塁率", "—")}',
            r'長打率</td><td>[.\d]+': f'長打率</td><td>{team_stats.get("長打率", "—")}',
            r'OPS</td><td class="hi">[.\d]+': f'OPS</td><td class="hi">{team_stats.get("OPS", "—")}',
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
    print(f'\n🐦 燕の巣 自動更新スクリプト')
    print(f'📅 実行日時: {today_str} (JST)\n')

    # 1. 順位表
    standings = get_standings()
    if standings:
        print(f'  ✅ 順位表: {len(standings)}チーム取得')
    else:
        print('  ⚠️  順位表: 取得失敗')

    # 2. 月別成績
    monthly, season = get_game_results()
    if monthly:
        print(f'  ✅ 月別成績: {list(monthly.keys())} 取得')
    else:
        print('  ⚠️  月別成績: 取得失敗')

    # 3. チーム成績
    team_stats = get_team_stats()
    if team_stats:
        print(f'  ✅ チーム成績: {list(team_stats.keys())} 取得')
    else:
        print('  ⚠️  チーム成績: 取得失敗')

    # 4. HTML更新
    print('\n📝 HTML更新中...')
    update_html(standings, monthly, season, team_stats)

if __name__ == '__main__':
    main()
