import asyncio

import aiohttp
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

from bet_db_creator import fetch_season_stats

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

SEASON_IDS = [
    63837
]

# Placeholder for the main data
main_data = []

async def main() -> None:
    async with aiohttp.ClientSession() as session:
        season_stats = await fetch_season_stats(session, SEASON_IDS)

    full_matches = [
        match for season in season_stats
        for week in season['weeks']
        for match in week if isinstance(match, dict)
        if match['response_code'] == 1
    ]

    # Process each match and calculate the averages of previous 5 matches
    for match in full_matches:

        home_team_prev_n_matches = []
        away_team_prev_n_matches = []

        for m in full_matches:
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
    selector = SelectKBest(f_classif, k=5)
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

        capital = 5000  # Starting capital
        bet_percentage = 0.4  # Percentage of capital to bet
        reset_bet_every_n_match = 8 # Reset the bet after n matches

        bet_per_match = (capital * bet_percentage) // reset_bet_every_n_match

        max_capital = capital
        n = 0

        # Iterate through the test set predictions and actual values
        for n, others in enumerate(zip(match_ids[X_test.index], y_test, y_pred, bookmaker_under_odds,
                                              bookmaker_over_odds)):

            match_id, y_t, y_p, uo, oo = others

            if n % reset_bet_every_n_match == 0:
                bet_per_match = (capital * bet_percentage) // reset_bet_every_n_match

            if y_p == 0 and y_t == 0:
                capital += bet_per_match * uo
            elif y_p == 1 and y_t == 1:
                capital += bet_per_match * oo
            else:
                capital -= bet_per_match

            max_capital = capital if capital > max_capital else max_capital

            # print(f"Match ID: {match_id}, Actual: {y_t}, Predicted: {y_p}, Under Odds: {uo}, Over Odds: {oo}")
            # print(f'Current Capital: ${capital:.2f}')

        print(f'Final Capital after simulation with model {model_name} in {n} matches: ${capital:.2f}')
        print(f'Maximum Capital after simulation with model {model_name} in {n} matches: ${max_capital:.2f}')

if __name__ == "__main__":
    asyncio.run(main())