import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

def train_advanced_model():
    path = "data/kbo_featured_games.csv"
    if not os.path.exists(path):
        print(f"[!] No se encontró {path}. Corre 'process_data.py' primero.")
        return

    df = pd.read_csv(path)

    features = [
        "Away_L10", "Home_L10", "L10_Diff",
        "Away_Pitcher_ERA", "Home_Pitcher_ERA", "ERA_Diff",
        "Away_Lineup_OPS", "Home_Lineup_OPS", "OPS_Diff",
        "Away_Bullpen_ERA", "Home_Bullpen_ERA", "Bullpen_ERA_Diff"
    ]
    
    X = df[features]
    y = df["Home_Win"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=180, max_depth=7, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/kbo_model.pkl")

    print("\n--- Modelo Reentrenado con Métricas Avanzadas ---")
    print(f"Registros analizados: {len(X)}")
    print(f"Precisión del Modelo: {acc * 100:.2f}%")
    print("Modelo guardado en: 'models/kbo_model.pkl'\n")

if __name__ == "__main__":
    train_advanced_model()