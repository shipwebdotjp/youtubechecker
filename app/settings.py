import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

LINE_TOKEN = os.environ.get("LINE_TOKEN")
YOUTUBE_KEY = os.environ.get("YOUTUBE_KEY")
LINE_CHANNEL_ID = os.environ.get("LINE_CHANNEL_ID")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
SECRET = os.environ.get("SECRET")
LINE_MESSAGING_TOKEN = os.environ.get("LINE_MESSAGING_TOKEN")
LINE_NOTIFY_ID = os.environ.get("LINE_NOTIFY_ID")
LINE_NOTIFY_SECRET = os.environ.get("LINE_NOTIFY_SECRET")
MAX_CHANNELS_PER_USER = os.environ.get("MAX_CHANNELS_PER_USER")