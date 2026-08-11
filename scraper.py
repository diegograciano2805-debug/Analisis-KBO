import requests
from bs4 import BeautifulSoup

def fetch_live_kbo_data(target_date):
    """Extrae los partidos programados, abridores y su estado actual (cancelado, pospuesto, etc.)."""
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
            
            # Detectar estado de cancelación / posposición en el texto del partido
            card_text = card.get_text().lower()
            is_canceled = any(word in card_text for word in ["cancel", "postpone", "ppd", "rainout", "suspend"])

            if len(teams) >= 2:
                away_team = teams[0].get_text(strip=True)
                home_team = teams[1].get_text(strip=True)

                away_starter = starters[0].get_text(strip=True) if len(starters) >= 1 else "TBD Abridor"
                home_starter = starters[1].get_text(strip=True) if len(starters) >= 2 else "TBD Abridor"

                games_data.append({
                    "equipo_visitante": away_team,
                    "equipo_local": home_team,
                    "abridor_visitante": away_starter,
                    "abridor_local": home_starter,
                    "estado_web": "CANCELADO" if is_canceled else "PROGRAMADO"
                })

        return games_data

    except Exception as e:
        print(f"⚠️ Error al conectar con el servidor de scraping: {e}")
        return []


def fetch_kbo_final_scores(target_date):
    """Obtiene marcadores reales o estado de cancelación de la web."""
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
                card_text = card.get_text().lower()

                if len(teams) >= 2:
                    away = teams[0].get_text(strip=True)
                    home = teams[1].get_text(strip=True)
                    partido_key = f"{away} vs {home}"

                    if any(word in card_text for word in ["cancel", "postpone", "ppd", "rainout"]):
                        scores[partido_key] = {"cancelado": True}
                    elif len(runs) >= 2:
                        try:
                            away_runs = int(runs[0].get_text(strip=True))
                            home_runs = int(runs[1].get_text(strip=True))
                            scores[partido_key] = {
                                "cancelado": False,
                                "away_runs": away_runs,
                                "home_runs": home_runs,
                                "ganador_real": home if home_runs > away_runs else away
                            }
                        except ValueError:
                            pass
    except Exception as e:
        print(f"⚠️ Error extrayendo marcadores web: {e}")

    return scores


def fetch_live_weather(city_name):
    """Genera datos de clima deterministas."""
    seed_val = abs(hash(city_name))
    return {
        "temperatura_c": 20 + (seed_val % 10),
        "viento_kmh": 5 + (seed_val % 15)
    }