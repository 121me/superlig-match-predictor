import csv

from smp_utils import mackolik_db

get_match_sorted = mackolik_db.get_sorted_match_ids_by_season(59416)

headers = [
    'team_id_home', 'team_id_away', 'team_power_home', 'team_power_away',
    'avg_possession_rate_home', 'avg_total_shots_home', 'avg_total_shots_away', 'avg_shots_on_target_home',
    'avg_shots_on_target_away', 'avg_successful_passes_home', 'avg_successful_passes_away',
    'avg_pass_success_rate_home', 'avg_pass_success_rate_away', 'avg_corners_home', 'avg_corners_away',
    'avg_crosses_home', 'avg_crosses_away', 'avg_fouls_home', 'avg_fouls_away', 'avg_offsides_home',
    'avg_offsides_away', 'avg_yellow_cards_home', 'avg_yellow_cards_away', 'avg_red_cards_home', 'avg_red_cards_away',
    'avg_team_goals_home', 'avg_team_goals_away', 'team_goals_home', 'team_goals_away'
]

keys = [
    'possession_rate_home', 'total_shots_home', 'total_shots_away',
    'shots_on_target_home', 'shots_on_target_away', 'successful_passes_home',
    'successful_passes_away', 'pass_success_rate_home', 'pass_success_rate_away',
    'corners_home', 'corners_away', 'crosses_home', 'crosses_away', 'fouls_home',
    'fouls_away', 'offsides_home', 'offsides_away', 'yellow_cards_home',
    'yellow_cards_away', 'red_cards_home', 'red_cards_away', 'team_goals_home', 'team_goals_away'
]

matches = [mackolik_db.get_match(match['match_id']) for match in get_match_sorted]

with open('match_data.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(headers)
    # take the average of the previous 5 games for each iteration
    for n, match in enumerate(matches[5:], 5):
        line = [match['team_id_home'], match['team_id_away'], mackolik_db.get_team(match['team_id_home'])['team_power'],
                mackolik_db.get_team(match['team_id_away'])['team_power']]
        line += [sum([match[key] for match in matches[n - 5:n]]) / 5 for key in keys]
        line += [match['team_goals_home'], match['team_goals_away']]
        writer.writerow(line)