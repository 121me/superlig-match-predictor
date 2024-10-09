import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from smp_utils import mackolik_db

# First Code - Data Collection

headers = ['avg_possession_rate_home', 'avg_possession_rate_away', 'avg_total_shots_home', 'avg_total_shots_away',
           'avg_shots_on_target_home', 'avg_shots_on_target_away', 'avg_successful_passes_home', 'avg_successful_passes_away',
           'avg_pass_success_rate_home', 'avg_pass_success_rate_away', 'avg_corners_home', 'avg_corners_away',
           'avg_crosses_home', 'avg_crosses_away', 'avg_fouls_home', 'avg_fouls_away',
           'avg_offsides_home', 'avg_offsides_away', 'avg_yellow_cards_home', 'avg_yellow_cards_away',
           'avg_red_cards_home', 'avg_red_cards_away', 'avg_ft_match_score_home', 'avg_ft_match_score_away',
           'avg_ht_match_score_home', 'avg_ht_match_score_away', "match_id", "bet_under_25_odd_rate", "bet_over_25_odd_rate", "is_match_under_25"]

avg_keys = ["possession_rate_home", "possession_rate_away", "total_shots_home", "total_shots_away",
            "shots_on_target_home", "shots_on_target_away", "successful_passes_home", "successful_passes_away",
            "pass_success_rate_home", "pass_success_rate_away", "corners_home", "corners_away",
            "crosses_home", "crosses_away", "fouls_home", "fouls_away",
            "offsides_home", "offsides_away", "yellow_cards_home", "yellow_cards_away",
            "red_cards_home", "red_cards_away", "ft_match_score_home", "ft_match_score_away",
            "ht_match_score_home", "ht_match_score_away"]

other_keys = ["match_id", "bet_under_25", "bet_over_25",]

get_match_sorted = mackolik_db.get_sorted_match_ids_by_season(59416)

matches = [mackolik_db.get_match(match['match_id']) for match in get_match_sorted]

data = []

# Take the average of the previous 5 games for each iteration
for n, match in enumerate(matches[5:], 5):
    line = [round(sum([match[key] for match in matches[n - 5:n]]) / 5, 5) for key in avg_keys]
    line += [match[key] for key in other_keys]
    line += [0] if match["ft_match_score_home"] + match["ft_match_score_away"] < 2.5 else [1]
    data += [line]

# Convert collected data into a DataFrame
df = pd.DataFrame(data, columns=headers)

# Second Code - Training the Model
df['goal_diff'] = df['avg_ft_match_score_home'] - df['avg_ft_match_score_away']
df['shot_diff'] = df['avg_total_shots_home'] - df['avg_total_shots_away']
df['pass_diff'] = df['avg_successful_passes_home'] - df['avg_successful_passes_away']
df['corner_diff'] = df['avg_corners_home'] - df['avg_corners_away']
df['foul_diff'] = df['avg_fouls_home'] - df['avg_fouls_away']
df['yellow_card_diff'] = df['avg_yellow_cards_home'] - df['avg_yellow_cards_away']
df['red_card_diff'] = df['avg_red_cards_home'] - df['avg_red_cards_away']

# Data Preprocessing
X = df.drop(columns=['is_match_under_25', 'match_id'])  # Drop the target column
match_ids = df['match_id']  # Save the match ids for future use
y = df['is_match_under_25']  # Define the target column

# Split the data in order, as is, get first 80% as training data and the rest as test data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False, random_state=None)

# Standardize the data
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Feature Selection using ANOVA F-test
selector = SelectKBest(f_classif, k=10)
X_train_selected = selector.fit_transform(X_train_scaled, y_train)
X_test_selected = selector.transform(X_test_scaled)

# Model Training and Evaluation
models = {
    'SVM': SVC(probability=True),
    # 'Random Forest': RandomForestClassifier()
}

for model_name, model in models.items():
    model.fit(X_train_selected, y_train)
    y_pred = model.predict(X_test_selected)
    accuracy = accuracy_score(y_test, y_pred)
    print(f'{model_name} Accuracy: {accuracy * 100:.2f}%')

    # Profitable betting opportunities (comparing with bookmaker odds)
    bookmaker_under_odds = X_test['bet_under_25_odd_rate'].values
    bookmaker_over_odds = X_test['bet_over_25_odd_rate'].values

    capital = 1000  # Starting capital
    bet_percentage = 0.4  # Betting percentage of the capital

    # Iterate through the test set predictions and actual values
    for match_id, y_t, y_p, uo, oo in zip(match_ids[X_test.index], y_test, y_pred, bookmaker_under_odds,
                                          bookmaker_over_odds):
        # Print the match ID along with other details
        print(f"Match ID: {match_id}, Actual: {y_t}, Predicted: {y_p}, Under Odds: {uo}, Over Odds: {oo}")

        if y_p == 0 and y_t == 0:
            capital += capital * uo * bet_percentage
        elif y_p == 1 and y_t == 1:
            capital += capital * oo * bet_percentage
        else:
            capital -= capital * bet_percentage

        print(f'Current Capital: ${capital:.2f}')

    print(f'Final Capital after simulation with model {model_name}: ${capital:.2f}')