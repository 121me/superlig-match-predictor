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

avg_keys_raw = ["possession_rate", "total_shots", "shots_on_target", "successful_passes",
                "pass_success_rate", "corners", "crosses", "fouls", "offsides", "yellow_cards",
                "red_cards", "ft_match_score", "ht_match_score"]

other_keys = ["match_id", "bet_under_25", "bet_over_25",]

season_ids = [
    63837, 61588, 59267, 57528, 54669,  # English Premier League 2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    64029, 61598, 59317, 57488, 54798,  # Bundesliga 2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    63917, 61638, 59338, 57623, 54839,  # La Liga 2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    64028, 61642, 59421, 57617, 55017,  # Serie A 2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    63977, 61596, 59318, 57305, 54705,  # Ligue 1 2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    63860, None, 59416, 57526, 54794,  # Süper Lig 2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    67180,
    67285,
    67194,
    67286,
    67238,
    67287,
    #67892, # UEFA Champions League 2024-2025
    #67909, # UEFA Europa League 2024-2025
]

# Placeholder for the main data
main_data = []

# Loop over each season to collect training data
for season_id in season_ids:
    if season_id is None:
        continue
    # Get sorted matches from the season
    matches = mackolik_db.get_sorted_match_ids_by_season(season_id)

    # Fetch full match data
    full_matches = [mackolik_db.get_match(match['match_id']) for match in matches]

    print(f"Season ID: {season_id}, Match Count: {len(full_matches)}")

    # Process each match and calculate the averages of previous 5 matches
    for match in full_matches:

        wi = match["week_index"]

        if season_id in [67892, 67909]:
            prev_n = 2
        else:
            prev_n = 6

        if wi < prev_n:
            continue

        home_team_prev_n_matches = []
        away_team_prev_n_matches = []

        for m in full_matches:
            if wi - prev_n < m['week_index'] < wi and m['match_result_type'] == 1:
                if m['team_id_home'] == match['team_id_home'] or m['team_id_away'] == match['team_id_home']:
                    home_team_prev_n_matches.append(m)
                elif m['team_id_home'] == match['team_id_away'] or m['team_id_away'] == match['team_id_away']:
                    away_team_prev_n_matches.append(m)

        for m in home_team_prev_n_matches:
            # swap the home and away team data and stats
            if m["team_id_away"] == match["team_id_home"]:
                for key in avg_keys_raw:
                    m[key + "_home"], m[key + "_away"] = m[key + "_away"], m[key + "_home"]

        for m in away_team_prev_n_matches:
            # swap the home and away team data and stats
            if m["team_id_home"] == match["team_id_away"]:
                for key in avg_keys_raw:
                    m[key + "_home"], m[key + "_away"] = m[key + "_away"], m[key + "_home"]

        home_averages = [round(sum([m[key + "_home"] for m in home_team_prev_n_matches]) / len(home_team_prev_n_matches), 2) for key in avg_keys_raw]
        away_averages = [round(sum([m[key + "_away"] for m in away_team_prev_n_matches]) / len(away_team_prev_n_matches), 2) for key in avg_keys_raw]

        line = home_averages + away_averages + [match[key] for key in other_keys]
        line += [0] if match["ft_match_score_home"] + match["ft_match_score_away"] < 2.5 else [1]

        # Append this match's data to the main dataset
        main_data.append(line)




# Convert the collected data into a DataFrame
df_main = pd.DataFrame(main_data, columns=headers)

# Feature engineering
df_main['goal_diff'] = df_main['avg_ft_match_score_home'] - df_main['avg_ft_match_score_away']
df_main['shot_diff'] = df_main['avg_total_shots_home'] - df_main['avg_total_shots_away']
df_main['pass_diff'] = df_main['avg_successful_passes_home'] - df_main['avg_successful_passes_away']
df_main['corner_diff'] = df_main['avg_corners_home'] - df_main['avg_corners_away']
df_main['foul_diff'] = df_main['avg_fouls_home'] - df_main['avg_fouls_away']
df_main['yellow_card_diff'] = df_main['avg_yellow_cards_home'] - df_main['avg_yellow_cards_away']
df_main['red_card_diff'] = df_main['avg_red_cards_home'] - df_main['avg_red_cards_away']

# Data Preprocessing
X = df_main.drop(columns=['is_match_under_25', 'match_id'])  # Drop the target column
y = df_main['is_match_under_25']  # Define the target column
match_ids = df_main['match_id']  # Save match IDs for future use

# Split data into training and test sets (80% for training)
# test size should be max 100 matches based on percentage and ratio
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, shuffle=False, random_state=None)

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
    'Random Forest': RandomForestClassifier()
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

    max_capital = capital

    # Iterate through the test set predictions and actual values
    for match_id, y_t, y_p, uo, oo in zip(match_ids[X_test.index], y_test, y_pred, bookmaker_under_odds,
                                          bookmaker_over_odds):

        if match_id < 4000000:
            continue

        print(f"Match ID: {match_id}, Actual: {y_t}, Predicted: {y_p}, Under Odds: {uo}, Over Odds: {oo}")

        if y_p == 0 and y_t == 0:
            capital += capital * uo * bet_percentage
        elif y_p == 1 and y_t == 1:
            capital += capital * oo * bet_percentage
        else:
            capital -= capital * bet_percentage

        max_capital = capital if capital > max_capital else max_capital

        print(f'Current Capital: ${capital:.2f}')

    print(f'Final Capital after simulation with model {model_name}: ${capital:.2f}')
    print(f'Maximum Capital after simulation with model {model_name}: ${max_capital:.2f}')