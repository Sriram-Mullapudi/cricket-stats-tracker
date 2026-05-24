"""
CricMetrics — Premium Cricket Analytics Dashboard
Backend: Flask + SQLite
Advanced analytics: Impact Score, Consistency Score, Form Index, Contribution %
"""

from flask import Flask, render_template, request, redirect, flash, send_file, jsonify
import sqlite3
from collections import defaultdict
import csv, io, os, json, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'cricmetrics_v3_2026'
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'matches.db')

# ─── DATABASE ────────────────────────────────────────────────────────────────
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS match_stats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            batsman     TEXT    NOT NULL,
            bowler      TEXT    NOT NULL,
            runs        INTEGER NOT NULL DEFAULT 0,
            balls       INTEGER NOT NULL DEFAULT 1,
            wickets     INTEGER NOT NULL DEFAULT 0,
            fours       INTEGER NOT NULL DEFAULT 0,
            sixes       INTEGER NOT NULL DEFAULT 0,
            match_date  TEXT    NOT NULL,
            match_name  TEXT    DEFAULT 'Match',
            innings     INTEGER DEFAULT 1,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit(); conn.close()

# ─── ANALYTICS ENGINE ─────────────────────────────────────────────────────────
def _std_dev(values):
    if len(values) < 2: return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))

def _trend(values):
    """Linear regression slope — positive = improving"""
    n = len(values)
    if n < 2: return 0.0
    sx = sum(range(n)); sy = sum(values)
    sxy = sum(i * v for i, v in enumerate(values))
    sxx = sum(i * i for i in range(n))
    denom = n * sxx - sx * sx
    return round((n * sxy - sx * sy) / denom, 3) if denom else 0.0

def calc_batting_metrics(s, all_avg_sr=100.0):
    """Compute advanced batting metrics from aggregated stats dict."""
    runs, balls, innings = s['runs'], s['balls'], s['innings']
    sr    = round(runs / balls * 100, 2) if balls else 0.0
    avg   = round(runs / innings, 2) if innings else 0.0
    bpct  = round((s['fours'] * 4 + s['sixes'] * 6) / runs * 100, 1) if runs else 0.0

    # Recent form (last 5 innings weighted — more recent = higher weight)
    hist = s['run_history']
    form_window = hist[-5:] if hist else []
    weights = [0.1, 0.15, 0.2, 0.25, 0.3][-len(form_window):]
    form_idx = round(sum(r * w for r, w in zip(form_window, weights)) / sum(weights), 1) if form_window else 0.0

    # Consistency: lower std_dev = more consistent (0–100 scale)
    sd = _std_dev(hist) if len(hist) > 1 else 0.0
    consistency = round(max(0, 100 - (sd / max(avg, 1) * 60)), 1)

    # Impact score: weighted combo of avg, sr, milestone frequency
    milestone_rate = (s['fifties'] + s['hundreds'] * 2) / max(innings, 1)
    sr_bonus = max(0, sr - 70) / 30  # bonus for high SR
    impact = round(min(100, avg * 0.4 + sr * 0.25 + milestone_rate * 20 + sr_bonus * 10), 1)

    # Aggression rating (how aggressive vs average SR benchmark)
    aggression = round(min(100, (sr / max(all_avg_sr, 50)) * 50), 1)

    # Trend (improving / declining over last 8 innings)
    trend_val = _trend(hist[-8:]) if len(hist) >= 3 else 0.0

    # Team contribution % — computed later when we have team total
    s.update({'sr': sr, 'avg': avg, 'bpct': bpct,
              'form': form_idx, 'consistency': consistency,
              'impact': impact, 'aggression': aggression,
              'trend': trend_val})
    return s

def calc_bowling_metrics(s):
    balls = s['balls_bowled']
    ov    = balls // 6 + (balls % 6) / 10
    eco   = round(s['runs_given'] / ov, 2) if ov else 0.0
    bavg  = round(s['runs_given'] / s['wickets'], 2) if s['wickets'] else 0.0
    sr_b  = round(balls / s['wickets'], 1) if s['wickets'] else 0.0  # bowling SR

    hist  = s['wkt_history']
    form_window = hist[-5:]
    form_idx = round(sum(form_window) / len(form_window), 2) if form_window else 0.0
    trend_val = _trend(hist[-8:]) if len(hist) >= 3 else 0.0

    # Control rating: lower eco + more wickets = higher control
    control = round(min(100, max(0, (12 - eco) / 12 * 60 + s['wickets'] / max(len(hist), 1) * 40)), 1)
    impact  = round(min(100, s['wickets'] * 5 + (12 - min(eco, 12)) * 3), 1)

    s.update({'eco': eco, 'bavg': bavg, 'sr_bowl': sr_b, 'overs': round(ov, 1),
              'form': form_idx, 'control': control, 'impact': impact,
              'trend': trend_val})
    return s

def run_analytics(data):
    bat  = defaultdict(lambda: {'runs':0,'balls':0,'fours':0,'sixes':0,
                                 'innings':0,'highest':0,'fifties':0,'hundreds':0,
                                 'run_history':[],'match_history':[]})
    bowl = defaultdict(lambda: {'wickets':0,'runs_given':0,'balls_bowled':0,
                                 'wkt_history':[],'match_history':[]})
    for r in data:
        b, bw = r['batsman'], r['bowler']
        bat[b]['runs']    += r['runs'];  bat[b]['balls']  += r['balls']
        bat[b]['fours']   += r['fours']; bat[b]['sixes']  += r['sixes']
        bat[b]['innings'] += 1
        bat[b]['run_history'].append(r['runs'])
        bat[b]['match_history'].append(r['match_date'])
        if r['runs'] > bat[b]['highest']:     bat[b]['highest']  = r['runs']
        if r['runs'] >= 100:                   bat[b]['hundreds'] += 1
        elif r['runs'] >= 50:                  bat[b]['fifties']  += 1

        bowl[bw]['wickets']      += r['wickets']
        bowl[bw]['runs_given']   += r['runs']
        bowl[bw]['balls_bowled'] += r['balls']
        bowl[bw]['wkt_history'].append(r['wickets'])
        bowl[bw]['match_history'].append(r['match_date'])

    # Global avg SR for aggression benchmark
    all_srs = [round(bat[b]['runs']/bat[b]['balls']*100,2) for b in bat if bat[b]['balls']]
    avg_sr  = sum(all_srs)/len(all_srs) if all_srs else 100.0
    total_runs = sum(bat[b]['runs'] for b in bat) or 1

    for b, s in bat.items():
        calc_batting_metrics(s, avg_sr)
        s['contribution'] = round(s['runs'] / total_runs * 100, 1)

    for bw, s in bowl.items():
        calc_bowling_metrics(s)

    return bat, bowl

def get_summary(data):
    if not data:
        return {'runs':0,'wickets':0,'matches':0,'sixes':0,'fours':0,
                'top_scorer':'—','top_wickets':'—','highest':0,'best_sr':0.0,
                'best_sr_player':'—','total_entries':0,'best_eco':'—',
                'total_balls':0,'avg_rr':0.0}
    bat, bowl = run_analytics(data)
    tr    = sum(r['runs'] for r in data)
    tw    = sum(r['wickets'] for r in data)
    tb    = sum(r['balls'] for r in data)
    tm    = len(set(r['match_date']+'|'+r['match_name'] for r in data))
    ts, tf = sum(r['sixes'] for r in data), sum(r['fours'] for r in data)
    top_s  = max(bat,  key=lambda k: bat[k]['runs'])    if bat  else '—'
    top_w  = max(bowl, key=lambda k: bowl[k]['wickets']) if bowl else '—'
    bsr_p  = max(bat,  key=lambda k: bat[k]['sr'])      if bat  else '—'
    beco_p = min(bowl, key=lambda k: bowl[k]['eco'])    if bowl else '—'
    return {'runs':tr,'wickets':tw,'matches':tm,'sixes':ts,'fours':tf,
            'top_scorer':top_s,'top_wickets':top_w,
            'highest':max(r['runs'] for r in data),
            'best_sr':bat[bsr_p]['sr'] if bat else 0.0,
            'best_sr_player':bsr_p,
            'best_eco': f"{bowl[beco_p]['eco']}" if bowl else '—',
            'best_eco_player': beco_p,
            'total_entries':len(data),
            'total_balls':tb,
            'avg_rr': round(tr/tb*6, 2) if tb else 0.0}

def build_match_history(data):
    matches = {}
    for r in data:
        key = r['match_date'] + '|' + r['match_name']
        if key not in matches:
            matches[key] = {'name':r['match_name'],'date':r['match_date'],
                            'runs':0,'wickets':0,'entries':0,'sixes':0,'fours':0}
        matches[key]['runs']    += r['runs']
        matches[key]['wickets'] += r['wickets']
        matches[key]['entries'] += 1
        matches[key]['sixes']   += r['sixes']
        matches[key]['fours']   += r['fours']
    return sorted(matches.values(), key=lambda x: x['date'], reverse=True)

def apply_filters(data, filters):
    """Filter raw rows by active filter criteria."""
    result = list(data)
    if filters.get('player'):
        p = filters['player'].lower()
        result = [r for r in result if p in r['batsman'].lower() or p in r['bowler'].lower()]
    if filters.get('match'):
        result = [r for r in result if filters['match'].lower() in r['match_name'].lower()]
    if filters.get('date_from'):
        result = [r for r in result if r['match_date'] >= filters['date_from']]
    if filters.get('date_to'):
        result = [r for r in result if r['match_date'] <= filters['date_to']]
    if filters.get('innings') and filters['innings'] != 'all':
        result = [r for r in result if str(r['innings']) == filters['innings']]
    return result

# ─── ROUTES ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    conn = get_db()
    all_data = conn.execute(
        'SELECT * FROM match_stats ORDER BY match_date DESC, id DESC'
    ).fetchall()
    conn.close()

    # Read active filters from query string
    filters = {
        'player':    request.args.get('player', '').strip(),
        'match':     request.args.get('match', '').strip(),
        'date_from': request.args.get('date_from', '').strip(),
        'date_to':   request.args.get('date_to', '').strip(),
        'innings':   request.args.get('innings', 'all'),
    }
    active_filters = {k: v for k, v in filters.items() if v and v != 'all'}
    data = apply_filters(all_data, filters)

    bat, bowl  = run_analytics(data)
    sm         = get_summary(data)
    match_list = build_match_history(data)

    # Chart data
    players    = sorted(bat.keys(), key=lambda p: bat[p]['runs'], reverse=True)
    runs_list  = [bat[p]['runs'] for p in players]
    sr_list    = [bat[p]['sr']   for p in players]
    avg_list   = [bat[p]['avg']  for p in players]
    impact_list= [bat[p]['impact'] for p in players]

    bowlers    = sorted(bowl.keys(), key=lambda b: bowl[b]['wickets'], reverse=True)
    wkt_list   = [bowl[b]['wickets'] for b in bowlers]
    eco_list   = [bowl[b]['eco']     for b in bowlers]
    control_list=[bowl[b]['control'] for b in bowlers]

    # Sparkline data (JSON for JS)
    sparklines  = {p: bat[p]['run_history'][-10:] for p in players}
    wkt_sparks  = {b: bowl[b]['wkt_history'][-10:] for b in bowlers}
    form_trends = {p: bat[p]['run_history'][-8:]   for p in players}

    # All unique player names and match names for filter dropdowns
    all_players = sorted(set(r['batsman'] for r in all_data) | set(r['bowler'] for r in all_data))
    all_matches = sorted(set(r['match_name'] for r in all_data))

    # Last updated timestamp
    last_updated = datetime.now().strftime('%d %b %Y, %H:%M')

    return render_template('index.html',
        data=data, bat=bat, bowl=bowl, sm=sm,
        players=players, runs_list=runs_list, sr_list=sr_list,
        avg_list=avg_list, impact_list=impact_list,
        bowlers=bowlers, wkt_list=wkt_list, eco_list=eco_list,
        control_list=control_list,
        sparklines=json.dumps(sparklines),
        wkt_sparks=json.dumps(wkt_sparks),
        form_trends=json.dumps(form_trends),
        match_list=match_list[:15],
        filters=filters, active_filters=active_filters,
        all_players=all_players, all_matches=all_matches,
        last_updated=last_updated)

@app.route('/add', methods=['POST'])
def add():
    try:
        conn = get_db()
        conn.execute('''INSERT INTO match_stats
            (batsman,bowler,runs,balls,wickets,fours,sixes,match_date,match_name,innings)
            VALUES(?,?,?,?,?,?,?,?,?,?)''', (
            request.form['batsman'].strip().title(),
            request.form['bowler'].strip().title(),
            int(request.form['runs']),
            max(1, int(request.form['balls'])),
            int(request.form['wickets']),
            int(request.form.get('fours', 0)),
            int(request.form.get('sixes', 0)),
            request.form['match_date'],
            request.form.get('match_name', 'Match').strip() or 'Match',
            int(request.form.get('innings', 1))
        ))
        conn.commit(); conn.close()
        flash('Entry added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding entry: {e}', 'danger')
    return redirect('/')

@app.route('/delete/<int:eid>', methods=['POST'])
def delete(eid):
    conn = get_db()
    conn.execute('DELETE FROM match_stats WHERE id=?', (eid,))
    conn.commit(); conn.close()
    flash('Entry deleted.', 'info')
    return redirect('/')

@app.route('/export')
def export():
    conn = get_db()
    rows = conn.execute('SELECT * FROM match_stats ORDER BY match_date DESC').fetchall()
    conn.close()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['ID','Batsman','Bowler','Runs','Balls','Wickets','4s','6s',
                'Match Date','Match Name','Innings','Created At'])
    for r in rows:
        w.writerow(list(r))
    out.seek(0)
    return send_file(io.BytesIO(out.getvalue().encode()),
                     mimetype='text/csv', as_attachment=True,
                     download_name='cricmetrics_export.csv')

@app.route('/api/data')
def api_data():
    conn = get_db()
    data = conn.execute('SELECT * FROM match_stats ORDER BY match_date').fetchall()
    conn.close()
    bat, bowl = run_analytics(data)
    return jsonify({
        'batsmen': {k: {kk: vv for kk, vv in v.items() if not isinstance(vv, list)}
                    for k, v in bat.items()},
        'bowlers': {k: {kk: vv for kk, vv in v.items() if not isinstance(vv, list)}
                    for k, v in bowl.items()}
    })

@app.route('/api/player/<name>/history')
def api_player_history(name):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM match_stats WHERE batsman=? ORDER BY match_date', (name,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
