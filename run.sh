#!/bin/bash
# ==============================================================================
# Script d'exécution du projet VF_projet
# ==============================================================================
# Usage:
#   ./run.sh                    # Affiche l'aide
#   ./run.sh v12                # Exécute le modèle V12
#   ./run.sh v13                # Exécute le modèle V13
#   ./run.sh config             # Affiche la configuration
#   ./run.sh install            # Installe les dépendances
# ==============================================================================

# Chemin du script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activation du venv
source venv/bin/activate 2>/dev/null || {
    echo "Erreur: L'environnement virtuel n'existe pas."
    echo "   Creez-le avec: python3 -m venv venv"
    echo "   Puis installez les dependances: ./run.sh install"
    exit 1
}

case "$1" in
    v12)
        echo "Execution du modele V12..."
        python best_models/V12_15Features.py
        ;;
    v13)
        echo "Execution du modele V13..."
        python best_models/V13_11Features.py
        ;;
    config)
        echo "Configuration du projet:"
        python config.py
        ;;
    install)
        echo "Installation des dependances..."
        pip install -r requirements.txt
        ;;
    jupyter)
        echo "Lancement de Jupyter..."
        jupyter notebook
        ;;
    *)
        echo "=================================="
        echo "Projet VF - Prediction Grippe"
        echo "=================================="
        echo ""
        echo "Usage: ./run.sh <commande>"
        echo ""
        echo "Commandes disponibles:"
        echo "  v12      Exécute le modèle V12 (15 features)"
        echo "  v13      Exécute le modèle V13 (11 features)"
        echo "  config   Affiche la configuration des chemins"
        echo "  install  Installe les dépendances Python"
        echo "  jupyter  Lance Jupyter Notebook"
        echo ""
        echo "Environnement Python: $(python --version)"
        echo "Chemin: $(which python)"
        ;;
esac
