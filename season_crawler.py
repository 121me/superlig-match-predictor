import asyncio
from typing import Any, Dict

import aiohttp
import json
import logging

from smp_utils import fetch, mackolik_db
from week_crawler import get_week_stats

# Configure logging
logging.basicConfig(level=logging.INFO)


async def get_season_stats(session: aiohttp.ClientSession, season_id: str) -> Dict[str, Any]:
    """
    Extracts season stats from the Mackolik website for a given season ID.

    Args:
        session: The aiohttp session to use for the request.
        season_id: The ID of the season to retrieve stats for.

    Returns:
        A dictionary containing season stats, including team count, max week count, and weekly match stats.
    """
    try:
        # Check if the season details are already in the database
        if mackolik_db.check_season(season_id):
            season_details = mackolik_db.get_season(season_id)
            team_count = season_details["team_count"]
            max_week_count = season_details["max_week_count"]
        else:
            # Fetch season details from Mackolik API
            response_season_details = await fetch(
                session,
                f"https://arsiv.mackolik.com/AjaxHandlers/StandingHandler.ashx?op=standing&id={season_id}"
            )
            season_details = json.loads(response_season_details)

            team_count = len(season_details["s"])
            max_week_count = (team_count - 1) * 2  # League match weeks calculation based on teams

        # Fetch match stats for each week
        tasks = [get_week_stats(session, season_id, str(i)) for i in range(1, max_week_count + 1)]
        week_stats = await asyncio.gather(*tasks)

        # Add season details to the database if not already present
        if not mackolik_db.check_season(season_id):
            mackolik_db.add_season({
                "season_id": season_id,
                "team_count": team_count,
                "team_ids": "l".join([str(team_details[0]) for team_details in season_details["s"]]),
                "max_week_count": max_week_count
            })

        return {
            "season_id": season_id,
            "team_count": team_count,
            "max_week_count": max_week_count,
            "weeks": week_stats
        }

    except Exception as e:
        logging.error(f"Error fetching season stats for season {season_id}: {e}")
        return {}


async def main() -> None:
    """
    Example usage to fetch and display match statistics for a specific season.
    """
    example_season_id = "67180"  # Example season ID
    count = 0

    async with aiohttp.ClientSession() as session:
        season_stats = await get_season_stats(session, example_season_id)

        # Handle cases where fetching the season stats failed
        if not season_stats:
            logging.error("Season stats could not be retrieved.")
            return

        # Iterate over weeks and matches, displaying the data
        for n, week in enumerate(season_stats['weeks'], 1):
            logging.info(f"Week: {n}")
            for match in week:
                logging.info(f"Match: {match['match_id']}")
                count += 1
                for k, v in match.items():
                    logging.info(f"{k}: {v}")
                logging.info("-----------------------------")
            logging.info("=============================")

    logging.info(f"Total matches: {count}")


if __name__ == "__main__":
    asyncio.run(main())
