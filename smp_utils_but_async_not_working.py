import asyncio
import os
import random
from distutils.core import setup
from functools import lru_cache

import aiohttp
import aiosqlite


async def fetch(session: aiohttp.ClientSession, url: str, retries: int = 5, timeout: int = 10) -> str:
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                return await response.text()
        except (aiohttp.ClientResponseError, asyncio.TimeoutError) as e:
            if attempt < retries - 1:
                delay = random.uniform(30, 60)  # Random delay between 30 and 60 seconds
                print(f"Retrying {url} in {delay:.2f} seconds after error: {e}")
                await asyncio.sleep(delay)
            else:
                print(f"Failed to fetch {url} after {retries} retries. Error: {e}")
                raise


def avg_odds_rate(aoh: float, aoa: float, aod: float) -> float:
    return 1 / ((1 / aoh) + (1 / aoa) + (1 / aod))


def kelly(odd: float, avg_odd: float, f99: float) -> float:
    return (odd / avg_odd) * f99


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


class MackolikDatabase:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, dbname="static/db/mackolik.db") -> None:
        if hasattr(self, 'con'):
            return  # Prevent re-initialization if already initialized
        self.dbname = dbname
        os.makedirs(os.path.dirname(dbname), exist_ok=True)
        self.con = None
        self.cur = None

    async def setup(self):
        # Await the connection here
        self.con = await aiosqlite.connect(self.dbname)
        self.con.row_factory = dict_factory
        self.cur = await self.con.cursor()

        stmt = """
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY,
            team_name TEXT
        );
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY,
            team_id_home INTEGER,
            team_id_away INTEGER,
            team_goals_home INTEGER,
            team_goals_away INTEGER,
            bet_1 REAL,
            bet_x REAL,
            bet_2 REAL,
            bet_1x REAL,
            bet_12 REAL,
            bet_x2 REAL,
            bet_under_25 REAL,
            bet_over_25 REAL,
            team_name_home TEXT,
            team_name_away TEXT,
            ht_match_score_home INTEGER,
            ht_match_score_away INTEGER,
            ft_match_score_home INTEGER,
            ft_match_score_away INTEGER,
            possession_rate_home REAL,
            possession_rate_away REAL,
            total_shots_home INTEGER,
            total_shots_away INTEGER,
            shots_on_target_home INTEGER,
            shots_on_target_away INTEGER,
            successful_passes_home INTEGER,
            successful_passes_away INTEGER,
            pass_success_rate_home REAL,
            pass_success_rate_away REAL,
            corners_home INTEGER,
            corners_away INTEGER,
            crosses_home INTEGER,
            crosses_away INTEGER,
            fouls_home INTEGER,
            fouls_away INTEGER,
            offsides_home INTEGER,
            offsides_away INTEGER,
            yellow_cards_home INTEGER,
            yellow_cards_away INTEGER,
            red_cards_home INTEGER,
            red_cards_away INTEGER,
            match_index INTEGER,
            match_year INTEGER,
            match_month INTEGER,
            match_day INTEGER,
            match_hour INTEGER,
            match_minute INTEGER,
            week_index INTEGER,
            season_id INTEGER,
            response_code INTEGER
            /*  response_code:
                0: Not able to fetch, not played at all or canceled.
                1: Fetched and stats are available.
                2: Fetched but match is not played yet.
                3: Fetched but some unimportant stats are missing.
                4: Fetched but stats are not available, missing, or incorrect.
                5: Fetched but match is postponed.
            */
        );
        CREATE TABLE IF NOT EXISTS weeks (
            season_id INTEGER,
            week_index INTEGER,
            match_count INTEGER
        );
        CREATE TABLE IF NOT EXISTS seasons (
            season_id INTEGER PRIMARY KEY,
            team_count INTEGER,
            team_ids TEXT,
            max_week_count INTEGER
        );
        """
        await self.con.executescript(stmt)  # Await async method
        await self.con.commit()  # Await async method

    async def add_match(self, match: dict) -> None:
        columns = ', '.join(match.keys())
        placeholders = ', '.join(['?' for _ in match.values()])
        stmt = f"INSERT INTO matches ({columns}) VALUES ({placeholders})"
        await self.con.execute(stmt, tuple(match.values()))
        await self.con.commit()

    async def check_team(self, team_id) -> bool:
        stmt = "SELECT EXISTS(SELECT 1 FROM teams WHERE team_id = ?)"
        async with self.con.execute(stmt, (team_id,)) as cursor:
            return (await cursor.fetchone())[0] == 1

    async def add_team(self, team) -> None:
        stmt = "INSERT INTO teams (team_id, team_name) VALUES (?, ?)"
        args = (team['team_id'], team['team_name'])
        await self.con.execute(stmt, args)
        await self.con.commit()

    async def check_match(self, match_id) -> bool:
        stmt = "SELECT EXISTS(SELECT 1 FROM matches WHERE match_id = ?)"
        async with self.con.execute(stmt, (match_id,)) as cursor:
            return (await cursor.fetchone())[0] == 1

    async def get_match(self, match_id):
        stmt = "SELECT * FROM matches WHERE match_id = ?"
        async with self.con.execute(stmt, (match_id,)) as cursor:
            return await cursor.fetchone()

    async def check_week(self, season_id, week_index) -> bool:
        stmt = "SELECT EXISTS(SELECT 1 FROM weeks WHERE season_id = ? AND week_index = ?)"
        async with self.con.execute(stmt, (season_id, week_index)) as cursor:
            return (await cursor.fetchone())[0] == 1

    async def add_week(self, week) -> None:
        stmt = "INSERT INTO weeks (season_id, week_index, match_count) VALUES (?, ?, ?)"
        args = (week['season_id'], week['week_index'], week['match_count'])
        await self.con.execute(stmt, args)
        await self.con.commit()

    async def get_week(self, season_id, week_index):
        stmt = "SELECT * FROM weeks WHERE season_id = ? AND week_index = ?"
        async with self.con.execute(stmt, (season_id, week_index)) as cursor:
            return await cursor.fetchone()

    async def delete_week(self, season_id, week_index):
        stmt = "DELETE FROM weeks WHERE season_id = ? AND week_index = ?"
        await self.con.execute(stmt, (season_id, week_index))
        await self.con.commit()

    async def get_matches_sw(self, season_id, week_index):
        stmt = "SELECT * FROM matches WHERE season_id = ? AND week_index = ?"
        async with self.con.execute(stmt, (season_id, week_index)) as cursor:
            return await cursor.fetchall()

    async def get_sorted_match_ids_by_season(self, season_id):
        stmt = ("SELECT match_id, match_index, week_index, response_code "
                "FROM matches WHERE season_id = ? AND response_code = 1 ORDER BY week_index, match_index")
        async with self.con.execute(stmt, (season_id,)) as cursor:
            return [row[0] for row in await cursor.fetchall()]

    async def get_season(self, season_id):
        stmt = "SELECT * FROM seasons WHERE season_id = ?"
        async with self.con.execute(stmt, (season_id,)) as cursor:
            return await cursor.fetchone()

    async def check_season(self, season_id) -> bool:
        stmt = "SELECT EXISTS(SELECT 1 FROM seasons WHERE season_id = ?)"
        args = (season_id,)
        async with self.con.execute(stmt, args) as cursor:
            return tuple(await cursor.fetchone().items())[0][1] == 1

    async def add_season(self, season) -> None:
        stmt = "INSERT INTO seasons (season_id, team_count, team_ids, max_week_count) VALUES (?, ?, ?, ?)"
        args = (season['season_id'], season['team_count'], season['team_ids'], season['max_week_count'])
        await self.con.execute(stmt, args)
        await self.con.commit()

    @lru_cache(maxsize=128)
    async def get_match_by_ti_wi_si(self, team_id, week_index, season_id):
        stmt = """
        SELECT * FROM matches WHERE (team_id_home = ? OR team_id_away = ?) AND week_index = ? AND season_id = ?
        AND response_code = 1
        """
        async with self.con.execute(stmt, (team_id, team_id, week_index, season_id)) as cursor:
            return await cursor.fetchone()

    async def close(self) -> None:
        await self.con.close()

mackolik_db = MackolikDatabase()

# Usage example with asyncio
async def main():
    async with aiohttp.ClientSession() as session:
        await mackolik_db.setup()
        example_match = 2118664
        example_season_id = 59416
        example_week_index1 = 16
        example_team_id = 2

        print(mackolik_db.con)

        # Fetch a match by team_id, week_index, and season_id
        match = await mackolik_db.get_match_by_ti_wi_si(example_team_id, example_week_index1, example_season_id)
        print(match)
        await mackolik_db.close()

if __name__ == "__main__":
    asyncio.run(main())
