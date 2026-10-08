#!/usr/bin/env bash
#
# stop_demo.sh
#
# Arrete proprement tous les processus Python demarres par run_demo.sh
# (backend, demo-webapp, feature-aggregator), et propose d'arreter aussi
# la stack Docker (Elasticsearch/Kibana/Suricata/Filebeat).
#
# Usage :
#   ./stop_demo.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_ROOT/.demo_pids"

echo "Arrêt des processus Python de la démo..."
if [ -f "$PID_FILE" ]; then
    while read -r pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  - processus $pid arrêté"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
else
    echo "  (aucun fichier de PIDs trouvé, rien à arrêter côté Python)"
fi

echo
read -r -p "Arrêter aussi la stack Docker (Elasticsearch/Kibana/Suricata) ? [o/N] " reponse
if [[ "$reponse" =~ ^[oO]$ ]]; then
    (cd "$PROJECT_ROOT/elk-suricata" && docker compose down)
    echo "Stack Docker arrêtée."
else
    echo "Stack Docker laissée en cours d'exécution."
fi

echo "Terminé."
