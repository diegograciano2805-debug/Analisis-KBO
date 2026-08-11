import requests
from bs4 import BeautifulSoup

def fetch_live_kbo_data(target_date):
    """Extrae los partidos programados y abridores de la KBO."""
    url = f"https://mykbostats.com/games?date={target_date}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        games_data = []

        game_cards = soup.select(".game-card, .matchup-container, tr.game-row")

        for card in game_cards:
            teams = card.select(".team-name, .team")
            starters = card.select(".pitcher-name, .starter")

            if len(teams) >= 2:
                away_team = teams[0].get_text(strip=True)
                home_team = teams[1].get_text(strip=True)

                away_starter = starters[0].get_text(strip=True) if len(starters) >= 1 else "TBD Abridor"
                home_starter = starters[1].get_text(strip=True) if len(starters) >= 2 else "TBD Abridor"

                games_data.append({
                    "equipo_visitante": away_team,
                    "equipo_local": home_team,
                    "abridor_visitante": away_starter,
                    "abridor_local": home_starter
                })

        return games_data

    except Exception as e:
        print(f"⚠️ Error al conectar con el servidor de scraping: {e}")
        return []


def fetch_kbo_final_scores(target_date):
    """Obtiene EXCLUSIVAMENTE marcadores reales de la web si el partido ya terminó."""
    url = f"https://mykbostats.com/games?date={target_date}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    scores = {}

    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            game_cards = soup.select(".game-card, .matchup-container, tr.game-row")

            for card in game_cards:
                teams = card.select(".team-name, .team")
                runs = card.select(".runs, .score")

                if len(teams) >= 2 and len(runs) >= 2:
                    away = teams[0].get_text(strip=True)
                    home = teams[1].get_text(strip=True)
                    try:
                        away_runs = int(runs[0].get_text(strip=True))
                        home_runs = int(runs[1].get_text(strip=True))
                        partido_key = f"{away} vs {home}"
                        scores[partido_key] = {
                            "away_runs": away_runs,
                            "home_runs": home_runs,
                            "ganador_real": home if home_runs > away_runs else away,
                            "total_carreras": away_runs + home_runs
                        }
                    except ValueError:
                        pass
    except Exception as e:
        print(f"⚠️ Error extrayendo marcadores web: {e}")

    return scores


def fetch_live_weather(city_name):
    """Genera datos de clima deterministas basados en el nombre de la ciudad."""
    seed_val = abs(hash(city_name))
    temp = 20 + (seed_val % 10)
    viento = 5 + (seed_val % 15)
    return {
        "temperatura_c": temp,
        "viento_kmh": viento
    }