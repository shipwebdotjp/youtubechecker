import os
import requests
import pickle
import schedule
import time
import csv
import datetime
from apiclient.discovery import build
from googleapiclient import errors
import settings

def main(): # メイン関数
    job() # 起動時に一回実行
    schedule.every().day.at("23:30").do(job) # 毎日23:30分に実行 UTC+0で記載
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

def channelcsv_load(path): 
    data = {}
    if os.path.exists(path):
        with open(path, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data[row['id']] = row
            return data
    else:
        return data

def channelcsv_save(data,path): 
    k_list = list(data.keys())
    header = data[k_list[0]].keys()
    with open(path, mode='w') as f:
        writer = csv.DictWriter(f,delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL, fieldnames=header)
        writer.writeheader()
        for k,v in data.items():
            writer.writerow(v)

def add_new_history(id,newdata):
    header = newdata.keys()
    path = os.path.join(os.path.dirname(__file__),'channel', id+'.csv')
    if not os.path.isdir(os.path.join(os.path.dirname(__file__),'channel')):
        os.mkdir(os.path.join(os.path.dirname(__file__),'channel'))

    isExists = os.path.exists(path)
    with open(path, mode='a') as f:
        writer = csv.DictWriter(f,delimiter=',', lineterminator='\n',fieldnames=header)
        if not isExists:
            writer.writeheader()

        writer.writerow(newdata)

def send_line_notify(notification_message): # LINE Notifyで通知する
    line_notify_token = settings.LINE_TOKEN
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': f'{notification_message}'}
    requests.post(line_notify_api, headers = headers, data = data)

def job(): # Youtube Data APIへアクセスする
    APIKEY = settings.YOUTUBE_KEY
    idfilepath = os.path.join(os.path.dirname(__file__), 'idlist.txt') # 調査するIDが書かれたファイル
    channel_dict_path = os.path.join(os.path.dirname(__file__), 'channels.csv') # チャンネルデータ保存用CSVファイル

    if os.path.exists(idfilepath): # チェックするIDリストが記載されたファイルが存在するかチェック
        with open(idfilepath, mode='r') as f: # チャネルIDリストファイルを読み込み
            idlines = f.read().splitlines() # 読み込んだ後，改行で分割して，リストへ代入
        ids = ','.join(idlines) # リストをコンマで結合して文字列
    else: # チェックするIDリストが記載されたファイルが存在しない場合エラーを出力して終了
        err = 'File not found: idlist.txt\nPlease write channel id to idlist.txt'
        print(err)
        send_line_notify(err)
        exit()

    channel_dict = channelcsv_load(channel_dict_path) # 保存してあるチャンネルデータをロード
    youtube = build('youtube', 'v3', developerKey=APIKEY) # Youtube APIへアクセスするオブジェクト作成

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
                current_subscriber = int(item['statistics']['subscriberCount']) # 現在の登録者数
                last_subscriber = int(channel_dict.get(item['id'])['subscriberCount']) # 前回の登録者数
                change = current_subscriber - last_subscriber # 今回から前回の値を減算
                change = ('+' if change > 0 else '') + "{:,}".format(change) # プラスの場合は先頭に＋をつける
                viewCountchange = int(item['statistics']['viewCount']) -  int(channel_dict.get(item['id'])['viewCount'])
                viewCountchange = ('+' if viewCountchange > 0 else '') + "{:,}".format(viewCountchange) # プラスの場合は先頭に＋をつける
            else: # 以前のデータが保存されていなければ，増減値は「New」にする
                change = 'New'
                viewCountchange = 'New'

            new_channel_dict[item['id']] = {
                'id':item['id'],
                'title':item['snippet']['title'],
                'subscriberCount':item['statistics']['subscriberCount'],
                'viewCount': item['statistics']['viewCount'],
                'videoCount': item['statistics']['videoCount'],
                'commentCount': item['statistics']['commentCount']
            } # 次回の参照用に保存するリストを新たに作成
            new_history = {
                'date': datetime.datetime.now().strftime('%y/%m/%d %H:%M:%S'),
                'subscriberCount':item['statistics']['subscriberCount'],
                'viewCount': item['statistics']['viewCount'],
                'videoCount': item['statistics']['videoCount'],
                'commentCount': item['statistics']['commentCount']
            }
            add_new_history(item['id'],new_history) # 各種データの履歴を保存
            print('Channel: '+item['snippet']['title']+' Subscriber: '+item['statistics']['subscriberCount']+ ' Change: '+change+' viewCount: '+item['statistics']['viewCount']+ ' Change: '+viewCountchange)
            # リストにチャンネルごとの結果を追加
            result.append(item['snippet']['title']+' Subscriber: '+"{:,}".format(int(item['statistics']['subscriberCount']))+ ' ('+change+')'+' viewCount: '+"{:,}".format(int(item['statistics']['viewCount']))+ ' ('+viewCountchange+')')

        send_line_notify('\n'+'\n'.join(result)) # 結果が入ったリストを改行で結合させて，LINE Notifyで結果をLINEに送信する
        channelcsv_save(new_channel_dict,channel_dict_path) # 今回取得したデータを次回増減を出すために保存
    except errors.HttpError as err:
        # HTTPエラーが生じた場合は，エラーメッセージを表示。
        print('There was an error creating the model. Check the details:')
        print(err._get_reason())
        send_line_notify(err._get_reason()) # LINEでもエラーを通知

main() #メイン関数を呼び出し