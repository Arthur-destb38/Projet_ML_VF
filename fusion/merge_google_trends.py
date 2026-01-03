"""
Script pour merger synop_hebdo_enrichi.csv avec les données Google Trends.
Attention : Google = mensuel, Synop = hebdomadaire
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Ajouter le dossier parent au path pour importer config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    PROJECT_ROOT, GOOGLE_TRENDS_DIR, 
    SYNOP_HEBDO_ENRICHI_CSV, SYNOP_HEBDO_GOOGLE_ENRICHI_CSV,
    TRAIN_ENRICHI_CSV, TEST_ENRICHI_CSV
)

# Mapping des noms de fichiers Google vers les noms de régions dans synop_hebdo_enrichi
FILENAME_TO_REGION = {
    'Alsace': 'ALSACE',
    'Aquitaine': 'AQUITAINE',
    'Auvergne': 'AUVERGNE',
    'BasseNormandie': 'BASSE-NORMANDIE',
    'Bourgogne': 'BOURGOGNE',
    'Bretagne': 'BRETAGNE',
    'CentreValdeLoire': 'CENTRE',
    'ChampagneArdenne': 'CHAMPAGNE-ARDENNE',
    'Corse': 'CORSE',
    'FrancheComte': 'FRANCHE-COMTE',
    'HauteNormandie': 'HAUTE-NORMANDIE',
    'IledeFrance': 'ILE-DE-FRANCE',
    'LanguedocRoussillon': 'LANGUEDOC-ROUSSILLON',
    'Limousin': 'LIMOUSIN',
    'Lorraine': 'LORRAINE',
    'MidiPyrenees': 'MIDI-PYRENEES',
    'NordPasdeCalais': 'NORD-PAS-DE-CALAIS',
    'PaysdelaLoire': 'PAYS-DE-LA-LOIRE',
    'Picardie': 'PICARDIE',
    'PoitouCharentes': 'POITOU-CHARENTES',
    'ProvenceAlpesCotedAzur': 'PROVENCE-ALPES-COTE-D-AZUR',
    'RhoneAlpes': 'RHONE-ALPES',
}


def week_to_month(week_id):
    """
    Convertit un identifiant de semaine YYYYWW en mois YYYY-MM.
    
    La semaine ISO peut chevaucher deux mois. On prend le mois du JEUDI de la semaine
    (standard ISO : le jeudi détermine l'année de la semaine).
    """
    year = week_id // 100
    week = week_id % 100
    
    # Trouver le jeudi de la semaine ISO
    # Le 4 janvier est toujours dans la semaine 1
    jan4 = datetime(year, 1, 4)
    
    # Trouver le lundi de la semaine 1
    week1_monday = jan4 - timedelta(days=jan4.weekday())
    
    # Calculer le lundi de la semaine demandée
    target_monday = week1_monday + timedelta(weeks=week - 1)
    
    # Le jeudi de cette semaine (lundi + 3 jours)
    target_thursday = target_monday + timedelta(days=3)
    
    # Retourner le mois au format YYYY-MM
    return target_thursday.strftime('%Y-%m')


def load_google_files(google_folder):
    """Charge tous les fichiers Google Trends et les concatène."""
    all_data = []
    
    for filepath in Path(google_folder).glob('*.csv'):
        filename = filepath.stem  # Nom sans extension
        
        if filename not in FILENAME_TO_REGION:
            print(f"  Fichier ignore (non mappe): {filename}")
            continue
        
        region_name = FILENAME_TO_REGION[filename]
        
        # Lire le fichier (skip les 2 premières lignes d'en-tête)
        df = pd.read_csv(filepath, skiprows=2)
        
        # Renommer les colonnes
        df.columns = ['month', 'google_grippe', 'google_grippe_no_aviaire', 'google_grippe_filtered']
        
        # Ajouter la région
        df['region_name'] = region_name
        
        all_data.append(df)
        print(f"  - {filename} -> {region_name}: {len(df)} mois")
    
    # Concaténer tous les fichiers
    google_df = pd.concat(all_data, ignore_index=True)
    
    return google_df


def main():
    # Utiliser les chemins centralises
    
    # 1. Charger synop_hebdo_enrichi
    print("Chargement de synop_hebdo_enrichi.csv...")
    synop = pd.read_csv(SYNOP_HEBDO_ENRICHI_CSV)
    print(f"   {len(synop)} lignes, {synop['region_name'].nunique()} regions")
    
    # 2. Charger les fichiers Google
    print("\nChargement des fichiers Google Trends...")
    google_df = load_google_files(GOOGLE_TRENDS_DIR)
    print(f"\n   Total Google: {len(google_df)} lignes")
    
    # 3. Convertir les semaines en mois dans synop
    print("\nConversion semaine -> mois...")
    synop['month'] = synop['week'].apply(week_to_month)
    
    # Verification
    print(f"   Exemple: semaine 200401 -> mois {week_to_month(200401)}")
    print(f"   Exemple: semaine 200405 -> mois {week_to_month(200405)}")
    print(f"   Exemple: semaine 200452 -> mois {week_to_month(200452)}")
    print(f"   Exemple: semaine 201201 -> mois {week_to_month(201201)}")
    
    # 4. Merger les donnees
    print("\nFusion des donnees...")
    merged = synop.merge(
        google_df,
        on=['month', 'region_name'],
        how='left'
    )
    
    # 5. Vérifier les valeurs manquantes
    missing_google = merged['google_grippe'].isna().sum()
    print(f"   Valeurs Google manquantes: {missing_google} / {len(merged)} ({100*missing_google/len(merged):.1f}%)")
    
    # 6. Réorganiser les colonnes (retirer 'month' temporaire ou le garder)
    # On garde 'month' pour référence
    cols_order = ['week', 'month', 'region_code', 'region_name', 
                  'google_grippe', 'google_grippe_no_aviaire', 'google_grippe_filtered',
                  'temp_mean', 'temp_min', 'temp_max', 'temp_std', 
                  'dewpoint_mean', 'humidity_mean', 'humidity_min', 'humidity_max',
                  'wind_speed_mean', 'wind_speed_max', 'pressure_mean',
                  'precipitation_sum', 'precipitation_mean', 'precipitation_max']
    
    merged = merged[cols_order]
    
    # 7. Sauvegarder
    merged.to_csv(SYNOP_HEBDO_GOOGLE_ENRICHI_CSV, index=False)
    
    print(f"\nFichier cree: {SYNOP_HEBDO_GOOGLE_ENRICHI_CSV}")
    print(f"   Lignes: {len(merged)}")
    print(f"   Colonnes: {len(merged.columns)}")
    
    print("\nApercu des donnees:")
    print(merged.head(15).to_string(index=False))
    
    print("\nStatistiques Google Trends:")
    print(merged[['google_grippe', 'google_grippe_no_aviaire', 'google_grippe_filtered']].describe())
    
    # Verifier quelques exemples de conversion
    print("\nVerification de la conversion semaine -> mois:")
    sample = merged[merged['week'].isin([200401, 200404, 200405, 200452, 200501])][['week', 'month', 'region_name', 'google_grippe']].drop_duplicates()
    print(sample.head(20).to_string(index=False))
    
    # =========================================================================
    # MISE À JOUR DES FICHIERS TRAIN_ENRICHI ET TEST_ENRICHI AVEC GOOGLE TRENDS
    # =========================================================================
    print("\n" + "="*70)
    print("MISE À JOUR DES FICHIERS ENRICHIS AVEC GOOGLE TRENDS")
    print("="*70)
    
    # Charger les fichiers enrichis existants
    train_enrichi = pd.read_csv(TRAIN_ENRICHI_CSV)
    test_enrichi = pd.read_csv(TEST_ENRICHI_CSV)
    
    # Préparer les données Google pour le merge (avec month)
    google_cols = ['region_name', 'month', 'google_grippe', 'google_grippe_no_aviaire', 'google_grippe_filtered']
    google_for_merge = merged[google_cols].drop_duplicates()
    
    # Ajouter la colonne month aux fichiers enrichis
    train_enrichi['month'] = train_enrichi['week'].apply(week_to_month)
    test_enrichi['month'] = test_enrichi['week'].apply(week_to_month)
    
    # Merger avec Google Trends
    train_enrichi = train_enrichi.merge(google_for_merge, on=['region_name', 'month'], how='left')
    test_enrichi = test_enrichi.merge(google_for_merge, on=['region_name', 'month'], how='left')
    
    # Sauvegarder
    train_enrichi.to_csv(TRAIN_ENRICHI_CSV, index=False)
    test_enrichi.to_csv(TEST_ENRICHI_CSV, index=False)
    
    print(f"\nFichiers mis à jour:")
    print(f"   - {TRAIN_ENRICHI_CSV} ({len(train_enrichi)} lignes, {len(train_enrichi.columns)} colonnes)")
    print(f"   - {TEST_ENRICHI_CSV} ({len(test_enrichi)} lignes, {len(test_enrichi.columns)} colonnes)")
    
    # Vérifier les valeurs manquantes Google
    train_missing = train_enrichi['google_grippe_filtered'].isna().sum()
    test_missing = test_enrichi['google_grippe_filtered'].isna().sum()
    print(f"\nValeurs Google manquantes: train={train_missing}, test={test_missing}")


if __name__ == '__main__':
    main()


