import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

LINE_TOKEN = os.environ.get("LINE_TOKEN")
YOUTUBE_KEY = os.environ.get("YOUTUBE_KEY")
