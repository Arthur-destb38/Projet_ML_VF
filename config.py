"""
Configuration - Gestion centralisee des chemins du projet.
"""

from pathlib import Path

# =============================================================================
# CHEMIN RACINE DU PROJET (détection automatique)
# =============================================================================
# Le fichier config.py est à la racine du projet VF_projet
PROJECT_ROOT = Path(__file__).parent.resolve()

# =============================================================================
# DOSSIERS PRINCIPAUX
# =============================================================================
DATA_DIR = PROJECT_ROOT / "data"
BEST_MODELS_DIR = PROJECT_ROOT / "best_models"
FUSION_DIR = PROJECT_ROOT / "fusion"

# =============================================================================
# FICHIERS DE DONNÉES
# =============================================================================
# Données d'entraînement et test
TRAIN_CSV = DATA_DIR / "train.csv"
TEST_CSV = DATA_DIR / "test.csv"
SAMPLE_SUBMISSION_CSV = DATA_DIR / "sample_submission.csv"

# Données enrichies (générées par les scripts de fusion)
TRAIN_ENRICHI_CSV = PROJECT_ROOT / "train_enrichi.csv"
TEST_ENRICHI_CSV = PROJECT_ROOT / "test_enrichi.csv"

# Liste des stations météo
STATIONS_METEO_CSV = DATA_DIR / "ListedesStationsMeteo.csv"

# =============================================================================
# DOSSIERS DE DONNÉES EXTERNES
# =============================================================================
METEO_DIR = DATA_DIR / "DonneesMeteorologiques" / "DonneesMeteorologiques"
GOOGLE_TRENDS_DIR = DATA_DIR / "RequetesGoogleParRegion"

# =============================================================================
# FICHIERS INTERMÉDIAIRES (générés par les scripts de fusion)
# =============================================================================
SYNOP_HEBDO_CSV = PROJECT_ROOT / "synop_hebdo.csv"
SYNOP_HEBDO_ENRICHI_CSV = PROJECT_ROOT / "synop_hebdo_enrichi.csv"
SYNOP_HEBDO_GOOGLE_ENRICHI_CSV = PROJECT_ROOT / "synop_hebdo_google_enrichi.csv"

# =============================================================================
# DOSSIER DE SOUMISSIONS
# =============================================================================
SUBMISSIONS_DIR = PROJECT_ROOT / "submissions"

# Créer le dossier submissions s'il n'existe pas
SUBMISSIONS_DIR.mkdir(exist_ok=True)

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================
def get_submission_path(version: str) -> Path:
    """Retourne le chemin pour un fichier de soumission."""
    return SUBMISSIONS_DIR / f"submission_{version}.csv"

def get_meteo_files():
    """Retourne la liste de tous les fichiers météo."""
    return sorted(METEO_DIR.glob("synop.*.csv"))

def get_google_trends_files():
    """Retourne la liste de tous les fichiers Google Trends."""
    return sorted(GOOGLE_TRENDS_DIR.glob("*.csv"))

def print_config():
    """Affiche la configuration actuelle."""
    print("=" * 70)
    print("CONFIGURATION DU PROJET")
    print("=" * 70)
    print(f"Racine projet:     {PROJECT_ROOT}")
    print(f"Donnees:           {DATA_DIR}")
    print(f"Modeles:           {BEST_MODELS_DIR}")
    print(f"Fusion:            {FUSION_DIR}")
    print(f"Soumissions:       {SUBMISSIONS_DIR}")
    print(f"Meteo:             {METEO_DIR}")
    print(f"Google Trends:     {GOOGLE_TRENDS_DIR}")
    print("-" * 70)
    print(f"Train:             {TRAIN_CSV}")
    print(f"Test:              {TEST_CSV}")
    print(f"Train enrichi:     {TRAIN_ENRICHI_CSV}")
    print(f"Test enrichi:      {TEST_ENRICHI_CSV}")
    print("=" * 70)

# =============================================================================
# VÉRIFICATION DES CHEMINS AU CHARGEMENT
# =============================================================================
def verify_paths():
    """Vérifie que les chemins essentiels existent."""
    errors = []
    
    if not DATA_DIR.exists():
        errors.append(f"Dossier data manquant: {DATA_DIR}")
    
    if not METEO_DIR.exists():
        errors.append(f"Dossier meteo manquant: {METEO_DIR}")
    
    if not GOOGLE_TRENDS_DIR.exists():
        errors.append(f"Dossier Google Trends manquant: {GOOGLE_TRENDS_DIR}")
    
    if errors:
        print("\nERREURS DE CONFIGURATION:")
        for e in errors:
            print(f"   {e}")
        return False
    
    return True


if __name__ == "__main__":
    print_config()
    verify_paths()
