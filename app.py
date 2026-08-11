import os
from auto_pipeline import run_autonomous_pipeline
from database import (
    get_model_metrics,
    get_predictions_history,
    update_match_results,
)
from flask import Flask, jsonify, render_template, request
from groq import Groq
from scraper import fetch_kbo_final_scores

app = Flask(__name__)


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/predict", methods=["POST"])
def process_predictions():
  data = request.get_json() or {}
  target_date = data.get("fecha", "2026-08-11")

  run_autonomous_pipeline(target_date)

  df = get_predictions_history()
  df_fecha = df[df["fecha"] == target_date]

  return jsonify({"status": "success", "partidos": df_fecha.to_dict(orient="records")})


@app.route("/api/history", methods=["GET"])
def history():
  df = get_predictions_history()
  if df.empty:
    return jsonify({"status": "success", "historial": []})
  
  # Ordenar del más reciente al más antiguo
  df_sorted = df.sort_values(by="fecha", ascending=False)
  return jsonify({"status": "success", "historial": df_sorted.to_dict(orient="records")})


@app.route("/api/sync-results", methods=["POST"])
def sync_results():
  data = request.get_json() or {}
  target_date = data.get("fecha", "2026-08-11")

  final_scores = fetch_kbo_final_scores(target_date)
  if final_scores:
    update_match_results(target_date, final_scores)
    return jsonify({
        "status": "success",
        "message": f"Resultados del {target_date} sincronizados.",
    })

  return jsonify(
      {"status": "warning", "message": "No se encontraron resultados aún."}
  )


@app.route("/api/metrics", methods=["GET"])
def metrics():
  metrics_data = get_model_metrics()
  return jsonify(metrics_data)


@app.route("/api/chat", methods=["POST"])
def chat_ai():
  api_key = os.environ.get("GROQ_API_KEY")
  if not api_key:
    return jsonify({
        "status": "error",
        "response": (
            "Falta la clave GROQ_API_KEY en la terminal. Ejecuta"
            ' $env:GROQ_API_KEY="tu_clave" antes de iniciar.'
        ),
    })

  data = request.get_json() or {}
  user_message = data.get("message", "")
  target_date = data.get("fecha", "2026-08-11")

  df = get_predictions_history()
  df_fecha = df[df["fecha"] == target_date]
  contexto = (
      df_fecha.to_dict(orient="records")
      if not df_fecha.empty
      else "Sin datos cargados."
  )

  system_instruction = f"""
    Eres un analista experto en apuestas de béisbol de la KBO. 
    Tu objetivo es debatir con el usuario sobre las probabilidades, valor de líneas (Moneyline, Over/Under, Runline), clima y métricas avanzadas (FIP, WHIP, wOBA).
    Usa los siguientes datos actuales calculados por el modelo para fundar tus opiniones:
    {contexto}

    REGLA OBLIGATORIA PARA PARLAYS / COMBINADAS:
    Siempre que el usuario pida un parlay, ticket o selección combinada, DEBES presentar tus recomendaciones principales utilizando una TABLA EN FORMATO MARKDOWN.
    La tabla debe contener exactamente las siguientes columnas:
    | Partido | Selección | Mercado | Justificación |
    """

  try:
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
    )
    return jsonify(
        {"status": "success", "response": completion.choices[0].message.content}
    )
  except Exception as e:
    return jsonify(
        {"status": "error", "response": f"Error al conectar con Groq: {str(e)}"}
    )


if __name__ == "__main__":
  app.run(debug=True, port=5000)