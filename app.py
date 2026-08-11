from flask import Flask, render_template, request, jsonify
import os
import groq
from scraper import fetch_live_kbo_data, fetch_kbo_final_scores
from predict import generar_pronostico_partido
from database import init_db, upsert_prediction, get_history, get_metrics

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

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
            {"equipo_visitante": "Samsung Lions", "equipo_local": "Kia Tigers", "abridor_visitante": "Won Tae-in", "abridor_local": "James Naile", "estado_web": "PROGRAMADO"},
            {"equipo_visitante": "Lotte Giants", "equipo_local": "SSG Landers", "abridor_visitante": "Charlie Barnes", "abridor_local": "Kim Kwang-hyun", "estado_web": "PROGRAMADO"},
            {"equipo_visitante": "LG Twins", "equipo_local": "Kiwoom Heroes", "abridor_visitante": "Dietrich Enns", "abridor_local": "Ariel Jurado", "estado_web": "PROGRAMADO"},
            {"equipo_visitante": "KT Wiz", "equipo_local": "NC Dinos", "abridor_visitante": "William Cuevas", "abridor_local": "Kyle Hart", "estado_web": "PROGRAMADO"},
            {"equipo_visitante": "Hanwha Eagles", "equipo_local": "Doosan Bears", "abridor_visitante": "Ryu Hyun-jin", "abridor_local": "Gwak Been", "estado_web": "PROGRAMADO"}
        ]

    real_scores = fetch_kbo_final_scores(target_date)
    processed_matches = []

    for match in raw_matches:
        pronostico = generar_pronostico_partido(match)
        partido_key = f"{pronostico['equipo_visitante']} vs {pronostico['equipo_local']}"
        
        # Determinar estado
        if match.get("estado_web") == "CANCELADO" or (partido_key in real_scores and real_scores[partido_key].get("cancelado")):
            estado = "CANCELADO"
            marcador = "SUSPENDIDO"
            upsert_prediction(target_date, partido_key, pronostico, estado, marcador)
        elif partido_key in real_scores and not real_scores[partido_key].get("cancelado"):
            score = real_scores[partido_key]
            ganador_real = score["ganador_real"]
            estado = "GANADA" if ganador_real == pronostico['favorito_pronostico'] else "PERDIDA"
            marcador = f"{score['away_runs']} - {score['home_runs']}"
            upsert_prediction(target_date, partido_key, pronostico, estado, marcador)
        else:
            estado = "PENDIENTE"
            marcador = "vs"

        card_item = dict(pronostico)
        card_item['estado'] = estado
        card_item['resultado_carreras'] = marcador
        processed_matches.append(card_item)

    return jsonify({"partidos": processed_matches})

@app.route("/api/metrics", methods=["GET"])
def metrics_endpoint():
    return jsonify(get_metrics())

@app.route("/api/history", methods=["GET"])
def history_endpoint():
    return jsonify({"historial": get_history()})

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