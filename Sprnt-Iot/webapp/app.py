from flask import Flask, jsonify, render_template, redirect, url_for
import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(os.path.dirname(BASE_DIR), "faces.db")  # usa o mesmo banco do script

SESSION_TTL_SECONDS = 10  # validade da sessão facial

def get_db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.get("/api/session")
def api_session():
    con = get_db()
    row = con.execute(
        "SELECT user_id, user_name, started_at FROM app_session WHERE id=1;"
    ).fetchone()

    if not row or not row["user_id"]:
        return jsonify({"authenticated": False})

    # valida a idade da sessão
    started_at = row["started_at"]
    try:
        # SQLite salva como 'YYYY-MM-DD HH:MM:SS'
        started_dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
    except Exception:
        started_dt = None

    if (started_dt is None) or (datetime.now() - started_dt > timedelta(seconds=SESSION_TTL_SECONDS)):
        # expirou → limpar e não autenticar
        con.execute("UPDATE app_session SET user_id=NULL, user_name=NULL, started_at=NULL WHERE id=1;")
        con.commit()
        return jsonify({"authenticated": False})

    # sessão válida → retorna portfólio fake
    portfolio = fake_portfolio(row["user_name"])
    return jsonify({
        "authenticated": True,
        "user": {"id": row["user_id"], "name": row["user_name"]},
        "portfolio": portfolio
    })

@app.post("/api/logout")
def api_logout():
    con = get_db()
    con.execute("UPDATE app_session SET user_id=NULL, user_name=NULL, started_at=NULL WHERE id=1;")
    con.commit()
    return jsonify({"ok": True})

@app.route("/dashboard")
def dashboard():
    con = get_db()
    row = con.execute("SELECT user_id, started_at FROM app_session WHERE id=1;").fetchone()
    if not row or not row["user_id"]:
        return redirect(url_for("home"))

    # checa validade também aqui
    started_at = row["started_at"]
    try:
        started_dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
    except Exception:
        started_dt = None

    if (started_dt is None) or (datetime.now() - started_dt > timedelta(seconds=SESSION_TTL_SECONDS)):
        con.execute("UPDATE app_session SET user_id=NULL, user_name=NULL, started_at=NULL WHERE id=1;")
        con.commit()
        return redirect(url_for("home"))

    return render_template("dashboard.html")

def fake_portfolio(name):
    return {
        "summary": {
            "accountName": f"Conta de {name}",
            "balance": 127_450.32,
            "dailyPnl": 842.18,
            "ytdPnl": 9_315.77
        },
        "positions": [
            {"ticker": "PETR4", "qty": 600, "price": 37.12, "avg": 33.90, "pnl": 1932.00},
            {"ticker": "VALE3", "qty": 150, "price": 62.45, "avg": 58.10, "pnl": 652.50},
            {"ticker": "IVVB11", "qty": 40, "price": 327.70, "avg": 305.00, "pnl": 907.99},
        ],
        "watchlist": [
            {"ticker": "BBDC4", "price": 13.42, "chg": +0.82},
            {"ticker": "ITUB4", "price": 36.05, "chg": -0.15},
            {"ticker": "WEGE3", "price": 38.90, "chg": +1.12},
        ],
        "allocation": [
            {"label": "Ações BR", "value": 55},
            {"label": "ETF US (IVVB11)", "value": 25},
            {"label": "Renda Fixa", "value": 15},
            {"label": "Caixa", "value": 5}
        ]
    }

if __name__ == "__main__":
    app.run(debug=True)
