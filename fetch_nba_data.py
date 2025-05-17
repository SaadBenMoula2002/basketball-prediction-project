import pandas as pd
from nba_api.stats.endpoints import leaguegamelog, leaguedashteamstats, leaguedashplayerstats, teamgamelog, ScoreboardV2
from nba_api.stats.static import teams
import os
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd


# Disable SSL verification for NBA API
os.environ['NBA_API_SSL_VERIFY'] = 'false'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function to get team ID by name
def get_team_id(team_name):
    nba_teams = teams.get_teams()
    matching_teams = [team for team in nba_teams if team['full_name'].lower() == team_name.lower()]
    if not matching_teams:
        raise ValueError(f"Team '{team_name}' not found.")
    return matching_teams[0]['id']

# Helper function to get the current NBA season
def get_current_season():
    today = datetime.today()
    year = today.year
    # NBA season typically starts in October
    if today.month >= 10:
        return f"{year}-{str(year + 1)[-2:]}"
    else:
        return f"{year - 1}-{str(year)[-2:]}"

# Fetch NBA schedule for the current season
# def fetch_nba_schedule():

#     # Fetch team names and IDs
#     team_data = teams.get_teams()
#     team_id_to_name = {team['id']: team['full_name'] for team in team_data}

#     try:
#         logging.info("Fetching NBA schedule...")
#         # Get today's date
#         current_date = datetime.now().strftime('%Y-%m-%d')

#         # Fetch today's games
#         scoreboard = ScoreboardV2(game_date=current_date)
#         games = scoreboard.get_data_frames()[0]

#         # Filter for upcoming games only (if any)
#         if not games.empty:
#             game_list = []
#             for _, game in games.iterrows():
#                 game_date = game['GAME_DATE_EST'].split('T')[0]  # Remove time part of the date
#                 home_team = team_id_to_name.get(game['HOME_TEAM_ID'], "Unknown Team")
#                 away_team = team_id_to_name.get(game['VISITOR_TEAM_ID'], "Unknown Team")

#                 game_list.append({
#                     'Game Date': game_date,
#                     'Home Team': home_team,
#                     'Away Team': away_team
#                 })
        
#         # Save the schedule to a CSV file
#         pd.DataFrame(game_list).to_csv('schedule.csv', index=False)
#         logging.info("NBA schedule saved to 'schedule.csv'.")
#     except Exception as e:
#         logging.error(f"Error fetching NBA schedule: {e}")

def fetch_nba_schedule():
    # Fetch team names and IDs
    team_data = teams.get_teams()
    team_id_to_name = {team['id']: team['full_name'] for team in team_data}

    def get_games_for_date(date_str):
        try:
            scoreboard = ScoreboardV2(game_date=date_str)
            games = scoreboard.get_data_frames()[0]
            return games
        except Exception as e:
            logging.warning(f"Failed to fetch games for {date_str}: {e}")
            return pd.DataFrame()

    try:
        logging.info("Fetching NBA schedule...")
        game_list = []
        today = datetime.now()

        games = get_games_for_date(today.strftime('%Y-%m-%d'))

        # If no games today, search up to 14 days ahead
        lookahead_days = 0
        while games.empty and lookahead_days < 14:
            lookahead_days += 1
            next_day = today + pd.Timedelta(days=lookahead_days)
            logging.info(f"No games today. Checking {next_day.strftime('%Y-%m-%d')}...")
            games = get_games_for_date(next_day.strftime('%Y-%m-%d'))

        if games.empty:
            logging.warning("No upcoming games found in the next 14 days.")
        else:
            for _, game in games.iterrows():
                game_date = game['GAME_DATE_EST'].split('T')[0]
                home_team = team_id_to_name.get(game['HOME_TEAM_ID'], "Unknown Team")
                away_team = team_id_to_name.get(game['VISITOR_TEAM_ID'], "Unknown Team")

                game_list.append({
                    'Game Date': game_date,
                    'Home Team': home_team,
                    'Away Team': away_team
                })

            pd.DataFrame(game_list).to_csv('schedule.csv', index=False)
            logging.info(f"NBA schedule saved to 'schedule.csv' with games on {game_date}.")

    except Exception as e:
        logging.error(f"Error fetching NBA schedule: {e}")


# Fetch all team stats for the current season
def fetch_all_team_stats():
    try:
        logging.info("Fetching all team stats...")
        season = get_current_season()
        team_stats = leaguedashteamstats.LeagueDashTeamStats(season=season).get_data_frames()[0]
        team_stats.to_csv('all_team_stats.csv', index=False)
        logging.info("All team stats saved to 'all_team_stats.csv'.")
    except Exception as e:
        logging.error(f"Error fetching team stats: {e}")

# Fetch all player stats for the current season
def fetch_all_player_stats():
    try:
        logging.info("Fetching all player stats...")
        season = get_current_season()
        player_stats = leaguedashplayerstats.LeagueDashPlayerStats(season=season).get_data_frames()[0]
        player_stats.to_csv('all_player_stats.csv', index=False)
        logging.info("All player stats saved to 'all_player_stats.csv'.")
    except Exception as e:
        logging.error(f"Error fetching player stats: {e}")

# Fetch last 3 games stats for a specific team (including regular season and playoffs)
def fetch_last_3_games_stats(team):
    try:
        logging.info(f"Fetching last 3 games (including playoffs) for {team}...")
        team_id = get_team_id(team)
        season = get_current_season()

        # Fetch both regular season and playoff game logs
        regular_season_log = teamgamelog.TeamGameLog(
            team_id=team_id,
            season=season,
            season_type_all_star="Regular Season"
        ).get_data_frames()[0]

        playoff_log = teamgamelog.TeamGameLog(
            team_id=team_id,
            season=season,
            season_type_all_star="Playoffs"
        ).get_data_frames()[0]

        # Combine both logs
        all_games = pd.concat([regular_season_log, playoff_log], ignore_index=True)

        # Convert GAME_DATE to datetime and sort
        all_games['GAME_DATE'] = pd.to_datetime(all_games['GAME_DATE'])
        all_games = all_games.sort_values('GAME_DATE', ascending=False)

        return all_games.head(3)
    except Exception as e:
        logging.error(f"Error fetching last 3 games stats for {team}: {e}")
        return pd.DataFrame()


def fetch_nba_injuries():
    url = "https://www.espn.com/nba/injuries"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"⚠️ Request error: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    injury_data = []

    teams = soup.find_all('div', class_='ResponsiveTable Table__league-injuries')
    if not teams:
        logging.error("⚠️ No teams found — check if ESPN changed the HTML structure.")
        return

    for team in teams:
        team_name_tag = team.find('span', class_='injuries__teamName')
        team_name = team_name_tag.text.strip() if team_name_tag else "Unknown Team"
        players = team.find_all('tr', class_='Table__TR--sm')

        for player in players:
            columns = player.find_all('td')
            if len(columns) >= 5:
                name = columns[0].text.strip()
                position = columns[1].text.strip()
                estimated_return = columns[2].text.strip()
                status = columns[3].text.strip()
                injury_data.append([team_name, name, position, estimated_return, status])

    # Convert to DataFrame
    df = pd.DataFrame(injury_data, columns=['Team', 'Player', 'Position', 'Estimated Return', 'Status'])
    df.to_csv('nba_injuries.csv', index=False)
    logging.info("NBA injuries data saved to 'nba_injuries.csv'.")

# Save all NBA data
def save_all_nba_data():
    fetch_nba_schedule()
    fetch_all_team_stats()
    fetch_all_player_stats()
    fetch_nba_injuries()

# Run the function to fetch and save all data
if __name__ == "__main__":
    save_all_nba_data()