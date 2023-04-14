import os
import tweepy
import openai
from datetime import datetime, timedelta
import pytz
from pytz import timezone
import random
import time
import re

# Load variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Load Twitter API v2 credentials & OpenAI API key
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Set up Twitter API
auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True)

# Set up OpenAI API
openai.api_key = OPENAI_API_KEY

# Set Tweet Format
def format_text(text, remove_newlines=False):
    # If remove_newlines is True, join sentences without newlines.
    if remove_newlines:
        # Split the text into sentences using regex.
        sentences = re.split('(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
        formatted_text = " ".join(sentences)
    else:
        formatted_text = text
    return formatted_text


# Get Topics from your "topics.txt"
def read_topics_from_file(file_path):
    topics = []
    with open(file_path, "r") as file:
        for line in file:
            # Remove leading and trailing whitespaces (including newlines) from each line
            topic = line.strip()
            if topic:  # Ignore empty lines
                topics.append(topic)
    return topics


def get_gpt_response(user_message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a warm and patient teaching assistant with expertise in Solidity, Smart Contract Auditing, and Blockchain Security. Provide informative and engaging answers while maintaining a lighthearted caretaker tone."},
            {"role": "user", "content": user_message},
        ],
        temperature=0.5,  # Adjust the randomness of the output. Lower values (e.g., 0.5) make the output more focused, while higher values (e.g., 1.0) make it more random.
        # max_tokens=1000,  # Set a limit to the number of tokens generated in the response.
    )
    return response.choices[0].message['content'].strip()

# Reply to mentions on Twitter (might turn off for now)
def reply_to_mentions():
    signature = "\n\n-- PickleBot 🥒"
    mentions = api.mentions_timeline()
    for mention in mentions:
        if not mention.favorited:
            question = mention.text.replace("@pickleyard", "").strip()
            response = get_gpt_response(question)
            formatted_response = format_text(response)
            response_with_signature = formatted_response + signature

            # Truncate the response to fit within Twitter's character limit
            max_length = 240 - len(mention.user.screen_name) - 2  # Subtract 2 for the '@' symbol and space
            if len(response_with_signature) > max_length:
                response_with_signature = response_with_signature[:max_length]

            api.update_status(f"@{mention.user.screen_name} {response_with_signature}", in_reply_to_status_id=mention.id)
            api.create_favorite(mention.id)

# Tweet a Good Morning thread
def tweet_security_tip():
    signature = "\n\n-- PickleBot 🥒"
    topics = read_topics_from_file("topics.txt")
    topic = random.choice(topics)
    user_message = f"Write a series of only 4 engaging tweets in a warm tone on {topic} for a non-technical audience. The first tweet should be an introduction to the series and not numbered like the rest of the tweets and should be within the same topic context of the previous tweet and explain in more detail with less than 225 characters."
    response = get_gpt_response(user_message)

    # Split the response into separate tweets
    tweets = response.split('\n\n')

    # Post the first tweet
    first_tweet = format_text(tweets[0], remove_newlines=True)
    if len(first_tweet) > 240:
        first_tweet = first_tweet[:first_tweet.rfind(' ', 0, 240)]
    tweet = api.update_status(first_tweet)

    # Post the remaining tweets as a thread
    for i in range(1, len(tweets)):
        tweet_text = format_text(tweets[i], remove_newlines=True)
        if i == len(tweets) - 1:
            # Add hashtags and signature only to the last tweet
            tweet_text += " #Security #Blockchain" + signature

        if len(tweet_text) > 240:
            tweet_text = tweet_text[:tweet_text.rfind(' ', 0, 240)]
        tweet = api.update_status(status=tweet_text, in_reply_to_status_id=tweet.id)



def main():

    scheduled_time = datetime.now(pytz.utc).replace(hour=14, minute=0, second=0, microsecond=0)
    last_checked_mentions = datetime.now(pytz.utc) - timedelta(hours=1)

    while True:
        now = datetime.now(pytz.utc)

        if now >= scheduled_time:
            tweet_security_tip()
            scheduled_time += timedelta(days=1)

        if (now - last_checked_mentions) >= timedelta(hours=1):
            reply_to_mentions()
            last_checked_mentions = now

        time.sleep(3600)  # Sleep for 3600 seconds (1 hour) before checking again

if __name__ == "__main__":
    tweet_security_tip()
    main()