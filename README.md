# 🏏 CricMetrics — Cricket Stats Tracker

> A premium, full-stack cricket performance analytics platform built with Python, Flask, SQLite, and Plotly.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)

---

## Overview

CricMetrics is a real-time cricket match statistics tracker and analytics dashboard. It allows coaches, players, and analysts to log batting and bowling performances, automatically calculate advanced metrics, and visualise results through interactive charts.

**Built to showcase:** full-stack web development, relational database design, RESTful routing, data analytics, and production-quality UI/UX.

---

## Features

- **Real-time performance logging** — add batsman & bowler stats including runs, balls, fours, sixes, and wickets
- **Advanced batting analytics** — strike rate, average, highest score, 50s, 100s, boundary %
- **Advanced bowling analytics** — economy rate, bowling average, overs bowled
- **4 interactive Plotly charts** — Runs, Strike Rate, Wickets, Economy
- **Animated KPI dashboard** — 7 live counters with smooth count-up animation
- **Delete entries** — per-row delete with confirmation prompt
- **Export to CSV** — one-click download of all match data
- **Scroll-reveal animations** — sections animate in as you scroll
- **Fully responsive** — works on desktop, tablet, and mobile

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask 3.0 |
| Database | SQLite (via sqlite3) |
| Frontend | HTML5, CSS3, Vanilla JS |
| Charts | Plotly.js 2.27 |
| Fonts | Bebas Neue, DM Sans, JetBrains Mono |

---

## Schema

```sql
CREATE TABLE match_stats (
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
);
```

---

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Main dashboard |
| `POST` | `/add` | Add a performance record |
| `POST` | `/delete/<id>` | Delete an entry |
| `GET` | `/export` | Download CSV report |
| `GET` | `/api/chart-data` | JSON analytics data |

---

## Run Locally

```bash
git clone https://github.com/Sriram-Mullapudi/cricket-stats-tracker
cd cricket-stats-tracker
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in your browser.

---

## Project Structure

```
cricket-stats-tracker/
├── app.py                  # Flask routes + analytics logic
├── requirements.txt
├── data/
│   └── matches.db          # SQLite database (auto-created)
├── templates/
│   └── index.html          # Full dashboard UI
└── static/
    └── style.css
```

---

## Calculated Metrics

**Batting**
- `Strike Rate = (runs / balls) × 100`
- `Average = total runs / innings played`
- `Boundary % = (4s×4 + 6s×6) / total runs × 100`

**Bowling**
- `Economy = runs given / overs bowled`
- `Bowling Average = runs given / wickets taken`

---

*Built by [Sriram Mullapudi](https://linkedin.com/in/srirammullapudi) · Backend Software Engineer*
