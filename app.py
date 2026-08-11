from flask import Flask, render_template, request, jsonify
import os
import groq
from scraper import fetch_live_kbo_data, fetch_kbo_final_scores
from predict import generar_pronostico_partido

app = Flask(__name__)

# Configuración del cliente Groq API
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Almacenamiento en memoria para el historial de resultados
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
        # Partidos por defecto si el scraper no obtiene datos de la URL
        raw_matches = [
            {"equipo_visitante": "Samsung Lions", "equipo_local": "Kia Tigers", "abridor_visitante": "Won Tae-in", "abridor_local": "James Naile"},
            {"equipo_visitante": "Lotte Giants", "equipo_local": "SSG Landers", "abridor_visitante": "Charlie Barnes", "abridor_local": "Kim Kwang-hyun"},
            {"equipo_visitante": "LG Twins", "equipo_local": "Kiwoom Heroes", "abridor_visitante": "Dietrich Enns", "abridor_local": "Ariel Jurado"},
            {"equipo_visitante": "KT Wiz", "equipo_local": "NC Dinos", "abridor_visitante": "William Cuevas", "abridor_local": "Kyle Hart"},
            {"equipo_visitante": "Hanwha Eagles", "equipo_local": "Doosan Bears", "abridor_visitante": "Ryu Hyun-jin", "abridor_local": "Gwak Been"}
        ]

    processed_matches = []
    for match in raw_matches:
        pronostico = generar_pronostico_partido(match)
        
        # Verificar si existe en el historial cargado
        partido_key = f"{pronostico['equipo_visitante']} vs {pronostico['equipo_local']}"
        hist_entry = next((item for item in DATABASE_HISTORY if item['partido'] == partido_key and item['fecha'] == target_date), None)
        
        if hist_entry:
            pronostico['estado'] = hist_entry['estado']
            pronostico['resultado_carreras'] = hist_entry['resultado_carreras']
        else:
            pronostico['estado'] = 'PENDIENTE'

        processed_matches.append(pronostico)

    return jsonify({"partidos": processed_matches})

@app.route("/api/sync-results", methods=["POST"])
def sync_results():
    data = request.json or {}
    target_date = data.get("fecha", "2026-08-11")

    scores = fetch_kbo_final_scores(target_date)

    for partido_key, score_info in scores.items():
        existing = next((item for item in DATABASE_HISTORY if item['partido'] == partido_key and item['fecha'] == target_date), None)
        
        # Determinar si el pronóstico acertó
        away_team, home_team = partido_key.split(" vs ")
        # Favorito según lógica del modelo
        pronostico_sample = generar_pronostico_partido({"equipo_visitante": away_team, "equipo_local": home_team})
        ganador_pronosticado = pronostico_sample["favorito_pronostico"]
        
        estado = "GANADA" if score_info["ganador_real"] == ganador_pronosticado else "PERDIDA"
        carreras_str = f"{score_info['away_runs']} - {score_info['home_runs']}"

        if existing:
            existing['estado'] = estado
            existing['resultado_carreras'] = carreras_str
        else:
            DATABASE_HISTORY.append({
                "fecha": target_date,
                "partido": partido_key,
                "favorito_pronostico": ganador_pronosticado,
                "momio_decimal": pronostico_sample["momio_decimal"],
                "stake_sugerido": pronostico_sample["stake_sugerido"],
                "resultado_carreras": carreras_str,
                "estado": estado
            })

    return jsonify({"status": "ok", "synced_count": len(scores)})

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

    # Cálculo aproximado de ROI
    ganancia_unidades = (ganadas * 0.85) - perdidas
    roi = round((ganancia_unidades / total) * 100, 1)
    roi_str = f"+{roi}%" if roi >= 0 else f"{roi}%"

    return jsonify({
        "precision": f"{precision}%",
        "roi_promedio": roi_str,
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
        return jsonify({"response": "La API Key de Groq no está configurada en las variables de entorno."})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres un analista experto en la KBO (Liga Coreana de Béisbol) y apuestas deportivas. Ofreces respuestas claras, estructuradas y recomendaciones de parlays bien argumentadas."},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.4
        )
        reply = response.choices[0].message.content
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"response": f"Error al procesar consulta con IA: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)