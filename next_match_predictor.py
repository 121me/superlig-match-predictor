import asyncio
from typing import Any, Dict, List, Generator

import aiohttp
import json
import logging

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import f_classif, SelectKBest
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from smp_utils import fetch
from team_match_history_crawler import get_previous_matches_by_team
from match_crawler import get_match_stats

# Configure logging
logging.basicConfig(level=logging.INFO)

# 20.07.2022 is going to be until_date

# First Code - Data Collection
headers = ['avg_possession_rate_home', 'avg_total_shots_home', 'avg_shots_on_target_home', 'avg_successful_passes_home',
            'avg_pass_success_rate_home', 'avg_corners_home', 'avg_crosses_home', 'avg_fouls_home', 'avg_offsides_home', 'avg_yellow_cards_home',
            'avg_red_cards_home', 'avg_ft_match_score_home', 'avg_ht_match_score_home',
            'avg_possession_rate_away', 'avg_total_shots_away', 'avg_shots_on_target_away', 'avg_successful_passes_away',
            'avg_pass_success_rate_away', 'avg_corners_away', 'avg_crosses_away', 'avg_fouls_away', 'avg_offsides_away', 'avg_yellow_cards_away',
            'avg_red_cards_away', 'avg_ft_match_score_away', 'avg_ht_match_score_away', "match_id", "bet_under_25_odd_rate", "bet_over_25_odd_rate", "is_match_under_25"]

avg_keys = ["possession_rate_home", "total_shots_home", "shots_on_target_home", "successful_passes_home",
            "pass_success_rate_home", "corners_home", "crosses_home", "fouls_home", "offsides_home", "yellow_cards_home",
            "red_cards_home", "ft_match_score_home", "ht_match_score_home",
            "possession_rate_away", "total_shots_away", "shots_on_target_away", "successful_passes_away",
            "pass_success_rate_away", "corners_away", "crosses_away", "fouls_away", "offsides_away", "yellow_cards_away",
            "red_cards_away", "ft_match_score_away", "ht_match_score_away"]

avg_keys_raw = ["possession_rate", "total_shots", "shots_on_target", "successful_passes",
                "pass_success_rate", "corners", "crosses", "fouls", "offsides", "yellow_cards",
                "red_cards", "ft_match_score", "ht_match_score"]

keys_to_swap_raw = ["team_id", "team_name", "ht_match_score", "ft_match_score", "possession_rate", "total_shots",
                    "shots_on_target", "successful_passes", "pass_success_rate", "corners", "crosses", "fouls",
                    "offsides", "yellow_cards", "red_cards", "prev_5_match_ids"]

other_keys = ["match_id", "bet_under_25", "bet_over_25",]

SEASON_IDS = [
    #'67180', # Premier League
    #'67285', # Bundesliga
    #'67194', # La Liga
    #'67286', # Serie A
    #'67238', # Ligue 1
    #'67106', # Pro League
    #'67206', # Super League
    #'67345', # Primeira Liga
    #'67204', # Eredivisie
    #'67287', # Super Lig
    '67892', # UEFA Championship League
    #'67909', # UEFA Europa League
    #'67940', # UEFA Conference League
]

UNTIL_DATE = '24.07.2023'


async def get_next_match_ids_by_league(session: aiohttp.ClientSession, season_id: str) -> Generator[
                                                                                              Any, Any, None] | None:
    """
    Predicts the very next matches for a given league season.

    Args:
        session: The aiohttp session to use for the request.
        season_id: The ID of the season to retrieve stats for.
    Returns:
        A dictionary containing the over-under predictions for the very next matches in the league.
    """
    try:
        # Fetch season details from Mackolik API
        response_season_details = await fetch(
            session,
            f"https://arsiv.mackolik.com/AjaxHandlers/StandingHandler.ashx?op=standing&id={season_id}"
        )
        season_details = json.loads(response_season_details)
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON response for season details of season {season_id}")
        return None

    return (i[0] for i in season_details['f'])

async def calculate_averages(session: aiohttp.ClientSession, match_id: str, is_future: bool) -> List[float] | None:
    full_match_stats = await get_match_stats(session, match_id)

    if is_future:
        pass
    elif full_match_stats['response_code'] == 3:  # the bet stats are not available
        print(f"Skipping match {match_id} due to missing bet stats")
        return None

    home_team_id = full_match_stats['team_id_home']
    away_team_id = full_match_stats['team_id_away']

    prev_5_match_ids_home = full_match_stats['prev_5_match_ids_home'].split('l')
    prev_5_match_ids_away = full_match_stats['prev_5_match_ids_away'].split('l')

    tasks_prev_5_matches_home = [get_match_stats(session, i) for i in prev_5_match_ids_home]
    tasks_prev_5_matches_away = [get_match_stats(session, i) for i in prev_5_match_ids_away]

    prev_5_matches_home = await asyncio.gather(*tasks_prev_5_matches_home)
    prev_5_matches_away = await asyncio.gather(*tasks_prev_5_matches_away)

    # Remove the match from the list if the response code is 0, 2, 4
    prev_5_matches_home = [m for m in prev_5_matches_home if int(m['response_code']) in ([1, 3] if is_future else [1,])]
    prev_5_matches_away = [m for m in prev_5_matches_away if int(m['response_code']) in ([1, 3] if is_future else [1,])]

    # If there are 2 or fewer matches, skip this match
    if len(prev_5_matches_home) <= 1 or len(prev_5_matches_away) <= 1:
        print(f"Skipping match {match_id} due to insufficient previous matches")
        return None

    # Swap the home and away team data and stats
    for m in prev_5_matches_home:
        if str(m['team_id_away']) == home_team_id:
            for key in keys_to_swap_raw:
                try:
                    m[key + "_home"], m[key + "_away"] = m[key + "_away"], m[key + "_home"]
                except KeyError:
                    pass

    for m in prev_5_matches_away:
        if str(m['team_id_home']) == away_team_id:
            for key in keys_to_swap_raw:
                try:
                    m[key + "_home"], m[key + "_away"] = m[key + "_away"], m[key + "_home"]
                except KeyError:
                    pass

    try:
        home_averages = [
            round(sum([float(m.get(key + "_home", 0)) for m in prev_5_matches_home if key + "_home" in m]) / len(
                prev_5_matches_home), 2)
            for key in avg_keys_raw
        ]

        away_averages = [
            round(sum([float(m.get(key + "_away", 0)) for m in prev_5_matches_away if key + "_away" in m]) / len(
                prev_5_matches_away), 2)
            for key in avg_keys_raw
        ]
    except Exception as e:
        logging.error(f"Error: {e}")
        print(f"Skipping match {match_id} due to calculating previous match averages")
        return None

    line = home_averages + away_averages + [full_match_stats[key] for key in other_keys]
    line += [0] if int(full_match_stats["ft_match_score_home"]) + int(
        full_match_stats["ft_match_score_away"]) < 2.5 else [1]

    return line


async def main():
    async with aiohttp.ClientSession() as session:
        tasks_next_match_ids_by_league = [get_next_match_ids_by_league(session, season_id) for season_id in SEASON_IDS]
        next_match_ids_by_league = await asyncio.gather(*tasks_next_match_ids_by_league)

        tasks_match_stats = [get_match_stats(session, match_id) for next_match_ids_of_the_league in next_match_ids_by_league for match_id in next_match_ids_of_the_league]
        future_match_stats = await asyncio.gather(*tasks_match_stats)

        # sort match stats by match_id
        future_match_stats.sort(key=lambda x: x['match_id'], reverse=True)

        # let the team_ids be unique
        team_ids = list(set(team_id for fms in future_match_stats for team_id in (fms['team_id_home'], fms['team_id_away'])))

        tasks_previous_matches_by_team = [get_previous_matches_by_team(session, team_id, UNTIL_DATE) for team_id in team_ids]
        previous_matches_by_teams = await asyncio.gather(*tasks_previous_matches_by_team)

        data_averages_all = {ti: await asyncio.gather(*(calculate_averages(session, pms['match_id'], False) for pms in pmbt)) for pmbt, ti in zip(previous_matches_by_teams, team_ids)}

        # filter out the None values
        data_averages_all = {k: [i for i in v if i] for k, v in data_averages_all.items()}
        data_averages_all = {k: v for k, v in data_averages_all.items() if v}

        for future_match in future_match_stats:
            # calculate the averages
            future_match_averages = await calculate_averages(session, future_match['match_id'], True)

            if not future_match_averages:
                print(f"Skipping match {future_match['match_id']} due to insufficient data")
                continue # TODO: handle this case, BUG: future_match_averages is sometimes None

            # home and away team ids
            home_team_id = future_match['team_id_home']
            away_team_id = future_match['team_id_away']

            # get the averages of the home and away teams
            try:
                home_team_averages = data_averages_all[home_team_id]
            except KeyError:
                print(f"Skipping match {future_match['match_id']} due to missing home key {home_team_id}")
                continue

            try:
                away_team_averages = data_averages_all[away_team_id]
            except KeyError:
                print(f"Skipping match {future_match['match_id']} due to missing away key {away_team_id}")
                continue

            main_data = home_team_averages + away_team_averages + [future_match_averages,]

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

            # Split data into training and test sets (90% for training)
            # test size should be max 100 matches based on percentage and ratio
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, shuffle=False, random_state=None)

            # Standardize the data
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            '''
            # Feature Selection using ANOVA F-test
            selector = SelectKBest(f_classif, k=5)
            X_train_selected = selector.fit_transform(X_train_scaled, y_train)
            X_test_selected = selector.transform(X_test_scaled)
            '''

            X_train_selected = X_train_scaled
            X_test_selected = X_test_scaled

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
                reset_bet_every_n_match = 8  # Reset the bet after n matches

                bet_per_match = (capital * bet_percentage) // reset_bet_every_n_match

                max_capital = capital
                n = 0

                # Predict probabilities to get the confidence
                y_pred_proba = model.predict_proba(X_test_selected)

                # Iterate through the test set predictions and actual values
                for n, others in enumerate(zip(match_ids[X_test.index], y_test, y_pred, y_pred_proba,
                                               bookmaker_under_odds, bookmaker_over_odds)):

                    match_id, y_t, y_p, y_p_proba, uo, oo = others

                    if n % reset_bet_every_n_match == 0:
                        bet_per_match = (capital * bet_percentage) // reset_bet_every_n_match

                    # Get confidence for the prediction
                    confidence = y_p_proba.max()

                    if y_p == 0 and y_t == 0:
                        capital += bet_per_match * uo
                    elif y_p == 1 and y_t == 1:
                        capital += bet_per_match * oo
                    else:
                        capital -= bet_per_match

                    max_capital = capital if capital > max_capital else max_capital

                    print(f"Match ID: {match_id}, Actual: {y_t}, Predicted: {y_p}, "
                          f"Confidence: {confidence:.2f}, Under Odds: {uo}, Over Odds: {oo}")
                    print(f'Current Capital: ${capital:.2f}')

                print(f'Final Capital after simulation with model {model_name} in {n} matches: ${capital:.2f}')
                print(f'Maximum Capital after simulation with model {model_name} in {n} matches: ${max_capital:.2f}')

            pass

if __name__ == '__main__':
    asyncio.run(main())
