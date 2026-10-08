"""
feature_aggregator.py

Surveille en continu le fichier de logs de l'app de demo
(login_attempts.log), agrege les tentatives par adresse IP source sur
une fenetre glissante, calcule les features attendues par l'API IDXIA,
et envoie chaque evenement pour prediction.

Equivalent simplifie de ce que ferait un pipeline Logstash/Filebeat dans
un vrai SOC : transformer des logs bruts en evenements exploitables par
un moteur de detection.

Usage :
    python feature_aggregator.py --log ../demo-webapp/login_attempts.log
"""

import argparse
import json
import time
from collections import defaultdict
from datetime import datetime

import requests

API_URL = "http://localhost:8000/predict"
WINDOW_SECONDS = 60
POLL_INTERVAL = 2


def parse_timestamp(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def build_features(attempts: list) -> dict:
    """A partir des tentatives recentes (fenetre glissante) pour UNE IP,
    construit les features attendues par le schema SessionInput de
    l'API (memes colonnes que le dataset d'entrainement)."""
    login_attempts = len(attempts)
    failed_logins = sum(1 for a in attempts if not a["success"])
    first_ts = parse_timestamp(attempts[0]["timestamp"])
    last_ts = parse_timestamp(attempts[-1]["timestamp"])
    session_duration = max((last_ts - first_ts).total_seconds(), 0.1)

    hour = last_ts.hour
    unusual_time_access = 1 if (hour < 6 or hour >= 22) else 0

    # Heuristique simple de reputation IP pour la demo : plus il y a
    # d'echecs rapproches, plus le score monte. Dans un systeme reel, ce
    # serait une base de reputation externe (threat intel).
    ip_reputation_score = min(0.95, 0.1 + failed_logins * 0.08)

    user_agent = attempts[-1].get("user_agent", "Unknown")
    browser_type = "Unknown" if "Mozilla" not in user_agent else "Chrome"

    return {
        "network_packet_size": 450,  # non observable depuis des logs applicatifs
        "protocol_type": "TCP",
        "login_attempts": login_attempts,
        "session_duration": session_duration,
        "encryption_used": "AES",  # le trafic est en HTTPS
        "ip_reputation_score": ip_reputation_score,
        "failed_logins": failed_logins,
        "browser_type": browser_type,
        "unusual_time_access": unusual_time_access,
    }


def tail_log(path: str):
    """Genere les nouvelles lignes ajoutees au fichier au fur et a
    mesure, comme `tail -f`."""
    with open(path, "r", encoding="utf-8") as f:
        f.seek(0, 2)  # se positionne a la fin du fichier existant
        while True:
            line = f.readline()
            if not line:
                time.sleep(POLL_INTERVAL)
                continue
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="Chemin vers login_attempts.log")
    args = parser.parse_args()

    windows = defaultdict(list)

    print(f"Surveillance de {args.log} (fenetre glissante {WINDOW_SECONDS}s)...\n")

    for entry in tail_log(args.log):
        ip = entry["source_ip"]
        windows[ip].append(entry)

        now = parse_timestamp(entry["timestamp"])
        windows[ip] = [
            a
            for a in windows[ip]
            if (now - parse_timestamp(a["timestamp"])).total_seconds() <= WINDOW_SECONDS
        ]

        features = build_features(windows[ip])

        try:
            resp = requests.post(API_URL, json=features, timeout=5)
            result = resp.json()
            print(
                f"[{ip}] tentatives={features['login_attempts']} "
                f"echecs={features['failed_logins']} -> "
                f"{result['risk_level']} (proba={result['probability_attack']:.2f})"
            )
            print(f"    {result['explanation_text']}")
        except requests.RequestException as e:
            print(f"[{ip}] Erreur API : {e}")


if __name__ == "__main__":
    main()