import openai
import pandas as pd
import json
import logging
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load OpenAI API key
with open('keys.json') as f:
    keys = json.load(f)
openai.api_key = keys['OPENAI_API_KEY']

def deepseek_chat(prompt):

    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {keys['DEEPSEEK_API_KEY']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        result = response.json()
        
        return result.get('choices', [{}])[0].get('message', {}).get('content', "No prediction available.")
    
    except Exception as e:

        return f"Error contacting Deepseek API: {e}"


def predict_winner(team1, team2):
    try:
        # Load data from local files
        logging.info("Loading team stats...")
        team_stats = pd.read_csv('all_team_stats.csv')
        logging.info("Loading player stats...")
        player_stats = pd.read_csv('all_player_stats.csv')
        logging.info("Loading team injuries...")
        team_injuries = pd.read_csv('nba_injuries.csv')

        # Load tweets if available
        try:
            logging.info("Loading tweets...")
            tweets = pd.read_csv('tweets.csv')
            # Filter relevant tweets (tweets that mention the teams or their players)
            relevant_tweets = []
            for tweet in tweets.to_dict('records'):
                if any(keyword.lower() in tweet['Tweet'].lower() for keyword in [team1, team2] + player_stats[player_stats['TEAM_ABBREVIATION'].isin([team1.split()[-1].upper(), team2.split()[-1].upper()])]['PLAYER_NAME'].tolist()):
                    relevant_tweets.append(tweet)
            tweets_info = relevant_tweets if relevant_tweets else "No relevant tweets available."
        except FileNotFoundError:
            tweets_info = "No tweets available."
            logging.warning("No tweets found. Proceeding without tweets.")
        
        # Load last 3 games stats
        logging.info("Loading last 3 games stats...")
        team1_last_3_games = pd.read_csv('last_3_games_stats_team1.csv')
        team2_last_3_games = pd.read_csv('last_3_games_stats_team2.csv')
        
        # Filter data for the selected teams
        logging.info(f"Filtering stats for {team1} and {team2}...")
        
        # Filter team stats
        team1_stats = team_stats[team_stats['TEAM_NAME'] == team1].iloc[0]
        team2_stats = team_stats[team_stats['TEAM_NAME'] == team2].iloc[0]
        
        # Get team abbreviations from the team_abbreviation_map
        team_abbreviation_map = {
            "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "Charlotte Hornets": "CHA",
            "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN",
            "Detroit Pistons": "DET", "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
            "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM", "Miami Heat": "MIA",
            "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
            "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
            "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
            "Utah Jazz": "UTA", "Washington Wizards": "WAS"
        }
        
        team1_abbreviation = team_abbreviation_map.get(team1, "")
        team2_abbreviation = team_abbreviation_map.get(team2, "")

        
        # Filter player stats using team abbreviations
        team1_players = player_stats[player_stats['TEAM_ABBREVIATION'] == team1_abbreviation].sort_values(by='PTS', ascending=False).head(5).to_dict('records')
        team2_players = player_stats[player_stats['TEAM_ABBREVIATION'] == team2_abbreviation].sort_values(by='PTS', ascending=False).head(5).to_dict('records')
        

        team1_missings = team_injuries[team_injuries['Team'] == team1]
        team2_missings = team_injuries[team_injuries['Team'] == team2]
        
        # Generate GPT prompt
        
        prompt = f"""
        ## 🏀 Predict the Winner: {team1} vs {team2}

        ### **Team 1: {team1}**
        - **Record:** {team1_stats['W']}W - {team1_stats['L']}L
        - **Points Per Game:** {team1_stats['PTS']}
        - **Field Goal Percentage:** {team1_stats['FG_PCT']}
        - **Three-Point Percentage:** {team1_stats['FG3_PCT']}
        - **Key Players:** {', '.join(player['PLAYER_NAME'] for player in team1_players)}
        - **Last 3 Games:** {team1_last_3_games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']].to_dict('records')}
        - **Injuries & Absences:** {', '.join(f"{player['Player']} ({player['Status']})" for player in team1_missings.to_dict('records'))}

        ### **Team 2: {team2}**
        - **Record:** {team2_stats['W']}W - {team2_stats['L']}L
        - **Points Per Game:** {team2_stats['PTS']}
        - **Field Goal Percentage:** {team2_stats['FG_PCT']}
        - **Three-Point Percentage:** {team2_stats['FG3_PCT']}
        - **Key Players:** {', '.join(player['PLAYER_NAME'] for player in team2_players)}
        - **Last 3 Games:** {team2_last_3_games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']].to_dict('records')}
        - **Injuries & Absences:** {', '.join(f"{player['Player']} ({player['Status']})" for player in team2_missings.to_dict('records'))}

        ### **🗣️ Relevant Social Media Insights**
        {tweets_info}

        ## 🔍 **Analysis & Prediction**
        1. **Compare team performance metrics** (scoring, efficiency, defense, key player impact).  
        2. **Analyze recent form** (last 3 games and notable trends).  
        3. **Account for injuries and absences** (impact on rotations and depth).  
        4. **Factor in social media buzz** (any last-minute reports or significant trends).  
        5. **Determine the most probable winner with a confidence score (%)**.

        ---
        ## 🏆 **Winner Prediction**  
        **[Predicted_Winner]** (Confidence: [Confidence_Score]%)

        ### **Reasoning:**  
        [Detailed_Analysis]
        """

        try:
            # Try GPT-4 first
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            prediction = response['choices'][0]['message']['content']
            logging.info("Prediction generated using OpenAI GPT-4.")
            return prediction

        except Exception as e:
            logging.warning(f"OpenAI GPT-4 failed: {e}")
            logging.info("Falling back to DeepSeek...")
            # Try DeepSeek if OpenAI fails
            try:
                prediction = deepseek_chat(prompt)
                logging.info("Prediction generated using DeepSeek.")
                return prediction
            except Exception as de:
                logging.error(f"DeepSeek API also failed: {de}")
                return f"Error: Both OpenAI and DeepSeek failed. GPT error: {e}, DeepSeek error: {de}"

    except Exception as e:
        logging.error(f"Error generating prediction: {e}")
        return f"Error generating prediction: {e}"
    