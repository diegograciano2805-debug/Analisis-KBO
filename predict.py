import hashlib

# Ranking de potencia estático para la KBO para generar pronósticos estables
TEAM_RATINGS = {
    "Kia Tigers": 0.62,
    "LG Twins": 0.58,
    "Samsung Lions": 0.55,
    "Doosan Bears": 0.53,
    "KT Wiz": 0.51,
    "SSG Landers": 0.49,
    "NC Dinos": 0.47,
    "Lotte Giants": 0.45,
    "Hanwha Eagles": 0.42,
    "Kiwoom Heroes": 0.38
}

def generar_pronostico_partido(match):
    away_team = match.get("equipo_visitante", "Equipo A")
    home_team = match.get("equipo_local", "Equipo B")

    rating_away = TEAM_RATINGS.get(away_team, 0.50)
    rating_home = TEAM_RATINGS.get(home_team, 0.50) + 0.04 # Ventaja de localía

    # Probabilidad base determinista
    total = rating_away + rating_home
    prob_local = round(rating_home / total, 3)
    prob_away = round(1.0 - prob_local, 3)

    # Favorito
    favorito = home_team if prob_local >= 0.5 else away_team
    prob_fav = prob_local if prob_local >= 0.5 else prob_away

    # Momio y EV determinista
    momio = round(1 / prob_fav, 2)
    ev_val = round(((prob_fav * momio) - 1.0) * 100, 1)
    ev_label = f"+{ev_val}% EV" if ev_val >= 0 else f"{ev_val}% EV"

    # Determinista de Altas/Bajas basado en los equipos
    match_hash = int(hashlib.md5(f"{away_team}{home_team}".encode()).hexdigest(), 16)
    ou_line = 8.5 if (match_hash % 2 == 0) else 9.5
    ou_pick = "Over" if (match_hash % 3 != 0) else "Under"

    return {
        "equipo_visitante": away_team,
        "equipo_local": home_team,
        "abridor_visitante": match.get("abridor_visitante", "TBD Abridor"),
        "abridor_local": match.get("abridor_local", "TBD Abridor"),
        "probabilidad_local": prob_local,
        "probabilidad_visitante": prob_away,
        "favorito_pronostico": favorito,
        "momio_decimal": momio,
        "ev_label": ev_label,
        "recomendacion_ou": f"{ou_pick} {ou_line}",
        "recomendacion_runline": f"{away_team} +1.5" if favorito == home_team else f"{home_team} +1.5",
        "stake_sugerido": "2.5%" if ev_val > 3.0 else ("1.5%" if ev_val > 0 else "0.0%"),
        "clima_info": "24°C, Viento 12 km/h"
    }