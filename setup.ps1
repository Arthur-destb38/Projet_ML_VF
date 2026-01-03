# ==============================================================================
# SCRIPT D'INSTALLATION ET D'EXÉCUTION COMPLET - WINDOWS
# Projet Prédiction Grippe - Challenge Kaggle
# ==============================================================================
# Usage (PowerShell):
#   .\setup.ps1              # Affiche l'aide
#   .\setup.ps1 install      # Installe l'environnement et dépendances
#   .\setup.ps1 run          # Exécute tout le pipeline (fusion + modèle)
#   .\setup.ps1 fusion       # Exécute seulement les scripts de fusion
#   .\setup.ps1 model        # Exécute seulement le modèle V12
#   .\setup.ps1 clean        # Nettoie les fichiers générés
#   .\setup.ps1 check        # Vérifie que tout est OK
# ==============================================================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

# Chemin du script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

function Write-Header($text) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Blue
    Write-Host "  $text" -ForegroundColor Blue
    Write-Host ("=" * 70) -ForegroundColor Blue
}

function Write-Success($text) {
    Write-Host "✓ $text" -ForegroundColor Green
}

function Write-Warning($text) {
    Write-Host "⚠ $text" -ForegroundColor Yellow
}

function Write-Error($text) {
    Write-Host "✗ $text" -ForegroundColor Red
}

function Write-Info($text) {
    Write-Host "→ $text" -ForegroundColor Cyan
}

# ==============================================================================
# TROUVER PYTHON COMPATIBLE (3.9-3.12)
# ==============================================================================

function Find-CompatiblePython {
    $versions = @("3.11", "3.12", "3.10", "3.9")
    
    foreach ($version in $versions) {
        # Essayer py launcher (Windows)
        try {
            $result = & py -$version --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                return "py -$version"
            }
        } catch {}
        
        # Essayer python3.X directement
        try {
            $cmd = "python$version"
            $result = & $cmd --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $cmd
            }
        } catch {}
    }
    
    # Essayer python par défaut et vérifier la version
    try {
        $result = & python --version 2>$null
        if ($result -match "Python 3\.(9|10|11|12)") {
            return "python"
        }
    } catch {}
    
    return $null
}

function Check-Python {
    Write-Info "Vérification de Python (compatible CatBoost: 3.9-3.12)..."
    
    $script:PythonCmd = Find-CompatiblePython
    
    if ($null -eq $PythonCmd) {
        Write-Error "Python 3.9-3.12 non trouvé!"
        Write-Host ""
        Write-Host "   Installez Python 3.11 depuis: https://www.python.org/downloads/"
        Write-Host "   Cochez 'Add Python to PATH' lors de l'installation"
        Write-Host ""
        exit 1
    }
    
    # Afficher la version
    if ($PythonCmd -like "py *") {
        $version = & py $PythonCmd.Split(" ")[1] --version 2>&1
    } else {
        $version = & $PythonCmd --version 2>&1
    }
    Write-Success "$version trouvé ($PythonCmd) - Compatible CatBoost"
}

# ==============================================================================
# CRÉATION DE L'ENVIRONNEMENT VIRTUEL
# ==============================================================================

function Setup-Venv {
    Write-Info "Configuration de l'environnement virtuel..."
    
    if (-not (Test-Path "venv")) {
        Write-Info "Création de l'environnement virtuel..."
        if ($PythonCmd -like "py *") {
            $pyVersion = $PythonCmd.Split(" ")[1]
            & py $pyVersion -m venv venv
        } else {
            & $PythonCmd -m venv venv
        }
        Write-Success "Environnement virtuel créé"
    } else {
        Write-Success "Environnement virtuel existant"
    }
    
    # Activation
    Write-Info "Activation de l'environnement..."
    & .\venv\Scripts\Activate.ps1
    Write-Success "Environnement activé"
    
    # Mise à jour de pip
    Write-Info "Mise à jour de pip..."
    & python -m pip install --upgrade pip --quiet
}

# ==============================================================================
# INSTALLATION DES DÉPENDANCES
# ==============================================================================

function Install-Dependencies {
    Write-Info "Installation des dépendances..."
    
    # Installer les dépendances de base
    & pip install pandas numpy scikit-learn scipy xlrd openpyxl jupyter matplotlib seaborn --quiet
    Write-Success "Dépendances de base installées"
    
    # Installer CatBoost
    Write-Info "Installation de CatBoost..."
    & pip install catboost --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Success "CatBoost installé"
    } else {
        Write-Error "Échec de l'installation de CatBoost"
        Write-Host "   Essayez: pip install catboost --no-cache-dir"
        exit 1
    }
}

# ==============================================================================
# VÉRIFICATION DES DONNÉES
# ==============================================================================

function Check-Data {
    Write-Info "Vérification des données..."
    
    $errors = 0
    
    if (-not (Test-Path "data\train.csv")) {
        Write-Error "Fichier manquant: data\train.csv"
        $errors++
    } else {
        Write-Success "data\train.csv trouvé"
    }
    
    if (-not (Test-Path "data\test.csv")) {
        Write-Error "Fichier manquant: data\test.csv"
        $errors++
    } else {
        Write-Success "data\test.csv trouvé"
    }
    
    $meteoDir = "data\DonneesMeteorologiques\DonneesMeteorologiques"
    if (-not (Test-Path $meteoDir)) {
        Write-Error "Dossier manquant: $meteoDir"
        $errors++
    } else {
        $meteoCount = (Get-ChildItem "$meteoDir\synop.*.csv").Count
        Write-Success "Données météo trouvées ($meteoCount fichiers)"
    }
    
    if (-not (Test-Path "data\RequetesGoogleParRegion")) {
        Write-Error "Dossier manquant: data\RequetesGoogleParRegion"
        $errors++
    } else {
        $googleCount = (Get-ChildItem "data\RequetesGoogleParRegion\*.csv").Count
        Write-Success "Données Google Trends trouvées ($googleCount fichiers)"
    }
    
    if ($errors -gt 0) {
        Write-Error "$errors erreur(s) trouvée(s)"
        return $false
    }
    return $true
}

# ==============================================================================
# CRÉATION DES DOSSIERS
# ==============================================================================

function Create-Directories {
    Write-Info "Création des dossiers..."
    
    if (-not (Test-Path "submissions")) {
        New-Item -ItemType Directory -Path "submissions" | Out-Null
    }
    if (-not (Test-Path "catboost_info")) {
        New-Item -ItemType Directory -Path "catboost_info" | Out-Null
    }
    
    Write-Success "Dossiers créés"
}

# ==============================================================================
# EXÉCUTION DES SCRIPTS DE FUSION
# ==============================================================================

function Run-Fusion {
    Write-Header "FUSION DES DONNÉES"
    
    & .\venv\Scripts\Activate.ps1
    
    Write-Info "Étape 1/3: Agrégation des données météo..."
    & python fusion\aggregate_meteo_weekly.py
    Write-Success "Données météo agrégées"
    
    Write-Info "Étape 2/3: Fusion avec Google Trends..."
    & python fusion\merge_google_trends.py
    Write-Success "Google Trends fusionné"
    
    Write-Info "Étape 3/3: Ajout des données de population..."
    & python fusion\merge_population.py
    Write-Success "Population ajoutée"
    
    Write-Success "Fusion terminée!"
}

# ==============================================================================
# EXÉCUTION DU MODÈLE
# ==============================================================================

function Run-Model {
    Write-Header "EXÉCUTION DU MODÈLE"
    
    & .\venv\Scripts\Activate.ps1
    
    # Vérifier que les fichiers enrichis existent
    if (-not (Test-Path "train_enrichi.csv") -or -not (Test-Path "test_enrichi.csv")) {
        Write-Warning "Fichiers enrichis manquants, exécution de la fusion d'abord..."
        Run-Fusion
    }
    
    Write-Info "Exécution du modèle V12 (15 features)..."
    & python best_models\V12_15Features.py
    
    Write-Success "Modèle exécuté!"
    
    if (Test-Path "submissions\submission_v12.csv") {
        Write-Success "Fichier de soumission créé: submissions\submission_v12.csv"
    }
}

# ==============================================================================
# NETTOYAGE
# ==============================================================================

function Clean-Files {
    Write-Header "NETTOYAGE"
    
    Write-Info "Suppression des fichiers générés..."
    
    $filesToRemove = @(
        "synop_hebdo.csv",
        "synop_hebdo_enrichi.csv",
        "synop_hebdo_google_enrichi.csv",
        "train_enrichi.csv",
        "test_enrichi.csv",
        "meteo_weekly.csv"
    )
    
    foreach ($file in $filesToRemove) {
        if (Test-Path $file) {
            Remove-Item $file -Force
        }
    }
    
    if (Test-Path "submissions\*.csv") {
        Remove-Item "submissions\*.csv" -Force
    }
    
    Write-Success "Nettoyage terminé"
}

# ==============================================================================
# VÉRIFICATION COMPLÈTE
# ==============================================================================

function Full-Check {
    Write-Header "VÉRIFICATION COMPLÈTE"
    
    Check-Python
    
    if (Test-Path "venv") {
        Write-Success "Environnement virtuel présent"
        & .\venv\Scripts\Activate.ps1
        
        try {
            & python -c "import catboost" 2>$null
            Write-Success "CatBoost installé"
        } catch {
            Write-Error "CatBoost non installé"
        }
        
        try {
            & python -c "import pandas" 2>$null
            Write-Success "Pandas installé"
        } catch {
            Write-Error "Pandas non installé"
        }
    } else {
        Write-Warning "Environnement virtuel non créé"
    }
    
    Check-Data
    
    Write-Host ""
    Write-Info "Fichiers générés:"
    if (Test-Path "train_enrichi.csv") { Write-Success "train_enrichi.csv" } else { Write-Warning "train_enrichi.csv (non généré)" }
    if (Test-Path "test_enrichi.csv") { Write-Success "test_enrichi.csv" } else { Write-Warning "test_enrichi.csv (non généré)" }
    if (Test-Path "submissions\submission_v12.csv") { Write-Success "submissions\submission_v12.csv" } else { Write-Warning "submissions\submission_v12.csv (non généré)" }
}

# ==============================================================================
# AIDE
# ==============================================================================

function Show-Help {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Blue
    Write-Host "           PROJET PRÉDICTION GRIPPE - CHALLENGE KAGGLE" -ForegroundColor Blue
    Write-Host ("=" * 70) -ForegroundColor Blue
    Write-Host ""
    Write-Host "Usage: .\setup.ps1 [COMMANDE]"
    Write-Host ""
    Write-Host "Commandes disponibles:"
    Write-Host ""
    Write-Host "  install     " -NoNewline -ForegroundColor Green
    Write-Host "Installe l'environnement Python et toutes les dépendances"
    Write-Host "  run         " -NoNewline -ForegroundColor Green
    Write-Host "Exécute le pipeline complet (fusion + modèle)"
    Write-Host "  fusion      " -NoNewline -ForegroundColor Green
    Write-Host "Exécute seulement les scripts de fusion de données"
    Write-Host "  model       " -NoNewline -ForegroundColor Green
    Write-Host "Exécute seulement le modèle V12"
    Write-Host "  check       " -NoNewline -ForegroundColor Green
    Write-Host "Vérifie que tout est correctement installé"
    Write-Host "  clean       " -NoNewline -ForegroundColor Green
    Write-Host "Supprime tous les fichiers générés"
    Write-Host ""
    Write-Host "Première utilisation:"
    Write-Host ""
    Write-Host "  1. .\setup.ps1 install    # Installe tout"
    Write-Host "  2. .\setup.ps1 run        # Lance le pipeline complet"
    Write-Host ""
    Write-Host "Le fichier de soumission sera dans: submissions\submission_v12.csv"
    Write-Host ""
}

# ==============================================================================
# INSTALLATION COMPLÈTE
# ==============================================================================

function Full-Install {
    Write-Header "INSTALLATION COMPLÈTE"
    
    Check-Python
    Setup-Venv
    Install-Dependencies
    Create-Directories
    Check-Data
    
    Write-Host ""
    Write-Success "Installation terminée!"
    Write-Host ""
    Write-Host "Prochaines étapes:"
    Write-Host "  1. Activez l'environnement: .\venv\Scripts\Activate.ps1"
    Write-Host "  2. Lancez le pipeline:      .\setup.ps1 run"
    Write-Host ""
}

# ==============================================================================
# PIPELINE COMPLET
# ==============================================================================

function Full-Run {
    Write-Header "EXÉCUTION DU PIPELINE COMPLET"
    
    if (-not (Test-Path "venv")) {
        Write-Warning "Environnement non installé, installation..."
        Full-Install
    }
    
    & .\venv\Scripts\Activate.ps1
    Run-Fusion
    Run-Model
    
    Write-Host ""
    Write-Success "Pipeline terminé!"
    Write-Host ""
    Write-Host "Fichier de soumission: submissions\submission_v12.csv"
    Write-Host ""
}

# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

switch ($Command.ToLower()) {
    "install" { Full-Install }
    "run"     { Full-Run }
    "fusion"  { Run-Fusion }
    "model"   { Run-Model }
    "check"   { Full-Check }
    "clean"   { Clean-Files }
    default   { Show-Help }
}
