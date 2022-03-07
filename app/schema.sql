CREATE TABLE IF NOT EXISTS user (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  profile_pic TEXT,
  push_time TEXT NOT NULL default '0900',
  notify_token TEXT,
  lang TEXT default 'ja'
);

CREATE TABLE IF NOT EXISTS user_channel (
  userid TEXT NOT NULL,
  channelid TEXT NOT NULL,
  notify integer,
  own integer
);
create index if not exists userindex on user_channel(userid); 

CREATE TABLE IF NOT EXISTS channel (
  channelid TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  publish_at TEXT NOT NULL,
  thumbnail TEXT,
  subscriberCount integer,
  viewCount integer,
  videoCount integer,
  commentCount integer,
  subscriberChange integer,
  viewChange integer,
  videoChange integer,
  commentChange integer
);

CREATE TABLE IF NOT EXISTS channel_history (
  channelid TEXT NOT NULL,
  date TEXT NOT NULL,
  subscriberCount integer,
  viewCount integer,
  videoCount integer,
  commentCount integer,
  subscriberChange integer,
  viewChange integer,
  videoChange integer,
  commentChange integer
);
create index if not exists channelindex on channel_history(channelid); 

CREATE TABLE IF NOT EXISTS channel_video (
  channelid TEXT PRIMARY KEY,
  video JSON 
);
create index if not exists channelindex on channel_video(channelid); 

CREATE TABLE IF NOT EXISTS video_waiting (
  channelid TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS video (
  videoid TEXT PRIMARY KEY,
  channelid TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  publish_at TEXT NOT NULL,
  thumbnail TEXT,
  categoryId TEXT,
  duration TEXT,
  viewCount integer,
  likeCount integer,
  dislikeCount integer,
  commentCount integer,
  viewChange integer,
  likeChange integer,
  dislikeChange integer,
  commentChange integer,
  lastUpdate TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_video (
  userid TEXT NOT NULL,
  videoid TEXT NOT NULL
);
create index if not exists userindex on user_video(userid); 

CREATE TABLE IF NOT EXISTS video_history (
  videoid TEXT NOT NULL,
  date TEXT NOT NULL,
  viewCount integer,
  likeCount integer,
  dislikeCount integer,
  commentCount integer,
  viewChange integer,
  likeChange integer,
  dislikeChange integer,
  commentChange integer,
  PRIMARY KEY(videoid,date)
);

CREATE TABLE IF NOT EXISTS site_history (
    id integer primary key,
    date TEXT NOT NULL,
    userCount integer,
    channelCount integer,
    videoCount integer,
    userChange integer,
    channelChange integer,
    videoChange integer
);