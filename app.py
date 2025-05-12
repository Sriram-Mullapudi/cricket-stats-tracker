from flask import Flask, render_template, request, redirect, flash, send_file
import sqlite3
from collections import defaultdict
import csv
import io

app = Flask(__name__)
app.secret_key = 'some_secret_key'

def get_db_connection():
    return sqlite3.connect('data/matches.db')

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS match_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batsman TEXT,
            bowler TEXT,
            runs INTEGER,
            balls INTEGER,
            wickets INTEGER,
            match_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def calculate_analytics(data):
    batsman_stats = defaultdict(lambda: {'runs': 0, 'balls': 0})
    bowler_stats = defaultdict(lambda: {'wickets': 0})

    for row in data:
        batsman, bowler, runs, balls, wickets = row[1], row[2], row[3], row[4], row[5]
        batsman_stats[batsman]['runs'] += runs
        batsman_stats[batsman]['balls'] += balls
        bowler_stats[bowler]['wickets'] += wickets

    return batsman_stats, bowler_stats

@app.route('/')
def index():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM match_stats')
    data = c.fetchall()
    conn.close()

    batsman_stats, bowler_stats = calculate_analytics(data)

    players = list(batsman_stats.keys())
    runs = [s['runs'] for s in batsman_stats.values()]
    bowlers = list(bowler_stats.keys())
    wickets = [s['wickets'] for s in bowler_stats.values()]

    return render_template('index.html',
                           data=data,
                           stats=batsman_stats,
                           players=players, runs=runs,
                           bowlers=bowlers, wickets=wickets)

@app.route('/add', methods=['POST'])
def add_stat():
    try:
        batsman = request.form['batsman']
        bowler = request.form['bowler']
        runs = int(request.form['runs'])
        balls = int(request.form['balls'])
        wickets = int(request.form['wickets'])
        match_date = request.form['match_date']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO match_stats (batsman, bowler, runs, balls, wickets, match_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (batsman, bowler, runs, balls, wickets, match_date))
        conn.commit()
        conn.close()
        flash('Entry added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding entry: {e}', 'danger')

    return redirect('/')

@app.route('/export')
def export_csv():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM match_stats')
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Batsman', 'Bowler', 'Runs', 'Balls', 'Wickets', 'Match Date'])
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='match_stats.csv')

if __name__ == '__main__':
    print("Initializing DB...")
    init_db()
    print("Starting app...")
    app.run(debug=True)
