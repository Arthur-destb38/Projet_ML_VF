"""
MODELE V13 - 11 Features + Regularisation Maximale

V12 Kaggle: 88 (15 features)
V13: 11 features (top importance) + regularisation encore plus forte
"""
#%%
import sys
from pathlib import Path

# Ajouter le dossier parent au path pour importer config
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_squared_error
import warnings
warnings.filterwarnings('ignore')

# Import de la configuration centralisée
from config import (
    TRAIN_ENRICHI_CSV, TEST_ENRICHI_CSV, 
    get_submission_path, print_config
)

np.random.seed(42)
rmse = lambda y, p: np.sqrt(mean_squared_error(y, p))

print("="*70)
print("MODELE V13 - 11 Features + Regularisation Maximale")
print("="*70)
print_config()

# =============================================================================
# CHARGEMENT DES DONNEES
# =============================================================================
train = pd.read_csv(TRAIN_ENRICHI_CSV)
test = pd.read_csv(TEST_ENRICHI_CSV)
train = train.sort_values(['region_code', 'week']).reset_index(drop=True)
test = test.sort_values(['region_code', 'week']).reset_index(drop=True)

print(f"\nTrain: {len(train)} lignes")
print(f"Test: {len(test)} lignes")

# =============================================================================
# FONCTION DE CRÉATION DE FEATURES
# =============================================================================
def create_features_v13(df, hist):
    """11 features les plus importantes."""
    df = df.copy()
    h = hist.copy()
    
    df['week_num'] = df['week'].astype(str).str[4:].astype(int)
    h['week_num'] = h['week'].astype(str).str[4:].astype(int)
    
    # Saisonnalité (seulement sin_1, cos_1)
    df['sin_1'] = np.sin(2 * np.pi * df['week_num'] / 52)
    df['cos_1'] = np.cos(2 * np.pi * df['week_num'] / 52)
    df['is_flu_season'] = ((df['week_num'] <= 12) | (df['week_num'] >= 45)).astype(int)
    
    # Historique (seulement std, max, mean)
    agg = h.groupby(['region_code', 'week_num'])['TauxGrippe'].agg(['mean', 'std', 'max']).reset_index()
    agg.columns = ['region_code', 'week_num', 'rw_mean', 'rw_std', 'rw_max']
    df = df.merge(agg, on=['region_code', 'week_num'], how='left')
    
    for c in ['rw_mean', 'rw_std', 'rw_max']:
        df[c] = df[c].fillna(df[c].median() if df[c].notna().any() else 0)
    
    # Google
    df['google'] = df['google_grippe_filtered'].fillna(0)
    df['google_log'] = np.log1p(df['google'])
    df['google_x_rw'] = df['google_log'] * df['rw_mean']
    
    return df

# =============================================================================
# PREPARATION DU TRAIN
# =============================================================================
print("\nPreparation du train...")

train_sorted = train.sort_values(['region_code', 'week']).reset_index(drop=True)

# Lags
train_sorted['taux_lag1'] = train_sorted.groupby('region_code')['TauxGrippe'].shift(1)
train_sorted['taux_lag2'] = train_sorted.groupby('region_code')['TauxGrippe'].shift(2)

for col in ['taux_lag1', 'taux_lag2']:
    train_sorted[col] = train_sorted[col].fillna(train_sorted[col].median())

# Features
train_f = create_features_v13(train_sorted, train_sorted)
train_f['taux_lag1'] = train_sorted['taux_lag1']
train_f['taux_lag2'] = train_sorted['taux_lag2']

# Interactions
train_f['lag1_x_season'] = train_f['taux_lag1'] * train_f['is_flu_season']
train_f['lag1_x_google'] = train_f['taux_lag1'] * train_f['google_log']
train_f['taux_diff1'] = train_f['taux_lag1'] - train_f['taux_lag2']

# =============================================================================
# 11 FEATURES (top importance de V12)
# =============================================================================
features = [
    # Top 5 (82% importance)
    'lag1_x_season',   # 28.0%
    'taux_lag1',       # 18.7%
    'lag1_x_google',   # 14.2%
    'rw_max',          # 12.2%
    'rw_std',          # 8.9%
    # Features 6-11
    'taux_diff1',      # 5.6%
    'google_x_rw',     # 3.2%
    'google_log',      # 2.3%
    'taux_lag2',       # 2.0%
    'cos_1',           # 1.4%
    'sin_1',           # 1.3%
]

print(f"   Features: {len(features)}")

# =============================================================================
# VALIDATION SUR DERNIERE ANNEE
# =============================================================================
print("\nValidation sur derniere annee...")

train_f = train_f.sort_values('week').reset_index(drop=True)
train_f['year'] = train_f['week'].astype(str).str[:4].astype(int)
max_year = train_f['year'].max()

train_d = train_f[train_f['year'] < max_year]
val_d = train_f[train_f['year'] == max_year]

print(f"   Train: années < {max_year} ({len(train_d)} lignes)")
print(f"   Val: année {max_year} ({len(val_d)} lignes)")

X_tr = train_d[features + ['region_code']]
y_tr = train_d['TauxGrippe']
X_va = val_d[features + ['region_code']]
y_va = val_d['TauxGrippe']

# =============================================================================
# MODELE ULTRA-REGULARISE
# =============================================================================
print("\nModele ultra-regularise...")

model = CatBoostRegressor(
    iterations=350,
    learning_rate=0.08,
    depth=3,                     # Tres peu profond
    l2_leaf_reg=18,              # Tres forte regularisation
    min_data_in_leaf=100,        # Beaucoup de donnees par feuille
    random_strength=3,           # Forte randomisation
    bagging_temperature=1.2,     # Bagging fort
    random_seed=42,
    verbose=0,
    early_stopping_rounds=15,
    use_best_model=True
)

model.fit(
    Pool(X_tr, y_tr, cat_features=['region_code']),
    eval_set=Pool(X_va, y_va, cat_features=['region_code'])
)

pred_va = np.clip(model.predict(X_va), 0, None)
val_rmse = rmse(y_va, pred_va)
print(f"\nVal RMSE (annee {max_year}): {val_rmse:.2f}")

# =============================================================================
# ENTRAINEMENT FINAL
# =============================================================================
print("\nEntrainement final...")

X_full = train_f[features + ['region_code']]
y_full = train_f['TauxGrippe']

model_full = CatBoostRegressor(
    iterations=model.get_best_iteration() + 10,
    learning_rate=0.08,
    depth=3,
    l2_leaf_reg=18,
    min_data_in_leaf=100,
    random_strength=3,
    bagging_temperature=1.2,
    random_seed=42,
    verbose=0
)

model_full.fit(Pool(X_full, y_full, cat_features=['region_code']))

# =============================================================================
# PREDICTION RECURSIVE
# =============================================================================
print("\nPrediction recursive...")

test_sorted = test.sort_values(['region_code', 'week']).reset_index(drop=True)
test_f = create_features_v13(test_sorted, train_sorted)

# Dernières valeurs du train
last_values = train_sorted.groupby('region_code').last()['TauxGrippe']
second_last = train_sorted.groupby('region_code').nth(-2)['TauxGrippe']

last_pred = last_values.to_dict()
second_last_pred = second_last.to_dict()

test_weeks = sorted(test_sorted['week'].unique())
predictions = {}

for week in test_weeks:
    week_mask = test_f['week'] == week
    week_data = test_f[week_mask].copy()
    
    # Lags
    week_data['taux_lag1'] = week_data['region_code'].map(last_pred)
    week_data['taux_lag2'] = week_data['region_code'].map(second_last_pred)
    
    # Remplir NaN
    week_data['taux_lag1'] = week_data['taux_lag1'].fillna(week_data['taux_lag1'].median())
    week_data['taux_lag2'] = week_data['taux_lag2'].fillna(week_data['taux_lag2'].median())
    
    # Interactions
    week_data['lag1_x_season'] = week_data['taux_lag1'] * week_data['is_flu_season']
    week_data['lag1_x_google'] = week_data['taux_lag1'] * week_data['google_log']
    week_data['taux_diff1'] = week_data['taux_lag1'] - week_data['taux_lag2']
    
    # Prédire
    X_week = week_data[features + ['region_code']]
    pred_week = np.clip(model_full.predict(X_week), 0, None)
    
    # Stocker et mettre à jour
    for idx, (_, row) in enumerate(week_data.iterrows()):
        predictions[row['Id']] = pred_week[idx]
        region = row['region_code']
        second_last_pred[region] = last_pred.get(region, 0)
        last_pred[region] = pred_week[idx]

# =============================================================================
# SOUMISSION
# =============================================================================
sub = pd.DataFrame([{'Id': int(k), 'TauxGrippe': v} for k, v in predictions.items()])
sub = sub.sort_values('Id').reset_index(drop=True)
submission_path = get_submission_path('v13')
sub.to_csv(submission_path, index=False)

print(f"\nStats predictions:")
print(f"   Mean:   {sub['TauxGrippe'].mean():.2f}")
print(f"   Median: {sub['TauxGrippe'].median():.2f}")
print(f"   Min:    {sub['TauxGrippe'].min():.2f}")
print(f"   Max:    {sub['TauxGrippe'].max():.2f}")

# Feature importance
print(f"\nFeature Importance:"))
feat_imp = pd.DataFrame({
    'feature': features,
    'importance': model_full.get_feature_importance()[:len(features)]
}).sort_values('importance', ascending=False)
print(feat_imp.to_string(index=False))

print(f"\n" + "="*70)
print(f"V13 - 11 Features Ultra-Regularise")
print(f"   Features: {len(features)} (vs V12: 15)")
print(f"   Regularisation: depth=3, l2=18, min_leaf=100")
print(f"   Val RMSE: {val_rmse:.2f}")
print(f"   Fichier: {submission_path}")
print("="*70)
# %%


