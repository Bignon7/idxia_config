"""
app.py

Mini application web de demo (login HTTPS) pour IDXIA.
Sert de cible au scenario de demonstration : une attaque de credential
stuffing menee en HTTPS, invisible pour un IDS a signatures (le contenu
est chiffre) mais detectee par IDXIA via les logs applicatifs.

Installation :
    pip install flask pyopenssl

Lancement (certificat auto-signe genere a la volee) :
    python app.py
Le service ecoute sur https://localhost:5443/login
"""

import json
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

LOG_PATH = os.path.join(os.path.dirname(__file__), "login_attempts.log")

# Un seul compte legitime pour la demo ; tout le reste est refuse.
VALID_CREDENTIALS = {"alice": "S3curePass!2024"}


def log_attempt(ip: str, username: str, success: bool, user_agent: str) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_ip": ip,
        "username": username,
        "success": success,
        "user_agent": user_agent,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    success = VALID_CREDENTIALS.get(username) == password

    log_attempt(
        ip=request.remote_addr,
        username=username,
        success=success,
        user_agent=request.headers.get("User-Agent", "Unknown"),
    )

    if success:
        return jsonify({"status": "ok", "message": "Connexion reussie"}), 200
    return jsonify({"status": "error", "message": "Identifiants invalides"}), 401


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5443, ssl_context="adhoc")