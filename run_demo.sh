#!/usr/bin/env bash
#
# run_demo.sh
#
# Lance automatiquement, dans l'ordre, tous les composants de la demo
# IDXIA : stack Docker (Elasticsearch/Kibana/Suricata/Filebeat), API
# backend, app de demo (login HTTPS), agregateur de features.
#
# L'attaque (attacker-simulator) N'EST PAS lancee automatiquement :
# elle se declenche manuellement, au moment choisi, avec la commande
# affichee a la fin de ce script.
#
# A placer a la racine du projet (au meme niveau que model/, backend/,
# demo-webapp/, etc.)
#
# Usage :
#   chmod +x run_demo.sh stop_demo.sh
#   ./run_demo.sh
#
# Pour tout arreter proprement :
#   ./stop_demo.sh

set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$PROJECT_ROOT/.demo_pids"

mkdir -p "$LOG_DIR"
: > "$PID_FILE"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}OK${NC}        - $1"; }
warn() { echo -e "${YELLOW}ATTENTION${NC} - $1"; }
fail() { echo -e "${RED}ECHEC${NC}     - $1"; }

wait_for_http() {
    # wait_for_http <url> <description> <timeout_secondes>
    local url="$1" desc="$2" timeout="${3:-30}"
    local waited=0
    while ! curl -ks -o /dev/null "$url"; do
        sleep 2
        waited=$((waited + 2))
        if [ "$waited" -ge "$timeout" ]; then
            fail "$desc ne répond pas après ${timeout}s ($url)"
            return 1
        fi
    done
    ok "$desc est prêt ($url)"
    return 0
}

start_background() {
    # start_background <nom_du_log> <dossier> <commande...>
    local name="$1" dir="$2"
    shift 2
    (
        cd "$dir" || exit 1
        # shellcheck disable=SC1091
        source venv/bin/activate
        nohup "$@" > "$LOG_DIR/${name}.log" 2>&1 &
        echo $! >> "$PID_FILE"
    )
}

echo "=================================================="
echo " IDXIA — Lancement automatique de la démo"
echo "=================================================="
echo

# --- 1. Stack Docker (Elasticsearch, Kibana, Suricata, Filebeat) ---
echo "[1/4] Stack Docker (Elasticsearch / Kibana / Suricata / Filebeat)"
(cd "$PROJECT_ROOT/elk-suricata" && docker compose up -d)

wait_for_http "http://localhost:9200" "Elasticsearch" 60
wait_for_http "http://localhost:5601/api/status" "Kibana" 90

SURICATA_STATUS=$(docker inspect -f '{{.State.Status}}' idxia-suricata 2>/dev/null)
if [ "$SURICATA_STATUS" = "running" ]; then
    ok "Suricata est en cours d'exécution"
else
    warn "Suricata n'est pas 'running' (statut: ${SURICATA_STATUS:-inconnu}). Vérifie : docker compose logs suricata"
fi
echo

# --- 2. Backend API ---
echo "[2/4] Backend API (FastAPI)"
start_background "backend" "$PROJECT_ROOT/backend" uvicorn app.main:app --port 8000
wait_for_http "http://localhost:8000/health" "API backend" 30
echo

# --- 3. App de démo (login HTTPS) ---
echo "[3/4] App de démo (login HTTPS)"
start_background "demo-webapp" "$PROJECT_ROOT/demo-webapp" python3 app.py
wait_for_http "https://localhost:5443/health" "App de démo" 30
echo

# --- 4. Agrégateur de features ---
echo "[4/4] Agrégateur de features (logs → API)"
start_background "feature-aggregator" "$PROJECT_ROOT/feature-aggregator" \
    python3 feature_aggregator.py --log "$PROJECT_ROOT/demo-webapp/login_attempts.log"
sleep 2
ok "Agrégateur démarré (logs : $LOG_DIR/feature-aggregator.log)"
echo

echo "=================================================="
echo " Tout est prêt."
echo "=================================================="
echo
echo "Dashboards à ouvrir :"
echo "  - Kibana             : http://localhost:5601"
echo "  - Doc API (Swagger)  : http://localhost:8000/docs"
echo
echo "Logs en direct si besoin :"
echo "  tail -f $LOG_DIR/backend.log"
echo "  tail -f $LOG_DIR/demo-webapp.log"
echo "  tail -f $LOG_DIR/feature-aggregator.log"
echo
echo "Pour déclencher l'attaque AU MOMENT CHOISI pendant la soutenance :"
echo "  cd attacker-simulator && source venv/bin/activate && python3 attack_credential_stuffing.py --count 30"
echo
echo "Pour tout arrêter proprement à la fin :"
echo "  ./stop_demo.sh"
echo
