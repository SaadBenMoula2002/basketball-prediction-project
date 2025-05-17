from flask import Flask, request, render_template
from fetch_nba_data import save_all_nba_data, fetch_last_3_games_stats
from fetch_tweets import save_tweets
from predict_winner import predict_winner
import pandas as pd
import os
import time
import logging

os.environ['NBA_API_SSL_VERIFY'] = 'false'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# List of NBA teams and abbreviation mapping
nba_teams = [
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls",
    "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons", "Golden State Warriors",
    "Houston Rockets", "Indiana Pacers", "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies",
    "Miami Heat", "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
    "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers",
    "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz", "Washington Wizards"
]

team_abbreviation_map = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets", "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves", "NOP": "New Orleans Pelicans", "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs", "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz", "WAS": "Washington Wizards"
}

# Check if data is older than 24 hours
def should_fetch_data():
    if not os.path.exists('last_fetched.txt'):
        return True
    with open('last_fetched.txt', 'r') as f:
        content = f.read().strip()
        if not content:
            return True
        try:
            last_fetched = float(content)
            return (time.time() - last_fetched) >= 86400
        except ValueError:
            return True

# Update last fetched timestamp
def update_last_fetched():
    with open('last_fetched.txt', 'w') as f:
        f.write(str(time.time()))

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'search' in request.form:
            team1 = request.form['team1']
            team2 = request.form['team2']
            
            # Check if data is older than 24 hours
            if should_fetch_data():
                logging.info("Fetching new NBA data...")
                save_all_nba_data()
                update_last_fetched()
            
            # Fetch last 3 games stats for each team
            logging.info(f"Fetching last 3 games stats for {team1} and {team2}...")
            team1_last_3_games = fetch_last_3_games_stats(team1)
            team2_last_3_games = fetch_last_3_games_stats(team2)
            
            # Save last 3 games stats to CSV files
            team1_last_3_games.to_csv('last_3_games_stats_team1.csv', index=False)
            team2_last_3_games.to_csv('last_3_games_stats_team2.csv', index=False)
            
            # Fetch relevant tweets
            logging.info("Fetching relevant tweets...")
            save_tweets(team1, team2, pd.read_csv('all_player_stats.csv')['PLAYER_NAME'].tolist())
            
            # Get upcoming games
            logging.info("Fetching upcoming games...")
            upcoming_games = pd.read_csv('schedule.csv')
            
            
            # Filter upcoming games for the selected teams
            upcoming_games = upcoming_games[
                ((upcoming_games['Home Team'].str.strip().str.lower() == team1.lower()) & 
                 (upcoming_games['Away Team'].str.strip().str.lower() == team2.lower())) |
                ((upcoming_games['Home Team'].str.strip().str.lower() == team2.lower()) & 
                 (upcoming_games['Away Team'].str.strip().str.lower() == team1.lower()))
            ]
            
            return render_template('index.html', nba_teams=nba_teams, team1=team1, team2=team2, upcoming_games=upcoming_games.to_dict('records'))
        
        elif 'predict' in request.form:
            team1 = request.form['team1']
            team2 = request.form['team2']
            game_date = request.form['game']
            logging.info("Generating prediction...")
            prediction = predict_winner(team1, team2)
            return render_template('index.html', nba_teams=nba_teams, prediction=prediction)
    
    return render_template('index.html', nba_teams=nba_teams)

if __name__ == '__main__':
    app.run(debug=True)