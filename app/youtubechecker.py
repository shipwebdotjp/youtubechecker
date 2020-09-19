import os
import requests
import pickle
import schedule
import time
from apiclient.discovery import build
from googleapiclient import errors
import settings

def main(): # メイン関数
    job() # 起動時に一回実行
    schedule.every().day.at("23:30").do(job) # 毎日23:30分に実行
    while True:
        schedule.run_pending()
        time.sleep(1)

def pickle_dump(obj, path): # データ保存用
    with open(path, mode='wb') as f:
        pickle.dump(obj,f)

def pickle_load(path): # データ読み出し用
    if os.path.exists(path):
        with open(path, mode='rb') as f:
            data = pickle.load(f)
            return data
    else:
        return None

def send_line_notify(notification_message): # LINE Notifyで通知する
    line_notify_token = settings.LINE_TOKEN
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': f'{notification_message}'}
    requests.post(line_notify_api, headers = headers, data = data)

def job(): # Youtube Data APIへアクセスする
    APIKEY = settings.YOUTUBE_KEY
    idfilepath = os.path.join(os.path.dirname(__file__), 'idlist.txt') # 調査するIDが書かれたファイル
    channel_dict_path = os.path.join(os.path.dirname(__file__), 'channel_dict.pickle') # データ保存用ファイル
    
    channel_dict = pickle_load(channel_dict_path) # 保存してあるデータをロード
    if channel_dict == None: # 初回の場合は空でデータ作成
        channel_dict = {}

    youtube = build('youtube', 'v3', developerKey=APIKEY) # Youtube APIへアクセスするオブジェクト作成

    if os.path.exists(idfilepath): # チェックするIDリストが記載されたファイルが存在するかチェック
        with open(idfilepath, mode='r') as f: # チャネルIDリストファイルを読み込み
            idlines = f.read().splitlines() # 読み込んだ後，改行で分割して，リストへ代入
        ids = ','.join(idlines) # リストをコンマで結合して文字列
    else: # チェックするIDリストが記載されたファイルが存在しない場合は終了
        exit()

    result = list() # 結果を入れるためのリスト
    new_channel_dict = {} # データ保存用の新たなリスト
    try:
        response = youtube.channels().list(
                part='snippet,statistics',
                id=ids,
                maxResults=50
            ).execute() # Youtube APIへのリクエスト作成
        for item in response['items']: # 帰ってきた結果をチャンネルごと処理
            if item['id'] in channel_dict.keys(): # 以前のデータが保存されているかどうか
                change = int(item['statistics']['subscriberCount']) - int(channel_dict.get(item['id'])['subscriberCount']) # 今回から前回の値を減算
                change = ('+' if change > 0 else '') + str(change) + "人" # プラスの場合は先頭に＋をつけて人を最後につける
            else: # 以前のデータが保存されていなければ，増減値は「New」にする
                change = 'New'

            new_channel_dict[item['id']] = {
                'title':item['snippet']['title'],
                'subscriberCount':item['statistics']['subscriberCount'],
                'change': change
            } # 次回の参照用に保存するリストを新たに作成
            print('チャンネル名: '+item['snippet']['title']+' 登録者数: '+item['statistics']['subscriberCount']+ ' 増減: '+change)
            # リストにチャンネルごとの結果を追加
            result.append(item['snippet']['title']+' 登録者数: '+item['statistics']['subscriberCount']+ ' 増減: '+change)

        send_line_notify('\n'+'\n'.join(result)) # 結果が入ったリストを改行で結合させて，LINE Notifyで結果をLINEに送信する
        pickle_dump(new_channel_dict,channel_dict_path) # 今回取得したデータを次回増減を出すために保存
    except errors.HttpError as err:
        # HTTPエラーが生じた場合は，エラーメッセージを表示。
        print('There was an error creating the model. Check the details:')
        print(err._get_reason())

main() #メイン関数を呼び出し