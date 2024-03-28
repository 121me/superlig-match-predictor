from season_crawler import get_season_stats
from smp_utils import avg_odds_rate, kelly

import aiohttp
import asyncio


async def main() -> None:
    # Example usage
    # 19480, 35232, 42124, 47148, 51830, 54794, 57526, 59416
    mackolik_season_ids = ["59416"]

    async with aiohttp.ClientSession() as session:
        tasks = [get_season_stats(session, season_id) for season_id in mackolik_season_ids]
        seasons_stats = await asyncio.gather(*tasks)

        match_count = 0
        total_odds_home = 0.0
        total_odds_away = 0.0
        total_odds_draw = 0.0

        for season_stats in seasons_stats:
            for week in season_stats['weeks']:
                for match in week:
                    # To suppress the warning, we need to check if the match is a dictionary
                    if not isinstance(match, dict):
                        continue
                    match_count += 1
                    total_odds_home += float(match['bet_1'])
                    total_odds_away += float(match['bet_2'])
                    total_odds_draw += float(match['bet_x'])

        avg_odds_home = total_odds_home / match_count
        avg_odds_away = total_odds_away / match_count
        avg_odds_draw = total_odds_draw / match_count

        print(f"Average odds for home win: {avg_odds_home:.5f}")
        print(f"Average odds for away win: {avg_odds_away:.5f}")
        print(f"Average odds for draw: {avg_odds_draw:.5f}")

        f99 = avg_odds_rate(avg_odds_home, avg_odds_away, avg_odds_draw)

        kelly_of_matches = dict()
        kelly_type_count = {
            "type_1": 0,
            "type_2": 0,
            "type_3": 0
        }

        not_fav_type1_count = 0

        # The matches are divided into 3 categories. These were, matches with Kelly indexes greater than 1 (Type 1),
        # matches with only one Kelly index greater than 1 (Type 2),
        # and matches with no Kelly Index greater than 1 (Type 3).
        for season_stats in seasons_stats:
            for week in season_stats['weeks']:
                for match in week:
                    if not isinstance(match, dict):
                        continue

                    kelly_home = kelly(float(match['bet_1']), avg_odds_home, f99)
                    kelly_away = kelly(float(match['bet_2']), avg_odds_away, f99)
                    kelly_draw = kelly(float(match['bet_x']), avg_odds_draw, f99)

                    kelly_of_matches[match['match_id']] = {
                        "home": kelly_home,
                        "away": kelly_away,
                        "draw": kelly_draw
                    }

                    # find how many of the kelly indexes are greater than 1 using (kelly_home, kelly_away, kelly_draw)
                    kgt1 = len(list(filter(lambda x: x > 1, (kelly_home, kelly_away, kelly_draw))))

                    if kgt1 == 1:
                        kelly_type_count["type_2"] += 1
                    elif kgt1 == 0:
                        kelly_type_count["type_3"] += 1
                    else:
                        if match['team_id_home'] not in [1, 2, 3, 4]:
                            if match['team_id_away'] not in [1, 2, 3, 4]:
                                print(f"Match ID: {match['match_id']}")
                                not_fav_type1_count += 1
                                pass
                        kelly_type_count["type_1"] += 1

        print(f"f99 is {f99:.5f}")
        print(f"Kelly type 1 count: {kelly_type_count['type_1']}")
        print(f"Kelly type 2 count: {kelly_type_count['type_2']}")
        print(f"Kelly type 3 count: {kelly_type_count['type_3']}")
        print(f"Not fav type 1 count: {not_fav_type1_count}")
        print(f"Total matches: {match_count}")

    pass


if __name__ == "__main__":
    asyncio.run(main())
