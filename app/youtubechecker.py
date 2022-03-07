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
import functions

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

def check_videoid(videoid):
    return re.search('([a-zA-Z0-9_-]{11})',videoid)

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
                # print(id)
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
                # print(f'{subscriberCount},{viewCount},{videoCount},{commentCount},{subscriberChange},{viewChange},{videoChange},{commentChange}')
    idlines = query_db('select count(channelid) from channel',(),True)
    userlines = query_db('select count(id) from user',(),True)
    videolines = query_db('select count(videoid) from video',(),True)
    curdata = query_db('select * from site_history order by id desc limit 0,1', (), True)
    userCount = userlines[0]
    channelCount = idlines[0]
    videoCount = videolines[0]
    if curdata:
        userChange = userCount - curdata['userCount']
        channelChange = channelCount - curdata['channelCount']
        videoChange = videoCount - curdata['videoCount']
    else:
        userChange = 0
        channelChange = 0
        videoChange = 0
    db.execute(
                    "INSERT INTO site_history (date,userCount,channelCount,videoCount,userChange,channelChange,videoChange) VALUES(?,?,?,?,?,?,?)",
                    (
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        userCount,
                        channelCount,
                        videoCount,
                        userChange,
                        channelChange,
                        videoChange
                    ),
                )
    db.commit()
    return f'Channel Count: {channelCount:,d} ({str(change_format(channelChange))}) User Count: {userCount:,d} ({str(change_format(userChange))}) Video Count: {videoCount:,d} ({str(change_format(videoChange))})'


def send_notify_each_user():
    nowtime = datetime.datetime.now().strftime('%H%M')
    for user in query_db('select id,notify_token from user where push_time = ?', [nowtime]):
        if user['notify_token']:
            send_notify_from_user(user['id'],user['notify_token'],['channel','video'])
            print('Send notify to '+user['id'])
    print("finished at "+nowtime)    

def send_notify_from_user(user_id,notify_token,category):
    if 'channel' in category:
        result = list()
        for channel in query_db('select user_channel.channelid,channel.title,channel.publish_at,channel.subscriberCount,channel.viewCount,channel.videoCount,channel.commentCount,channel.subscriberChange,channel.viewChange,channel.videoChange,channel.commentChange from user_channel left outer join channel on user_channel.channelid = channel.channelid where user_channel.userid = ?',
            [user_id]):
            result.append(
                channel['title']+
                ' 🔔: '+functions.human_format(int(0 if channel['subscriberCount'] is None else channel['subscriberCount']))+ ' ('+str(change_format(channel['subscriberChange']))+')'+
                ' 👀: '+functions.human_format(int(channel['viewCount']))+ ' ('+str(change_format(channel['viewChange']))+')'+
                ' 🎞: '+functions.human_format(int(channel['videoCount']))+ ' ('+str(change_format(channel['videoChange']))+')')
        n = 10
        for split_result in [result[idx:idx + n] for idx in range(0,len(result), n)]: # リストを10ずつ分割（長すぎると切れるため）
            send_line_notify('\n'+'\n'.join(split_result),notify_token) # 結果が入ったリストを改行で結合させて，LINE Notifyで結果をLINEに送信する

    if 'video' in category:
        video_result = list()
        for video in query_db('select user_video.videoid,video.title,video.publish_at,video.duration,video.viewCount,video.likeCount,video.dislikeCount,video.commentCount,video.viewChange,video.likeChange,video.dislikeChange,video.commentChange from user_video left outer join video on user_video.videoid = video.videoid where user_video.userid = ?', [user_id]):
            video_result.append(video['title'][:15]+' 👀: '+functions.human_format(int(0 if video['viewCount'] is None else video['viewCount']))+ ' ('+str(change_format(video['viewChange']))+')'+' 👍: '+functions.human_format(int(0 if video['likeCount'] is None else video['likeCount']))+ ' ('+str(change_format(video['likeChange']))+')'+' 👎: '+functions.human_format(int(0 if video['dislikeCount'] is None else video['dislikeCount']))+ ' ('+str(change_format(video['dislikeChange']))+')'+' 💬: '+functions.human_format(int(0 if video['commentCount'] is None else video['commentCount']))+ ' ('+str(change_format(video['commentChange']))+')')
        n = 10
        for split_result in [video_result[idx:idx + n] for idx in range(0,len(video_result), n)]: # リストを10ずつ分割（長すぎると切れるため）
            send_line_notify('\n'+'\n'.join(split_result),notify_token) # 結果が入ったリストを改行で結合させて，LINE Notifyで結果をLINEに送信する

def change_format(change):
    change = ('+' if change > 0 else ('±' if change == 0 else '')) + "{:,}".format(change) # プラスの場合は先頭に＋をつける
    return change

def getChannelUploads(channelids): # Youtube Data APIチャンネル　アップロード画像のプレイリスト取得
    new_channel_list = list()
    n = 50
    for split_result in [channelids[idx:idx + n] for idx in range(0,len(channelids), n)]: # リストを50ずつ分割（長すぎると切れるため）
        ids = ','.join(split_result)
        youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_KEY)
        # print(ids)
        try:
            response = youtube.channels().list(
                    part='id,contentDetails',
                    id=ids,
                    maxResults=50
                ).execute() # Youtube APIへのリクエスト作成
            if response.get('items'):
                for item in response['items']:
                    id = item.get('id')
                    # print(item)
                    if item.get('contentDetails'):
                        contentDetails = item.get('contentDetails')
                        if contentDetails.get('relatedPlaylists'):
                            new_channel_list.append({
                                'channelid':id,
                                'uploads':contentDetails.get('relatedPlaylists').get('uploads'),
                            })
            
        except errors.HttpError as err:
            return {'error':err._get_reason(),'errorDetail':'function getChannelUploads'}

    new_uploads = list()
    for playlist in new_channel_list:
        if playlist.get('uploads'):
            videos = getVideosFromPlaylist(playlist.get('uploads'))
            if isinstance(videos, dict) and videos.get('error'):
                return videos
            else:
                new_uploads.append({
                    'channelid':playlist.get('channelid'),
                    'videos':videos,
                })

    return new_uploads

def getVideosFromPlaylist(playlistUrl): # Youtube Data APIでプレイリストに含まれる動画情報を取得
    new_video_list = list()
    youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_KEY)
    try:
        playlistitems_list_request = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlistUrl,
                maxResults=50
            ) # Youtube APIへのリクエスト作成
        while playlistitems_list_request:
            playlistitems_list_response = playlistitems_list_request.execute()
            if playlistitems_list_response.get('items'):
                temp_video_ids = list()
                for item in playlistitems_list_response['items']:
                    if item.get('snippet'):
                        if item.get('snippet').get('resourceId'):
                            if item.get('snippet').get('resourceId').get('videoId'):
                                videoId = item.get('snippet').get('resourceId').get('videoId')
                                temp_video_ids.append(videoId)
                videoDetails = getVideoDetails(temp_video_ids)
                if isinstance(videoDetails, dict) and videoDetails.get('error'):
                    return videoDetails
                else:
                    for videoDetail in videoDetails:
                        new_video_list.append({
                            'videoId':videoDetail.get('videoId'),
                            'detail':videoDetail,
                        })
            playlistitems_list_request = youtube.playlistItems().list_next(playlistitems_list_request, playlistitems_list_response)

        
    except errors.HttpError as err:
        return {'error':err._get_reason(),'errorDetail':'function getVideosFromPlaylist, playlistUrl:'+playlistUrl}
    
    return new_video_list

def getVideoDetails(videoIds): # Youtube Data APIで動画情報を取得
    new_video_list = list()
    n = 50
    for split_result in [videoIds[idx:idx + n] for idx in range(0,len(videoIds), n)]: # リストを50ずつ分割（長すぎると切れるため）
        ids = ','.join(split_result)
        youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_KEY)

        try:
            response = youtube.videos().list(
                    part='id,snippet,contentDetails,statistics',
                    id=ids
                ).execute() # Youtube APIへのリクエスト作成
            if response.get('items'):
                for item in response['items']:
                    new_video = {
                        'videoId': item.get('id'),
                    }
                    if item.get('snippet'):
                        new_video['snippet'] = item.get('snippet')
                    if item.get('statistics'):
                        new_video['statistics'] = item.get('statistics')
                    if item.get('contentDetails'):
                        new_video['contentDetails'] = item.get('contentDetails')
                    new_video_list.append(new_video)
        
        except errors.HttpError as err:
            return {'error':err._get_reason(),'errorDetail':'function getVideoDetails, videoID:'+videoId}

    return new_video_list

def updateVideosJob(): # ビデオの情報を更新する
    db = get_db()
    dataFinish = False
    start=0
    while dataFinish == False:
        idlines = query_db('select videoid from video limit ?,50', [start])
        if not idlines:
            break
        start += 50
        idlist = list()
        for video in idlines:
            idlist.append(video['videoid'])
        ids = ','.join(idlist) # リストをコンマで結合して文字列

        youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_KEY) # Youtube APIへアクセスするオブジェクト作成

        try:
            response = youtube.videos().list(
                    part='id,snippet,statistics',
                    id=ids
                ).execute() # Youtube APIへのリクエスト作成
        except errors.HttpError as err:
            # HTTPエラーが生じた場合は，エラーメッセージを表示。
            print('There was an error creating the model. Check the details:')
            print(err._get_reason())
            send_line_notify(err._get_reason()) # LINEでもエラーを通知
        if response.get('items'):
            for item in response['items']: # 帰ってきた結果をチャンネルごと処理
                id = item.get('id')
                # print(id)

                curdata = query_db('select * from video where videoid = ?', [id], True)
                if item.get('statistics') and item.get('snippet'):
                    likeCount = item['statistics'].get('likeCount')
                    viewCount = item['statistics'].get('viewCount')
                    dislikeCount = item['statistics'].get('dislikeCount')
                    commentCount = item['statistics'].get('commentCount')

                    if curdata and item.get('statistics') and item.get('snippet'): # 以前のデータが保存されているかどうか
                        likeChange = int(0 if likeCount is None else likeCount) - int(0 if curdata['likeCount'] is None else curdata['likeCount'])
                        viewChange = int(0 if viewCount is None else viewCount) - int(0 if curdata['viewCount'] is None else curdata['viewCount'])
                        dislikeChange = int(0 if dislikeCount is None else dislikeCount) - int(0 if curdata['dislikeCount'] is None else curdata['dislikeCount'])
                        commentChange = int(0 if commentCount is None else commentCount) - int(0 if curdata['commentCount'] is None else curdata['commentCount'])
                        #change = ('+' if change > 0 else '') + "{:,}".format(change) # プラスの場合は先頭に＋をつける
                    else: # 以前のデータが保存されていなければ，増減値は「New」にする
                        likeChange = 0
                        viewChange = 0
                        dislikeChange = 0
                        commentChange = 0
                
                    queryData = {
                        'videoid': id,
                        'title': item.get('snippet').get('title'), 
                        'description': item.get('snippet').get('description'), 
                        'viewCount': viewCount, 
                        'likeCount': likeCount, 
                        'dislikeCount': dislikeCount, 
                        'commentCount': commentCount, 
                        'viewChange': viewChange, 
                        'likeChange': likeChange, 
                        'dislikeChange': dislikeChange, 
                        'commentChange': commentChange, 
                        'lastUpdate': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    db.execute(
                            "UPDATE video SET title = :title, description = :description, likeCount = :likeCount, viewCount = :viewCount, dislikeCount = :dislikeCount, commentCount = :commentCount, likeChange = :likeChange, viewChange = :viewChange, dislikeChange = :dislikeChange, commentChange = :commentChange, lastUpdate = :lastUpdate WHERE videoid = :videoid",
                            queryData
                    )
                    db.execute(
                            "INSERT INTO video_history (videoid, date,likeCount,viewCount,dislikeCount,commentCount,likeChange,viewChange,dislikeChange,commentChange) VALUES(:videoid,:lastUpdate,:likeCount,:viewCount,:dislikeCount,:commentCount,:likeChange,:viewChange,:dislikeChange,:commentChange)",
                            queryData,
                    )
                    db.commit()
                    # print(f'{viewCount},{likeCount},{dislikeCount},{commentCount},{viewChange},{likeChange},{dislikeChange},{commentChange}')
    idlines = query_db('select count(videoid) from video',(),True)
    return f'Video Count: {idlines[0]:,d}'