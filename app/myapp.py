from flask import Flask, render_template, url_for, send_from_directory, request, redirect,  flash, Response, abort, session, make_response, Request
import os
import datetime
import urllib
import json
import sqlite3
import random
import string
import csv
import click
import re
import requests
import math
#import gspread

from io import StringIO
from oauthlib.oauth2 import WebApplicationClient
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask.cli import with_appcontext
#from oauth2client.service_account import ServiceAccountCredentials 

#from gspread_formatting import *

# Internal imports
from db import init_db_command, get_db, query_db
from user import User
import youtubechecker
import settings
import functions
from proxiedRequest import ProxiedRequest

#blueprint module imports
from video.video import bp_video
            
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SCHEDULER_API_ENABLED'] = True
app.secret_key = settings.SECRET
app.config['LINE_ADMIN_ID'] = settings.LINE_ADMIN_ID

@app.context_processor
def inject_settings():
    return dict(settings=settings)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# register blueprint modules
app.register_blueprint(bp_video)

# request
app.request_class = ProxiedRequest

login_manager = LoginManager()
login_manager.init_app(app)

from functools import wraps

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.id != settings.LINE_ADMIN_ID:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    newdata = {
            'header' : 'Sorry',
            'message' : 'You must be logged in to access this content.',
            'next_url': url_for('login'),
            'next_text': 'Login'
        }
    return render_template('message.html',title='Unauthorized',data=newdata), 403

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route("/")
def main():
    cur_page = request.args.get("page") if request.args.get("page") else '0'
    order = request.args.get("order") if request.args.get("order") else '0'
    num = 30 # number of list 
    num_range = 2 # number of around current pager item
    if not (re.match('^[0-9]+$', cur_page) and re.match('^[0-9]+$', order)):
        return 'page or order error'
    order_query = {}
    numdata = query_db('select count(*) from channel', order_query, True)
    num_all = int(numdata[0]) # all amount of data
    orderstr = settings.channel_order[int(order)]['val']
    order_query.update( {
        'start': int(cur_page) * num,
        'num': num 
        })
    newdata = query_db('select * from channel order by {} limit :start, :num'.format(orderstr), order_query)
    page_max = int(num_all / num) # max page number ( 0 start)
    pager_list = [0]
    #pager_start = 0 if int(cur_page) - 2 - (0 if int(cur_page) + 2 <= page_max else page_max - int(cur_page) + 2) < 0 else int(cur_page) - 2 - (0 if int(cur_page) + 2 <= page_max else page_max - int(cur_page) + 2)
    pager_start = max(num_range - 1, int(cur_page) - num_range - max(int(cur_page) + num_range - page_max, 0))
    #pager_end = page_max if int(cur_page) + 2 + abs(0 if int(cur_page) - 2 > 0 else int(cur_page) - 2) > page_max else int(cur_page) + 2 + abs(0 if int(cur_page) - 2 > 0 else int(cur_page) - 2)
    pager_end = min(page_max - 1, int(cur_page) + num_range + abs(min(0, int(cur_page) - num_range)))
    pager_list.extend(list(range(pager_start,pager_end+1)))
    pager_list.append(page_max)
    pager_list = list(dict.fromkeys(pager_list))
    #for item in newdata:
        
    pager = {
        'page': int(cur_page),
        'num' : num,
        'page_min' : 0,
        'page_max' : page_max,
        'page_min_ommit': True if len(pager_list)>1 and pager_list[1]!=1 else False,
        'page_max_ommit': True if len(pager_list)>1 and pager_list[len(pager_list)-2]!=page_max-1 else False,
        'num_all' : num_all,
        'list': pager_list
    }
    order = {
        'order': int(order),
        'list': settings.channel_order
    }
    return render_template('main.html',title='Channels',data=newdata, pager=pager, order=order)

@app.route('/channel/<channelid>')
def channel(channelid):
    newdata = query_db('select * from channel where channelid = ?',(channelid,),True)
    return render_template('channel.html',title=newdata['title'],data=newdata)

@app.route('/download/<channelid>')
@login_required
def download(channelid):
    f = StringIO()
    writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")

    if channelid == 'channels' and current_user.is_authenticated :
        writer.writerow(['Channel Id','Channel name','Published at','subscriberCount','subscriberChange','viewCount','viewChange','videoCount','videoChange','commentCount','commentChange'])
        downloadFileName = 'channels' + '-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
        for channel in query_db('select user_channel.channelid,channel.title,channel.publish_at,channel.subscriberCount,channel.viewCount,channel.videoCount,channel.commentCount,channel.subscriberChange,channel.viewChange,channel.videoChange,channel.commentChange from user_channel left outer join channel on user_channel.channelid = channel.channelid where user_channel.userid = ?', [current_user.id]):
            writer.writerow([channel['channelid'],channel['title'],channel['publish_at'],channel['subscriberCount'],channel['subscriberChange'],channel['viewCount'],channel['viewChange'],channel['videoCount'],channel['videoChange'],channel['commentCount'],channel['commentChange']])
    else:
        newdata = query_db('select * from channel where channelid = ?',(channelid,),True)
        if newdata:
            downloadFileName = newdata['title'] + '-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
        else:
            downloadFileName = channelid + '-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
        if youtubechecker.check_channelid(channelid):
            writer.writerow(['Date','subscriberCount','subscriberChange','viewCount','viewChange','videoCount','videoChange','commentCount','commentChange'])
            for channel in query_db('select * from channel_history where channelid = ?', [channelid]):
                writer.writerow([channel['date'],channel['subscriberCount'],channel['subscriberChange'],channel['viewCount'],channel['viewChange'],channel['videoCount'],channel['videoChange'],channel['commentCount'],channel['commentChange']])
        else:
            return 'err: channel ID'

    res = make_response()
    res.data = f.getvalue()
    res.headers['Content-Type'] = 'text/csv'
    res.headers['Content-Disposition'] = functions.rfc5987_content_disposition(downloadFileName) #'attachment; filename='+ downloadFileName
    return res


@app.route('/videochannel/<channelid>')
@login_required
def channelvideos(channelid):
    newdata = query_db('select * from channel where channelid = ?',(channelid,),True)
    result = query_db('SELECT json_extract(video, "$") as video FROM channel_video WHERE channelid = ? ',[channelid], True)
    videos = list()
    if result:
        result = None if result['video'] is None else json.loads(result['video'])
        for video in result:
            detail = video.get('detail')
            snippet = detail.get('snippet') if detail != None else None
            contentDetails = detail.get('contentDetails') if detail != None else None
            statistics = detail.get('statistics')  if detail != None else None      

            title = snippet.get('title') if snippet != None else ''
            duration = functions.duration_format(contentDetails.get('duration').replace('PT', '').replace('H', ':').replace('M', ':').replace('S', '')) if contentDetails != None else ''
            viewCount = statistics.get('viewCount') if statistics != None else ''
            likeCount = statistics.get('likeCount') if statistics != None else ''
            dislikeCount = statistics.get('dislikeCount') if statistics != None else ''
            commentCount = statistics.get('commentCount') if statistics != None else ''
            publishedAt = snippet.get('publishedAt').replace('Z', '').replace('T', ' ') if snippet != None else ''

            videos.append({
               'videoid':video.get('videoId'), 'title':title, 'duration':duration, 'viewCount':viewCount, 'likeCount':likeCount, 'dislikeCount':dislikeCount, 'commentCount':commentCount, 'publishedAt':publishedAt
            })


    return render_template('channelvideos.html',title='Videos for '+newdata['title'],data=newdata,videos=videos)


@app.route('/videodownload/<channelid>')
@login_required
def videodownload(channelid):
    f = StringIO()
    writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")

    newdata = query_db('select * from channel where channelid = ?',(channelid,),True)
    if newdata:
        downloadFileName = newdata['title'] + '-videos-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
    else:
        downloadFileName = channelid + '-videos-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
    if youtubechecker.check_channelid(channelid):
        writer.writerow(['Title','Duration','View','Like','Dislike','Comment','Date'])
        result = query_db('SELECT json_extract(video, "$") as video FROM channel_video WHERE channelid = ? ',[channelid], True)
        if result:
            videos = None if result['video'] is None else json.loads(result['video'])
            for video in videos:
                detail = video.get('detail')
                snippet = detail.get('snippet') if detail != None else None
                contentDetails = detail.get('contentDetails') if detail != None else None
                statistics = detail.get('statistics')  if detail != None else None      

                title = snippet.get('title') if snippet != None else ''
                duration = contentDetails.get('duration').replace('PT', '').replace('M', ':').replace('S', '') if contentDetails != None else ''
                viewCount = statistics.get('viewCount') if statistics != None else ''
                likeCount = statistics.get('likeCount') if statistics != None else ''
                dislikeCount = statistics.get('dislikeCount') if statistics != None else ''
                commentCount = statistics.get('commentCount') if statistics != None else ''
                publishedAt = snippet.get('publishedAt').replace('Z', '').replace('T', ' ') if snippet != None else ''

                writer.writerow([
                    title, duration, viewCount, likeCount, dislikeCount, commentCount, publishedAt
                ])
    else:
        return 'err: channel ID'

    res = make_response()
    res.data = f.getvalue()
    res.headers['Content-Type'] = 'text/csv'
    res.headers['Content-Disposition'] = functions.rfc5987_content_disposition(downloadFileName) #'attachment; filename='+ downloadFileName
    return res


@app.route('/docheck')
def docheck():
    user = query_db('select id from user where id = ?', [current_user.id],True)
    if user['id'].startswith('U'):
        youtubechecker.send_notify_from_user(user['id'],['channel'])
        flash('Plese see your LINE!', 'alert-success')
    else:
        flash('Plese link to LINE first!', 'alert-warning')
    
    return redirect(url_for('channellist'))

@app.route('/requestcheckvideo/<channelid>')
@login_required
def requestcheckvideo(channelid):
    # listChannelVideo(channelid)
    result = query_db('SELECT * FROM video_waiting WHERE channelid = ? ',[channelid], True)
    if not result:
        db = get_db()
        db.execute(
            "INSERT INTO video_waiting (channelid) VALUES (?)",
            (channelid,),
        )
        db.commit()
        flash('Your request has been received. Since we check requests once a day, Plese come back tomorrow!', 'alert-success')
    else:
        flash('This channel is already in the que. Plese come back tomorrow!', 'alert-warning')
    return redirect(url_for('channelvideos',channelid=channelid))

@app.route('/login')
def login():
    return render_template('login.html',title='Login')

@app.route('/line')
def line_login():
    oauth = WebApplicationClient(settings.LINE_CHANNEL_ID)
    state = "".join([random.choice(string.ascii_letters + string.digits) for i in range(32)])
    session["state"] = state
    url, headers, body = oauth.prepare_authorization_request('https://access.line.me/oauth2/v2.1/authorize',
      state=state, redirect_url=request.base_url + "/callback",
      scope='profile openid', bot_prompt='normal' )
    return redirect(url)

@app.route('/line/callback')
def callback():
    oauth = WebApplicationClient(settings.LINE_CHANNEL_ID)
    if request.args.get("error"):
        flash('Error! '+request.args.get("error_description"), 'alert-warning')
        return redirect(url_for('main'))

    state = request.args.get("state")
    if state != session.get("state"):
        flash('Error! state not match.', 'alert-warning')
        return redirect(url_for('main'))
    
    session.pop('state', None)
    friendship_status_changed = request.args.get("friendship_status_changed")
    url, headers, body = oauth.prepare_token_request('https://api.line.me/oauth2/v2.1/token',
                            authorization_response=request.url,
                            redirect_url=request.base_url,
                            state='', body='', client_secret=settings.LINE_CHANNEL_SECRET)
    req = urllib.request.Request(url, body.encode(), headers=headers)
    with urllib.request.urlopen(req) as res:
        response_body=res.read()
    oauth_res = oauth.parse_request_body_response(response_body)
    data = {
        'id_token' : oauth_res.get('id_token') ,
        'client_id' : settings.LINE_CHANNEL_ID
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    req = urllib.request.Request('https://api.line.me/oauth2/v2.1/verify', urllib.parse.urlencode(data).encode(), headers)
    try:
        with urllib.request.urlopen(req) as res:
            response_body=res.read()
    except urllib.error.HTTPError as err:
        return err.read()

    verify_res = json.loads(response_body)
    if verify_res.get('error'):
        flash('Error! '+verify_res.get('error_description'), 'alert-warning')
        return redirect(url_for('main'))
    
    unique_id = verify_res.get('sub')
    users_name = verify_res.get('name')
    picture = verify_res.get('picture')
    user = User(
        id_=unique_id, name=users_name, profile_pic=picture
    )
    if not User.get(unique_id):
        User.create(unique_id, users_name, picture)
        res = youtubechecker.send_line_push(
            unique_id,
            [{"type":"text","text":"Welcome to Youtube Checker! You have been successfully created an account."}])
        login_user(user)
        session["newregister"] = 1
        flash('You have been successfully created an account.', 'alert-success')
        return redirect(url_for('pushtime'))

    login_user(user)
    return redirect(url_for('channellist'))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main"))

@app.route("/account")
@login_required
def account():
    userdata = query_db('select push_time,notify_token from user where id = ?',(current_user.id,),True)
    newdata = {
        'title':'Account',
        'push_time':userdata['push_time'][:2]+":"+userdata['push_time'][2:],
        'notify_token':userdata['notify_token']
        }
    return render_template('account.html',title=newdata['title'],data=newdata)

@app.route("/account/delete")
@login_required
def account_delete():
    db = get_db()
    delete_list = list()
    for channel in query_db('SELECT * FROM user_channel WHERE userid = ? ',[current_user.id]):
        delete_list.append(channel['channelid'])
    db.execute(
        "DELETE FROM user_channel where userid = ?",
        (current_user.id, ),
    )
    db.commit()
    for channelid in delete_list:
        ret = youtubechecker.deletechannel(channelid)

    User.delete(current_user.id)
    logout_user()
    flash('Deleted your account.', 'alert-warning')
    return redirect(url_for("main"))

@app.route("/account/pushtime", methods=["GET", "POST"])
@login_required
def pushtime():
    hour = "09"
    min = "15"

    if request.method == "POST":
        hour = request.form["hour"]
        min = request.form["min"]
        if re.match('^[0-9]{4}$',hour+min):
            db = get_db()
            db.execute(
                "UPDATE user set push_time = ? WHERE id = ?",
                (hour+min, current_user.id),
            )
            db.commit()
            flash('Your notify time was updated!', 'alert-success')
            if session.get("newregister") == 1:
                return redirect(url_for("gonotify"))
            #else:
            #    return redirect(url_for("account"))
        else:
            return 'err: invalid value'

    userdata = query_db('select push_time from user where id = ?',(current_user.id,),True)
    if userdata:
        hour = userdata['push_time'][:2]
        min = userdata['push_time'][2:]
    newdata = {'title':'Notify time','hour':hour,'min':min}
    return render_template('pushtime.html',title=newdata['title'],data=newdata)

@app.route('/notify/disable')
@login_required
def disable_notify():
    ret = youtubechecker.disable_notify_from(current_user.id)
    flash(ret, 'alert-success')
    return redirect(url_for('account'))

@app.route('/notify/enable')
@login_required
def enable_notify():
    ret = youtubechecker.enable_notify_from(current_user.id)
    flash(ret, 'alert-success')
    return redirect(url_for('account'))

@app.route('/admin/users')
@admin_required
def admin_users():
    users = query_db('SELECT * FROM user')
    return render_template('admin_users.html', title='User List', users=users)

@app.route("/channellist", methods=["GET", "POST"])
@login_required
def channellist():
    err_msg = list()
    if request.method == "POST":
        # clean_idlist = list()
        check_ids = list()
        # new_channels = list()
        exists_ids = list()
        # valid_ids = list()
        isSuccess = False
        newids = request.form["lists"].splitlines()
        (valid_ids, new_ids, err_msg) = insert_channels(newids, False)
        
        for channelid in valid_ids:
            if not query_db('SELECT * FROM user_channel WHERE userid = ? AND channelid = ?',[current_user.id, channelid],True):
                check_ids.append((current_user.id, channelid))
            else:
                exists_ids.append(channelid)
            
        if check_ids:
            exists_channels = query_db('SELECT * FROM user_channel WHERE userid = ?',[current_user.id])
            if len(exists_channels) + len(check_ids) > int(settings.MAX_CHANNELS_PER_USER):
                err_msg.append('Your channels already too many. max '+str(settings.MAX_CHANNELS_PER_USER)) 
            else:
                isSuccess = True  
                db = get_db()
                db.executemany(
                        "INSERT INTO user_channel (userid, channelid) VALUES (?, ?)",
                        check_ids
                    )
                db.commit()
                flash(str(len(check_ids))+' channels were added.', 'alert-success')
        if exists_ids:
            err_msg.append('The channels already exists.('+','.join(exists_ids)+')')

        if isSuccess and session.get("newregister") == 1:
            return redirect(url_for("bp_video.videolist"))

    if request.args.get('delid'):
        matched = youtubechecker.check_channelid(request.args.get('delid'))
        if matched:
            channelid = matched.group()
            db = get_db()
            db.execute(
                "DELETE FROM user_channel where userid = ? and channelid = ?",
                (current_user.id, channelid),
            )
            db.commit()
            ret = youtubechecker.deletechannel(channelid)
            flash('The channels has been deleted.', 'alert-warning')

    newdata = query_db('select user_channel.channelid,channel.title,channel.publish_at,channel.subscriberCount,channel.viewCount,channel.videoCount,channel.commentCount,channel.subscriberChange,channel.viewChange,channel.videoChange,channel.commentChange from user_channel left outer join channel on user_channel.channelid = channel.channelid where user_channel.userid = ?', [current_user.id])
    list_percent=int(len(newdata) / int(settings.MAX_CHANNELS_PER_USER) * 100)
    return render_template('channellist.html',title='Channels',data=newdata, err_msg=err_msg, list_percent=list_percent, max_list_cnt=settings.MAX_CHANNELS_PER_USER)

@app.route("/chart")
def chart():
    if request.args.get("channelid") and request.args.get("period") and request.args.get("datatype"):
        channelid = request.args.get("channelid")
        matched = youtubechecker.check_channelid(channelid)
        if not matched:
            return 'err'
        period = request.args.get("period")
        datatype = request.args.get("datatype")
        if (period == '30' or period == '365' or period == 'all') and (datatype == "daily" or datatype == "total"):
            wherestr = 'where channelid = :channelid'
            qeuerydata = {'channelid':channelid}
            chart_type = {'daily':'bar','total':'line'}
            data_label = list()
            data_subscriber = list()
            data_view = list()
            if period == '30' or period == '365':
                dt1 = datetime.datetime.now()
                dt2 = dt1 + datetime.timedelta(days=-1 * int(period))
                wherestr += ' and date > :date'
                qeuerydata['date'] = dt2.strftime('%Y-%m-%d %H:%M:%S')
            
            for history in query_db('select * from channel_history ' + wherestr + ' order by date desc', qeuerydata):
                data_label.append(history['date'][:10])
                data_subscriber.append(history['subscriberCount'] if datatype == "total" else history['subscriberChange'])
                data_view.append(history['viewCount'] if datatype == "total" else history['viewChange'])
            data_label.reverse()
            data_subscriber.reverse()
            data_view.reverse()
            datasets = [
                {
                    'type':chart_type[datatype],
                    'label': 'Subscriber',
                    'data': data_subscriber,
                    'borderColor': "rgba(255, 99, 132, 0.5)",
                    'backgroundColor':"rgba(255, 99, 132, 0.1)",
                    'fill':'false',
                    'pointRadius':6,
                    'pointHoverRadius':12,
                    'lineTension':0,
                    'yAxisID': "y-axis-1"
                },
                {
                    'type':chart_type[datatype],
                    'label': 'View',
                    'data': data_view,
                    'borderColor': "rgba(99, 132, 255, 0.5)",
                    'backgroundColor':"rgba(99, 132, 255, 0.2)",
                    'fill':'false',
                    'pointRadius':6,
                    'pointHoverRadius':12,
                    'lineTension':0,
                    'yAxisID': "y-axis-2"
                }
            ]
            
            newdata = {
                'labels':data_label,
                'datasets':datasets
            }
            return newdata


    newdata = {
            'header' : 'Sorry',
            'message' : 'Query string error.',
            'next_url': url_for('main'),
            'next_text': 'Main'
        }
    return render_template('message.html',title='Bad Request',data=newdata), 400

@app.route("/test")
def test():
    return ''

@app.route("/about")
def about():
    newdata = {'title':'About'}
    return render_template('about.html',title=newdata['title'],data=newdata)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/apple-touch-icon.png')
def appleicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'apple-touch-icon.png', mimetype='image/png')

def get_google_provider_cfg():
    return requests.get("https://accounts.google.com/.well-known/openid-configuration").json()


@app.route('/google')
def google_login():
    google_provider_cfg = get_google_provider_cfg()
    oauth = WebApplicationClient(settings.GOOGLE_CLIENT_ID)
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    state = "".join([random.choice(string.ascii_letters + string.digits) for i in range(32)])
    session["state"] = state
    url, headers, body = oauth.prepare_authorization_request(authorization_endpoint,
      state=state, redirect_url=request.base_url + "/callback",
      scope=['profile','openid'] )
    return redirect(url)

@app.route('/google/callback')
def google_callback():
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    oauth = WebApplicationClient(settings.GOOGLE_CLIENT_ID)
    if request.args.get("error"):
        flash('Error! '+request.args.get("error"), 'alert-warning')
        return redirect(url_for('main'))

    state = request.args.get("state")
    if state != session.get("state"):
        flash('Error! state not match.', 'alert-warning')
        return redirect(url_for('main'))

    session.pop('state', None)
    url, headers, body = oauth.prepare_token_request(token_endpoint,
                            authorization_response=request.url,
                            redirect_url=request.base_url,
                            state='', body='', client_secret=settings.GOOGLE_CLIENT_SECRET)

    token_response = requests.post(
        url,
        headers=headers,
        data=body,
        auth=(settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET),
    )
    
    oauth.parse_request_body_response(json.dumps(token_response.json()))
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = oauth.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.status_code != 200:
        flash('Error! '+userinfo_response.json(), 'alert-warning')
        return redirect(url_for('main'))
    
    unique_id = userinfo_response.json()["sub"]
    users_name = userinfo_response.json()["name"]
    picture = userinfo_response.json()["picture"]
    user = User(
        id_=unique_id, name=users_name, profile_pic=picture
    )
    if not User.get(unique_id):
        User.create(unique_id, users_name, picture)
        login_user(user)
        session["newregister"] = 1
        flash('You have been successfully created an account.', 'alert-success')
        return redirect(url_for('pushtime'))

    login_user(user)
    return redirect(url_for('channellist'))

def import_from_text(): #import channels from import.txt to database directly 
    with open('import.txt') as f:
        matched_list = list()
        newids = f.read().splitlines()
        for channelid in newids:
            l = channelid.split(',')
            if len(l) == 2:
                matched_list.append(l[0])
        (valid_ids, new_ids, err_msg) = insert_channels(matched_list, True)
        res = '{} channel ids valid. {} channels are new. {} channel ids wrong.'.format(len(valid_ids),len(new_ids),len(err_msg))
        print(res)
        for err in err_msg:
            print(err)
    return res

def insert_channels(newids, isAllowCustomUrl = False):
    clean_idlist = list()
    valid_ids = list()
    err_msg = list()
    new_channels = list()
    for channelid in newids:
        matched = youtubechecker.check_channelid(channelid)
        if matched:
            clean_idlist.append(matched.group())
        elif re.search('user/([a-zA-Z0-9_-]+)',channelid):
            matched = re.search('user/([a-zA-Z0-9_-]+)',channelid)
            clean_idlist.extend(youtubechecker.name_to_id(matched.group(1)))
        elif re.search('c/([a-zA-Z0-9_-]+)',channelid):
            matched = re.search('c/([a-zA-Z0-9_-]+)',channelid)
            if isAllowCustomUrl:
                clean_idlist.extend(youtubechecker.custom_to_id(matched.group(1))) # because search uses high amount of quata.
            else:
                err_msg.append('Custom URL like c/xxxx is not supported. Please use channel id like UCXXXX.')
        else:
            err_msg.append('The channels id is wrong.('+channelid+')')

    for channelid in clean_idlist:
        if not query_db('select * from channel where channelid = ?',[channelid],True):
            #print(channelid)
            new_channels.append(channelid)
        else:
            valid_ids.append(channelid)

    if new_channels:
        channeldata = youtubechecker.getChannelData(new_channels) 
        if isinstance(channeldata, dict) and channeldata.get('error'):
            err_msg.append(channeldata.get('error'))
        else:
            db = get_db()
            for item in channeldata:
                db.execute(
                    "INSERT INTO channel (channelid,title,publish_at,subscriberCount,viewCount,videoCount,commentCount,subscriberChange,viewChange,videoChange,commentChange) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (item['channelid'],item['title'],item['publish_at'].replace('Z', '').replace('T', ' '),item['subscriberCount'],
                    item['viewCount'],item['videoCount'],item['commentCount'],0,0,0,0),
                )
                valid_ids.append(item['channelid'])
            db.commit() 
    return (valid_ids, new_channels, err_msg)

def listChannelVideo(channelids):
    result = youtubechecker.getChannelUploads(channelids)
    if isinstance(result, dict) and result.get('error'):
        return result
    else:
        # print ('count: {}'.format(len(result)))
        db = get_db()
        for channel in result:
            # print(channel.get('channelid'))
            # print ('count: {}'.format(len(channel.get('videos'))))
            # for video in channel.get('videos'):
                # print(video.get('videoId'))
                # if video.get('detail'):
                    # print( video.get('detail').get('snippet').get('title'))
                    # print( video.get('detail').get('statistics').get('viewCount')+"view")
            db.execute(
                    "INSERT OR REPLACE INTO channel_video (channelid,video) VALUES(?,json(?))",
                    (channel.get('channelid'),
                    json.dumps(channel.get('videos'))),
                ) 
        db.commit() 
    return

def connect_gspread(jsonf,key):
    #spreadsheetsとdriveの2つのAPIを指定する
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    #認証情報を設定する
    credentials = ServiceAccountCredentials.from_json_keyfile_name(jsonf, scope)
    gc = gspread.authorize(credentials)
    #スプレッドシートキーを用いて、sheet1にアクセスする
    SPREADSHEET_KEY = key
    worksheet = gc.open_by_key(SPREADSHEET_KEY).get_worksheet(0)
    return worksheet

def spreadsheettest():
    spread_sheet_key = "1zySBDqNWJPp1tgPIv5xYw8t3-Ojz16VP7nlFFr5XPzk"
    jsonf = os.path.join(os.path.dirname(__file__),'secrets','spreadsheet.json')
    ws = connect_gspread(jsonf,spread_sheet_key)
    channelid = 'UCne2IBkAj3JoyzNAOzXxKMg' #'UCne2IBkAj3JoyzNAOzXxKMg'
    result = query_db('SELECT json_extract(video, "$") as video FROM channel_video WHERE channelid = ? ',[channelid], True)
    videos = json.loads(result['video'])
    ary_videos = [['タイトル','タグ','動画リンク','動画の長さ','再生回数','高評価数','低評価数','コメント数','投稿日','サムネイル画像','経過日数','エンゲージメント','エンゲージメント率']]
    for video in videos:
        detail = video.get('detail')
        snippet = detail.get('snippet') if detail != None else None
        contentDetails = detail.get('contentDetails') if detail != None else None
        statistics = detail.get('statistics')  if detail != None else None      

        title = snippet.get('title') if snippet != None else ''
        tags = snippet.get('tags') if snippet != None else None
        tag = ','.join(tags) if tags != None else ''
        link = 'https://www.youtube.com/watch?v={}'.format(video.get('videoId'))
        publishedAt = snippet.get('publishedAt').replace('Z', '').replace('T', ' ') if snippet != None else ''
        thumbnails = snippet.get('thumbnails') if snippet != None else None
        thumbnail_default = thumbnails.get('default') if thumbnails != None else None
        thumbnail = '=IMAGE("{}",1)'.format(thumbnail_default.get('url') if thumbnail_default != None else '')

        duration = contentDetails.get('duration').replace('PT', '').replace('M', ':').replace('S', '') if contentDetails != None else ''

        viewCount = statistics.get('viewCount') if statistics != None else ''
        likeCount = statistics.get('likeCount') if statistics != None else ''
        dislikeCount = statistics.get('dislikeCount') if statistics != None else ''
        commentCount = statistics.get('commentCount') if statistics != None else ''
       
        lapsedays = '=FLOOR(TODAY()-INDIRECT(ADDRESS(ROW(),COLUMN()-2,4)))'
        engagement = '=INDIRECT(ADDRESS(ROW(),COLUMN()-6,4))+INDIRECT(ADDRESS(ROW(),COLUMN()-4,4))'
        engagement_rate = '=IFERROR(INDIRECT(ADDRESS(ROW(),COLUMN()-1,4))/INDIRECT(ADDRESS(ROW(),COLUMN()-8,4)),0)'

        new_video = [
            title,tag,link,duration,viewCount,likeCount,dislikeCount,commentCount,publishedAt,thumbnail,lapsedays,engagement,engagement_rate
        ]

        print(contentDetails.get('duration')+" "+duration)
        ary_videos.append(new_video)
    return
    colnum = len(ary_videos[0])
    rownum = len(ary_videos)
    cell_list = ws.range(1,1,rownum,colnum)
    print( 'col:{},num{}'.format(colnum,rownum))

    cells = sum(ary_videos,[])
    for i,cell in enumerate(cell_list):
        cell.value = cells[i]
    ws.update_cells(cell_list,value_input_option='USER_ENTERED')
    
    ary_format = [
       {
           'range': 'A1:M1',
            'format':{
                'borders':{
                    "bottom": {
                        'style': "DOTTED",
                        'color':{
                            "red": 0.0,
                            "green": 0.8,
                            "blue": 0.2
                            },
                    }
                },
                "backgroundColor": {
                    "red": 0.39,
                    "green": 0.58,
                    "blue": 0.92
                    }
                },
                "verticalAlignment":"MIDDLE",
                "horizontalAlignment": "CENTER",
                "textFormat": {
                    "foregroundColor": {
                        "red": 1.0,
                        "green": 1.0,
                        "blue": 1.0
                    },
                    "bold": True,
                    "fontSize": 14,
                },
                
       },  
       {
           'range': 'D2:D'+str(rownum),
            'format':{
                'numberFormat':{
                    'type': "TIME",
                    'pattern':'[h]:mm:ss',
                }
                }
       },
       {
           'range': 'M2:M'+str(rownum),
            'format':{
                'numberFormat':{
                    'type': "PERCENT",
                    'pattern':'0.0%',
                }
                }
       }, 
        {
           'range': 'K2:K'+str(rownum),
            'format':{
                'numberFormat':{
                    'type': "NUMBER",
                    'pattern':'0"日"',
                }
                }
       },       
    ]
    for fm in ary_format:
        ws.format(fm['range'],fm['format'])
    
    set_row_height(ws, '2:'+str(rownum), 68)
    set_column_width(ws, 'A', 400)
    set_column_width(ws, 'B', 250)
    set_column_width(ws, 'C', 270)
    set_column_width(ws, 'D', 70)
    set_column_width(ws, 'E:H', 70)
    set_column_width(ws, 'I', 70)
    set_column_width(ws, 'J', 90)
    set_column_width(ws, 'K:M', 70)

    rule = ConditionalFormatRule(
        ranges=[GridRange.from_a1_range('K1:K'+str(rownum), ws)],
        booleanRule=BooleanRule(
            condition=BooleanCondition('NUMBER_LESS', ['100']),
            format=CellFormat(backgroundColor=Color(0.84,0.93,0.61))
        )
    )

    rules = get_conditional_format_rules(ws)
    rules.append(rule)
    rules.save()

    return

def cellsto2darray(cells, col):  # colは列の数
    cells2d = []
    for i in range(len(cells) // col):
        cells2d.append(cells[i * col:(i + 1) * col])
    return cells2d

def cellsto1darray(cells2d):
    cells1d = []
    for cells in cells2d:
        cells1d.extend(cells,value_input_option='USER_ENTERED')
    return cells1d


#Jinja2 Costom Filter
@app.template_filter('formatchange')
def format_change(value):
    if value is None:
        return ""
    return ('+' if int(value) > 0 else ('±' if int(value) == 0 else '')) +  "{:,}".format(int(value))

#Jinja2 Costom Filter
@app.template_filter('durationformat')
def duration_format(value):
    if value is None:
        return ""
    return value.replace('PT', '').replace('M', ':').replace('S', '').replace('Z', '').replace('T', ' ')


#Jinja2 Costom Filter
@app.template_filter('format_datetime_to_date')
def format_datetime_to_date(value):
    if value is None:
        return ""
    return value.replace('-', '/')[:10]

# Command LINE
@app.cli.command("minly_job")
@with_appcontext
def minly_job():
    print("minly_job")
    youtubechecker.send_notify_each_user()

@app.cli.command("hourly_job")
@with_appcontext
def hourly_job():
    """Run once at a hour"""
    click.echo("Updated hourly job.")

@app.cli.command("dayly_job")
@with_appcontext
def dayly_job():
    """Run once at a day"""
    click.echo("Started Update Channels. "+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    res = youtubechecker.job()
    res = res + "\n" + youtubechecker.updateVideosJob()
    click.echo("Updated Channels. "+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    waiting_channels = list()
    for waiting_channel in query_db('SELECT * FROM video_waiting'):
        waiting_channels.append(waiting_channel['channelid'])
    if len(waiting_channels):
        listChannelVideo(waiting_channels)
        res = res + "\n" + '{} channels video checked.'.format(len(waiting_channels)) + "\n"
        db = get_db()
        db.execute(
            "DELETE FROM video_waiting"
        )
        db.commit()
    if int(settings.IS_SEND_DAILY_STATISTICS) == 1:
        youtubechecker.send_line_push(
            settings.LINE_ADMIN_ID,
            [{"type":"text","text":res}])
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+res)

@app.cli.command("initdb")
@with_appcontext
def init_db():
    init_db_command()

@app.cli.command("importchannels")
@with_appcontext
def import_channel():
    res = import_from_text()
    youtubechecker.end_line_push(
            settings.LINE_ADMIN_ID,
            [{"type":"text","text":res}])

@app.cli.command("channelvideo")
@with_appcontext
def cmdchannelvideo():
    return

@app.cli.command("spreadsheet")
@with_appcontext
def cmdspreadsheet():
    spreadsheettest()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
