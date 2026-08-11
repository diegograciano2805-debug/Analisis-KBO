import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "kbo_predictions.db")

def init_db():
    """Inicializa la base de datos de manera segura."""
    with sqlite3.connect(DB_PATH) as conn:
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

def upsert_prediction(fecha, partido_key, pronostico, estado, marcador):
    """Guarda o actualiza registros asegurando que 'estado' y 'resultado_carreras' no se pierdan."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM predictions WHERE fecha = ? AND partido = ?", (fecha, partido_key))
        cursor.execute("""
            INSERT INTO predictions (
                fecha, partido, equipo_local, equipo_visitante, favorito_pronostico,
                probabilidad_local, recomendacion_ou, recomendacion_runline, stake_sugerido,
                clima_info, momio_decimal, ev_label, estado, resultado_carreras
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fecha, partido_key, pronostico['equipo_local'], pronostico['equipo_visitante'],
            pronostico['favorito_pronostico'], pronostico['probabilidad_local'],
            pronostico['recomendacion_ou'], pronostico['recomendacion_runline'],
            pronostico['stake_sugerido'], pronostico['clima_info'],
            pronostico['momio_decimal'], pronostico['ev_label'],
            estado, marcador
        ))
        conn.commit()

def get_history():
    """Retorna todo el historial almacenado."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fecha, partido, favorito_pronostico, momio_decimal, stake_sugerido, resultado_carreras, estado 
            FROM predictions 
            ORDER BY fecha DESC, id DESC
        """)
        rows = cursor.fetchall()

    return [{
        "fecha": r[0],
        "partido": r[1],
        "favorito_pronostico": r[2],
        "momio_decimal": r[3],
        "stake_sugerido": r[4],
        "resultado_carreras": r[5],
        "estado": r[6]
    } for r in rows]

def get_metrics():
    """Calcula las métricas reales del historial acumulado."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT estado FROM predictions WHERE estado IN ('GANADA', 'PERDIDA')")
        rows = cursor.fetchall()

    total = len(rows)
    if total == 0:
        return {
            "precision": "0.0%",
            "roi_promedio": "+0.0%",
            "partidos_evaluados": 0,
            "ganadas": 0,
            "perdidas": 0
        }

    ganadas = sum(1 for r in rows if r[0] == 'GANADA')
    perdidas = total - ganadas
    precision = round((ganadas / total) * 100, 1)
    ganancia_unidades = (ganadas * 0.85) - perdidas
    roi = round((ganancia_unidades / total) * 100, 1)

    return {
        "precision": f"{precision}%",
        "roi_promedio": f"+{roi}%" if roi >= 0 else f"{roi}%",
        "partidos_evaluados": total,
        "ganadas": ganadas,
        "perdidas": perdidas
    }