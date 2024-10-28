import asyncio

import aiohttp
from bs4 import BeautifulSoup
import json
from json_repair import repair_json

from smp_utils import fetch, mackolik_db
from datetime import datetime

current_datetime = datetime.now()

async def fetch_match_json(session, match_id: str) -> dict:
    """Fetch and repair JSON match data from the Mackolik website."""
    response = await fetch(session, f"https://arsiv.mackolik.com/Match/MatchData.aspx?t=dtl&id={match_id}")
    repaired_json = repair_json(str(response))
    return json.loads(repaired_json)


async def fetch_match_html(session, match_id: str) -> BeautifulSoup:
    """Fetch and parse the HTML match data from the Mackolik website."""
    response = await fetch(session, f"https://arsiv.mackolik.com/Match/Default.aspx?id={match_id}")
    return BeautifulSoup(str(response), "html.parser")


async def fetch_bet_json(session, match_id):
    # https://arsiv.mackolik.com/AjaxHandlers/IddaaHandler.aspx?command=morebets&mac=3562667
    response = await fetch(session, f"https://arsiv.mackolik.com/AjaxHandlers/IddaaHandler.aspx?command=morebets&mac={match_id}")
    repaired_json = repair_json(str(response))
    return json.loads(repaired_json)


def parse_match_events(events: list) -> tuple[dict, dict]:
    """Extract yellow and red card statistics from match events."""
    yellow_cards = {1: 0, 2: 0}
    red_cards = {1: 0, 2: 0}

    for event in events:
        team = event[0]
        event_type = event[4]

        if event_type == 2:
            yellow_cards[team] += 1
        elif event_type == 3:
            red_cards[team] += 1
            if event[5]["d"] == 1:  # Second yellow card
                yellow_cards[team] += 1

    return yellow_cards, red_cards


def extract_match_stats(lines: list, home_team_name: str, away_team_name: str, ht_score: str, ft_score: str) -> list:
    """Extract and format match statistics from the HTML content."""
    stats = [
        ("Teams", home_team_name, away_team_name),
        ("Half-time Score", *ht_score.split(" - ")),
        ("Full-time Score", *ft_score.split(" - "))
    ]
    # Add more stats from the lines list (each stat is divided into 3 parts: label, home, away)
    stats += list(zip(lines[1::3], lines[0::3], lines[2::3]))

    return stats


def format_match_date(soup: BeautifulSoup) -> list[str]:
    """Extract and format the match date."""
    try:
        match_date, match_time = soup.select_one(".match-info-date").text.split(" : ")[1].split(" ")
        match_date = match_date.split(".")
        match_time = match_time.split(":")
    except AttributeError:
        match_date = ["1", "1", "1900"]
        match_time = ["23", "59"]
    return match_date + match_time


def extract_bets(bet_details, bet_type):
    bet_types = [bt for bt in bet_details['Event']['Markets']]
    for bt in bet_types:
        if bet_type in bt['MarketType'].values():
            return [b['Odd'] for b in bt['Outcomes']]
    return [1, 1]


async def get_match_stats(session, match_id: str|int) -> dict[str, str]:
    """Extracts all match stats from the Mackolik website for a given match ID."""
    print(f"Getting match {match_id}")

    if not match_id:
        return {
            'match_id': match_id,
            'team_id_home': 0,
            'team_id_away': 0,
            'bet_under_25': 1,
            'bet_over_25': 1,
            'team_name_home': "Unknown",
            'team_name_away': "Unknown",
            'ht_match_score_home': 0,
            'ht_match_score_away': 0,
            'ft_match_score_home': 0,
            'ft_match_score_away': 0,
            'possession_rate_home': 0,
            'possession_rate_away': 0,
            'total_shots_home': 0,
            'total_shots_away': 0,
            'shots_on_target_home': 0,
            'shots_on_target_away': 0,
            'successful_passes_home': 0,
            'successful_passes_away': 0,
            'pass_success_rate_home': 0,
            'pass_success_rate_away': 0,
            'corners_home': 0,
            'corners_away': 0,
            'crosses_home': 0,
            'crosses_away': 0,
            'fouls_home': 0,
            'fouls_away': 0,
            'offsides_home': 0,
            'offsides_away': 0,
            'yellow_cards_home': 0,
            'yellow_cards_away': 0,
            'red_cards_home': 0,
            'red_cards_away': 0,
            'match_year': 0,
            'match_month': 0,
            'match_day': 0,
            'match_hour': 0,
            'match_minute': 0,
            'prev_5_match_ids_home': "0l0l0l0", # l is the separator, like in the 'lake' word
            'prev_5_match_ids_away': "0l0l0l0", # l is the separator, like in the 'lake' word
            'response_code': 0,
        }

    if mackolik_db.check_match(match_id):
        print(f"Match {match_id} already exists in the database")
        return mackolik_db.get_match(match_id)

    response_code = 1

    try:
        match_details = await fetch_match_json(session, match_id)
        soup = await fetch_match_html(session, match_id)
        bet_details = await fetch_bet_json(session, match_id)
    except Exception as e:
        print(f"Error fetching match {match_id}: {e}")
        return {
            'match_id': match_id,
            'team_id_home': 0,
            'team_id_away': 0,
            'bet_under_25': 1,
            'bet_over_25': 1,
            'team_name_home': "Unknown",
            'team_name_away': "Unknown",
            'ht_match_score_home': 0,
            'ht_match_score_away': 0,
            'ft_match_score_home': 0,
            'ft_match_score_away': 0,
            'possession_rate_home': 0,
            'possession_rate_away': 0,
            'total_shots_home': 0,
            'total_shots_away': 0,
            'shots_on_target_home': 0,
            'shots_on_target_away': 0,
            'successful_passes_home': 0,
            'successful_passes_away': 0,
            'pass_success_rate_home': 0,
            'pass_success_rate_away': 0,
            'corners_home': 0,
            'corners_away': 0,
            'crosses_home': 0,
            'crosses_away': 0,
            'fouls_home': 0,
            'fouls_away': 0,
            'offsides_home': 0,
            'offsides_away': 0,
            'yellow_cards_home': 0,
            'yellow_cards_away': 0,
            'red_cards_home': 0,
            'red_cards_away': 0,
            'match_year': 0,
            'match_month': 0,
            'match_day': 0,
            'match_hour': 0,
            'match_minute': 0,
            'prev_5_match_ids_home': "0l0l0l0", # l is the separator, like in the 'lake' word
            'prev_5_match_ids_away': "0l0l0l0", # l is the separator, like in the 'lake' word
            'response_code': 0,
        }

    match_date = format_match_date(soup)

    try:
        home_team_name = match_details["home"]
        away_team_name = match_details["away"]
    except Exception as e:
        print(f"Error fetching team names for match {match_id}: {e}")
        home_team_name = "Unknown"
        away_team_name = "Unknown"
        pass

    is_future = (current_datetime <
                 datetime(*map(int, [match_date[2], match_date[1], match_date[0], match_date[3], match_date[4]]))
                )

    # Extract bet types or use default values in case of error
    try:
        bet_under_25, bet_over_25 = extract_bets(bet_details, "2,5 Alt/Üst")
    except (ValueError, TypeError):
        bet_under_25, bet_over_25 = 1, 1
        response_code = 3

    team_id_home = int(soup.find("a", {"class": "left-block-team-name"})["href"].split("/")[-2])
    team_id_away = int(soup.find("a", {"class": "r-left-block-team-name"})["href"].split("/")[-2])

    season_id = int(soup.find("div", {"class": "match-info-wrapper-season"}).find("a")["href"].split("=")[-1].split("/")[0])

    prev_5_match_ids_home = [e['onclick'].split("(")[1].split(")")[0] for e in soup.find("div", {"class": "last-games-temp"}).find_all("div", {"class": "last-games"})]
    prev_5_match_ids_away = [e['onclick'].split("(")[1].split(")")[0] for e in soup.find("div", {"class": "r-last-games-temp"}).find_all("div", {"class": "last-games"})]

    if is_future:
        return {
            'match_id': match_id,
            'team_id_home': team_id_home,
            'team_id_away': team_id_away,
            'bet_under_25': bet_under_25,
            'bet_over_25': bet_over_25,
            'team_name_home': home_team_name,
            'team_name_away': away_team_name,
            'ht_match_score_home': 0,
            'ht_match_score_away': 0,
            'ft_match_score_home': 0,
            'ft_match_score_away': 0,
            'possession_rate_home': 0,
            'possession_rate_away': 0,
            'total_shots_home': 0,
            'total_shots_away': 0,
            'shots_on_target_home': 0,
            'shots_on_target_away': 0,
            'successful_passes_home': 0,
            'successful_passes_away': 0,
            'pass_success_rate_home': 0,
            'pass_success_rate_away': 0,
            'corners_home': 0,
            'corners_away': 0,
            'crosses_home': 0,
            'crosses_away': 0,
            'fouls_home': 0,
            'fouls_away': 0,
            'offsides_home': 0,
            'offsides_away': 0,
            'yellow_cards_home': 0,
            'yellow_cards_away': 0,
            'red_cards_home': 0,
            'red_cards_away': 0,
            'match_year': match_date[2],
            'match_month': match_date[1],
            'match_day': match_date[0],
            'match_hour': match_date[3],
            'match_minute': match_date[4],
            'prev_5_match_ids_home': 'l'.join(prev_5_match_ids_home),
            'prev_5_match_ids_away': 'l'.join(prev_5_match_ids_away),
            'response_code': 2,
        }

    ht_match_score = match_details["d"]["ht"]
    ft_match_score = match_details["d"]["s"]

    yellow_cards, red_cards = parse_match_events(match_details["e"])

    # Extract stats from HTML content or use default values in case of error
    try:
        match_analysis = soup.select_one("#dvOPTAStats > div:nth-child(2)").text
        lines = [line.strip() for line in match_analysis.splitlines() if line.strip()]
    except AttributeError:
        lines = ["%50", "Topla Oynama", "%50", "0", "Toplam Şut", "0", "0", "İsabetli Şut", "0", "0", "Başarılı Paslar", "0", "%0", "Pas Başarı(%)", "%0", "0", "Korner", "0", "0/0", "Orta", "0/0", "0", "Faul", "0", "0", "Ofsayt", "0"]
        response_code = 3

    if len(lines) % 3 != 0:
        raise ValueError("Unexpected number of lines in match stats, bug in parsing")

    stats = extract_match_stats(lines, home_team_name, away_team_name, ht_match_score, ft_match_score)
    # If the ft_match_score is ['v', 'P - P'] or empty string, set it to 0 - 0
    if not ft_match_score or ft_match_score in ['v', 'P - P']:
        stats[2] = ("Full-time Score", "0", "0")
        response_code = 4

    if not ht_match_score or ht_match_score in ['v', 'P - P']:
        stats[1] = ("Half-time Score", "0", "0")
        response_code = 4

    print(f"Returning match {match_id}")

    output = {
        'match_id': match_id,
        'team_id_home': team_id_home,
        'team_id_away': team_id_away,
        'bet_under_25': bet_under_25,
        'bet_over_25': bet_over_25,
        'team_name_home': home_team_name,
        'team_name_away': away_team_name,
        'ht_match_score_home': stats[1][1],
        'ht_match_score_away': stats[1][2],
        'ft_match_score_home': stats[2][1],
        'ft_match_score_away': stats[2][2],
        'possession_rate_home': stats[3][1][1:],  # remove '%' sign
        'possession_rate_away': stats[3][2][1:],  # remove '%' sign
        'total_shots_home': stats[4][1],
        'total_shots_away': stats[4][2],
        'shots_on_target_home': stats[5][1],
        'shots_on_target_away': stats[5][2],
        'successful_passes_home': stats[6][1],
        'successful_passes_away': stats[6][2],
        'pass_success_rate_home': float(stats[7][1][1:]) / 100,  # convert percentage to float
        'pass_success_rate_away': float(stats[7][2][1:]) / 100,  # convert percentage to float
        'corners_home': stats[8][1],
        'corners_away': stats[8][2],
        'crosses_home': stats[9][1].split("/")[0],
        'crosses_away': stats[9][2].split("/")[0],
        'fouls_home': stats[10][1],
        'fouls_away': stats[10][2],
        'offsides_home': stats[11][1],
        'offsides_away': stats[11][2],
        'yellow_cards_home': yellow_cards[1],
        'yellow_cards_away': yellow_cards[2],
        'red_cards_home': red_cards[1],
        'red_cards_away': red_cards[2],
        'match_year': match_date[2],
        'match_month': match_date[1],
        'match_day': match_date[0],
        'match_hour': match_date[3],
        'match_minute': match_date[4],
        'prev_5_match_ids_home': 'l'.join(prev_5_match_ids_home),
        'prev_5_match_ids_away': 'l'.join(prev_5_match_ids_away),
        'response_code': response_code,
    }

    if not mackolik_db.check_match(match_id):
        mackolik_db.add_match(output)

    return output


async def main() -> None:
    example_match_id = '4182766'
    async with aiohttp.ClientSession() as session:

        match_stats_v2 = await get_match_stats(session, example_match_id)
        print("match_stats_v2:")
        for k, v in match_stats_v2.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
