"""
Script pour ajouter les données de population au fichier synop_hebdo_google_enrichi.csv
Interpolation par spline cubique pour passer de données annuelles à hebdomadaires.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from scipy.interpolate import CubicSpline

# Ajouter le dossier parent au path pour importer config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    PROJECT_ROOT, DATA_DIR, 
    SYNOP_HEBDO_GOOGLE_ENRICHI_CSV
)

# Mapping des noms de régions dans Excel vers ceux de notre fichier
REGION_MAPPING = {
    'Alsace': 'ALSACE',
    'Aquitaine': 'AQUITAINE',
    'Auvergne': 'AUVERGNE',
    'Basse-Normandie': 'BASSE-NORMANDIE',
    'Bourgogne': 'BOURGOGNE',
    'Bretagne': 'BRETAGNE',
    'Centre': 'CENTRE',
    'Champagne-Ardenne': 'CHAMPAGNE-ARDENNE',
    'Corse': 'CORSE',
    'Franche-Comté': 'FRANCHE-COMTE',
    'Haute-Normandie': 'HAUTE-NORMANDIE',
    'Île-de-France': 'ILE-DE-FRANCE',
    'Languedoc-Roussillon': 'LANGUEDOC-ROUSSILLON',
    'Limousin': 'LIMOUSIN',
    'Lorraine': 'LORRAINE',
    'Midi-Pyrénées': 'MIDI-PYRENEES',
    'Nord - Pas-de-Calais': 'NORD-PAS-DE-CALAIS',
    'Pays de la Loire': 'PAYS-DE-LA-LOIRE',
    'Picardie': 'PICARDIE',
    'Poitou-Charentes': 'POITOU-CHARENTES',
    'Provence-Alpes-Côte d\'Azur': 'PROVENCE-ALPES-COTE-D-AZUR',
    'Rhône-Alpes': 'RHONE-ALPES',
}


def normalize_region_name(name):
    """Normalise le nom de région pour le matching."""
    if pd.isna(name):
        return None
    name = str(name).strip()
    # Essayer le mapping direct
    if name in REGION_MAPPING:
        return REGION_MAPPING[name]
    # Essayer en ignorant les accents (approximatif)
    name_lower = name.lower()
    for key, value in REGION_MAPPING.items():
        if key.lower() == name_lower:
            return value
        # Matching partiel pour Île-de-France
        if 'le-de-france' in name_lower or 'ile-de-france' in name_lower:
            return 'ILE-DE-FRANCE'
    return None


def week_to_date(week_id):
    """Convertit YYYYWW en date (jeudi de la semaine ISO)."""
    week_id = int(week_id)  # Convertir numpy.int64 en int
    year = week_id // 100
    week = week_id % 100
    
    # Le 4 janvier est toujours dans la semaine 1
    jan4 = datetime(year, 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.weekday())
    target_monday = week1_monday + timedelta(weeks=week - 1)
    target_thursday = target_monday + timedelta(days=3)
    
    return target_thursday


def date_to_numeric(dt):
    """Convertit une date en nombre de jours depuis une référence."""
    ref = datetime(2000, 1, 1)
    return (dt - ref).days


def load_population_data(excel_path, years):
    """Charge les données de population par région et année."""
    xls = pd.ExcelFile(excel_path)
    
    all_data = []
    
    for year in years:
        sheet_name = str(year)
        if sheet_name not in xls.sheet_names:
            print(f"  Annee {year} non trouvee dans le fichier Excel")
            continue
        
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        # Trouver la ligne d'en-tête (celle qui contient "Régions" ou "0 à 19 ans")
        header_row = None
        region_col = 0
        
        for i, row in df.iterrows():
            if 'Régions' in str(row.values):
                header_row = i
                break
        
        if header_row is None:
            print(f"  Structure non reconnue pour l'annee {year}")
            continue
        
        # Les données commencent après les lignes d'en-tête
        data_start = header_row + 2  # Skip "Régions" row and age groups row
        
        # Extraire les données pour chaque région
        for idx in range(data_start, len(df)):
            region_name_excel = df.iloc[idx, 0]
            
            if pd.isna(region_name_excel):
                continue
            region_str = str(region_name_excel)
            # Ignorer les lignes agrégées (France métropolitaine, DOM, etc.)
            # mais garder Île-de-France
            if ('France métropolitaine' in region_str or 
                'DOM' in region_str or
                region_str.strip() == 'France'):
                continue
            if 'Source' in region_str:
                break
                
            region_name_excel = str(region_name_excel).strip()
            
            region_name = normalize_region_name(region_name_excel)
            if region_name is None:
                continue
            
            # Extraire les populations par tranche d'âge (colonnes Ensemble)
            # Structure: col 1-5 = Ensemble par âge, col 6 = Total Ensemble
            try:
                pop_0_19 = df.iloc[idx, 1]
                pop_20_39 = df.iloc[idx, 2]
                pop_40_59 = df.iloc[idx, 3]
                pop_60_74 = df.iloc[idx, 4]
                pop_75_plus = df.iloc[idx, 5]
                pop_total = df.iloc[idx, 6]  # Total
                
                # Vérifier que ce sont des nombres
                if pd.isna(pop_total) or not isinstance(pop_total, (int, float)):
                    # Essayer une autre position
                    pop_total = pop_0_19 + pop_20_39 + pop_40_59 + pop_60_74 + pop_75_plus
                
                all_data.append({
                    'year': year,
                    'region_name': region_name,
                    'pop_total': int(pop_total),
                    'pop_0_19': int(pop_0_19),
                    'pop_20_39': int(pop_20_39),
                    'pop_40_59': int(pop_40_59),
                    'pop_60_74': int(pop_60_74),
                    'pop_75_plus': int(pop_75_plus),
                })
            except Exception as e:
                print(f"  Erreur pour {region_name_excel} en {year}: {e}")
                continue
        
        print(f"  ✓ {year}: {sum(1 for d in all_data if d['year'] == year)} régions")
    
    return pd.DataFrame(all_data)


def interpolate_population_weekly(pop_annual, weeks):
    """
    Interpole la population annuelle vers des données hebdomadaires 
    en utilisant une spline cubique.
    """
    results = []
    
    # Obtenir toutes les régions
    regions = pop_annual['region_name'].unique()
    
    # Colonnes de population à interpoler
    pop_columns = ['pop_total', 'pop_0_19', 'pop_20_39', 'pop_40_59', 'pop_60_74', 'pop_75_plus']
    
    for region in regions:
        region_data = pop_annual[pop_annual['region_name'] == region].sort_values('year')
        
        if len(region_data) < 2:
            print(f"  Pas assez de donnees pour {region}")
            continue
        
        # Points d'ancrage : 1er janvier de chaque année
        anchor_dates = [datetime(year, 1, 1) for year in region_data['year']]
        anchor_numeric = [date_to_numeric(d) for d in anchor_dates]
        
        # Créer les splines pour chaque colonne
        splines = {}
        for col in pop_columns:
            values = region_data[col].values
            # Spline cubique avec extrapolation
            splines[col] = CubicSpline(anchor_numeric, values, extrapolate=True)
        
        # Interpoler pour chaque semaine
        for week_id in weeks:
            week_date = week_to_date(week_id)
            week_numeric = date_to_numeric(week_date)
            
            row = {
                'week': week_id,
                'region_name': region,
            }
            
            for col in pop_columns:
                # Interpoler et arrondir (population = entier)
                value = float(splines[col](week_numeric))
                row[col] = max(0, int(np.round(value)))  # Pas de population négative
            
            results.append(row)
    
    return pd.DataFrame(results)


def main():
    # Utiliser les chemins centralises
    
    # 1. Charger le fichier synop enrichi avec Google
    print("Chargement de synop_hebdo_google_enrichi.csv...")
    synop = pd.read_csv(SYNOP_HEBDO_GOOGLE_ENRICHI_CSV)
    print(f"   {len(synop)} lignes")
    
    # Obtenir les semaines uniques
    weeks = sorted(synop['week'].unique())
    print(f"   Semaines: {min(weeks)} a {max(weeks)}")
    
    # 2. Charger les donnees de population
    print("\nChargement des donnees de population...")
    # Années nécessaires : de 2003 (pour interpolation début 2004) à 2016
    years_needed = list(range(2003, 2017))
    pop_annual = load_population_data(
        DATA_DIR / 'estim-pop-areg-sexe-gca-1975-2015.xls',
        years_needed
    )
    print(f"\n   Total: {len(pop_annual)} enregistrements annuels")
    print(f"   Années couvertes: {pop_annual['year'].min()} - {pop_annual['year'].max()}")
    
    # 3. Interpoler vers des donnees hebdomadaires
    print("\nInterpolation spline cubique vers donnees hebdomadaires...")
    pop_weekly = interpolate_population_weekly(pop_annual, weeks)
    print(f"   {len(pop_weekly)} enregistrements hebdomadaires crees")
    
    # 4. Merger avec synop
    print("\nFusion des donnees...")
    merged = synop.merge(
        pop_weekly,
        on=['week', 'region_name'],
        how='left'
    )
    
    # Vérifier les valeurs manquantes
    missing = merged['pop_total'].isna().sum()
    print(f"   Valeurs population manquantes: {missing} / {len(merged)}")
    
    # 5. Calculer des ratios utiles
    print("\nCalcul des ratios de population...")
    merged['pop_ratio_elderly'] = (merged['pop_60_74'] + merged['pop_75_plus']) / merged['pop_total']
    merged['pop_ratio_young'] = merged['pop_0_19'] / merged['pop_total']
    merged['pop_ratio_75_plus'] = merged['pop_75_plus'] / merged['pop_total']
    
    # 6. Réorganiser les colonnes
    cols_order = [
        'week', 'month', 'region_code', 'region_name',
        'google_grippe', 'google_grippe_no_aviaire', 'google_grippe_filtered',
        'pop_total', 'pop_0_19', 'pop_20_39', 'pop_40_59', 'pop_60_74', 'pop_75_plus',
        'pop_ratio_elderly', 'pop_ratio_young', 'pop_ratio_75_plus',
        'temp_mean', 'temp_min', 'temp_max', 'temp_std',
        'dewpoint_mean', 'humidity_mean', 'humidity_min', 'humidity_max',
        'wind_speed_mean', 'wind_speed_max', 'pressure_mean',
        'precipitation_sum', 'precipitation_mean', 'precipitation_max'
    ]
    
    merged = merged[cols_order]
    
    # 7. Sauvegarder
    output_path = PROJECT_ROOT / 'synop_hebdo_complet.csv'
    merged.to_csv(output_path, index=False)
    
    print(f"\nFichier cree: {output_path}")
    print(f"   Lignes: {len(merged)}")
    print(f"   Colonnes: {len(merged.columns)}")
    
    print("\nApercu des donnees:")
    print(merged[['week', 'region_name', 'pop_total', 'pop_75_plus', 'pop_ratio_elderly']].head(15).to_string(index=False))
    
    print("\nStatistiques population:")
    print(merged[['pop_total', 'pop_ratio_elderly', 'pop_ratio_75_plus']].describe())
    
    # Verification de l'interpolation
    print("\nVerification de l'interpolation (Ile-de-France):")
    idf = merged[merged['region_name'] == 'ILE-DE-FRANCE'][['week', 'pop_total']].head(20)
    print(idf.to_string(index=False))


if __name__ == '__main__':
    main()

