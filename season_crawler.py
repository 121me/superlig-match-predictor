import asyncio
from typing import Dict, Any, Tuple

import aiohttp
import json

from week_crawler import get_week_stats


async def get_season_stats(session: aiohttp.ClientSession, season_id: str) -> dict[str, tuple[Any] | int | str]:
    """
    Extracts season stats from the Mackolik website for a given season ID.

    Args:
        session: The aiohttp session to use for the request.
        season_id: The ID of the season to retrieve stats for.
    """

    # Retrieve season details from the JSON endpoint
    async with (session.get(f"https://arsiv.mackolik.com/AjaxHandlers/StandingHandler.ashx?op=standing&id={season_id}")
                as response):
        response.raise_for_status()  # Raise an error if request fails
        season_details = json.loads(await response.text())

    team_count = len(season_details["s"])
    max_week_count = (team_count - 1) * 2

    tasks = [get_week_stats(session, season_id, str(i)) for i in range(1, max_week_count + 1)]
    week_stats = await asyncio.gather(*tasks)

    return {
        "season_id": str(season_details["id"]),
        "team_count": team_count,
        "max_week_count": max_week_count,
        "weeks": week_stats
    }


async def main() -> None:
    # Example usage
    example_season_id = "59416"

    count = 0

    async with aiohttp.ClientSession() as session:
        season_stats = await get_season_stats(session, example_season_id)
        for n, week in enumerate(season_stats['weeks'], 1):
            print("Week:", n)
            for match in week:
                print("Match:", match["match_id"])
                count += 1
                for k, v in match.items():
                    print(f"{k}: {v}")
                print("-----------------------------")
            print("=============================")

    print(f"Total matches: {count}")


if __name__ == "__main__":
    asyncio.run(main())
