from database import init_db, save_prediction
from KBO import get_kbo_schedule
from process_data import compute_features


def run_autonomous_pipeline(target_date):
  init_db()
  raw_df = get_kbo_schedule(target_date)

  if raw_df.empty:
    return False

  processed_df = compute_features(raw_df)

  for idx, row in processed_df.iterrows():
    partido_str = f"{row['equipo_visitante']} vs {row['equipo_local']}"
    save_prediction(
        fecha=target_date,
        partido=partido_str,
        home=row['equipo_local'],
        away=row['equipo_visitante'],
        favorito=row['prediccion_ganador'],
        prob=float(row['probabilidad_local']),
        rec_ou=row['recomendacion_ou'],
        rec_rl=row['recomendacion_runline'],
        stake=row['stake_sugerido'],
        clima=row['clima_info'],
        momio=float(row['momio_decimal']),
        ev=row['ev_label'],
    )
  return True