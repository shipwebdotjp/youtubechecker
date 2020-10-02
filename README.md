# Youtube Subscriber Checker

Notificate number of subscriber and total view count of specific Youtube Channel via LINE once a day.  
Add subscriber, view count and video count to each channel file as csv file.
So, you can see the transition in the data. To use Excel you can also draw a graph.

指定したYoutubeチャンネルの登録者数，総再生数と増減を毎日一回LINEで通知  
登録者数，再生数，動画数のデータをチャンネルごとにCSVファイルでダウンロード可能
それらのデータの推移知ることができ，Excelなどで読み込むことでグラフ表示も可能。

![LINE](https://blog.shipweb.jp/wp-content/uploads/2020/09/Screenshot-LINE01.jpg)

## Need API Keys
* LINE Notify token(for developers)
* LINE login channel(ID and secret)
* LINE messaging channel access token
* LINE Notify service(Client ID and secret)
* Google Data API Key

## 必要なAPI
* LINE Notify トークン(開発者向け)
* LINE ログインチャンネル(IDとシークレット)
* LINE メッセージングチャンネル アクセストークン
* LINE Notify サービス(クライアントIDとシークレット)
* Google Data APIキー

## Setting
1.input tokens to .env file.  

1..envファイルに各種トークンとキーを記入  


## Requirements
* Dcoker
* Python 3
* Flask

## Install
```
git clone https://github.com/shipwebdotjp/youtubechecker
cd youtubechecker
mkdir ./app/log
vi ./app/.env
--Edit Your Keys
:wq
```

### Run with Docker
```
docker-compose up -d --build
docker-compose exec python flask initdb
chmod 777 ./app
chmod 666 ./app/sqlite_db
```
Access http://localhost:5000/  

## Data file output
You can download CSV file format file  

### channels-%y%M%D.csv for example shipweb-201002.csv
```
"Channel Id","Channel name","Published at","subscriberCount","subscriberChange","viewCount","viewChange","videoCount","videoChange","commentCount","commentChange"
"UCne2IBkAj3JoyzNAOzXxKMg","shipweb","2015-11-29 10:55:00","52","0","17841","0","17","0","0","0"
```
### 'Channel name'-%y%M%D.csv for example shipweb-201002.csv
```
"Date","subscriberCount","subscriberChange","viewCount","viewChange","videoCount","videoChange","commentCount","commentChange"
"2020-10-02 00:02:01","52","0","17841","0","17","0","0","0"
```

## Demo site
[Youtube Checker](https://ytc.shipweb.jp/)

## Author
ship [Youtube channel](https://www.youtube.com/channel/UCne2IBkAj3JoyzNAOzXxKMg)

## Youtube Video
[![thumbnail](http://img.youtube.com/vi/JO33NnIL6es/0.jpg)](http://www.youtube.com/watch?v=JO33NnIL6es "Python Programming")

## License
MIT License