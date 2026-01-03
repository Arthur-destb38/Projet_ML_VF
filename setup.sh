#!/bin/bash
# ==============================================================================
# SCRIPT D'INSTALLATION ET D'EXÉCUTION COMPLET
# Projet Prédiction Grippe - Challenge Kaggle
# ==============================================================================
# Usage:
#   ./setup.sh              # Installation complète + aide
#   ./setup.sh install      # Installe l'environnement et dépendances
#   ./setup.sh run          # Exécute tout le pipeline (fusion + modèle)
#   ./setup.sh fusion       # Exécute seulement les scripts de fusion
#   ./setup.sh model        # Exécute seulement le modèle V12
#   ./setup.sh clean        # Nettoie les fichiers générés
#   ./setup.sh check        # Vérifie que tout est OK
# ==============================================================================

set -e  # Arrête le script en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Chemin du script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# ==============================================================================
# DÉTECTION DU SYSTÈME
# ==============================================================================

detect_system() {
    OS="unknown"
    ARCH="unknown"
    
    case "$(uname -s)" in
        Darwin*)
            OS="macos"
            if [[ $(uname -m) == "arm64" ]]; then
                ARCH="arm64"  # Mac M1/M2/M3
            else
                ARCH="x86_64"  # Mac Intel
            fi
            ;;
        Linux*)
            OS="linux"
            ARCH=$(uname -m)
            ;;
        MINGW*|MSYS*|CYGWIN*)
            OS="windows"
            ARCH=$(uname -m)
            ;;
    esac
    
    echo -e "Système détecté: ${GREEN}$OS ($ARCH)${NC}"
}

# ==============================================================================
# VÉRIFICATION DE PYTHON (version compatible CatBoost: 3.9-3.12)
# ==============================================================================

find_compatible_python() {
    # CatBoost supporte Python 3.8-3.12, pas 3.13+
    # On cherche la meilleure version disponible
    
    # Liste des versions compatibles (ordre de préférence)
    COMPATIBLE_VERSIONS=("3.11" "3.12" "3.10" "3.9")
    
    for VERSION in "${COMPATIBLE_VERSIONS[@]}"; do
        # Chercher dans Homebrew (macOS)
        if [[ -x "/opt/homebrew/bin/python$VERSION" ]]; then
            echo "/opt/homebrew/bin/python$VERSION"
            return 0
        fi
        # Chercher dans /usr/local (Intel Mac / Linux)
        if [[ -x "/usr/local/bin/python$VERSION" ]]; then
            echo "/usr/local/bin/python$VERSION"
            return 0
        fi
        # Chercher dans le PATH
        if command -v "python$VERSION" &> /dev/null; then
            command -v "python$VERSION"
            return 0
        fi
    done
    
    # Aucune version compatible trouvée
    return 1
}

check_python() {
    print_info "Vérification de Python (compatible CatBoost: 3.9-3.12)..."
    
    # D'abord, chercher une version compatible avec CatBoost
    PYTHON_CMD=$(find_compatible_python)
    
    if [[ -n "$PYTHON_CMD" ]]; then
        PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        print_success "Python $PYTHON_VERSION trouvé ($PYTHON_CMD) - Compatible CatBoost ✓"
        return 0
    fi
    
    # Sinon, vérifier si python3 par défaut est compatible
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')
        
        if [[ $PYTHON_MINOR -ge 9 && $PYTHON_MINOR -le 12 ]]; then
            print_success "Python $PYTHON_VERSION trouvé - Compatible CatBoost ✓"
            return 0
        else
            print_warning "Python $PYTHON_VERSION trouvé mais NON compatible avec CatBoost"
            print_info "CatBoost nécessite Python 3.9-3.12"
            echo ""
            echo "   Installation recommandée:"
            if [[ "$OS" == "macos" ]]; then
                echo "   brew install python@3.11"
            else
                echo "   sudo apt install python3.11 python3.11-venv"
            fi
            echo ""
            exit 1
        fi
    fi
    
    print_error "Python n'est pas installé!"
    echo "   Installez Python 3.11 depuis https://www.python.org/"
    exit 1
}

# ==============================================================================
# CRÉATION DE L'ENVIRONNEMENT VIRTUEL
# ==============================================================================

setup_venv() {
    print_info "Configuration de l'environnement virtuel..."
    
    # Vérifier si le venv existe et utilise la bonne version
    if [[ -d "venv" ]]; then
        VENV_PYTHON_VERSION=$(./venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "unknown")
        VENV_PYTHON_MINOR=$(./venv/bin/python -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "99")
        
        # Vérifier si la version du venv est compatible avec CatBoost
        if [[ $VENV_PYTHON_MINOR -ge 9 && $VENV_PYTHON_MINOR -le 12 ]]; then
            print_success "Environnement virtuel existant (Python $VENV_PYTHON_VERSION) - Compatible ✓"
        else
            print_warning "Environnement existant utilise Python $VENV_PYTHON_VERSION (non compatible)"
            print_info "Suppression et recréation avec Python compatible..."
            rm -rf venv
        fi
    fi
    
    # Créer le venv si nécessaire
    if [[ ! -d "venv" ]]; then
        print_info "Création de l'environnement virtuel avec $PYTHON_CMD..."
        $PYTHON_CMD -m venv venv
        print_success "Environnement virtuel créé"
    fi
    
    # Activation
    source venv/bin/activate
    print_success "Environnement activé (Python $(python --version 2>&1 | cut -d' ' -f2))"
    
    # Mise à jour de pip
    print_info "Mise à jour de pip..."
    pip install --upgrade pip --quiet
}

# ==============================================================================
# INSTALLATION DES DÉPENDANCES
# ==============================================================================

install_dependencies() {
    print_info "Installation des dépendances..."
    
    # Installer les dépendances de base (sans catboost)
    pip install pandas numpy scikit-learn scipy xlrd openpyxl jupyter matplotlib seaborn --quiet
    print_success "Dépendances de base installées"
    
    # Installer CatBoost selon le système
    print_info "Installation de CatBoost..."
    
    if [[ "$OS" == "macos" && "$ARCH" == "arm64" ]]; then
        print_warning "Mac Apple Silicon détecté - installation spéciale de CatBoost..."
        
        # Essayer plusieurs méthodes
        if pip install catboost --quiet 2>/dev/null; then
            print_success "CatBoost installé (pip standard)"
        elif arch -x86_64 pip install catboost --quiet 2>/dev/null; then
            print_success "CatBoost installé (via Rosetta x86)"
        else
            print_warning "Installation pip échouée, tentative avec conda..."
            if command -v conda &> /dev/null; then
                conda install -c conda-forge catboost -y
                print_success "CatBoost installé (via conda)"
            else
                print_error "Impossible d'installer CatBoost automatiquement"
                echo ""
                echo "   Solutions manuelles:"
                echo "   1. Installer Miniforge: https://github.com/conda-forge/miniforge"
                echo "   2. Puis: conda install -c conda-forge catboost"
                echo ""
                exit 1
            fi
        fi
    else
        # Installation standard pour Linux/Windows/Mac Intel
        if pip install catboost --quiet; then
            print_success "CatBoost installé"
        else
            print_error "Échec de l'installation de CatBoost"
            echo "   Essayez: pip install catboost --no-cache-dir"
            exit 1
        fi
    fi
}

# ==============================================================================
# VÉRIFICATION DES DONNÉES
# ==============================================================================

check_data() {
    print_info "Vérification des données..."
    
    ERRORS=0
    
    # Fichiers requis
    if [[ ! -f "data/train.csv" ]]; then
        print_error "Fichier manquant: data/train.csv"
        ERRORS=$((ERRORS + 1))
    else
        print_success "data/train.csv trouvé"
    fi
    
    if [[ ! -f "data/test.csv" ]]; then
        print_error "Fichier manquant: data/test.csv"
        ERRORS=$((ERRORS + 1))
    else
        print_success "data/test.csv trouvé"
    fi
    
    # Dossier météo
    METEO_DIR="data/DonneesMeteorologiques/DonneesMeteorologiques"
    if [[ ! -d "$METEO_DIR" ]]; then
        print_error "Dossier manquant: $METEO_DIR"
        ERRORS=$((ERRORS + 1))
    else
        METEO_COUNT=$(ls -1 "$METEO_DIR"/synop.*.csv 2>/dev/null | wc -l | tr -d ' ')
        print_success "Données météo trouvées ($METEO_COUNT fichiers)"
    fi
    
    # Dossier Google Trends
    if [[ ! -d "data/RequetesGoogleParRegion" ]]; then
        print_error "Dossier manquant: data/RequetesGoogleParRegion"
        ERRORS=$((ERRORS + 1))
    else
        GOOGLE_COUNT=$(ls -1 data/RequetesGoogleParRegion/*.csv 2>/dev/null | wc -l | tr -d ' ')
        print_success "Données Google Trends trouvées ($GOOGLE_COUNT fichiers)"
    fi
    
    if [[ $ERRORS -gt 0 ]]; then
        print_error "$ERRORS erreur(s) trouvée(s)"
        return 1
    fi
    
    return 0
}

# ==============================================================================
# CRÉATION DES DOSSIERS
# ==============================================================================

create_directories() {
    print_info "Création des dossiers..."
    
    mkdir -p submissions
    mkdir -p catboost_info
    
    print_success "Dossiers créés"
}

# ==============================================================================
# EXÉCUTION DES SCRIPTS DE FUSION
# ==============================================================================

run_fusion() {
    print_header "FUSION DES DONNÉES"
    
    source venv/bin/activate
    
    print_info "Étape 1/3: Agrégation des données météo..."
    python fusion/aggregate_meteo_weekly.py
    print_success "Données météo agrégées"
    
    print_info "Étape 2/3: Fusion avec Google Trends..."
    python fusion/merge_google_trends.py
    print_success "Google Trends fusionné"
    
    print_info "Étape 3/3: Ajout des données de population..."
    python fusion/merge_population.py
    print_success "Population ajoutée"
    
    print_success "Fusion terminée!"
}

# ==============================================================================
# EXÉCUTION DU MODÈLE
# ==============================================================================

run_model() {
    print_header "EXÉCUTION DU MODÈLE"
    
    source venv/bin/activate
    
    # Vérifier que les fichiers enrichis existent
    if [[ ! -f "train_enrichi.csv" ]] || [[ ! -f "test_enrichi.csv" ]]; then
        print_warning "Fichiers enrichis manquants, exécution de la fusion d'abord..."
        run_fusion
    fi
    
    print_info "Exécution du modèle V12 (15 features)..."
    python best_models/V12_15Features.py
    
    print_success "Modèle exécuté!"
    
    if [[ -f "submissions/submission_v12.csv" ]]; then
        print_success "Fichier de soumission créé: submissions/submission_v12.csv"
    fi
}

# ==============================================================================
# NETTOYAGE
# ==============================================================================

clean() {
    print_header "NETTOYAGE"
    
    print_info "Suppression des fichiers générés..."
    
    rm -f synop_hebdo.csv
    rm -f synop_hebdo_enrichi.csv
    rm -f synop_hebdo_google_enrichi.csv
    rm -f train_enrichi.csv
    rm -f test_enrichi.csv
    rm -f meteo_weekly.csv
    rm -rf submissions/*.csv
    rm -rf catboost_info/*
    rm -rf __pycache__
    rm -rf fusion/__pycache__
    rm -rf best_models/__pycache__
    
    print_success "Nettoyage terminé"
}

# ==============================================================================
# VÉRIFICATION COMPLÈTE
# ==============================================================================

full_check() {
    print_header "VÉRIFICATION COMPLÈTE"
    
    detect_system
    check_python
    
    if [[ -d "venv" ]]; then
        print_success "Environnement virtuel présent"
        source venv/bin/activate
        
        # Vérifier les packages
        if python -c "import catboost" 2>/dev/null; then
            print_success "CatBoost installé"
        else
            print_error "CatBoost non installé"
        fi
        
        if python -c "import pandas" 2>/dev/null; then
            print_success "Pandas installé"
        else
            print_error "Pandas non installé"
        fi
    else
        print_warning "Environnement virtuel non créé"
    fi
    
    check_data
    
    # Fichiers enrichis
    echo ""
    print_info "Fichiers générés:"
    [[ -f "train_enrichi.csv" ]] && print_success "train_enrichi.csv" || print_warning "train_enrichi.csv (non généré)"
    [[ -f "test_enrichi.csv" ]] && print_success "test_enrichi.csv" || print_warning "test_enrichi.csv (non généré)"
    [[ -f "submissions/submission_v12.csv" ]] && print_success "submissions/submission_v12.csv" || print_warning "submissions/submission_v12.csv (non généré)"
}

# ==============================================================================
# AIDE
# ==============================================================================

show_help() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           PROJET PRÉDICTION GRIPPE - CHALLENGE KAGGLE                ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Usage: ./setup.sh [COMMANDE]"
    echo ""
    echo "Commandes disponibles:"
    echo ""
    echo -e "  ${GREEN}install${NC}     Installe l'environnement Python et toutes les dépendances"
    echo -e "  ${GREEN}run${NC}         Exécute le pipeline complet (fusion + modèle)"
    echo -e "  ${GREEN}fusion${NC}      Exécute seulement les scripts de fusion de données"
    echo -e "  ${GREEN}model${NC}       Exécute seulement le modèle V12"
    echo -e "  ${GREEN}check${NC}       Vérifie que tout est correctement installé"
    echo -e "  ${GREEN}clean${NC}       Supprime tous les fichiers générés"
    echo ""
    echo "Première utilisation:"
    echo ""
    echo "  1. ./setup.sh install    # Installe tout"
    echo "  2. ./setup.sh run        # Lance le pipeline complet"
    echo ""
    echo "Le fichier de soumission sera dans: submissions/submission_v12.csv"
    echo ""
}

# ==============================================================================
# INSTALLATION COMPLÈTE
# ==============================================================================

full_install() {
    print_header "INSTALLATION COMPLÈTE"
    
    detect_system
    check_python
    setup_venv
    install_dependencies
    create_directories
    check_data
    
    echo ""
    print_success "Installation terminée!"
    echo ""
    echo "Prochaines étapes:"
    echo "  1. Activez l'environnement: source venv/bin/activate"
    echo "  2. Lancez le pipeline:      ./setup.sh run"
    echo ""
}

# ==============================================================================
# PIPELINE COMPLET
# ==============================================================================

full_run() {
    print_header "EXÉCUTION DU PIPELINE COMPLET"
    
    if [[ ! -d "venv" ]]; then
        print_warning "Environnement non installé, installation..."
        full_install
    fi
    
    source venv/bin/activate
    run_fusion
    run_model
    
    echo ""
    print_success "Pipeline terminé!"
    echo ""
    echo "Fichier de soumission: submissions/submission_v12.csv"
    echo ""
}

# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

case "${1:-help}" in
    install)
        full_install
        ;;
    run)
        full_run
        ;;
    fusion)
        run_fusion
        ;;
    model)
        run_model
        ;;
    check)
        full_check
        ;;
    clean)
        clean
        ;;
    help|--help|-h|*)
        show_help
        ;;
esac
