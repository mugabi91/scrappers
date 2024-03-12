import config
import tweepy
import sqlite3
import schedule
import time
import os 
import requests
from requests.exceptions import Timeout, ConnectionError
from datetime import datetime
import socket
import urllib3

# Authenticating to Twitter API
try:
    auth = tweepy.OAuth1UserHandler(config.CONSUMER_KEY, config.CONSUMER_SECRET, config.ACCESS_TOKEN, config.ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
except AttributeError as e:
    print(f"Error authenticating to Twitter API: {e}")
    exit()

# Connecting to SQLite database
conn = sqlite3.connect('tweets.db')
c = conn.cursor()

# Creating table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS tweets
             (id_str TEXT PRIMARY KEY, text TEXT)''')
conn.commit()

# where images are to be saved  
image_dir = 'images'
os.makedirs(image_dir, exist_ok=True)

def download_image(url, filename, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(os.path.join(image_dir, f"{filename}.jpg"), 'wb') as f:
                    f.write(response.content)
                print(f"Image:{filename} downloaded")
                return
        except Timeout:
            print("Request timed out. Retrying...")
        except Exception as e:
            print(f"An error occurred while downloading image: {e}")
    print("Max retries exceeded. Request Failed")

def scrape_twitter_profile():
    print("starting scrapping task")
    username = config.TWITTER_USERNAME
    try:
        tweets = api.user_timeline(screen_name=username, count=10)
    except Exception as e:
        print(f"Error fetching tweets: {e}")
        return

    for tweet in tweets:
        c.execute("SELECT * FROM tweets WHERE id_str=?", (tweet.id_str,))
        existing_tweet = c.fetchone()
        if existing_tweet:
            print("No new tweet")
        else:
            try:
                c.execute("INSERT INTO tweets (id_str, text) VALUES (?, ?)", (tweet.id_str, tweet.text))
                conn.commit()
                print("New tweet:", tweet.text)

                if 'media' in tweet.entities:
                    media = tweet.entities['media']
                    if media[0]['type'] == 'photo':
                        image_url = media[0]['media_url']
                        download_image(image_url, tweet.id_str)
            except Exception as e:
                print(f"An error occurred while processing tweet: {e}")

print("Twitter scraping script is running...")

# Scheduling the scraping task to run every 1 minute (for testing purposes)
schedule.every(1).minutes.do(scrape_twitter_profile)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except (socket.gaierror, urllib3.exceptions.NameResolutionError) as e:
        print(f"Error connecting to Twitter API: {e}")
        time.sleep(60)  # Wait for 1 minute before retrying
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        time.sleep(60)  # Wait for 1 minute before retrying
