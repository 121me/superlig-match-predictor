from bs4 import BeautifulSoup
import requests
import json


def get_match_stats(match_id: str) -> list[tuple[str, str, str]]:
    """
    Extracts match stats from the Mackolik website for a given match ID.

    Args:
        match_id: The ID of the match to retrieve stats for.

    Returns:
        A list of tuples, where each tuple contains:
            - The stat name
            - The home team's stat value
            - The away team's stat value
    """

    # Retrieve match details from the JSON endpoint
    response_match_details = requests.get(
        f"https://arsiv.mackolik.com/Match/MatchData.aspx?t=dtl&id={match_id}"
    )
    response_match_details.raise_for_status()  # Raise an error if request fails
    match_details = json.loads(response_match_details.content)

    # Retrieve detailed analyses from the HTML endpoint
    response_detailed_analyses = requests.get(
        f"https://arsiv.mackolik.com/Match/Default.aspx?id={match_id}"
    )
    response_detailed_analyses.raise_for_status()  # Raise an error if request fails
    soup = BeautifulSoup(response_detailed_analyses.content, "html.parser")

    # Extract team names from the JSON data
    home_team_name = match_details["home"]
    away_team_name = match_details["away"]

    # Extract match scores from the JSON data
    ht_match_score = match_details["d"]["ht"]
    ft_match_score = match_details["d"]["s"]

    # Parse match stats from the HTML content
    match_analysis = soup.select_one("#dvOPTAStats > div:nth-child(2)").text
    lines = [line.strip() for line in match_analysis.splitlines() if line.strip()]

    # Validate the structure of the extracted lines
    if len(lines) % 3 != 0:
        raise ValueError("Unexpected number of lines in match stats")

    # Organize stats into a list of tuples
    stats = [
        ("Teams", home_team_name, away_team_name),
        ("Half-time Score", *ht_match_score.split(" - ")),
        ("Full-time Score", *ft_match_score.split(" - ")),
    ]
    stats += list(zip(lines[1::3], lines[0::3], lines[2::3]))

    return stats


if __name__ == "__main__":
    # Example usage
    example_match_id = "3870958"
    match_stats = get_match_stats(example_match_id)
    for stat, home, away in match_stats:
        print(f"{stat}, {home}, {away}")

    # Output:
    # Teams, Kayserispor, Fenerbahçe
    # Half-time Score, 1, 2
    # Full-time Score, 3, 4
    # Topla Oynama, %51, %49
    # Toplam Şut, 14, 13
    # İsabetli Şut, 6, 6
    # Başarılı Paslar, 272, 269
    # Pas Başarı(%), %72, %74
    # Korner, 5, 3
    # Orta, 4/18, 2/12
    # Faul, 22, 11
    # Ofsayt, 2, 1
