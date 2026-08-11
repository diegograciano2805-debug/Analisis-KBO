from flask import Flask, render_template, request, jsonify
import os
import hashlib
import groq
from scraper import fetch_live_kbo_data, fetch_kbo_final_scores
from predict import generar_pronostico_partido

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Base de datos en memoria para el historial automático
DATABASE_HISTORY = []

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

    # Intentar obtener marcadores reales de la web
    real_scores = fetch_kbo_final_scores(target_date)

    processed_matches = []
    for match in raw_matches:
        pronostico = generar_pronostico_partido(match)
        partido_key = f"{pronostico['equipo_visitante']} vs {pronostico['equipo_local']}"
        
        # 1. Verificar si existe marcador real en internet
        if partido_key in real_scores:
            score = real_scores[partido_key]
            ganador_real = score["ganador_real"]
            pronostico['estado'] = "GANADA" if ganador_real == pronostico['favorito_pronostico'] else "PERDIDA"
            pronostico['resultado_carreras'] = f"{score['away_runs']} - {score['home_runs']}"
        else:
            # Si no hay marcador (fecha futura o partido no comenzado)
            pronostico['estado'] = 'PENDIENTE'
            pronostico['resultado_carreras'] = 'vs'

        # 2. Registrar automáticamente en el historial si ya se resolvió
        if pronostico['estado'] in ['GANADA', 'PERDIDA']:
            existing = next((item for item in DATABASE_HISTORY if item['partido'] == partido_key and item['fecha'] == target_date), None)
            if not existing:
                DATABASE_HISTORY.append({
                    "fecha": target_date,
                    "partido": partido_key,
                    "favorito_pronostico": pronostico["favorito_pronostico"],
                    "momio_decimal": pronostico["momio_decimal"],
                    "stake_sugerido": pronostico["stake_sugerido"],
                    "resultado_carreras": pronostico["resultado_carreras"],
                    "estado": pronostico["estado"]
                })

        processed_matches.append(pronostico)

    return jsonify({"partidos": processed_matches})

@app.route("/api/metrics", methods=["GET"])
def metrics_endpoint():
    evaluados = [h for h in DATABASE_HISTORY if h['estado'] in ['GANADA', 'PERDIDA']]
    total = len(evaluados)
    
    if total == 0:
        return jsonify({
            "precision": "0.0%",
            "roi_promedio": "+0.0%",
            "partidos_evaluados": 0,
            "ganadas": 0,
            "perdidas": 0
        })

    ganadas = sum(1 for h in evaluados if h['estado'] == 'GANADA')
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

@app.route("/api/history", methods=["GET"])
def history_endpoint():
    return jsonify({"historial": DATABASE_HISTORY})

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
                {"role": "system", "content": "Eres un analista experto en la KBO (Liga Coreana de Béisbol). Ofreces análisis tácticos y recomendaciones de parlay claras."},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.4
        )
        return jsonify({"response": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"response": f"Error en la consulta: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)