# Youtube Subscriber Checker

Notificate number of subscriber of specific Youtube Channel via LINE once a day.  
指定したYoutubeチャンネルの登録者数を毎日一回LINEで通知  

![LINE](https://blog.shipweb.jp/wp-content/uploads/2020/09/Screenshot-LINE01.jpg)

## Setting
1.input LINE Notify token and Google Data API Key to .env file.  
2.add Youtube channel ID to idlist.txt (1 id per 1 line)  

1..envファイルにLINE Notifyトークンと，Google Data APIのキーを記入  
2.idlist.txtファイルにチェックしたいYoutubeチャンネルIDを一行ごとに一つ記載  


## Requirements
* Python 3
* Dcoker

## Install
```
git clone https://github.com/shipwebdotjp/youtubechecker
cd youtubechecker
vi ./app/.env
LINE_TOKEN=<LINE NOTIFY TOKEN>
YOUTUBE_KEY=<GCP KEY>
:wq
echo 'Youtube channel ID' > ./app/idlist.txt
```

### Run with Docker
```
docker-compose up -d --build
```

### Run with Standalone Python
```
pip install -r requirements.txt
nohup python ./app/youtubechecker.py &
```


## Author
ship [Youtube channel](https://www.youtube.com/channel/UCne2IBkAj3JoyzNAOzXxKMg)


## License
MIT License