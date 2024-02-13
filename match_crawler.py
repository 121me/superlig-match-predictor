import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from json_repair import repair_json


async def get_match_stats(session, match_id: str) -> dict:
    """
    Extracts match stats from the Mackolik website for a given match ID.

    Args:
        session: The aiohttp session to use for the request.
        match_id: The ID of the match to retrieve stats for.

    Returns:
        A dictionary containing the match stats.
    """

    print(f"Getting match {match_id}")

    # Retrieve match details from the JSON endpoint
    async with session.get(f"https://arsiv.mackolik.com/Match/MatchData.aspx?t=dtl&id={match_id}") as response:
        response.raise_for_status()  # Raise an error if request fails
        good_json = repair_json(await response.text())
        match_details = json.loads(good_json)

    # Retrieve detailed analyses from the HTML endpoint
    async with session.get(f"https://arsiv.mackolik.com/Match/Default.aspx?id={match_id}") as response:
        response.raise_for_status()  # Raise an error if request fails
        soup = BeautifulSoup(await response.text(), "html.parser")

    # Extract team names from the JSON data
    home_team_name = match_details["home"]
    away_team_name = match_details["away"]

    # Extract match scores from the JSON data
    ht_match_score = match_details["d"]["ht"]
    ft_match_score = match_details["d"]["s"]

    yellow_cards = {
        1: 0,
        2: 0,
    }

    red_cards = {
        1: 0,
        2: 0,
    }

    # Search event data
    for e in match_details["e"]:
        # e[0] is for: 1 = home team, 2 = away team
        team = e[0]
        # e[4] is the event
        # e[4] == 2 is for yellow card
        if e[4] == 2:
            yellow_cards[team] += 1

        # e[4] == 3 is for red card
        elif e[4] == 3:
            red_cards[team] += 1
            # and if e[5]["d"] == 1 is for second yellow card
            if e[5]["d"] == 1:
                yellow_cards[team] += 1

    # Parse match stats from the HTML content
    match_analysis = soup.select_one("#dvOPTAStats > div:nth-child(2)").text
    lines = [line.strip() for line in match_analysis.splitlines() if line.strip()]

    # Validate the structure of the extracted lines
    if len(lines) % 3 != 0:
        raise ValueError("Unexpected number of lines in match stats")

    # Organize stats into a list of tuples
    stats = [
        ("Teams", home_team_name, away_team_name),
        ("Half-time Score", *ht_match_score.split(" - ")),
        ("Full-time Score", *ft_match_score.split(" - ")),
    ]
    stats += list(zip(lines[1::3], lines[0::3], lines[2::3]))

    # stats output
    # Teams, Kayserispor, Fenerbahçe
    # Half-time Score, 1, 2
    # Full-time Score, 3, 4
    # Topla Oynama, %51, %49
    # Toplam Şut, 14, 13
    # İsabetli Şut, 6, 6
    # Başarılı Paslar, 272, 269
    # Pas Başarı(%), %72, %74
    # Korner, 5, 3
    # Orta, 4/18, 2/12
    # Faul, 22, 11
    # Ofsayt, 2, 1

    print(f"Returning match {match_id}")

    return {
        "team_name_home": home_team_name,
        "team_name_away": away_team_name,
        "ht_match_score_home": stats[1][1],
        "ht_match_score_away": stats[1][2],
        "ft_match_score_home": stats[2][1],
        "ft_match_score_away": stats[2][2],
        "possession_home": stats[3][1],
        "possession_away": stats[3][2],
        "total_shots_home": stats[4][1],
        "total_shots_away": stats[4][2],
        "shots_on_target_home": stats[5][1],
        "shots_on_target_away": stats[5][2],
        "successful_passes_home": stats[6][1],
        "successful_passes_away": stats[6][2],
        "pass_success_rate_home": stats[7][1],
        "pass_success_rate_away": stats[7][2],
        "corners_home": stats[8][1],
        "corners_away": stats[8][2],
        "crosses_home": stats[9][1],
        "crosses_away": stats[9][2],
        "fouls_home": stats[10][1],
        "fouls_away": stats[10][2],
        "offsides_home": stats[11][1],
        "offsides_away": stats[11][2],
        "yellow_cards_home": yellow_cards[1],
        "yellow_cards_away": yellow_cards[2],
        "red_cards_home": red_cards[1],
        "red_cards_away": red_cards[2],
    }


async def main() -> None:
    # Example usage
    example_match_id = "3870958"

    async with aiohttp.ClientSession() as session:
        match_stats = await get_match_stats(session, example_match_id)
        for k, v in match_stats.items():
            print(f"{k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())
