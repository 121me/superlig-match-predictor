import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from json_repair import repair_json
from datetime import datetime

from smp_utils import fetch

# Today's date day month year
today = datetime.now()

async def get_pvn_matches_by_team(session, team_id, until_date: str = '1.01.2024'):
    """Get the previous matches of a team. Last match in the list is the most recent match."""

    base_url = f"https://arsiv.mackolik.com/AjaxHandlers/TeamHandler.aspx?command=teamtabs&id={team_id}&type=1&viewType=1"

    response = await fetch(session, base_url)
    soup = BeautifulSoup(response, "html.parser")

    # Get the table
    table = soup.find("table", {"id": "tblFixture"})
    # Get the rows
    rows = table.find_all("tr")
    # Get the match details
    match_details = []
    for row in rows:
        cells = row.find_all("td")
        # Get the date
        date = cells[0].text.strip()
        # if the date is older than the until_date, continue
        if datetime.strptime(date, "%d.%m.%Y") < datetime.strptime(until_date, "%d.%m.%Y"):
            continue
        try:
            # Get the home team id
            home_team_id = cells[5].find("a")["href"].split("/")[4]
            # Get the away team id
            away_team_id = team_id

            op_team = home_team_id
        except TypeError:
            # Get the away team id
            away_team_id = cells[8].find("a")["href"].split("/")[4]
            # Get the home team id
            home_team_id = team_id

            op_team = away_team_id

        # Get the half-time score
        # half_time_score = cells[10].text.strip()
        # Get the result
        # result = cells[11].text.strip()
        # Print the match details
        # Get the score
        score = cells[9].text.strip()
        # Get the match id
        match_id = cells[9].find("b").find("a")["href"].split("/")[4]

        # Append the match details to the list
        match_details.append({
            "date": date,
            "match_id": match_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "main_team_id": team_id,
            "opponent_team_id": op_team,
        })

        # Stop if the score is v, which means the match is not played yet
        if score == "v":
            break

    return match_details

async def main():
    async with aiohttp.ClientSession() as session:
        pvn = await get_pvn_matches_by_team(session, 2, "3.04.2024")

    for match in pvn:
        print(match)


if __name__ == '__main__':
    asyncio.run(main())
