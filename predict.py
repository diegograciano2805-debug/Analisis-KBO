import os
import joblib
import pandas as pd

MODEL_PATH = "models/kbo_model.pkl"
FEATURED_DATA_PATH = "data/kbo_featured_games.csv"

KBO_TEAMS = [
    "SSG Landers", "LG Twins", "Doosan Bears", "KT Wiz", "NC Dinos",
    "Kia Tigers", "Lotte Giants", "Samsung Lions", "Hanwha Eagles", "Kiwoom Heroes"
]


def get_latest_team_l10(team_name, df):
    team_games = df[(df["Away_Team"] == team_name) | (df["Home_Team"] == team_name)]
    if team_games.empty:
        return 0.500
    last_game = team_games.iloc[-1]
    return last_game["Home_L10"] if last_game["Home_Team"] == team_name else last_game["Away_L10"]


def predict_game(home_team, away_team, home_era, away_era):
    if not os.path.exists(MODEL_PATH):
        print("[!] No se encontró el modelo. Ejecuta 'train_model.py' primero.")
        return

    model = joblib.load(MODEL_PATH)

    if os.path.exists(FEATURED_DATA_PATH):
        df = pd.read_csv(FEATURED_DATA_PATH)
        home_l10 = get_latest_team_l10(home_team, df)
        away_l10 = get_latest_team_l10(away_team, df)
    else:
        home_l10, away_l10 = 0.500, 0.500

    l10_diff = home_l10 - away_l10
    era_diff = home_era - away_era

    X_input = pd.DataFrame([{
        "Away_L10": away_l10,
        "Home_L10": home_l10,
        "L10_Diff": l10_diff,
        "Away_Pitcher_ERA": away_era,
        "Home_Pitcher_ERA": home_era,
        "ERA_Diff": era_diff
    }])

    prob = model.predict_proba(X_input)[0]
    prob_home = prob[1] if len(prob) > 1 else prob[0]
    prob_away = 1 - prob_home

    winner = home_team if prob_home >= 0.5 else away_team

    print("\n==========================================")
    print("   PREDICCIÓN KBO (L10 + Pitcher Abridor)")
    print("==========================================")
    print(f" Local: {home_team} (L10: {home_l10:.3f} | ERA Abridor: {home_era:.2f})")
    print(f" Visitante: {away_team} (L10: {away_l10:.3f} | ERA Abridor: {away_era:.2f})")
    print(f" Diferencial ERA: {era_diff:+.2f} (Menor es mejor)\n")
    print(f" Probabilidad [{home_team} - Local]: {prob_home * 100:.1f}%")
    print(f" Probabilidad [{away_team} - Visitante]: {prob_away * 100:.1f}%")
    print(f"\n GANADOR PRONOSTICADO: {winner.upper()}")
    print("==========================================\n")


def main():
    while True:
        print("\n--- MENÚ DE PREDICCIÓN KBO (CON PITCHERS) ---")
        for idx, team in enumerate(KBO_TEAMS, 1):
            print(f" {idx}. {team}")
        print(" 0. Salir")

        try:
            home_idx = int(input("\nNúmero del equipo LOCAL: "))
            if home_idx == 0: break
            away_idx = int(input("Número del equipo VISITANTE: "))
            if away_idx == 0: break

            if home_idx == away_idx:
                print("\n[!] Equipos deben ser distintos.")
                continue

            home_era = float(input(f"ERA del Abridor de {KBO_TEAMS[home_idx-1]} (ej. 3.45): "))
            away_era = float(input(f"ERA del Abridor de {KBO_TEAMS[away_idx-1]} (ej. 4.10): "))

            predict_game(KBO_TEAMS[home_idx-1], KBO_TEAMS[away_idx-1], home_era, away_era)

        except (ValueError, IndexError):
            print("\n[!] Selección inválida.")


if __name__ == "__main__":
    main()