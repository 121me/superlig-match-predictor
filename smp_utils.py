import asyncio
import os
import random

import aiohttp
import sqlite3


async def fetch(session: aiohttp.ClientSession, url: str, retries: int = 5, timeout: int = 10) -> str:
    base_delay = 5  # Base delay for backoff
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()  # Raise if non-2xx status
                return await response.text()
        except (aiohttp.ClientResponseError, asyncio.TimeoutError, aiohttp.ClientConnectorError) as e:
            if attempt < retries:
                # Exponential backoff with jitter
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                print(f"Attempt {attempt}/{retries} failed for {url} with error: {e}. Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
            else:
                print(f"Failed to fetch {url} after {retries} retries. Error: {e}")
                raise e


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
        self.con = sqlite3.connect(dbname, check_same_thread=False)
        self.con.row_factory = dict_factory
        self.cur = self.con.cursor()
        self.setup()

    def setup(self) -> None:
        stmt = """
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY,
            team_id_home INTEGER,
            team_id_away INTEGER,
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
            match_year INTEGER,
            match_month INTEGER,
            match_day INTEGER,
            match_hour INTEGER,
            match_minute INTEGER,
            prev_5_match_ids_home TEXT,
            prev_5_match_ids_away TEXT,
            response_code INTEGER
            /*  response_code:
                0: Not able to fetch.
                1: Fetched and stats are available.
                2: Fetched but match is not played yet.
                3: Fetched but most stats are not available, missing, or incorrect.
                4: Fetched but match is postponed, canceled, or abandoned.
            */
        );
        """
        self.con.executescript(stmt)  # Await async method
        self.con.commit()  # Await async method

    def add_match(self, match: dict) -> None:
        columns = ', '.join(match.keys())
        placeholders = ', '.join(['?' for _ in match.values()])
        stmt = f"INSERT INTO matches ({columns}) VALUES ({placeholders})"
        self.cur.execute(stmt, tuple(match.values()))
        self.con.commit()

    def check_match(self, match_id):
        # if response_code is not 2, then the match is fetched
        stmt = "SELECT EXISTS(SELECT 1 FROM matches WHERE match_id = ? and response_code != 2)"
        self.cur.execute(stmt, (match_id,))
        return tuple(self.cur.fetchone().items())[0][1] == 1

    def get_match(self, match_id):
        stmt = "SELECT * FROM matches WHERE match_id = ?"
        self.cur.execute(stmt, (match_id,))
        return self.cur.fetchone()

    def delete_match(self, match_id):
        stmt = "DELETE FROM matches WHERE match_id = ?"
        self.cur.execute(stmt, (match_id,))
        self.con.commit()

    def get_match_response_code(self, match_id):
        stmt = "SELECT response_code FROM matches WHERE match_id = ?"
        self.cur.execute(stmt, (match_id,))
        return self.cur.fetchone()['response_code']

    def fix_db(self):
        stmt = "DELETE FROM matches WHERE response_code = 4 OR response_code = 3"
        self.cur.execute(stmt)
        self.con.commit()

    def close(self) -> None:
        self.con.close()

    def __del__(self) -> None:
        self.close()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __enter__(self):
        return self

    def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()

mackolik_db = MackolikDatabase()

# Usage example with asyncio
async def main():
    async with aiohttp.ClientSession() as session:
        print(mackolik_db.get_match_response_code(4182728))

if __name__ == "__main__":
    asyncio.run(main())
