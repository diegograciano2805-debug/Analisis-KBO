import numpy as np
import pandas as pd
from scraper import fetch_live_kbo_data, fetch_live_weather


def get_kbo_schedule(target_date):
  """Obtiene el calendario llamando al scraper web en tiempo real con respaldo sintético."""
  # 1. Intentar scraping en vivo
  scraped_games = fetch_live_kbo_data(target_date)

  if scraped_games:
    df = pd.DataFrame(scraped_games)
    print(
        f'✅ Se extrajeron exitosamente {len(df)} partidos reales vía Web'
        ' Scraping.'
    )
  else:
    print(
        '⚠️ No se detectaron datos en vivo o la web no responde. Usando'
        ' respaldo de cartelera KBO...'
    )
    partidos_default = [
        {"equipo_visitante": "Samsung Lions", "equipo_local": "Kia Tigers"},
        {"equipo_visitante": "Lotte Giants", "equipo_local": "SSG Landers"},
        {"equipo_visitante": "LG Twins", "equipo_local": "Kiwoom Heroes"},
        {"equipo_visitante": "KT Wiz", "equipo_local": "NC Dinos"},
        {"equipo_visitante": "Hanwha Eagles", "equipo_local": "Doosan Bears"},
    ]
    df = pd.DataFrame(partidos_default)

  df["fecha"] = target_date

  # 2. Asignar métricas avanzadas (FIP, WHIP, wOBA)
  size = len(df)
  df["Home_Lineup_OPS"] = np.round(
      np.random.uniform(0.700, 0.850, size=size), 3
  )
  df["Away_Lineup_OPS"] = np.round(
      np.random.uniform(0.700, 0.850, size=size), 3
  )
  df["Home_Starter_ERA"] = np.round(
      np.random.uniform(2.50, 5.50, size=size), 2
  )
  df["Away_Starter_ERA"] = np.round(
      np.random.uniform(2.50, 5.50, size=size), 2
  )
  df["L10_Diff"] = np.random.randint(-5, 6, size=size)

  df["Home_Starter_FIP"] = np.round(
      np.random.uniform(2.80, 5.20, size=size), 2
  )
  df["Away_Starter_FIP"] = np.round(
      np.random.uniform(2.80, 5.20, size=size), 2
  )
  df["Home_Starter_WHIP"] = np.round(
      np.random.uniform(1.05, 1.55, size=size), 2
  )
  df["Away_Starter_WHIP"] = np.round(
      np.random.uniform(1.05, 1.55, size=size), 2
  )
  df["Home_Lineup_wOBA"] = np.round(
      np.random.uniform(0.310, 0.370, size=size), 3
  )
  df["Away_Lineup_wOBA"] = np.round(
      np.random.uniform(0.310, 0.370, size=size), 3
  )

  # 3. Integrar variables de clima extraídas
  clima_list = [fetch_live_weather(row["equipo_local"]) for _, row in df.iterrows()]
  df["temperatura_c"] = [c["temperatura_c"] for c in clima_list]
  df["viento_kmh"] = [c["viento_kmh"] for c in clima_list]

  return df