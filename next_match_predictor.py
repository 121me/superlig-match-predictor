import asyncio
from typing import Any, Dict

import aiohttp
import json
import logging

from smp_utils import fetch
from team_match_history_crawler import get_pvn_matches_by_team
from match_crawler import get_match_stats_v2

# Configure logging
logging.basicConfig(level=logging.INFO)

# 20.07.2022 is going to be until_date

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

async def predict_next_matches_by_league(session: aiohttp.ClientSession, season_id: str, until_date: str = '1.01.2024') -> Dict[str, Any]:
    """
    Predicts the very next matches for a given league season.

    Args:
        session: The aiohttp session to use for the request.
        season_id: The ID of the season to retrieve stats for.
        until_date: The date to stop fetching matches at.

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
        return {}

    to_be_predicted_match_ids = [i[0] for i in season_details['f']]

    for match_id in to_be_predicted_match_ids:
        main_data = []

        to_be_predicted_match = await get_match_stats_v2(session, match_id)

        home_team_id = to_be_predicted_match['team_id_home']
        away_team_id = to_be_predicted_match['team_id_away']

        home_team_prev_match_details = await get_pvn_matches_by_team(session, home_team_id, until_date)
        away_team_prev_match_details = await get_pvn_matches_by_team(session, away_team_id, until_date)

        # Process each match and calculate the averages of previous 5 matches
        for side in [home_team_prev_match_details, away_team_prev_match_details]:
            for match in side:
                mid = match['match_id']
                m_details = await get_match_stats_v2(session, mid)

                # instead, create coroutines to avoid 'RuntimeError: cannot reuse already awaited coroutine'
                tasks_home = [get_match_stats_v2(session, i) for i in m_details['prev_5_match_ids_home'].split("l")]
                tasks_away = [get_match_stats_v2(session, i) for i in m_details['prev_5_match_ids_away'].split("l")]

                previous_5_match_stats_home = await asyncio.gather(*tasks_home)
                previous_5_match_stats_away = await asyncio.gather(*tasks_away)

                stats_to_be_averaged_home = []
                stats_to_be_averaged_away = []

                for m in previous_5_match_stats_home:
                    # swap the home and away team data and stats
                    if m["team_id_away"] == m_details["team_id_home"]:
                        for key in avg_keys_raw:
                            m[key + "_home"], m[key + "_away"] = m[key + "_away"], m[key + "_home"]

                        stats_to_be_averaged_home.append([m[key] for key in avg_keys])


                for m in previous_5_match_stats_away:
                    # swap the home and away team data and stats
                    if m["team_id_home"] == m_details["team_id_away"]:
                        for key in avg_keys_raw:
                            m[key + "_home"], m[key + "_away"] = m[key + "_away"], m[key + "_home"]
                            stats_to_be_averaged_away.append(m)

                        stats_to_be_averaged_away.append([m[key] for key in avg_keys])

                home_averages = [round(sum([m[key + "_home"] for m in stats_to_be_averaged_home]) / len(stats_to_be_averaged_home), 2) for key in avg_keys_raw]
                away_averages = [round(sum([m[key + "_away"] for m in stats_to_be_averaged_away]) / len(stats_to_be_averaged_away), 2) for key in avg_keys_raw]

                line = home_averages + away_averages + [m_details[key] for key in other_keys]
                line += [0] if m_details["ft_match_score_home"] + m_details["ft_match_score_away"] < 2.5 else [1]

                # Add match date to sort the main data by
                # match contains "match_year", "match_month", "match_day", "match_hour", "match_minute"
                # format it into 2022.07.20.20.00
                # all of them are integers so we can directly concatenate them
                # make it like yyyy.mm.dd.hh.mm
                # if any of them is less than 10, add a 0 before it
                match_date = f"{m_details['match_year']:04}.{m_details['match_month']:02}.{m_details['match_day']:02}.{m_details['match_hour']:02}.{m_details['match_minute']:02}"
                line.append(match_date)

                # Append this match's data to the main dataset
                main_data.append(line)

        # Sort the main data by match date
        main_data.sort(key=lambda x: x[-1])

        print(main_data)


async def main():
    async with aiohttp.ClientSession() as session:
        await predict_next_matches_by_league(session, '67287', '20.07.2022')


if __name__ == '__main__':
    asyncio.run(main())
