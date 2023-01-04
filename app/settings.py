import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

#From .env
LINE_TOKEN = os.environ.get("LINE_TOKEN")
YOUTUBE_KEY = os.environ.get("YOUTUBE_KEY")
LINE_CHANNEL_ID = os.environ.get("LINE_CHANNEL_ID")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
SECRET = os.environ.get("SECRET")
LINE_MESSAGING_TOKEN = os.environ.get("LINE_MESSAGING_TOKEN")
LINE_NOTIFY_ID = os.environ.get("LINE_NOTIFY_ID")
LINE_NOTIFY_SECRET = os.environ.get("LINE_NOTIFY_SECRET")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

MAX_VIDEOS_PER_USER = os.environ.get("MAX_VIDEOS_PER_USER")
MAX_CHANNELS_PER_USER = os.environ.get("MAX_CHANNELS_PER_USER")

IS_SEND_DAILY_STATISTICS = os.environ.get("IS_SEND_DAILY_STATISTICS")

#Local settings
channel_order = [
    {'title': 'Subscriber Day Descending', 'val':'subscriberChange desc'},
    {'title': 'Subscriber Day Ascending', 'val':'subscriberChange asc'},
    {'title': 'Subscriber Total Descending', 'val':'subscriberCount desc'},
    {'title': 'Subscriber Total Ascending', 'val':'subscriberCount asc'},
    {'title': 'View Day Descending', 'val':'viewChange desc'},
    {'title': 'View Day Ascending', 'val':'viewChange asc'},
    {'title': 'View Total Descending', 'val':'viewCount desc'},
    {'title': 'View Total Ascending', 'val':'viewCount asc'},
    {'title': 'Video Day Descending', 'val':'videoChange desc'},
    {'title': 'Video Day Ascending', 'val':'videoChange asc'},
    {'title': 'Video Total Descending', 'val':'videoCount desc'},
    {'title': 'Video Total Ascending', 'val':'videoCount asc'},
]
