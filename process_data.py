import numpy as np
import pandas as pd

PARK_FACTORS = {
    "Kia Tigers": 1.05,
    "SSG Landers": 1.12,
    "Kiwoom Heroes": 0.94,
    "NC Dinos": 1.02,
    "Doosan Bears": 0.88,
    "LG Twins": 0.88,
    "Samsung Lions": 1.10,
    "Lotte Giants": 0.96,
    "KT Wiz": 1.03,
    "Hanwha Eagles": 0.98,
}


def calculate_kelly_criterion(prob, decimal_odds=1.90, max_fraction=0.08):
  b = decimal_odds - 1.0
  q = 1.0 - prob
  f_kelly = (b * prob - q) / b

  if f_kelly <= 0:
    if prob >= 0.55:
      return "1.0%"
    return "0.0%"

  half_kelly = min(f_kelly * 0.50, max_fraction)
  final_stake = max(half_kelly, 0.015)
  return f"{round(final_stake * 100, 1)}%"


def calculate_ev(prob, decimal_odds):
  ev = (prob * decimal_odds) - 1.0
  return round(ev * 100, 1)


def compute_features(df):
  df = df.copy()

  # Bullpen
  df["Away_Bullpen_ERA"] = np.round(
      np.random.normal(loc=4.30, scale=0.70, size=len(df)), 2
  ).clip(2.00, 7.00)
  df["Home_Bullpen_ERA"] = np.round(
      np.random.normal(loc=4.20, scale=0.70, size=len(df)), 2
  ).clip(2.00, 7.00)
  df["Bullpen_ERA_Diff"] = df["Home_Bullpen_ERA"] - df["Away_Bullpen_ERA"]

  # Métricas Avanzadas
  df["FIP_Diff"] = df["Home_Starter_FIP"] - df["Away_Starter_FIP"]
  df["WHIP_Diff"] = df["Home_Starter_WHIP"] - df["Away_Starter_WHIP"]
  df["wOBA_Diff"] = df["Home_Lineup_wOBA"] - df["Away_Lineup_wOBA"]

  # Modelo Win Prob
  win_prob = (
      0.50
      + (df["L10_Diff"] * 0.015)
      - (df["FIP_Diff"] * 0.06)
      - (df["WHIP_Diff"] * 0.08)
      + (df["wOBA_Diff"] * 0.85)
      - (df["Bullpen_ERA_Diff"] * 0.03)
  )
  df["probabilidad_local"] = win_prob.clip(0.18, 0.82)

  df["prediccion_ganador"] = np.where(
      df["probabilidad_local"] >= 0.50,
      df["equipo_local"],
      df["equipo_visitante"],
  )

  # Momios y EV
  prob_ganador = np.where(
      df["prediccion_ganador"] == df["equipo_local"],
      df["probabilidad_local"],
      1 - df["probabilidad_local"],
  )
  df["momio_decimal"] = np.round(
      (1.0 / prob_ganador) * np.random.uniform(0.92, 1.08, size=len(df)), 2
  ).clip(1.30, 3.50)

  df["ev_porcentaje"] = [
      calculate_ev(p, o) for p, o in zip(prob_ganador, df["momio_decimal"])
  ]
  df["ev_label"] = df["ev_porcentaje"].apply(
      lambda x: f"+{x}% EV" if x > 0 else f"{x}% EV"
  )

  # Over/Under
  df["park_factor"] = df["equipo_local"].map(PARK_FACTORS).fillna(1.00)
  weather_modifier = 1.0 + (
      (df["temperatura_c"] - 22) * 0.005 + (df["viento_kmh"] - 10) * 0.003
  )

  total_carreras_base = (
      df["Home_Starter_FIP"] + df["Away_Starter_FIP"]
  ) * 0.80 + (df["Home_Lineup_wOBA"] + df["Away_Lineup_wOBA"]) * 8.0

  total_carreras_ajustado = (
      total_carreras_base * df["park_factor"] * weather_modifier
  )

  df["linea_over_under"] = 8.5
  df["recomendacion_ou"] = np.where(
      total_carreras_ajustado > 9.0,
      f"Over {df['linea_over_under'].iloc[0]}",
      f"Under {df['linea_over_under'].iloc[0]}",
  )

  # Runline
  df["recomendacion_runline"] = np.where(
      df["probabilidad_local"] >= 0.62,
      df["equipo_local"] + " -1.5",
      np.where(
          df["probabilidad_local"] <= 0.38,
          df["equipo_visitante"] + " -1.5",
          df["equipo_visitante"] + " +1.5",
      ),
  )

  # Criterio de Kelly
  df["stake_sugerido"] = [
      calculate_kelly_criterion(p, o)
      for p, o in zip(prob_ganador, df["momio_decimal"])
  ]

  df["clima_info"] = (
      df["temperatura_c"].astype(str)
      + "°C, "
      + df["viento_kmh"].astype(str)
      + " km/h"
  )

  return df