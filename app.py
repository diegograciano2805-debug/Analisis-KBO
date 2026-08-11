from flask import Flask, render_template, request, jsonify
import os
import sqlite3
import groq
from scraper import fetch_live_kbo_data, fetch_kbo_final_scores
from predict import generar_pronostico_partido

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

DB_FILE = "kbo_predictions.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
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
                resultado_carreras TEXT DEFAULT 'N/A'
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error inicializando BD: {e}")

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/predict", methods=["POST"])
def predict_endpoint():
    data = request.json or {}
    target_date = data.get("fecha", "2026-08-11")

    raw_matches = fetch_live_kbo_data(target_date)

    if not raw_matches:
        raw_matches = [
            {"equipo_visitante": "Samsung Lions", "equipo_local": "Kia Tigers", "abridor_visitante": "Won Tae-in", "abridor_local": "James Naile"},
            {"equipo_visitante": "Lotte Giants", "equipo_local": "SSG Landers", "abridor_visitante": "Charlie Barnes", "abridor_local": "Kim Kwang-hyun"},
            {"equipo_visitante": "LG Twins", "equipo_local": "Kiwoom Heroes", "abridor_visitante": "Dietrich Enns", "abridor_local": "Ariel Jurado"},
            {"equipo_visitante": "KT Wiz", "equipo_local": "NC Dinos", "abridor_visitante": "William Cuevas", "abridor_local": "Kyle Hart"},
            {"equipo_visitante": "Hanwha Eagles", "equipo_local": "Doosan Bears", "abridor_visitante": "Ryu Hyun-jin", "abridor_local": "Gwak Been"}
        ]

    real_scores = fetch_kbo_final_scores(target_date)

    processed_matches = []
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for match in raw_matches:
            pronostico = generar_pronostico_partido(match)
            partido_key = f"{pronostico['equipo_visitante']} vs {pronostico['equipo_local']}"
            
            if partido_key in real_scores:
                score = real_scores[partido_key]
                ganador_real = score["ganador_real"]
                estado = "GANADA" if ganador_real == pronostico['favorito_pronostico'] else "PERDIDA"
                marcador = f"{score['away_runs']} - {score['home_runs']}"
            else:
                estado = "PENDIENTE"
                marcador = "Pendiente"

            # Eliminar duplicados previos e insertar registro actualizado
            cursor.execute("DELETE FROM predictions WHERE fecha = ? AND partido = ?", (target_date, partido_key))
            
            cursor.execute("""
                INSERT INTO predictions (
                    fecha, partido, equipo_local, equipo_visitante, favorito_pronostico,
                    probabilidad_local, recomendacion_ou, recomendacion_runline, stake_sugerido,
                    clima_info, momio_decimal, ev_label, estado, resultado_carreras
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                target_date, partido_key, pronostico['equipo_local'], pronostico['equipo_visitante'],
                pronostico['favorito_pronostico'], pronostico['probabilidad_local'],
                pronostico['recomendacion_ou'], pronostico['recomendacion_runline'],
                pronostico['stake_sugerido'], pronostico['clima_info'],
                pronostico['momio_decimal'], pronostico['ev_label'],
                estado, marcador
            ))

            pronostico_card = dict(pronostico)
            pronostico_card['estado'] = estado
            pronostico_card['resultado_carreras'] = marcador
            processed_matches.append(pronostico_card)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error procesando SQLite: {e}")

    return jsonify({"partidos": processed_matches})

@app.route("/api/metrics", methods=["GET"])
def metrics_endpoint():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT estado FROM predictions WHERE estado IN ('GANADA', 'PERDIDA')")
        rows = cursor.fetchall()
        conn.close()

        total = len(rows)
        if total == 0:
            return jsonify({
                "precision": "0.0%",
                "roi_promedio": "+0.0%",
                "partidos_evaluados": 0,
                "ganadas": 0,
                "perdidas": 0
            })

        ganadas = sum(1 for r in rows if r[0] == 'GANADA')
        perdidas = total - ganadas
        precision = round((ganadas / total) * 100, 1)
        ganancia_unidades = (ganadas * 0.85) - perdidas
        roi = round((ganancia_unidades / total) * 100, 1)

        return jsonify({
            "precision": f"{precision}%",
            "roi_promedio": f"+{roi}%" if roi >= 0 else f"{roi}%",
            "partidos_evaluados": total,
            "ganadas": ganadas,
            "perdidas": perdidas
        })
    except Exception as e:
        return jsonify({
            "precision": "0.0%",
            "roi_promedio": "+0.0%",
            "partidos_evaluados": 0,
            "ganadas": 0,
            "perdidas": 0
        })

@app.route("/api/history", methods=["GET"])
def history_endpoint():
    historial = []
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fecha, partido, favorito_pronostico, momio_decimal, stake_sugerido, resultado_carreras, estado 
            FROM predictions 
            ORDER BY fecha DESC, id DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            historial.append({
                "fecha": r[0],
                "partido": r[1],
                "favorito_pronostico": r[2],
                "momio_decimal": r[3],
                "stake_sugerido": r[4],
                "resultado_carreras": r[5],
                "estado": r[6]
            })
    except Exception as e:
        print(f"Error consultando historial: {e}")

    return jsonify({"historial": historial})

@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    data = request.json or {}
    user_msg = data.get("message", "")

    if not client:
        return jsonify({"response": "La API Key de Groq no está configurada."})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres un analista experto en la KBO (Liga Coreana de Béisbol). Ofreces análisis tácticos y recomendaciones de parlay."},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.4
        )
        return jsonify({"response": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"response": f"Error en la consulta: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)