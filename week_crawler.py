from bs4 import BeautifulSoup
import requests
import json

from match_crawler import get_match_stats


def get_week_stats(season_id: str, week_index: str):
    """
    Extracts weekly match stats from the Mackolik website for a given match ID.

    Args:
        season_id: The ID of the season to retrieve stats for.
        week_index: The index of the week to retrieve stats for.

    """

    # Retrieve week details from the JSON endpoint
    response_week_details = requests.get(
        f"https://arsiv.mackolik.com/Standings/Data/WeeklyStandingData.aspx?seas={season_id}&hft={week_index}"
    )
    response_week_details.raise_for_status()  # Raise an error if request fails
    week_details = json.loads(response_week_details.content)["d"]

    return [
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
            # add get_match_stats
            **get_match_stats(match[0])
        } for match in week_details]


if __name__ == "__main__":
    # Example usage
    example_season_id = "59416"
    example_week_index = "1"
    week_stats = get_week_stats(example_season_id, example_week_index)

    for n, m in enumerate(week_stats):
        print("Match:", n)
        for k, v in m.items():
            print(f"{k}: {v}")
        print("-----------------------------")
