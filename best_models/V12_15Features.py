"""
MODELE V12 - 15 Features (Top importance de V10)

15 features selectionnees par importance:
1. taux_lag1 (23.4%)      9. google_x_rw (1.5%)
2. lag1_x_season (23.4%)  10. cos_1 (1.4%)
3. rw_max (13.9%)         11. sin_1 (0.7%)
4. lag1_x_google (13.7%)  12. rw_median (0.7%)
5. rw_std (10.4%)         13. cos_2 (0.5%)
6. taux_diff1 (5.2%)      14. rw_mean (0.4%)
7. google_log (2.6%)      15. is_flu_season (0.3%)
8. taux_lag2 (1.6%)

+ Regularisation forte pour eviter l'overfitting
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
print("MODELE V12 - 15 Features Anti-Overfitting")
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
def create_features_v12(df, hist):
    """15 features les plus importantes."""
    df = df.copy()
    h = hist.copy()
    
    df['week_num'] = df['week'].astype(str).str[4:].astype(int)
    h['week_num'] = h['week'].astype(str).str[4:].astype(int)
    
    # Saisonnalité
    df['sin_1'] = np.sin(2 * np.pi * df['week_num'] / 52)
    df['cos_1'] = np.cos(2 * np.pi * df['week_num'] / 52)
    df['cos_2'] = np.cos(2 * np.pi * 2 * df['week_num'] / 52)
    df['is_flu_season'] = ((df['week_num'] <= 12) | (df['week_num'] >= 45)).astype(int)
    
    # Historique
    agg = h.groupby(['region_code', 'week_num'])['TauxGrippe'].agg([
        'mean', 'median', 'std', 'max'
    ]).reset_index()
    agg.columns = ['region_code', 'week_num', 'rw_mean', 'rw_median', 'rw_std', 'rw_max']
    df = df.merge(agg, on=['region_code', 'week_num'], how='left')
    
    for c in ['rw_mean', 'rw_median', 'rw_std', 'rw_max']:
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
train_f = create_features_v12(train_sorted, train_sorted)
train_f['taux_lag1'] = train_sorted['taux_lag1']
train_f['taux_lag2'] = train_sorted['taux_lag2']

# Interactions
train_f['lag1_x_season'] = train_f['taux_lag1'] * train_f['is_flu_season']
train_f['lag1_x_google'] = train_f['taux_lag1'] * train_f['google_log']
train_f['taux_diff1'] = train_f['taux_lag1'] - train_f['taux_lag2']

# =============================================================================
# 15 FEATURES (triées par importance V10)
# =============================================================================
features = [
    # Top 5 (82% importance)
    'taux_lag1',       # 23.4%
    'lag1_x_season',   # 23.4%
    'rw_max',          # 13.9%
    'lag1_x_google',   # 13.7%
    'rw_std',          # 10.4%
    # Features 6-10
    'taux_diff1',      # 5.2%
    'google_log',      # 2.6%
    'taux_lag2',       # 1.6%
    'google_x_rw',     # 1.5%
    'cos_1',           # 1.4%
    # Features 11-15
    'sin_1',           # 0.7%
    'rw_median',       # 0.7%
    'cos_2',           # 0.5%
    'rw_mean',         # 0.4%
    'is_flu_season',   # 0.3%
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
# MODELE AVEC REGULARISATION FORTE
# =============================================================================
print("\nModele avec regularisation forte...")

model = CatBoostRegressor(
    iterations=500,
    learning_rate=0.06,
    depth=4,                     # Arbres peu profonds
    l2_leaf_reg=12,              # Regularisation forte
    min_data_in_leaf=60,         # Beaucoup de donnees par feuille
    random_strength=2.5,
    bagging_temperature=0.8,
    random_seed=42,
    verbose=0,
    early_stopping_rounds=25,
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
    iterations=model.get_best_iteration() + 15,
    learning_rate=0.06,
    depth=4,
    l2_leaf_reg=12,
    min_data_in_leaf=60,
    random_strength=2.5,
    bagging_temperature=0.8,
    random_seed=42,
    verbose=0
)

model_full.fit(Pool(X_full, y_full, cat_features=['region_code']))

# =============================================================================
# PREDICTION RECURSIVE
# =============================================================================
print("\nPrediction recursive...")

test_sorted = test.sort_values(['region_code', 'week']).reset_index(drop=True)
test_f = create_features_v12(test_sorted, train_sorted)

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
submission_path = get_submission_path('v12')
sub.to_csv(submission_path, index=False)

print(f"\nStats predictions:")
print(f"   Mean:   {sub['TauxGrippe'].mean():.2f}")
print(f"   Median: {sub['TauxGrippe'].median():.2f}")
print(f"   Min:    {sub['TauxGrippe'].min():.2f}")
print(f"   Max:    {sub['TauxGrippe'].max():.2f}")

# Feature importance
print(f"\nFeature Importance:")
feat_imp = pd.DataFrame({
    'feature': features,
    'importance': model_full.get_feature_importance()[:len(features)]
}).sort_values('importance', ascending=False)
print(feat_imp.to_string(index=False))

print(f"\n" + "="*70)
print(f"V12 - 15 Features Anti-Overfitting")
print(f"   Features: {len(features)}")
print(f"   Regularisation: depth=4, l2=12, min_leaf=60")
print(f"   Val RMSE: {val_rmse:.2f}")
print(f"   Fichier: {submission_path}")
print("="*70)
# %%


