import asyncio

import aiohttp
import json

from match_crawler import get_match_stats
from smp_utils import fetch, mackolik_db


async def get_week_stats(session, season_id: str, week_index: str) -> list[dict[str, str]]:
    """
    Extracts weekly match stats from the Mackolik website for a given match ID.

    Args:
        session: The aiohttp session to use for the request.
        season_id: The ID of the season to retrieve stats for.
        week_index: The index of the week to retrieve stats for.

    Returns:
        A list of dictionaries containing the stats for each match in the week.
    """

    if mackolik_db.check_week(season_id, week_index):
        week_details = mackolik_db.get_week(season_id, week_index)
        matches = mackolik_db.get_matches_sw(season_id, week_index)

        if len(matches) != week_details['match_count']:
            mackolik_db.delete_week(season_id, week_index)
            raise ValueError("Mismatch between match count in database and week details, please re-run the crawler.")

        return matches

    else:
        # Retrieve week details from the JSON endpoint
        response_week_details = await fetch(
            session,
            f"https://arsiv.mackolik.com/Standings/Data/WeeklyStandingData.aspx?seas={season_id}&hft={week_index}"
        )
        week_details = json.loads(str(response_week_details))["d"]

        tasks = [get_match_stats(session, match[0]) for match in week_details]
        match_stats = await asyncio.gather(*tasks)

        match_indices = range(len(week_details))

        output = [
            {
                'match_id': match[0],
                'team_id_home': match[3],
                'team_id_away': match[4],
                'team_goals_home': match[6],
                'team_goals_away': match[7],
                'bet_1': match[10],
                'bet_x': match[11],
                'bet_2': match[12],
                'bet_1x': match[13],
                'bet_12': match[14],
                'bet_x2': match[15],
                'bet_under_25': match[16],
                'bet_over_25': match[17],
                'match_index': n,
                'week_index': week_index,
                'season_id': season_id,
                **stats
            }
            for match, stats, n in zip(week_details, match_stats, match_indices)
        ]

        for match in output:
            if not mackolik_db.check_match(match['match_id']):
                mackolik_db.add_match(match)
            if not mackolik_db.check_team(match['team_id_home']):
                mackolik_db.add_team({
                    'team_id': match['team_id_home'],
                    'team_name': match['team_name_home'],
                    'team_power': '0'
                })
            if not mackolik_db.check_team(match['team_id_away']):
                mackolik_db.add_team({
                    'team_id': match['team_id_away'],
                    'team_name': match['team_name_away'],
                    'team_power': '0'
                })

        if not mackolik_db.check_week(week_index, season_id):
            mackolik_db.add_week({
                'week_index': week_index,
                'season_id': season_id,
                'match_count': len(output)
            })

        return output


async def main():
    example_season_id = "59416"
    example_week_index = "16"

    async with aiohttp.ClientSession() as session:
        week_stats = await get_week_stats(session, example_season_id, example_week_index)
        for n, m in enumerate(week_stats):
            print("Match:", n)
            for k, v in m.items():
                print(f"{k}: {v}")
            print("-----------------------------")


if __name__ == "__main__":
    asyncio.run(main())
