import os
import requests
import pickle
import schedule
import time
import csv
import datetime
import re
import json
import sqlite3
from apiclient.discovery import build
from googleapiclient import errors
import settings

def main(): # メイン関数
    job() # 起動時に一回実行
    #schedule.every().day.at("23:30").do(job) # 毎日23:30分に実行 UTC+0で記載
    #while True:
    #    schedule.run_pending()
    #    time.sleep(1)

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

def check_channelid(channelid):
    return re.search('(UC[a-zA-Z0-9_-]+)',channelid)

def deletechannel(channelid):
    if not query_db('select * from user_channel where channelid = ?',[channelid],True): # 使用しているユーザーがほかにいない
        db = get_db()
        db.execute("DELETE FROM channel where channelid = ?", (channelid,))
        db.execute("DELETE FROM channel_history where channelid = ?", (channelid,))
        db.commit()
        return True
    else:
        return False

def send_line_push(to,messages):
    line_message_token = settings.LINE_MESSAGING_TOKEN
    line_message_api = 'https://api.line.me/v2/bot/message/push'
    headers = {'Authorization': f'Bearer {line_message_token}', 'Content-Type': f'application/json'}
    data = {'to':to, 'messages': messages}
    response = requests.post(line_message_api, headers = headers, data = json.dumps(data)) 
    return response   

def getChannelData(channelids): # Youtube Data APIチャンネル情報取得
    ids = ','.join(channelids)
    youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_KEY)
    new_channel_list = list()
    try:
        response = youtube.channels().list(
                part='snippet,statistics',
                id=ids,
                maxResults=50
            ).execute() # Youtube APIへのリクエスト作成
        for item in response['items']:
            new_channel_list.append({
                'channelid':item['id'],
                'title':item['snippet']['title'],
                'publish_at':item['snippet']['publishedAt'],
                'subscriberCount':item['statistics']['subscriberCount'],
                'viewCount': item['statistics']['viewCount'],
                'videoCount': item['statistics']['videoCount'],
                'commentCount': item['statistics']['commentCount']
            })
        return new_channel_list
    except errors.HttpError as err:
        return {'error':err._get_reason()}

def job(): # Youtube Data APIへアクセスする
    dbpath = os.path.join(os.path.dirname(__file__),'sqlite_db')
    connection = sqlite3.connect(dbpath)
    db = connection.cursor()
    db.row_factory = sqlite3.Row
    APIKEY = settings.YOUTUBE_KEY
    dataFinish = False
    start=0
    while dataFinish == False:
        cur = db.execute('select channelid from channel limit ?,50', (start,))
        rv = cur.fetchall()
        #cur.close()
        idlines = rv # 読み込んだ後，改行で分割して，リストへ代入
        print (str(start) + ' '+ str(len(idlines)))
        if len(idlines) == 0:
            break
        start += 50
        idlist = list()
        for channel in idlines:
            idlist.append(channel['channelid'])
        ids = ','.join(idlist) # リストをコンマで結合して文字列

        youtube = build('youtube', 'v3', developerKey=APIKEY) # Youtube APIへアクセスするオブジェクト作成

        result = list() # 結果を入れるためのリスト
        new_channel_dict = {} # データ保存用の新たなリスト
        try:
            response = youtube.channels().list(
                    part='snippet,statistics',
                    id=ids,
                    maxResults=50
                ).execute() # Youtube APIへのリクエスト作成
        except errors.HttpError as err:
            # HTTPエラーが生じた場合は，エラーメッセージを表示。
            print('There was an error creating the model. Check the details:')
            print(err._get_reason())
            send_line_notify(err._get_reason()) # LINEでもエラーを通知
        for item in response['items']: # 帰ってきた結果をチャンネルごと処理
            cur = db.execute('select * from channel where channelid = ?', (item['id'],))
            rv = cur.fetchall()
            #cur.close()
            curdata = rv[0]
            if curdata: # 以前のデータが保存されているかどうか
                subscriberChange = int(item['statistics']['subscriberCount']) - int(curdata['subscriberCount'])
                viewChange = int(item['statistics']['viewCount']) - int(curdata['viewCount'])
                videoChange = int(item['statistics']['videoCount']) - int(curdata['videoCount'])
                commentChange = int(item['statistics']['commentCount']) - int(curdata['commentCount'])
                #change = ('+' if change > 0 else '') + "{:,}".format(change) # プラスの場合は先頭に＋をつける
            else: # 以前のデータが保存されていなければ，増減値は「New」にする
                subscriberChange = 0
                viewChange = 0
                videoChange = 0
                commentChange = 0
            db.execute(
                    "UPDATE channel SET title = ?,subscriberCount = ?,viewCount = ?,videoCount = ?,commentCount = ?,subscriberChange = ?,viewChange = ?,videoChange = ?,commentChange = ? WHERE channelid = ?",
                    (item['snippet']['title'],
                        item['statistics']['subscriberCount'],
                        item['statistics']['viewCount'],
                        item['statistics']['videoCount'],
                        item['statistics']['commentCount'],
                        subscriberChange,viewChange,videoChange,commentChange,item['id']),
            )
            db.execute(
                    "INSERT INTO channel_history (channelid, date,subscriberCount,viewCount,videoCount,commentCount,subscriberChange,viewChange,videoChange,commentChange) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (item['id'],
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        item['statistics']['subscriberCount'],
                        item['statistics']['viewCount'],
                        item['statistics']['videoCount'],
                        item['statistics']['commentCount'],
                        subscriberChange,viewChange,videoChange,commentChange),
            )
            connection.commit() 
            #print('Channel: '+item['snippet']['title']+' Subscriber: '+item['statistics']['subscriberCount']+ ' Change: '+str(subscriberChange)+' viewCount: '+item['statistics']['viewCount']+ ' Change: '+str(viewCountchange))
            # リストにチャンネルごとの結果を追加
            #result.append(item['snippet']['title']+' Subscriber: '+"{:,}".format(int(item['statistics']['subscriberCount']))+ ' ('+change+')'+' view: '+"{:,}".format(int(item['statistics']['viewCount']))+ ' ('+viewCountchange+')')
        
            #n = 10
            #for split_result in [result[idx:idx + n] for idx in range(0,len(result), n)]: # リストを10ずつ分割（長すぎると切れるため）
            #    send_line_notify('\n'+'\n'.join(split_result)) # 結果が入ったリストを改行で結合させて，LINE Notifyで結果をLINEに送信する
            
            #channelcsv_save(new_channel_dict,channel_dict_path) # 今回取得したデータを次回増減を出すために保存
    connection.close()

if __name__ == '__main__':
	main() #メイン関数を呼び出し