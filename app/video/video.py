from flask import Flask, render_template, url_for, send_from_directory, request, redirect,  flash, Response, abort, session, make_response
from flask import Blueprint
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import datetime
import urllib
import json
import random
import string
import csv
import re
import requests
import math

#import advanced module
from io import StringIO

#import self module
from db import init_db_command, get_db, query_db
import youtubechecker
import settings
import functions


bp_video = Blueprint('bp_video', __name__, url_prefix='/video')

@bp_video.route('/list', methods=["GET", "POST"])
@login_required
def videolist():
    err_msg = list()
    if request.method == "POST":
        # clean_idlist = list()
        check_ids = list()
        # new_channels = list()
        exists_ids = list()
        # valid_ids = list()
        isSuccess = False
        newids = request.form["lists"].splitlines()
        (valid_ids, new_ids, err_msg) = insert_videos(newids)
        
        for videoid in valid_ids:
            if not query_db('SELECT * FROM user_video WHERE userid = ? AND videoid = ?',[current_user.id, videoid],True):
                check_ids.append((current_user.id, videoid))
            else:
                exists_ids.append(videoid)
            
        if check_ids:
            exists_videos = query_db('SELECT * FROM user_video WHERE userid = ?',[current_user.id])
            if len(exists_videos) + len(check_ids) > int(settings.MAX_VIDEOS_PER_USER):
                err_msg.append('Your videos already too many. max '+str(settings.MAX_VIDEOS_PER_USER)) 
            else:
                isSuccess = True  
                db = get_db()
                db.executemany(
                        "INSERT INTO user_video (userid, videoid) VALUES (?, ?)",
                        check_ids
                    )
                db.commit()
                flash(str(len(check_ids))+' videos were added.', 'alert-success')
        if exists_ids:
            err_msg.append('The videos already exists.('+','.join(exists_ids)+')')

        if isSuccess and session.get("newregister") == 1:
            session.pop('newregister', None)
            newdata = {
                'message' : 'Complete! Your account is ready now!',
                'style':'alert-success'
            }
            return render_template('finished.html',title='Finished!',data=newdata)

    if request.args.get('delid'):
        matched = youtubechecker.check_videoid(request.args.get('delid'))
        if matched:
            videoid = matched.group()
            db = get_db()
            db.execute(
                "DELETE FROM user_video where userid = ? and videoid = ?",
                (current_user.id, videoid),
            )
            db.commit()
            # ret = youtubechecker.deletechannel(videoid)
            flash('The videos has been deleted.', 'alert-warning')

    newdata = query_db('select user_video.videoid,video.title,video.publish_at,video.duration,video.viewCount,video.likeCount,video.dislikeCount,video.commentCount,video.viewChange,video.likeChange,video.dislikeChange,video.commentChange from user_video left outer join video on user_video.videoid = video.videoid where user_video.userid = ?', [current_user.id])
    list_percent=int(len(newdata) / int(settings.MAX_VIDEOS_PER_USER) * 100)
    return render_template('video/videolist.html',title='videos',data=newdata, err_msg=err_msg, list_percent=list_percent, max_list_cnt=settings.MAX_VIDEOS_PER_USER)


@bp_video.route('/detail/<videoid>')
def videodetail(videoid):
    newdata = query_db('select * from video where videoid = ?',(videoid,),True)
    return render_template('video/detail.html', title=newdata['title'], data=newdata)

@bp_video.route('/csv/<videoid>')
def videocsv(videoid):
    f = StringIO()
    writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")

    if videoid == 'videos' and current_user.is_authenticated :
        writer.writerow(['videoid','channelid','title','description','publish_at','thumbnail','categoryId','duration','viewCount','likeCount','dislikeCount','commentCount','viewChange','likeChange','dislikeChange','commentChange','Updatedate'])
        downloadFileName = 'videos' + '-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
        for video in query_db('select user_video.videoid,video.channelid,video.title,video.description,video.publish_at,video.thumbnail,video.categoryId,video.duration,video.viewCount,video.likeCount,video.dislikeCount,video.commentCount,video.viewChange,video.likeChange,video.dislikeChange,video.commentChange,video.lastUpdate from user_video left outer join video on user_video.videoid = video.videoid where user_video.userid = ?', [current_user.id]):
            writer.writerow([video['videoid'],video['channelid'],video['title'],video['description'],video['publish_at'],video['thumbnail'],video['categoryId'],video['duration'],video['viewCount'],video['likeCount'],video['dislikeCount'],video['commentCount'],video['viewChange'],video['likeChange'],video['dislikeChange'],video['commentChange'],video['lastUpdate']])
    else:
        newdata = query_db('select * from video where videoid = ?',(videoid,),True)
        if newdata:
            downloadFileName = newdata['title'] + datetime.datetime.now().strftime('%y%m%d') + '.csv'
        else:
            downloadFileName = videoid + datetime.datetime.now().strftime('%y%m%d') + '.csv'
        if youtubechecker.check_videoid(videoid):
            writer.writerow(['Date','viewCount','viewChange','likeCount','likeChange','dislikeCount','dislikeChange','commentCount','commentChange'])
            for video in query_db('select * from video_history where videoid = ?', [videoid]):
                writer.writerow([video['date'],video['viewCount'],video['viewChange'],video['likeCount'],video['likeChange'],video['dislikeCount'],video['dislikeChange'],video['commentCount'],video['commentChange']])
        else:
            return 'err: video ID'

    res = make_response()
    res.data = f.getvalue()
    res.headers['Content-Type'] = 'text/csv'
    res.headers['Content-Disposition'] = functions.rfc5987_content_disposition(downloadFileName)
    return res

@bp_video.route('/docheck')
def docheckvideo():
    user = query_db('select id from user where id = ?', [current_user.id],True)
    if user['id'].startswith('U'):
        youtubechecker.send_notify_from_user(user['id'],['video'])
        flash('Plese see your LINE!', 'alert-success')
    else:
        flash('Plese link to LINE first!', 'alert-warning')
    
    return redirect(url_for('bp_video.videolist'))


def insert_videos(newids):
    clean_idlist = list()
    valid_ids = list()
    err_msg = list()
    new_videos = list()
    for videoid in newids:
        matched = youtubechecker.check_videoid(videoid)
        if matched:
            clean_idlist.append(matched.group())
        else:
            err_msg.append('The videos id is wrong.('+videoid+')')

    for videoid in clean_idlist:
        if not query_db('select * from video where videoid = ?',[videoid],True):
            new_videos.append(videoid)
        else:
            valid_ids.append(videoid)

    if new_videos:
        videodata = youtubechecker.getVideoDetails(new_videos) 
        if isinstance(videodata, dict) and videodata.get('error'):
            err_msg.append(videodata.get('error'))
        else:
            db = get_db()
            for item in videodata:
                if item.get('snippet') and item.get('statistics') and item.get('contentDetails'):
                    thumbnails = item.get('snippet').get('thumbnails')
                    thumbnail_default = thumbnails.get('default') if thumbnails != None else None
                    thumbnail = thumbnail_default.get('url') if thumbnail_default != None else None

                    queryData = {
                        'videoid': item['videoId'],
                        'channelid': item.get('snippet').get('channelId'), 
                        'title': item.get('snippet').get('title'), 
                        'description': item.get('snippet').get('description'), 
                        'publish_at': item.get('snippet').get('publishedAt').replace('Z', '').replace('T', ' '), 
                        'thumbnail': thumbnail, 
                        'categoryId': item.get('snippet').get('categoryId'), 
                        'duration': functions.duration_format(item.get('contentDetails').get('duration').replace('PT', '').replace('H', ':').replace('M', ':').replace('S', '')), 
                        'viewCount': item.get('statistics').get('viewCount'), 
                        'likeCount': item.get('statistics').get('likeCount'), 
                        'dislikeCount': item.get('statistics').get('dislikeCount'), 
                        'commentCount': item.get('statistics').get('commentCount'), 
                        'viewChange': 0, 'likeChange': 0, 'dislikeChange': 0, 'commentChange': 0, 
                        'lastUpdate': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    db.execute(
                        "INSERT INTO video (videoid,channelid,title,description,publish_at,thumbnail,categoryId,duration,viewCount,likeCount,dislikeCount,commentCount,viewChange,likeChange,dislikeChange,commentChange,lastUpdate) VALUES(:videoid,:channelid,:title,:description,:publish_at,:thumbnail,:categoryId,:duration,:viewCount,:likeCount,:dislikeCount,:commentCount,:viewChange,:likeChange,:dislikeChange,:commentChange,:lastUpdate)", queryData
                    )
                    valid_ids.append(item['videoId'])
            db.commit() 
    return (valid_ids, new_videos, err_msg)
