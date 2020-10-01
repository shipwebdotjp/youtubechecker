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
