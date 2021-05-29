import os
import requests
import time
import csv
import datetime
import re
import json
import sqlite3
import click
from apiclient.discovery import build
from googleapiclient import errors
from db import init_db_command, get_db, query_db
from flask.cli import with_appcontext
import settings

def send_line_notify(notification_message, notify_token=settings.LINE_TOKEN): # LINE Notifyで通知する
    line_notify_token = notify_token
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': f'{notification_message}'}
    res = requests.post(line_notify_api, headers = headers, data = data)
    if res.status_code == 401:
        notify_revoke_from_token(line_notify_token)

def notify_revoke_from(user_id):
    userdata = query_db('select notify_token from user where id = ?',(user_id,),True)
    line_notify_token = userdata['notify_token']
    line_notify_api = 'https://notify-api.line.me/api/revoke'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {}
    res = requests.post(line_notify_api, headers = headers, data = data) 
    if res.status_code == 401:
        retval = 'Already unlinked.'
    else:
        retval = 'Unlinked.'
    notify_revoke_from_token(line_notify_token)
    return retval

def notify_revoke_from_token(line_notify_token):
    db = get_db()
    db.execute(
        "UPDATE user SET notify_token = null where notify_token = ?",
        (line_notify_token,),
    )
    db.commit()

def check_channelid(channelid):
    return re.search('(UC[a-zA-Z0-9_-]+)',channelid)

def name_to_id(name):
    new_channel_list = list()
    youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_KEY)
    try:
        response = youtube.channels().list(part='id', forUsername=name).execute() # Youtube APIへのリクエスト作成
        for item in response['items']:
            new_channel_list.append(item['id'])
        return new_channel_list
    except errors.HttpError as err:
        return {'error':err._get_reason()}

def custom_to_id(name):
    youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_KEY)
    try:
        response = youtube.search().list(part='id', type='channel', q=name).execute() # Youtube APIへのリクエスト作成
        if len(response['items']):
            item = response['items'][0]
            return [item['id']['channelId']]
        return []
    except errors.HttpError as err:
        return {'error':err._get_reason()}

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
    new_channel_list = list()
    n = 50
    for split_result in [channelids[idx:idx + n] for idx in range(0,len(channelids), n)]: # リストを50ずつ分割（長すぎると切れるため）
        ids = ','.join(split_result)
        youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_KEY)

        try:
            response = youtube.channels().list(
                    part='snippet,statistics',
                    id=ids,
                    maxResults=50
                ).execute() # Youtube APIへのリクエスト作成
            if response.get('items'):
                for item in response['items']:
                    id = item.get('id')
                    if item.get('snippet') and item.get('statistics'):
                        new_channel_list.append({
                            'channelid':id,
                            'title':item['snippet'].get('title'),
                            'publish_at':item['snippet'].get('publishedAt'),
                            'subscriberCount':item['statistics'].get('subscriberCount'),
                            'viewCount': item['statistics'].get('viewCount'),
                            'videoCount': item['statistics'].get('videoCount'),
                            'commentCount': item['statistics'].get('commentCount')
                        })
            
        except errors.HttpError as err:
            return {'error':err._get_reason()}

    return new_channel_list

def job(): # Youtube Data APIへアクセスする
    db = get_db()
    APIKEY = settings.YOUTUBE_KEY
    dataFinish = False
    start=0
    while dataFinish == False:
        idlines = query_db('select channelid from channel limit ?,50', [start])
        if not idlines:
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
                    part='statistics',
                    id=ids,
                    maxResults=50
                ).execute() # Youtube APIへのリクエスト作成
        except errors.HttpError as err:
            # HTTPエラーが生じた場合は，エラーメッセージを表示。
            print('There was an error creating the model. Check the details:')
            print(err._get_reason())
            send_line_notify(err._get_reason()) # LINEでもエラーを通知
        if response.get('items'):
            for item in response['items']: # 帰ってきた結果をチャンネルごと処理
                id = item.get('id')
                print(id)
                curdata = query_db('select * from channel where channelid = ?', [id], True)
                if curdata and item.get('statistics'): # 以前のデータが保存されているかどうか
                    subscriberCount = item['statistics'].get('subscriberCount')
                    viewCount = item['statistics'].get('viewCount')
                    videoCount = item['statistics'].get('videoCount')
                    commentCount = item['statistics'].get('commentCount')
                    subscriberChange = int(0 if subscriberCount is None else subscriberCount) - int(0 if curdata['subscriberCount'] is None else curdata['subscriberCount'])
                    viewChange = int(0 if viewCount is None else viewCount) - int(0 if curdata['viewCount'] is None else curdata['viewCount'])
                    videoChange = int(0 if videoCount is None else videoCount) - int(0 if curdata['videoCount'] is None else curdata['videoCount'])
                    commentChange = int(0 if commentCount is None else commentCount) - int(0 if curdata['commentCount'] is None else curdata['commentCount'])
                    #change = ('+' if change > 0 else '') + "{:,}".format(change) # プラスの場合は先頭に＋をつける
                else: # 以前のデータが保存されていなければ，増減値は「New」にする
                    subscriberChange = 0
                    viewChange = 0
                    videoChange = 0
                    commentChange = 0
                db.execute(
                        "UPDATE channel SET subscriberCount = ?,viewCount = ?,videoCount = ?,commentCount = ?,subscriberChange = ?,viewChange = ?,videoChange = ?,commentChange = ? WHERE channelid = ?",
                        (
                            subscriberCount,
                            viewCount,
                            videoCount,
                            commentCount,
                            subscriberChange,viewChange,videoChange,commentChange,id),
                )
                db.execute(
                        "INSERT INTO channel_history (channelid, date,subscriberCount,viewCount,videoCount,commentCount,subscriberChange,viewChange,videoChange,commentChange) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (
                            id,
                            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            subscriberCount,
                            viewCount,
                            videoCount,
                            commentCount,
                            subscriberChange,viewChange,videoChange,commentChange),
                )
                db.commit()
                print(f'{subscriberCount},{viewCount},{videoCount},{commentCount},{subscriberChange},{viewChange},{videoChange},{commentChange}')
    idlines = query_db('select count(channelid) from channel',(),True)
    userlines = query_db('select count(id) from user',(),True)
    return f'Channel Count: {idlines[0]:,d} User Count: {userlines[0]:,d}'


def send_notify_each_user():
    nowtime = datetime.datetime.now().strftime('%H%M')
    for user in query_db('select id,notify_token from user where push_time = ?', [nowtime]):
        if user['notify_token']:
            send_notify_from_user(user['id'],user['notify_token'])
            print('Send notify to '+user['id'])
    print("finished at "+nowtime)    

def send_notify_from_user(user_id,notify_token):
    result = list()
    for channel in query_db('select user_channel.channelid,channel.title,channel.publish_at,channel.subscriberCount,channel.viewCount,channel.videoCount,channel.commentCount,channel.subscriberChange,channel.viewChange,channel.videoChange,channel.commentChange from user_channel left outer join channel on user_channel.channelid = channel.channelid where user_channel.userid = ?',
        [user_id]):
        result.append(
            channel['title']+
            ' Subscriber: '+"{:,}".format(int(0 if channel['subscriberCount'] is None else channel['subscriberCount']))+ ' ('+str(change_format(channel['subscriberChange']))+')'+
            ' View: '+"{:,}".format(int(channel['viewCount']))+ ' ('+str(change_format(channel['viewChange']))+')')
    n = 10
    for split_result in [result[idx:idx + n] for idx in range(0,len(result), n)]: # リストを10ずつ分割（長すぎると切れるため）
        send_line_notify('\n'+'\n'.join(split_result),notify_token) # 結果が入ったリストを改行で結合させて，LINE Notifyで結果をLINEに送信する

def change_format(change):
    change = ('+' if change > 0 else ('±' if change == 0 else '')) + "{:,}".format(change) # プラスの場合は先頭に＋をつける
    return change
