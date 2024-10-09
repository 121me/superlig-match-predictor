from smp_utils import mackolik_db

get_match_sorted = mackolik_db.get_sorted_match_ids_by_season(59416)

headers = ['avg_possession_rate_home', 'avg_possession_rate_away', 'avg_total_shots_home', 'avg_total_shots_away',
'avg_shots_on_target_home', 'avg_shots_on_target_away', 'avg_successful_passes_home', 'avg_successful_passes_away',
'avg_pass_success_rate_home', 'avg_pass_success_rate_away', 'avg_corners_home', 'avg_corners_away',
'avg_crosses_home', 'avg_crosses_away', 'avg_fouls_home', 'avg_fouls_away',
'avg_offsides_home', 'avg_offsides_away', 'avg_yellow_cards_home', 'avg_yellow_cards_away',
'avg_red_cards_home', 'avg_red_cards_away', 'avg_ft_match_score_home', 'avg_ft_match_score_away',
'avg_ht_match_score_home', 'avg_ht_match_score_away']

avg_keys = ["possession_rate_home", "possession_rate_away", "total_shots_home", "total_shots_away",
"shots_on_target_home", "shots_on_target_away", "successful_passes_home", "successful_passes_away",
"pass_success_rate_home", "pass_success_rate_away", "corners_home", "corners_away",
"crosses_home", "crosses_away", "fouls_home", "fouls_away",
"offsides_home", "offsides_away", "yellow_cards_home", "yellow_cards_away",
"red_cards_home", "red_cards_away", "ft_match_score_home", "ft_match_score_away",
"ht_match_score_home", "ht_match_score_away"]

bets = ["bet_under_25", "bet_over_25"]

matches = [mackolik_db.get_match(match['match_id']) for match in get_match_sorted]

data = []

# take the average of the previous 5 games for each iteration
for n, match in enumerate(matches[5:], 5):

    # precision 2 digits, round to 5 digits, last 5 matches avgs
    line = [round(sum([match[key] for match in matches[n - 5:n]]) / 5, 5) for key in avg_keys]

    # bet rates of bet_under_25 and bet_over_25 for later calculation
    line += [match[key] for key in bets]

    # bet result, 0 for under 2.5, 1 for over 2.5, for classification and later calculation
    line += [0] if match["ft_match_score_home"] + match["ft_match_score_away"] < 2.5 else [1]

    data += [line]