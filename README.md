# Prediction du Taux de Grippe - Challenge Kaggle

Projet de prediction du taux de grippe hebdomadaire par region en France.

## Structure du projet

```
VF_projet/
├── data/                          # Donnees brutes
│   ├── train.csv                  # Donnees d'entrainement
│   ├── test.csv                   # Donnees a predire
│   ├── DonneesMeteorologiques/    # Fichiers SYNOP (meteo)
│   └── RequetesGoogleParRegion/   # Fichiers Google Trends
├── fusion/                        # Scripts de preparation des donnees
│   ├── aggregate_meteo_weekly.py
│   ├── merge_google_trends.py
│   └── merge_population.py
├── best_models/                   # Modeles de prediction
│   ├── V12_15Features.py
│   └── V13_11Features.py
├── config.py                      # Configuration des chemins
├── requirements.txt               # Dependances Python
└── NoteBook_resume_explicatif.ipynb  # Notebook explicatif
```

## Installation

### 1. Creer l'environnement virtuel

```bash
cd VF_projet
python3 -m venv venv
source venv/bin/activate
```

### 2. Installer les dependances

```bash
pip install -r requirements.txt
```

## Execution

### Etape 1 : Preparer les donnees (fusion)

Les scripts de fusion doivent etre lances dans cet ordre :

```bash
# Activer le venv
source venv/bin/activate

# 1. Agreger les donnees meteo (SYNOP) en hebdomadaire par region
python fusion/aggregate_meteo_weekly.py
# -> Cree: meteo_weekly.csv

# 2. Fusionner avec Google Trends
python fusion/merge_google_trends.py
# -> Cree: synop_hebdo_google_enrichi.csv

# 3. Ajouter les donnees de population
python fusion/merge_population.py
# -> Cree: synop_hebdo_complet.csv
```

**Note** : Ces scripts necessitent que les fichiers `synop_hebdo_enrichi.csv`, `train_enrichi.csv` et `test_enrichi.csv` existent deja dans le dossier.

### Etape 2 : Lancer le modele

```bash
# Modele V12 (15 features) - Recommande
python best_models/V12_15Features.py
# -> Cree: submissions/submission_v12.csv

# OU Modele V13 (11 features)
python best_models/V13_11Features.py
# -> Cree: submissions/submission_v13.csv
```

### Raccourci avec run.sh

```bash
chmod +x run.sh

./run.sh v12      # Lance le modele V12
./run.sh v13      # Lance le modele V13
./run.sh config   # Affiche la configuration
./run.sh install  # Installe les dependances
```

## Fichiers generes

| Fichier | Description |
|---------|-------------|
| `meteo_weekly.csv` | Donnees meteo agregees par semaine et region |
| `synop_hebdo_google_enrichi.csv` | Meteo + Google Trends |
| `synop_hebdo_complet.csv` | Meteo + Google + Population |
| `submissions/submission_v12.csv` | Predictions du modele V12 |
| `submissions/submission_v13.csv` | Predictions du modele V13 |

## Notebook

Le fichier `NoteBook_resume_explicatif.ipynb` contient une explication detaillee de :
- La fusion des donnees
- Le feature engineering
- Le modele CatBoost
- Les resultats

Pour le lancer :
```bash
source venv/bin/activate
jupyter notebook NoteBook_resume_explicatif.ipynb
```

## Resume du pipeline

```
train.csv ──┐
            │
test.csv ───┼──► Scripts fusion ──► train_enrichi.csv ──► V12_15Features.py ──► submission_v12.csv
            │                        test_enrichi.csv
Meteo ──────┤
            │
Google ─────┤
            │
Population ─┘
```

## Dependances principales

- pandas
- numpy
- catboost
- scikit-learn
- scipy
- matplotlib
