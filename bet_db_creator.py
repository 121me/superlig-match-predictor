from season_crawler import get_season_stats
from smp_utils import avg_odds_rate, kelly

import aiohttp
import asyncio


SEASON_IDS = [
    67285, 64029, 61598, 59317, 57488, 54798,  # Bundesliga             2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    67180, 63837, 61588, 59267, 57528, 54669,  # English Premier League 2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    67601, 64266, 61791, 59467, 57709, 55515,  # Andorra Primera Divisió 2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
    67477, 64389, 61796, 59627, 58002, 55236,  # Albanian Superliga      2024-2025, 2023-2024, 2022-2023, 2021-2022, 2020-2021, 2019-2020
]


async def fetch_season_stats(session, season_ids):
    """Fetch statistics for a list of season IDs asynchronously."""
    tasks = [get_season_stats(session, season_id) for season_id in season_ids if season_id]
    return await asyncio.gather(*tasks)


def calculate_avg_odds(match_data):
    """Calculate average betting odds across all matches."""

    '''it should be 'bet_1', 'bet_2', and 'bet_x' instead of 'bet_home', 'bet_away', and 'bet_draw'
    total_odds = {"home": 0.0, "away": 0.0, "draw": 0.0}

    for match in match_data:
        for outcome in total_odds:
            total_odds[outcome] += float(match[f'bet_{outcome[0]}'])
    '''
    total_odds = {"home": 0.0, "away": 0.0, "draw": 0.0}
    match_count = 0

    for match in match_data:
        if not isinstance(match, dict):
            continue
        if match["response_code"] in [1, 3]:
            total_odds["home"] += float(match['bet_1'])
            total_odds["away"] += float(match['bet_2'])
            total_odds["draw"] += float(match['bet_x'])
            match_count += 1

    avg_odds = {key: total / match_count for key, total in total_odds.items()}
    return avg_odds, match_count


def categorize_kelly_indices(kelly_values):
    """Categorize matches based on Kelly indices."""
    count_above_1 = sum(k > 1 for k in kelly_values)

    if count_above_1 == 1:
        return "type_2"
    elif count_above_1 == 0:
        return "type_3"
    return "type_1"


def process_match(match, avg_odds, f99):
    """Calculate Kelly values for a match and return the results."""
    kelly_home = kelly(float(match['bet_1']), avg_odds['home'], f99)
    kelly_away = kelly(float(match['bet_2']), avg_odds['away'], f99)
    kelly_draw = kelly(float(match['bet_x']), avg_odds['draw'], f99)

    return {
        "kelly_home": kelly_home,
        "kelly_away": kelly_away,
        "kelly_draw": kelly_draw,
        "kelly_type": categorize_kelly_indices([kelly_home, kelly_away, kelly_draw])
    }


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        # Fetch all season stats
        season_stats = await fetch_season_stats(session, SEASON_IDS)

        # Flatten the matches across all seasons and weeks
        all_matches = [
            match for season in season_stats
            for week in season['weeks']
            for match in week if isinstance(match, dict)
        ]

        # Calculate average odds across all matches
        avg_odds, match_count = calculate_avg_odds(all_matches)
        print(f"Average odds: Home {avg_odds['home']:.5f}, Away {avg_odds['away']:.5f}, Draw {avg_odds['draw']:.5f}")

        f99 = avg_odds_rate(avg_odds['home'], avg_odds['away'], avg_odds['draw'])

        # Initialize counters and data holders
        kelly_type_count = {"type_1": 0, "type_2": 0, "type_3": 0}
        not_fav_type1_count = 0

        for match in all_matches:
            result = process_match(match, avg_odds, f99)
            kelly_type = result["kelly_type"]

            kelly_type_count[kelly_type] += 1

            # Track non-favorite type 1 matches
            if kelly_type == "type_1" and match['team_id_home'] not in [1, 2, 3, 4] and match['team_id_away'] not in [1, 2, 3, 4]:
                print(f"Match ID: {match['match_id']}")
                not_fav_type1_count += 1

        # Output results
        print(f"f99: {f99:.5f}")
        print(f"Kelly type 1 count: {kelly_type_count['type_1']}")
        print(f"Kelly type 2 count: {kelly_type_count['type_2']}")
        print(f"Kelly type 3 count: {kelly_type_count['type_3']}")
        print(f"Not favored type 1 count: {not_fav_type1_count}")
        print(f"Total matches: {match_count}")


if __name__ == "__main__":
    asyncio.run(main())
