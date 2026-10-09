# IDXIA — Détection comportementale explicable, complémentaire à un IDS à signatures

IDXIA détecte les abus d'authentification (brute-force, credential stuffing) à partir de métadonnées de session, et explique chaque décision en langage clair. Le projet démontre de façon reproductible une limite des IDS à signatures : face à une attaque menée sur un canal chiffré (HTTPS), Suricata observe les connexions mais ne génère aucune alerte, alors qu'IDXIA détecte l'attaque et la justifie. Les deux sources d'alertes sont centralisées dans Elasticsearch et comparées dans Kibana.

## Architecture

```
   Dataset Kaggle                     App de démo (login HTTPS, port 5443)
        |                                      |
        | entraînement                         | logs applicatifs bruts
        v                                      v
   Modèle + SHAP  <---- API FastAPI <---- Agrégateur de features
   (model/)             (backend/, 8000)   (feature-aggregator/)
                              |
                              | indexation (index idxia-alerts)
                              v
   Suricata + Filebeat ---> Elasticsearch ---> Kibana
   (index suricata-*)        (elk-suricata/)
```

## Structure du dépôt

| Dossier / fichier | Rôle |
|---|---|
| `model/` | Pipeline d'entraînement, évaluation et explicabilité (voir `model/README.md`) |
| `backend/` | API FastAPI de prédiction (voir `backend/README.md`) |
| `demo-webapp/` | Application cible de la démonstration : formulaire de connexion en HTTPS |
| `attacker-simulator/` | Script de credential stuffing contre l'application de démonstration |
| `feature-aggregator/` | Transforme les logs de connexion en variables de session et interroge l'API |
| `elk-suricata/` | Docker Compose : Elasticsearch, Kibana, Suricata, Filebeat (voir `elk-suricata/README.md`) |
| `cic_validation/` | Validation sur CIC-IDS2017, piste d'approfondissement en pause |
| `run_demo.sh` / `stop_demo.sh` | Lancement et arrêt orchestrés de la démonstration |
| `logs/` | Journaux des services lancés par `run_demo.sh` (généré) |

## Prérequis

- Linux (testé sous Ubuntu). Suricata utilise le mode réseau `host` de Docker, non disponible sous macOS ni Windows.
- Docker et Docker Compose.
- Python 3.11 ou supérieur, `curl`.
- Réglage noyau requis par Elasticsearch : `sudo sysctl -w vm.max_map_count=262144`.

## Installation (une seule fois)

1. Entraîner le modèle en suivant `model/README.md`. Cette étape produit les fichiers consommés par l'API.

2. Créer un environnement virtuel dans chaque module exécuté par `run_demo.sh`. Le nom `venv` est attendu par le script.

```bash
for d in backend demo-webapp feature-aggregator attacker-simulator; do
  (cd "$d" && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt)
done
```

3. Télécharger les règles Suricata (ruleset Emerging Threats Open) dans le volume Docker persistant :

```bash
cd elk-suricata
docker compose up -d elasticsearch kibana
docker compose run --rm suricata suricata-update
cd ..
```

Le message `Reload command failed ... suricata-command.socket` affiché à la fin de cette commande est sans gravité si Suricata n'est pas encore démarré.

## Lancer la démonstration

```bash
chmod +x run_demo.sh stop_demo.sh
./run_demo.sh
```

Le script démarre dans l'ordre la stack Docker, l'API, l'application de démonstration et l'agrégateur, en vérifiant la disponibilité de chaque composant. L'attaque n'est pas lancée automatiquement. Pour la déclencher :

```bash
cd attacker-simulator
source venv/bin/activate
python3 attack_credential_stuffing.py --count 30
```

Pour tout arrêter : `./stop_demo.sh`.

## Observer le résultat dans Kibana

1. Ouvrir http://localhost:5601, puis Stack Management, Data Views.
2. Créer deux data views : `suricata-*` et `idxia-alerts*`.
3. Dans Discover, comparer les deux sur la fenêtre de temps de l'attaque.

Résultat attendu :
- `idxia-alerts*` : alertes de niveau critique avec le champ `explanation_text` ;
- `suricata-*` : événements TLS (SNI, version, empreinte JA4) sur le port 5443, mais aucune alerte.

Vérification en ligne de commande côté Suricata (ne doit rien retourner) :

```bash
docker exec idxia-suricata sh -c 'grep "\"dest_port\":5443" /var/log/suricata/eve.json | grep "\"event_type\":\"alert\""'
```

Test de contrôle prouvant que Suricata détecte bien les attaques réseau classiques : `nmap localhost` (ou `sudo nmap -sS -T4 -p 1-1000 localhost`) génère des alertes dans `eve.json`.

## Périmètre et limites

- IDXIA cible les abus d'authentification. Il ne couvre pas les attaques réseau de bas niveau (ARP spoofing, tunneling DNS, scans de ports, déni de service).
- Le dataset d'entraînement est synthétique ; les performances ne se transposent pas directement à du trafic réel.
- Environnement de démonstration uniquement : conteneur Suricata en mode `privileged`, sécurité d'Elasticsearch désactivée, API sans authentification, certificat TLS auto-signé.
- Aucune notification en temps réel (email, Telegram) : la supervision passe par Kibana.
- Certaines variables envoyées par l'agrégateur sont des constantes ou des heuristiques (taille de paquet, protocole, chiffrement, réputation IP), faute d'être observables depuis des logs applicatifs.

## Crédits

- Dataset : "Cybersecurity Intrusion Detection Dataset" (Kaggle, licence MIT).
- IDS : Suricata, avec le ruleset Emerging Threats Open.
- Supervision : Elasticsearch, Kibana et Filebeat.