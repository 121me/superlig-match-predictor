import os
from types import NoneType

import aiohttp
import sqlite3


async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


def avg_odds_rate(aoh: float, aoa: float, aod: float) -> float:
    return 1 / ((1 / aoh) + (1 / aoa) + (1 / aod))


def kelly(odd: float, avg_odd: float, f99: float) -> float:
    return (odd / avg_odd) * f99


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


class SMPDatabase:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, dbname="static/db/smp.db") -> None:
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
            ht_match_score_home TEXT,
            ht_match_score_away TEXT,
            ft_match_score_home TEXT,
            ft_match_score_away TEXT,
            possession_home TEXT,
            possession_away TEXT,
            total_shots_home TEXT,
            total_shots_away TEXT,
            shots_on_target_home TEXT,
            shots_on_target_away TEXT,
            successful_passes_home TEXT,
            successful_passes_away TEXT,
            pass_success_rate_home TEXT,
            pass_success_rate_away TEXT,
            corners_home TEXT,
            corners_away TEXT,
            crosses_home TEXT,
            crosses_away TEXT,
            fouls_home TEXT,
            fouls_away TEXT,
            offsides_home TEXT,
            offsides_away TEXT,
            yellow_cards_home INTEGER,
            yellow_cards_away INTEGER,
            red_cards_home INTEGER,
            red_cards_away INTEGER,
            match_index INTEGER,
            week_index INTEGER,
            season_id INTEGER
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
            ft_match_score_home, ft_match_score_away, possession_home, possession_away,
            total_shots_home, total_shots_away, shots_on_target_home, shots_on_target_away,
            successful_passes_home, successful_passes_away, pass_success_rate_home, pass_success_rate_away,
            corners_home, corners_away, crosses_home, crosses_away, fouls_home, fouls_away,
            offsides_home, offsides_away, yellow_cards_home, yellow_cards_away,
            red_cards_home, red_cards_away, match_index, week_index, season_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        args = (
            match['match_id'], match['team_id_home'], match['team_id_away'],
            match['team_goals_home'], match['team_goals_away'], match['bet_1'],
            match['bet_x'], match['bet_2'], match['bet_1x'], match['bet_12'],
            match['bet_x2'], match['bet_under_25'], match['bet_over_25'],
            match['team_name_home'], match['team_name_away'], match['ht_match_score_home'],
            match['ht_match_score_away'], match['ft_match_score_home'], match['ft_match_score_away'],
            match['possession_home'], match['possession_away'], match['total_shots_home'],
            match['total_shots_away'], match['shots_on_target_home'], match['shots_on_target_away'],
            match['successful_passes_home'], match['successful_passes_away'], match['pass_success_rate_home'],
            match['pass_success_rate_away'], match['corners_home'], match['corners_away'],
            match['crosses_home'], match['crosses_away'], match['fouls_home'], match['fouls_away'],
            match['offsides_home'], match['offsides_away'], match['yellow_cards_home'],
            match['yellow_cards_away'], match['red_cards_home'], match['red_cards_away'], match['match_index'],
            match['week_index'], match['season_id']
        )
        self.cur.execute(stmt, args)
        self.con.commit()

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


smp_db = SMPDatabase()

if __name__ == "__main__":
    print("Running smp_utils.py")
    db = SMPDatabase()
    example_match = 3562668
    example_season_id = 59416
    example_week_index = 16
    print(db.check_match(example_match))
    print(db.get_match(example_match))
    print(db.check_week(example_season_id, example_week_index))
    print(db.get_week(example_season_id, example_week_index))
    db.close()
    print("Done running smp_utils.py")
