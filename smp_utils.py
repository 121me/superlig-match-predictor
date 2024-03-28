import asyncio
import os
from typing import Any, Coroutine

import aiohttp
import sqlite3


async def fetch(session: aiohttp.ClientSession, url: str) -> Coroutine[Any, Any, str]:
    return await _fetch(session, url, 0)


async def _fetch(session: aiohttp.ClientSession, url: str, retries: int) -> Coroutine[Any, Any, str] | str:
    async with session.get(url) as response:
        try:
            response.raise_for_status()
        except aiohttp.ClientResponseError as e:
            # wait for 20 seconds and try again
            await asyncio.sleep(20)
            if retries < 5:
                return await _fetch(session, url, retries + 1)
            else:
                raise e
        return await response.text()


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
            return
        self.dbname = dbname
        try:
            self.con = sqlite3.connect(dbname, check_same_thread=True)
        except sqlite3.OperationalError:
            os.makedirs("static/db", exist_ok=True)
            self.con = sqlite3.connect(dbname, check_same_thread=True)
        self.con.row_factory = dict_factory
        self.cur = self.con.cursor()
        self.setup()

    def setup(self) -> None:
        stmt = """
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY,
            team_name TEXT,
            team_power REAL
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
            match_date TEXT,
            week_index INTEGER,
            season_id INTEGER,
            match_result_type INTEGER
        );
        CREATE TABLE IF NOT EXISTS weeks (
            season_id INTEGER,
            week_index INTEGER,
            match_count INTEGER
        );
        CREATE TABLE IF NOT EXISTS seasons (
            season_id INTEGER PRIMARY KEY,
            team_count INTEGER,
            max_week_count INTEGER
        );
        """
        self.cur.executescript(stmt)
        self.con.commit()

    def add_match(self, match) -> None:
        stmt = """
        INSERT INTO matches (
            match_id, team_id_home, team_id_away, team_goals_home, team_goals_away,
            bet_1, bet_x, bet_2, bet_1x, bet_12, bet_x2, bet_under_25, bet_over_25,
            team_name_home, team_name_away, ht_match_score_home, ht_match_score_away,
            ft_match_score_home, ft_match_score_away, possession_rate_home, possession_rate_away,
            total_shots_home, total_shots_away, shots_on_target_home, shots_on_target_away,
            successful_passes_home, successful_passes_away, pass_success_rate_home, pass_success_rate_away,
            corners_home, corners_away, crosses_home, crosses_away, fouls_home, fouls_away,
            offsides_home, offsides_away, yellow_cards_home, yellow_cards_away, red_cards_home, red_cards_away,
            match_index, week_index, season_id, match_result_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        args = (
            match['match_id'], match['team_id_home'], match['team_id_away'], match['team_goals_home'],
            match['team_goals_away'], match['bet_1'], match['bet_x'], match['bet_2'], match['bet_1x'],
            match['bet_12'], match['bet_x2'], match['bet_under_25'], match['bet_over_25'], match['team_name_home'],
            match['team_name_away'], match['ht_match_score_home'], match['ht_match_score_away'],
            match['ft_match_score_home'], match['ft_match_score_away'], match['possession_rate_home'],
            match['possession_rate_away'], match['total_shots_home'], match['total_shots_away'],
            match['shots_on_target_home'], match['shots_on_target_away'], match['successful_passes_home'],
            match['successful_passes_away'], match['pass_success_rate_home'], match['pass_success_rate_away'],
            match['corners_home'], match['corners_away'], match['crosses_home'], match['crosses_away'],
            match['fouls_home'], match['fouls_away'], match['offsides_home'], match['offsides_away'],
            match['yellow_cards_home'], match['yellow_cards_away'], match['red_cards_home'], match['red_cards_away'],
            match['match_index'], match['week_index'], match['season_id'], match['match_result_type']
        )
        self.cur.execute(stmt, args)
        self.con.commit()

    def check_team(self, team_id):
        stmt = "SELECT EXISTS(SELECT 1 FROM teams WHERE team_id = ?)"
        self.cur.execute(stmt, (team_id,))
        return tuple(self.cur.fetchone().items())[0][1] == 1

    def add_team(self, team) -> None:
        stmt = "INSERT INTO teams (team_id, team_name, team_power) VALUES (?, ?, ?)"
        args = (team['team_id'], team['team_name'], team['team_power'])
        self.cur.execute(stmt, args)
        self.con.commit()

    def get_team(self, team_id):
        stmt = "SELECT * FROM teams WHERE team_id = ?"
        self.cur.execute(stmt, (team_id,))
        return self.cur.fetchone()

    def check_match(self, match_id):
        stmt = "SELECT EXISTS(SELECT 1 FROM matches WHERE match_id = ?)"
        self.cur.execute(stmt, (match_id,))
        return tuple(self.cur.fetchone().items())[0][1] == 1

    def get_match(self, match_id):
        stmt = "SELECT * FROM matches WHERE match_id = ?"
        self.cur.execute(stmt, (match_id,))
        return self.cur.fetchone()

    def get_matches_sw(self, season_id, week_index):
        stmt = "SELECT * FROM matches WHERE season_id = ? AND week_index = ?"
        self.cur.execute(stmt, (season_id, week_index))
        return self.cur.fetchall()

    def get_matches_s(self, season_id):
        stmt = "SELECT * FROM matches WHERE season_id = ?"
        self.cur.execute(stmt, (season_id,))
        return self.cur.fetchall()

    def add_week(self, week) -> None:
        stmt = "INSERT INTO weeks (season_id, week_index, match_count) VALUES (?, ?, ?)"
        args = (week['season_id'], week['week_index'], week['match_count'])
        self.cur.execute(stmt, args)
        self.con.commit()

    def delete_week(self, season_id, week_index) -> None:
        stmt = "DELETE FROM weeks WHERE season_id = ? AND week_index = ?"
        args = (season_id, week_index)
        self.cur.execute(stmt, args)
        self.con.commit()

    def get_week(self, season_id, week_index):
        stmt = "SELECT * FROM weeks WHERE week_index = ? AND season_id = ?"
        args = (week_index, season_id)
        self.cur.execute(stmt, args)
        return self.cur.fetchone()

    def get_weeks(self, season_id):
        stmt = "SELECT * FROM weeks WHERE season_id = ?"
        args = (season_id,)
        self.cur.execute(stmt, args)
        return self.cur.fetchall()

    def check_week(self, season_id, week_index):
        stmt = "SELECT EXISTS(SELECT 1 FROM weeks WHERE week_index = ? AND season_id = ?)"
        args = (week_index, season_id)
        self.cur.execute(stmt, args)
        return tuple(self.cur.fetchone().items())[0][1] == 1

    def add_season(self, season) -> None:
        stmt = "INSERT INTO seasons (season_id, team_count, max_week_count) VALUES (?, ?, ?)"
        args = (season['season_id'], season['team_count'], season['max_week_count'])
        self.cur.execute(stmt, args)
        self.con.commit()

    def check_season(self, season_id):
        stmt = "SELECT EXISTS(SELECT 1 FROM seasons WHERE season_id = ?)"
        args = (season_id,)
        self.cur.execute(stmt, args)
        return tuple(self.cur.fetchone().items())[0][1] == 1

    def get_season(self, season_id):
        stmt = "SELECT * FROM seasons WHERE season_id = ?"
        args = (season_id,)
        self.cur.execute(stmt, args)
        return self.cur.fetchone()

    def get_sorted_match_ids_by_season(self, season_id):
        """
        Get these features:
        match_id INTEGER PRIMARY KEY,
        match_index INTEGER,
        week_index INTEGER,
        match_result_type INTEGER

        order by week_index and match_index
        """
        stmt = ("SELECT match_id, match_index, week_index, match_result_type "
                "FROM matches WHERE season_id = ? ORDER BY week_index, match_index")
        self.cur.execute(stmt, (season_id,))
        return self.cur.fetchall()

    def get_match_features(self, match_id):
        stmt = query = """
    SELECT t1.team_id AS team_id_home, t2.team_id AS team_id_away, t1.team_power AS team_power_home,
    t2.team_power AS team_power_away,
        m.possession_rate_home, m.total_shots_home, m.total_shots_away, m.shots_on_target_home, m.shots_on_target_away,
        m.successful_passes_home, m.successful_passes_away, m.pass_success_rate_home, m.pass_success_rate_away,
        m.corners_home, m.corners_away, m.crosses_home, m.crosses_away, m.fouls_home, m.fouls_away,
        m.offsides_home, m.offsides_away, m.yellow_cards_home, m.yellow_cards_away, m.red_cards_home, m.red_cards_away,
        m.team_goals_home AS goals_home, m.team_goals_away AS goals_away
    FROM matches AS m
    INNER JOIN teams AS t1 ON t1.team_id = m.team_id_home
    INNER JOIN teams AS t2 ON t2.team_id = m.team_id_away
    WHERE m.match_id = ?
    """
        self.cur.execute(stmt, (match_id,))
        return self.cur.fetchone()

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

if __name__ == "__main__":
    print("Running smp_utils.py")
    db = MackolikDatabase()
    example_match = 2118664
    example_season_id = 59416
    example_week_index = 16
    print(db.check_match(example_match))
    print(db.get_match(example_match))
    print(db.check_week(example_season_id, example_week_index))
    print(db.get_week(example_season_id, example_week_index))

    db.close()
    print("Done running smp_utils.py")
