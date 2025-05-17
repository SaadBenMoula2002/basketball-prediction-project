import tweepy
import pandas as pd
import json
from datetime import datetime, timedelta
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load API keys
with open('keys.json') as f:
    keys = json.load(f)

# Authenticate with Twitter API
client = tweepy.Client(bearer_token=keys['TWITTER_BEARER_TOKEN'])

def save_tweets(team1, team2, players):
    try:
        with open('usernames.txt', 'r') as f:
            usernames = f.read().splitlines()

        tweets_data = []
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=3)

        # Format timestamps correctly (RFC3339 format)
        start_time = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        for username in usernames:
            try:
                user = client.get_user(username=username)
                user_id = user.data.id
                tweets = client.get_users_tweets(
                    id=user_id,
                    max_results=5,  # Fetch up to 5 tweets
                    start_time=start_time,
                    end_time=end_time,
                    tweet_fields=["created_at", "text"]
                )
                if tweets and tweets.data:
                    # Take the first tweet, even if it's not relevant
                    first_tweet = tweets.data[0]
                    tweets_data.append({
                        'Username': username,
                        'Tweet': first_tweet.text,
                        'Created At': first_tweet.created_at.isoformat()  # Convert datetime to string
                    })
                    logging.info(f"Found tweet from {username}: {first_tweet.text}")
                    break  # Stop after finding the first tweet
                # Add a delay to avoid hitting rate limits
                time.sleep(2)  # 2-second delay between requests
            except tweepy.TooManyRequests as e:
                logging.error(f"Rate limit exceeded. Skipping tweet fetching.")
                return  # Bypass tweet fetching entirely
            except Exception as e:
                logging.error(f"Error fetching tweets for {username}: {e}")
                continue

        # Save the first tweet to CSV
        if tweets_data:
            pd.DataFrame(tweets_data).to_csv('tweets.csv', index=False)
            logging.info("Tweet saved to 'tweets.csv'.")
        else:
            logging.warning("No tweets found.")
    except Exception as e:
        logging.error(f"Error fetching tweets: {e}")




