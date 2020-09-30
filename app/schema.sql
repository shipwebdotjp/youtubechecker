CREATE TABLE user (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  profile_pic TEXT,
  push_time TEXT NOT NULL default '0000',
  notify_token TEXT
);

CREATE TABLE user_channel (
  userid TEXT NOT NULL,
  channelid TEXT NOT NULL
);
create index userindex on user_channel(userid); 

CREATE TABLE channel (
  channelid TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  publish_at TEXT NOT NULL,
  subscriberCount integer,
  viewCount integer,
  videoCount integer,
  commentCount integer,
  subscriberChange integer,
  viewChange integer,
  videoChange integer,
  commentChange integer
);

CREATE TABLE channel_history (
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
create index channelindex on channel_history(channelid); 
