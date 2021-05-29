# Youtube Subscriber Checker

Notificate number of subscriber and total view count of specific Youtube Channel via LINE once a day.  
Add subscriber, view count and video count to each channel file as csv file.
So, you can see the transition in the data. To use Excel you can also draw a graph.

指定したYoutubeチャンネルの登録者数，総再生数と増減を毎日一回LINEで通知  
登録者数，再生数，動画数のデータをチャンネルごとにCSVファイルに記録していく
それらのデータの推移知ることができ，Excelなどで読み込むことでグラフ表示も可能。

![LINE](https://blog.shipweb.jp/wp-content/uploads/2020/09/Screenshot-LINE01.jpg)

## Setting
1. input LINE Notify token and Google Data API Key to .env file.  
 .envファイルにLINE Notifyトークンと，Google Data APIのキーを記入   
2. write Youtube channel ID to idlist.txt (1 id per 1 line)  
 idlist.txtファイルを作成しチェックしたいYoutubeチャンネルIDを一行ごとに一つ記載  

## Requirements
* Python 3
* Dcoker

## Install
```
git clone https://github.com/shipwebdotjp/youtubechecker
cd youtubechecker
cp ./app/.env.sample ./app/.env
vi ./app/.env
LINE_TOKEN=<LINE NOTIFY TOKEN>
YOUTUBE_KEY=<GCP KEY>
:wq
```

### Run with Docker
```
docker-compose up -d --build
```

## Data file output
You can download csv file from /channellist which contains current data of all channels.  
If you want to see the history, see the each channel page.
You can find CSV Download button.  

## CSV file format
### channels.csv
```
"id","title","subscriberCount","viewCount","videoCount","commentCount"
"UCne2IBkAj3JoyzNAOzXxKMg","shipweb","51","17418","17","0"
```
### 'channelid'.csv for example UCne2IBkAj3JoyzNAOzXxKMg.csv
```
date,subscriberCount,viewCount,videoCount,commentCount
20/09/26 07:00:53,51,17413,17,0
20/09/27 07:00:32,51,17417,17,0
20/09/28 07:00:46,51,17417,17,0
```

## Author
ship [Youtube channel](https://www.youtube.com/channel/UCne2IBkAj3JoyzNAOzXxKMg)

## Youtube Video
[![thumbnail](http://img.youtube.com/vi/JO33NnIL6es/0.jpg)](http://www.youtube.com/watch?v=JO33NnIL6es "Python Programming")

## License
MIT License