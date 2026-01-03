"""
Script pour agréger les données météorologiques SYNOP en données hebdomadaires par région.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Ajouter le dossier parent au path pour importer config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    PROJECT_ROOT, DATA_DIR, METEO_DIR, STATIONS_METEO_CSV,
    TRAIN_CSV, TEST_CSV, SYNOP_HEBDO_ENRICHI_CSV, TRAIN_ENRICHI_CSV, TEST_ENRICHI_CSV
)

# Mapping des stations météo vers les régions (basé sur la localisation géographique)
# Format: station_id -> region_code
STATION_TO_REGION = {
    # ALSACE (42)
    7190: 42,  # STRASBOURG-ENTZHEIM
    7299: 42,  # BALE-MULHOUSE
    
    # AQUITAINE (72)
    7510: 72,  # BORDEAUX-MERIGNAC
    7535: 72,  # GOURDON
    7607: 72,  # MONT-DE-MARSAN
    
    # AUVERGNE (83)
    7460: 83,  # CLERMONT-FD
    7471: 83,  # LE PUY-LOUDES
    
    # BASSE-NORMANDIE (25)
    7020: 25,  # PTE DE LA HAGUE
    7027: 25,  # CAEN-CARPIQUET
    
    # BOURGOGNE (26)
    7280: 26,  # DIJON-LONGVIC
    
    # BRETAGNE (53)
    7110: 53,  # BREST-GUIPAVAS
    7117: 53,  # PLOUMANAC'H
    7207: 53,  # BELLE ILE-LE TALUT
    
    # CENTRE (24)
    7240: 24,  # TOURS
    7255: 24,  # BOURGES
    
    # CHAMPAGNE-ARDENNE (21)
    7072: 21,  # REIMS-PRUNAY
    7168: 21,  # TROYES-BARBEREY
    
    # CORSE (94)
    7761: 94,  # AJACCIO
    7790: 94,  # BASTIA
    
    # FRANCHE-COMTE (43)
    7181: 43,  # NANCY-OCHEY (en fait Lorraine, à corriger)
    
    # HAUTE-NORMANDIE (23)
    7037: 23,  # ROUEN-BOOS
    
    # ILE-DE-FRANCE (11)
    7149: 11,  # ORLY
    
    # LANGUEDOC-ROUSSILLON (91)
    7643: 91,  # MONTPELLIER
    7558: 91,  # MILLAU
    7747: 91,  # PERPIGNAN
    
    # LIMOUSIN (74)
    7434: 74,  # LIMOGES-BELLEGARDE
    
    # LORRAINE (41)
    7181: 41,  # NANCY-OCHEY
    
    # MIDI-PYRENEES (73)
    7621: 73,  # TARBES-OSSUN
    7627: 73,  # ST GIRONS
    7630: 73,  # TOULOUSE-BLAGNAC
    
    # NORD-PAS-DE-CALAIS (31)
    7005: 31,  # ABBEVILLE (en fait Picardie)
    7015: 31,  # LILLE-LESQUIN
    
    # PAYS-DE-LA-LOIRE (52)
    7130: 52,  # RENNES-ST JACQUES (en fait Bretagne, mais proche)
    7222: 52,  # NANTES-BOUGUENAIS
    
    # PICARDIE (22)
    7005: 22,  # ABBEVILLE
    7139: 22,  # ALENCON (en fait Basse-Normandie)
    
    # POITOU-CHARENTES (54)
    7314: 54,  # PTE DE CHASSIRON
    7335: 54,  # POITIERS-BIARD
    
    # PROVENCE-ALPES-COTE-D-AZUR (93)
    7577: 93,  # MONTELIMAR (en fait Rhône-Alpes)
    7591: 93,  # EMBRUN
    7650: 93,  # MARIGNANE
    7661: 93,  # CAP CEPET
    7690: 93,  # NICE
    
    # RHONE-ALPES (82)
    7481: 82,  # LYON-ST EXUPERY
    7577: 82,  # MONTELIMAR
}

# Mapping manuel précis des stations vers les régions
MANUAL_STATION_MAPPING = {
    # ALSACE (42)
    7190: 42,  # STRASBOURG-ENTZHEIM
    
    # AQUITAINE (72)
    7510: 72,  # BORDEAUX-MERIGNAC
    7607: 72,  # MONT-DE-MARSAN
    
    # AUVERGNE (83)
    7460: 83,  # CLERMONT-FD
    7471: 83,  # LE PUY-LOUDES
    
    # BASSE-NORMANDIE (25)
    7020: 25,  # PTE DE LA HAGUE
    7027: 25,  # CAEN-CARPIQUET
    7139: 25,  # ALENCON
    
    # BOURGOGNE (26)
    7280: 26,  # DIJON-LONGVIC
    
    # BRETAGNE (53)
    7110: 53,  # BREST-GUIPAVAS
    7117: 53,  # PLOUMANAC'H
    7207: 53,  # BELLE ILE-LE TALUT
    7130: 53,  # RENNES-ST JACQUES
    
    # CENTRE (24)
    7240: 24,  # TOURS
    7255: 24,  # BOURGES
    
    # CHAMPAGNE-ARDENNE (21)
    7072: 21,  # REIMS-PRUNAY
    7168: 21,  # TROYES-BARBEREY
    
    # CORSE (94)
    7761: 94,  # AJACCIO
    7790: 94,  # BASTIA
    
    # FRANCHE-COMTE (43) - utiliser Bâle-Mulhouse (proche frontière)
    7299: 43,  # BALE-MULHOUSE (réassigné à Franche-Comté au lieu d'Alsace)
    
    # HAUTE-NORMANDIE (23)
    7037: 23,  # ROUEN-BOOS
    
    # ILE-DE-FRANCE (11)
    7149: 11,  # ORLY
    
    # LANGUEDOC-ROUSSILLON (91)
    7643: 91,  # MONTPELLIER
    7558: 91,  # MILLAU
    7747: 91,  # PERPIGNAN
    
    # LIMOUSIN (74)
    7434: 74,  # LIMOGES-BELLEGARDE
    7535: 74,  # GOURDON (proche Limousin)
    
    # LORRAINE (41)
    7181: 41,  # NANCY-OCHEY
    
    # MIDI-PYRENEES (73)
    7621: 73,  # TARBES-OSSUN
    7627: 73,  # ST GIRONS
    7630: 73,  # TOULOUSE-BLAGNAC
    
    # NORD-PAS-DE-CALAIS (31)
    7015: 31,  # LILLE-LESQUIN
    
    # PAYS-DE-LA-LOIRE (52)
    7222: 52,  # NANTES-BOUGUENAIS
    
    # PICARDIE (22)
    7005: 22,  # ABBEVILLE
    
    # POITOU-CHARENTES (54)
    7314: 54,  # PTE DE CHASSIRON
    7335: 54,  # POITIERS-BIARD
    
    # PROVENCE-ALPES-COTE-D-AZUR (93)
    7591: 93,  # EMBRUN
    7650: 93,  # MARIGNANE
    7661: 93,  # CAP CEPET
    7690: 93,  # NICE
    
    # RHONE-ALPES (82)
    7481: 82,  # LYON-ST EXUPERY
    7577: 82,  # MONTELIMAR
}


def get_region_from_coords(lat, lon, station_id=None):
    """Détermine la région à partir des coordonnées ou du mapping manuel."""
    # D'abord, vérifier le mapping manuel
    if station_id and station_id in MANUAL_STATION_MAPPING:
        return MANUAL_STATION_MAPPING[station_id]
    
    # Sinon, utiliser les coordonnées (fallback)
    # Régions approximatives basées sur les coordonnées
    if lat > 49.5 and lon > 1.5 and lon < 4.5:
        return 31  # NORD-PAS-DE-CALAIS
    elif lat > 49 and lon > 0 and lon < 2:
        return 23  # HAUTE-NORMANDIE
    elif lat > 49 and lon < 0.5:
        return 22  # PICARDIE
    elif lat > 48.5 and lon > 6:
        return 42  # ALSACE
    elif lat > 48 and lon > 4 and lon < 6.5:
        return 21  # CHAMPAGNE-ARDENNE
    elif lat > 48 and lat < 49.5 and lon > 5 and lon < 7:
        return 41  # LORRAINE
    elif lat > 46.5 and lat < 48.5 and lon > 5 and lon < 7.5:
        return 43  # FRANCHE-COMTE
    elif lat > 46.5 and lat < 48 and lon > 3.5 and lon < 5.5:
        return 26  # BOURGOGNE
    elif lat > 47.5 and lon > -5 and lon < -1:
        return 53  # BRETAGNE
    elif lat > 46.5 and lat < 48 and lon > -2.5 and lon < 0:
        return 52  # PAYS-DE-LA-LOIRE
    elif lat > 48 and lat < 50 and lon > -2 and lon < 0:
        return 25  # BASSE-NORMANDIE
    elif lat > 48 and lat < 49.5 and lon > 1.5 and lon < 3.5:
        return 11  # ILE-DE-FRANCE
    elif lat > 46.5 and lat < 48.5 and lon > -0.5 and lon < 2.5:
        return 24  # CENTRE
    elif lat > 45.5 and lat < 47 and lon > -1.5 and lon < 1:
        return 54  # POITOU-CHARENTES
    elif lat > 45 and lat < 46.5 and lon > 0.5 and lon < 2.5:
        return 74  # LIMOUSIN
    elif lat > 43.5 and lat < 46 and lon > -2 and lon < 0.5:
        return 72  # AQUITAINE
    elif lat > 42.5 and lat < 44.5 and lon > -0.5 and lon < 2.5:
        return 73  # MIDI-PYRENEES
    elif lat > 42 and lat < 45 and lon > 2 and lon < 4.5:
        return 91  # LANGUEDOC-ROUSSILLON
    elif lat > 44.5 and lat < 46.5 and lon > 2 and lon < 4.5:
        return 83  # AUVERGNE
    elif lat > 44 and lat < 46.5 and lon > 4 and lon < 6.5:
        return 82  # RHONE-ALPES
    elif lat > 43 and lat < 45 and lon > 4.5 and lon < 8:
        return 93  # PROVENCE-ALPES-COTE-D-AZUR
    elif lat > 41 and lat < 43 and lon > 8 and lon < 10:
        return 94  # CORSE
    else:
        return None


def parse_synop_date(date_val):
    """Parse la date SYNOP au format YYYYMMDDHHMMSS."""
    try:
        date_str = str(int(date_val))
        return datetime.strptime(date_str, '%Y%m%d%H%M%S')
    except:
        return None


def get_week_id(dt):
    """Retourne l'identifiant de semaine au format YYYYWW."""
    if dt is None:
        return None
    year, week, _ = dt.isocalendar()
    return year * 100 + week


def load_stations(filepath):
    """Charge la liste des stations avec leurs coordonnées."""
    df = pd.read_csv(filepath, sep=';')
    df.columns = ['station_id', 'name', 'latitude', 'longitude', 'altitude']
    
    # Ajouter la région basée sur le mapping manuel + coordonnées
    df['region_code'] = df.apply(
        lambda row: get_region_from_coords(
            row['latitude'], 
            row['longitude'],
            row['station_id']
        ), 
        axis=1
    )
    
    return df


def load_synop_file(filepath):
    """Charge un fichier SYNOP."""
    try:
        df = pd.read_csv(filepath, sep=';', low_memory=False)
        return df
    except Exception as e:
        print(f"Erreur lors du chargement de {filepath}: {e}")
        return None


def aggregate_weekly(data_dir):
    """Agrège toutes les données météo en données hebdomadaires par région."""
    
    print("Chargement de la liste des stations...")
    stations_df = load_stations(STATIONS_METEO_CSV)
    station_to_region = dict(zip(stations_df['station_id'], stations_df['region_code']))
    
    print(f"Stations mappées: {len(station_to_region)}")
    print(f"Stations avec région: {sum(1 for v in station_to_region.values() if v is not None)}")
    
    # Colonnes météo à agréger
    meteo_cols = ['t', 'td', 'u', 'ff', 'pmer', 'vv', 'n', 'rr1', 'rr3', 'rr6', 'rr12', 'rr24']
    
    all_data = []
    
    synop_files = sorted(METEO_DIR.glob('synop.*.csv'))
    print(f"\nTraitement de {len(synop_files)} fichiers SYNOP...")
    
    for i, filepath in enumerate(synop_files):
        if (i + 1) % 20 == 0:
            print(f"  Progression: {i+1}/{len(synop_files)} fichiers...")
        
        df = load_synop_file(filepath)
        if df is None:
            continue
        
        # Parser la date et obtenir la semaine
        df['datetime'] = df['date'].apply(parse_synop_date)
        df['week'] = df['datetime'].apply(get_week_id)
        
        # Mapper la station à la région
        df['region_code'] = df['numer_sta'].map(station_to_region)
        
        # Filtrer les lignes sans région
        df = df[df['region_code'].notna()]
        
        if len(df) == 0:
            continue
        
        # Convertir les colonnes météo en numérique
        for col in meteo_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convertir la température de Kelvin en Celsius
        if 't' in df.columns:
            df['t_celsius'] = df['t'] - 273.15
        if 'td' in df.columns:
            df['td_celsius'] = df['td'] - 273.15
        
        all_data.append(df)
    
    print("\nConcaténation des données...")
    full_df = pd.concat(all_data, ignore_index=True)
    
    print(f"Total observations: {len(full_df)}")
    print(f"Semaines uniques: {full_df['week'].nunique()}")
    print(f"Régions uniques: {full_df['region_code'].nunique()}")
    
    # Agrégation par semaine et région
    print("\nAgrégation hebdomadaire par région...")
    
    agg_dict = {
        't_celsius': ['mean', 'min', 'max', 'std'],
        'td_celsius': ['mean'],
        'u': ['mean', 'min', 'max'],  # Humidité
        'ff': ['mean', 'max'],  # Vitesse du vent
        'pmer': ['mean'],  # Pression
    }
    
    # Ajouter les précipitations si disponibles
    for col in ['rr24']:
        if col in full_df.columns:
            agg_dict[col] = ['sum', 'mean', 'max']
    
    # Filtrer pour ne garder que les colonnes présentes
    agg_dict = {k: v for k, v in agg_dict.items() if k in full_df.columns}
    
    weekly_df = full_df.groupby(['week', 'region_code']).agg(agg_dict).reset_index()
    
    # Aplatir les noms de colonnes
    weekly_df.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col 
                         for col in weekly_df.columns]
    
    # Renommer les colonnes pour plus de clarté
    column_rename = {
        't_celsius_mean': 'temp_mean',
        't_celsius_min': 'temp_min',
        't_celsius_max': 'temp_max',
        't_celsius_std': 'temp_std',
        'td_celsius_mean': 'dewpoint_mean',
        'u_mean': 'humidity_mean',
        'u_min': 'humidity_min',
        'u_max': 'humidity_max',
        'ff_mean': 'wind_speed_mean',
        'ff_max': 'wind_speed_max',
        'pmer_mean': 'pressure_mean',
        'rr24_sum': 'precipitation_sum',
        'rr24_mean': 'precipitation_mean',
        'rr24_max': 'precipitation_max',
    }
    
    weekly_df = weekly_df.rename(columns=column_rename)
    
    # Convertir region_code en int
    weekly_df['region_code'] = weekly_df['region_code'].astype(int)
    
    print(f"\nDonnées agrégées: {len(weekly_df)} lignes")
    print(f"Colonnes: {list(weekly_df.columns)}")
    
    return weekly_df


def main():
    # Utiliser les chemins centralisés
    
    # Agréger les données météo
    weekly_meteo = aggregate_weekly(DATA_DIR)
    
    # Sauvegarder le fichier météo brut
    output_path = PROJECT_ROOT / 'meteo_weekly.csv'
    weekly_meteo.to_csv(output_path, index=False)
    print(f"\nDonnees sauvegardees dans: {output_path}")
    
    # Afficher un apercu
    print("\nApercu des donnees:")
    print(weekly_meteo.head(20))
    
    print("\nStatistiques:")
    print(weekly_meteo.describe())
    
    # Verifier la couverture
    print("\nRegions couvertes:")
    print(weekly_meteo['region_code'].value_counts().sort_index())
    
    # =========================================================================
    # CRÉER LES FICHIERS ENRICHIS (train + meteo, test + meteo)
    # =========================================================================
    print("\n" + "="*70)
    print("CRÉATION DES FICHIERS ENRICHIS")
    print("="*70)
    
    # Charger train et test
    train = pd.read_csv(TRAIN_CSV)
    test = pd.read_csv(TEST_CSV)
    print(f"\nTrain: {len(train)} lignes")
    print(f"Test: {len(test)} lignes")
    
    # Fusionner avec la météo
    train_enrichi = train.merge(weekly_meteo, on=['week', 'region_code'], how='left')
    test_enrichi = test.merge(weekly_meteo, on=['week', 'region_code'], how='left')
    
    print(f"\nTrain enrichi: {len(train_enrichi)} lignes, {len(train_enrichi.columns)} colonnes")
    print(f"Test enrichi: {len(test_enrichi)} lignes, {len(test_enrichi.columns)} colonnes")
    
    # Sauvegarder
    train_enrichi.to_csv(TRAIN_ENRICHI_CSV, index=False)
    test_enrichi.to_csv(TEST_ENRICHI_CSV, index=False)
    print(f"\nFichiers créés:")
    print(f"   - {TRAIN_ENRICHI_CSV}")
    print(f"   - {TEST_ENRICHI_CSV}")
    
    # Créer synop_hebdo_enrichi (train enrichi avec region_name pour Google Trends)
    synop_hebdo_enrichi = train_enrichi.copy()
    synop_hebdo_enrichi.to_csv(SYNOP_HEBDO_ENRICHI_CSV, index=False)
    print(f"   - {SYNOP_HEBDO_ENRICHI_CSV}")
    
    # Vérifier les valeurs manquantes
    missing = train_enrichi.isnull().sum()
    if missing.any():
        print(f"\nValeurs manquantes dans train_enrichi:")
        print(missing[missing > 0])


if __name__ == '__main__':
    main()

