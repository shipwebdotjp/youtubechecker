# youtubechecker

指定したYoutubeチャンネルの登録者数を毎日一回LINEで通知

## Setting
1..envファイルにLINE Notifyトークンと，Google Data APIのキーを記入  
2.idlist.txtファイルにチェックしたいYoutubeチャンネルIDを一行ごとに一つ記載

## Install & Run
```
git clone https://github.com/shipwebdotjp/youtubechecker
cd youtubechecker
vi ./app/.env
LINE_TOKEN=<LINE NOTIFY TOKEN>
YOUTUBE_KEY=<GCP KEY>
:wq
docker-compose up -d --build
```

## Author
ship [Youtube channel](https://www.youtube.com/channel/UCne2IBkAj3JoyzNAOzXxKMg)
