import asyncio
import aiohttp
import json

from week_crawler import get_week_stats


async def get_season_stats(session: aiohttp.ClientSession, season_id: str) -> tuple[list[dict[str, str]]]:
    """
    Extracts season stats from the Mackolik website for a given season ID.

    Args:
        session: The aiohttp session to use for the request.
        season_id: The ID of the season to retrieve stats for.
    """

    # Retrieve season details from the JSON endpoint
    async with session.get(f"https://arsiv.mackolik.com/AjaxHandlers/StandingHandler.ashx?op=standing&id={season_id}") as response:
        response.raise_for_status()  # Raise an error if request fails
        season_details = json.loads(await response.text())

    team_count = len(season_details["s"])
    week_count = (team_count - 1) * 2

    tasks = [get_week_stats(session, season_id, str(i)) for i in range(1, week_count + 1)]
    return await asyncio.gather(*tasks)


async def main() -> None:
    # Example usage
    example_season_id = "59416"

    async with aiohttp.ClientSession() as session:
        season_stats = await get_season_stats(session, example_season_id)
        for n, week in enumerate(season_stats, 1):
            print("Week:", n)
            for match in week:
                print("Match:", match["match_id"])
                for k, v in match.items():
                    print(f"{k}: {v}")
                print("-----------------------------")
            print("=============================")

if __name__ == "__main__":
    asyncio.run(main())
