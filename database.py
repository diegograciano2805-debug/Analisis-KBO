import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "kbo_predictions.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            partido TEXT,
            equipo_local TEXT,
            equipo_visitante TEXT,
            favorito_pronostico TEXT,
            probabilidad_local REAL,
            recomendacion_ou TEXT,
            recomendacion_runline TEXT,
            stake_sugerido TEXT,
            clima_info TEXT,
            momio_decimal REAL,
            ev_label TEXT,
            estado TEXT DEFAULT 'PENDIENTE',
            resultado_carreras TEXT DEFAULT 'N/A',
            UNIQUE(fecha, partido)
        )
    """)
    conn.commit()
    conn.close()

def save_prediction(fecha, partido, home, away, favorito, prob, rec_ou="Over 8.5", rec_rl="N/A", stake="2.0%", clima="25°C, 10 km/h", momio=1.90, ev="+0.0% EV"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO predictions (
            fecha, partido, equipo_local, equipo_visitante, favorito_pronostico, 
            probabilidad_local, recomendacion_ou, recomendacion_runline, stake_sugerido, 
            clima_info, momio_decimal, ev_label, estado, resultado_carreras
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 'N/A')
        ON CONFLICT(fecha, partido) DO UPDATE SET
            favorito_pronostico = excluded.favorito_pronostico,
            probabilidad_local = excluded.probabilidad_local,
            momio_decimal = excluded.momio_decimal,
            ev_label = excluded.ev_label
    """, (fecha, partido, home, away, favorito, prob, rec_ou, rec_rl, stake, clima, momio, ev))

    conn.commit()
    conn.close()

def update_match_results(fecha, final_scores):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, partido, favorito_pronostico FROM predictions WHERE fecha = ?", (fecha,))
    matches = cursor.fetchall()

    for m_id, partido_str, favorito in matches:
        if partido_str in final_scores:
            data = final_scores[partido_str]
            ganador_real = data["ganador_real"]
            res_str = f"{data['away_runs']} - {data['home_runs']}"
            estado = "GANADA" if favorito == ganador_real else "PERDIDA"

            cursor.execute(
                "UPDATE predictions SET estado = ?, resultado_carreras = ? WHERE id = ?",
                (estado, res_str, m_id)
            )

    conn.commit()
    conn.close()

def get_predictions_history():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM predictions WHERE estado IN ('GANADA', 'PERDIDA')", conn)
    conn.close()
    return df

def get_model_metrics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*), 
               SUM(CASE WHEN estado = 'GANADA' THEN 1 ELSE 0 END), 
               SUM(CASE WHEN estado = 'PERDIDA' THEN 1 ELSE 0 END) 
        FROM predictions WHERE estado IN ('GANADA', 'PERDIDA')
    """)
    row = cursor.fetchone()
    conn.close()

    total_eval = row[0] if row and row[0] else 0
    ganadas = row[1] if row and row[1] else 0
    perdidas = row[2] if row and row[2] else 0

    if total_eval == 0:
        return {
            "precision": "0.0%",
            "roi_promedio": "+0.0%",
            "partidos_evaluados": 0,
            "ganadas": 0,
            "perdidas": 0
        }

    precision_val = round((ganadas / total_eval) * 100, 1)
    roi_estimado = round(((ganadas * 0.85) - perdidas) / total_eval * 100, 1)

    return {
        "precision": f"{precision_val}%",
        "roi_promedio": f"+{roi_estimado}%" if roi_estimado >= 0 else f"{roi_estimado}%",
        "partidos_evaluados": total_eval,
        "ganadas": ganadas,
        "perdidas": perdidas
    }