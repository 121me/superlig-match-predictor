import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import pickle

from sklearn.preprocessing import OneHotEncoder

# Assuming your data is in a CSV file named 'match_data.csv'
data = pd.read_csv('match_data.csv')

# Define features and target variables
features = [
    'team_power_home', 'team_power_away',
    'avg_possession_rate_home', 'avg_total_shots_home', 'avg_total_shots_away', 'avg_shots_on_target_home',
    'avg_shots_on_target_away', 'avg_successful_passes_home', 'avg_successful_passes_away',
    'avg_pass_success_rate_home', 'avg_pass_success_rate_away', 'avg_corners_home', 'avg_corners_away',
    'avg_crosses_home', 'avg_crosses_away', 'avg_fouls_home', 'avg_fouls_away', 'avg_offsides_home',
    'avg_offsides_away', 'avg_yellow_cards_home', 'avg_yellow_cards_away', 'avg_red_cards_home', 'avg_red_cards_away',
    'avg_team_goals_home', 'avg_team_goals_away'
]
target_variable = ['team_goals_home', 'team_goals_away']  # Adjusted for tuple output

# Separate training, validation, and test sets
# First 28 weeks for training, next 7 for validation, last 3 for testing
training_data = data.head(28 * 10)  # Assuming 10 matches per week
validation_data = data[28 * 10:35 * 10]
testing_data = data[35 * 10:]

# Example hyperparameter grid:
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [3, 5, 7]
}

# Prepare data for train/test/validation split
X_train = training_data[features]
y_train = training_data[target_variable]
X_val = validation_data[features]
y_val = validation_data[target_variable]
X_test = testing_data[features]
y_test = testing_data[target_variable]

# One-hot encode categorical features (team IDs and potentially others)
encoder = OneHotEncoder(sparse=False)
encoded_X_train = encoder.fit_transform(X_train[['team_id_home', 'team_id_away']])
encoded_X_val = encoder.transform(X_val[['team_id_home', 'team_id_away']])
encoded_X_test = encoder.transform(X_test[['team_id_home', 'team_id_away']])
X_train[['team_id_home', 'team_id_away']] = pd.DataFrame(encoded_X_train, columns=encoder.get_feature_names_out(['team_id_home', 'team_id_away']))
X_val[['team_id_home', 'team_id_away']] = pd.DataFrame(encoded_X_val, columns=encoder.get_feature_names_out(['team_id_home', 'team_id_away']))
X_test[['team_id_home', 'team_id_away']] = pd.DataFrame(encoded_X_test, columns=encoder.get_feature_names_out(['team_id_home', 'team_id_away']))

# Combine encoded team IDs with other features
X_train = pd.concat([X_train, X_train.drop(['team_id_home', 'team_id_away'], axis=1)], axis=1)
X_val = pd.concat([X_val, X_val.drop(['team_id_home', 'team_id_away'], axis=1)], axis=1)
X_test = pd.concat([X_test, X_test.drop(['team_id_home', 'team_id_away'], axis=1)], axis=1)

# Train-validation split for hyperparameter tuning (optional)
from sklearn.model_selection import GridSearchCV

# Example hyperparameter grid:
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [3, 5, 7]
}

grid_search = GridSearchCV(RandomForestRegressor(random_state=42), param_grid, cv=5)
grid_search.fit(X_train, y_train)

# Get best model from grid search or create a new model
best_model = grid_search.best_estimator_
# Or:
# model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
# model.fit(X_train, y_train)

# Evaluate on validation set
y_pred_val = best_model.predict(X_val)
mse = mean_squared_error(y_val, y_pred_val)
r2 = r2_score(y_val, y_pred_val)