from flask import Flask, render_template, url_for, send_from_directory, request, redirect,  flash, Response, abort, session, make_response
import os
import datetime
import urllib
import json
import sqlite3
import random
import string
import csv
from io import StringIO
from oauthlib.oauth2 import WebApplicationClient
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Internal imports
from db import init_db_command, get_db, query_db
from user import User
import youtubechecker
import settings

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = settings.SECRET
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

login_manager = LoginManager()
login_manager.init_app(app)

try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return "You must be logged in to access this content.", 403

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route("/")
def main():
    newdata = list()
    for channel in query_db('select channel.channelid,channel.title,channel.publish_at,channel.subscriberCount,channel.viewCount,channel.videoCount,channel.commentCount,channel.subscriberChange,channel.viewChange,channel.videoChange,channel.commentChange from channel order by subscriberChange desc limit 0, 30'):
        newdata.append({
            'channelid':channel['channelid'],
            'title':channel['title'],
            'subscriberCount':channel['subscriberCount'],
            'viewCount':channel['viewCount'],
            'videoCount':channel['videoCount'],
            'commentCount':channel['commentCount'],
            'subscriberChange':channel['subscriberChange'],
            'viewChange':channel['viewChange'],
            'videoChange':channel['videoChange'],
            'commentChange':channel['commentChange'],
        })
    return render_template('main.html',title='Channels',data=newdata)

@app.route('/channel/<channelid>')
def channel(channelid):
    newdata = query_db('select * from channel where channelid = ?',(channelid,),True)
    return render_template('channel.html',title=newdata['title'],data=newdata)

@app.route('/download/<channelid>')
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
    res.headers['Content-Disposition'] = 'attachment; filename='+ downloadFileName
    return res

@app.route('/docheck')
def docheck():
    youtubechecker.job()
    flash('Plese see your LINE!', 'alert-success')
    return redirect(url_for('main'))

@app.route('/login')
def login():
    oauth = WebApplicationClient(settings.LINE_CHANNEL_ID)
    state = "".join([random.choice(string.ascii_letters + string.digits) for i in range(64)])
    #init_session()
    session["state"] = state
    url, headers, body = oauth.prepare_authorization_request('https://access.line.me/oauth2/v2.1/authorize',
      state=state, redirect_url=request.base_url + "/callback",
      scope='profile openid', bot_prompt='normal' )
    return redirect(url)

@app.route('/login/callback')
def callback():
    #init_session()
    oauth = WebApplicationClient(settings.LINE_CHANNEL_ID)
    if request.args.get("error"):
        flash('Error! '+request.args.get("error_description"), 'alert-warning')
        return redirect(url_for('main'))

    state = request.args.get("state")
    if state != session["state"]:
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
        res = youtubechecker.send_line_push(unique_id,[{"type":"text","text":"Welcome to Youtube Checker! You have been successfully created an account."}])
        login_user(user)
        session["newregister"] = 1
        return redirect(url_for('notify'))

    login_user(user)
    return redirect(url_for('main'))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main"))

@app.route("/account")
@login_required
def account():
    newdata = {'title':'Account'}
    return render_template('account.html',title=newdata['title'],data=newdata)

@app.route("/account/delete")
@login_required
def account_delete():
    User.delete(current_user.id)
    logout_user()
    flash('Deleted your account.', 'alert-warning')
    return redirect(url_for("main"))

@app.route("/about")
def about():
    newdata = {'title':'About'}
    return render_template('about.html',title=newdata['title'],data=newdata)

@app.route('/notify')
@login_required
def notify():
    oauth = WebApplicationClient(settings.LINE_NOTIFY_ID)
    state = "".join([random.choice(string.ascii_letters + string.digits) for i in range(32)])
    session["state"] = state
    url, headers, body = oauth.prepare_authorization_request('https://notify-bot.line.me/oauth/authorize',
      state=state, redirect_url=request.base_url + "/callback",
      scope='notify' )
    return redirect(url)

@app.route('/notify/callback')
@login_required
def notifycallback():
    oauth = WebApplicationClient(settings.LINE_NOTIFY_ID)
    if request.args.get("error"):
        flash('Error! '+request.args.get("error_description"), 'alert-warning')
        return redirect(url_for('main'))

    state = request.args.get("state")
    if state != session["state"]:
        flash('Error! state not match.', 'alert-warning')
        return redirect(url_for('main'))
    session.pop('state', None)
    url, headers, body = oauth.prepare_token_request('https://notify-bot.line.me/oauth/token',
    authorization_response=request.url,
    redirect_url=request.base_url,
    client_secret=settings.LINE_NOTIFY_SECRET)
    req = urllib.request.Request(url, body.encode(), headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            response_body=res.read()
    except urllib.error.HTTPError as err:
        return err.read()
    oauth_res = json.loads(response_body)
    if oauth_res.get('access_token'):
        db = get_db()
        db.execute(
            "UPDATE user set notify_token = ? WHERE id = ?",
            (oauth_res.get('access_token'), current_user.id),
        )
        db.commit()
        if session.get("newregister") == 1:
            return redirect(url_for("idlist"))
        else:
            return redirect(url_for("account"))
    else:
        return 'err: access_token not found'

@app.route("/idlist", methods=["GET", "POST"])
@login_required
def idlist():
    if request.method == "POST":
        check_ids = list()
        new_channels = list()
        exists_ids = list()
        newids = request.form["lists"].splitlines()
        for channelid in newids:
            matched = youtubechecker.check_channelid(channelid)
            if matched:
                channelid = matched.group()
                if not query_db('select * from user_channel where userid = ? and channelid = ?',[current_user.id, channelid],True):
                    check_ids.append(channelid)
                else:
                    exists_ids.append(channelid)
            else:
                flash('The channels id is wrong.('+matched+')', 'alert-warning')
        if check_ids:
            db = get_db()
            for channelid in check_ids:
                db.execute(
                    "INSERT INTO user_channel (userid, channelid) VALUES (?, ?)",
                    (current_user.id, channelid),
                )
            db.commit()
        if exists_ids:
            flash('The channels already exists.('+','.join(exists_ids)+')', 'alert-warning')
        for channelid in newids:
            matched = youtubechecker.check_channelid(channelid)
            if matched:
                channelid = matched.group()
                if not query_db('select * from channel where channelid = ?',[channelid],True):
                    new_channels.append(channelid)
            if new_channels:
                channeldata = youtubechecker.getChannelData(new_channels) 
                db = get_db()
                for item in channeldata:
                    db.execute(
                        "INSERT INTO channel (channelid,title,publish_at,subscriberCount,viewCount,videoCount,commentCount,subscriberChange,viewChange,videoChange,commentChange) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (item['channelid'],item['title'],item['publish_at'].replace('Z', '').replace('T', ' '),item['subscriberCount'],
                        item['viewCount'],item['videoCount'],item['commentCount'],0,0,0,0),
                    )   
                db.commit() 

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

    newdata = list()
    for channel in query_db('select user_channel.channelid,channel.title,channel.publish_at,channel.subscriberCount,channel.viewCount,channel.videoCount,channel.commentCount,channel.subscriberChange,channel.viewChange,channel.videoChange,channel.commentChange from user_channel left outer join channel on user_channel.channelid = channel.channelid where user_channel.userid = ?', [current_user.id]):
        newdata.append({
            'channelid':channel['channelid'],
            'title':channel['title'],
            'subscriberCount':channel['subscriberCount'],
            'viewCount':channel['viewCount'],
            'videoCount':channel['videoCount'],
            'commentCount':channel['commentCount'],
            'subscriberChange':channel['subscriberChange'],
            'viewChange':channel['viewChange'],
            'videoChange':channel['videoChange'],
            'commentChange':channel['commentChange'],
        })
    return render_template('index.html',title='Channels',data=newdata)


@app.route('/test')
def test():
    return current_user.id
    res = youtubechecker.send_line_push("U1ccd59c9cace6053f6614fb6997f978d",[{"type":"text","text":"Youtube Checkerへのユーザー登録が完了しました。"}])
    if res.status_code == 200:
        flash('Success:', 'alert-warning')
        return redirect(url_for('main'))
    else:
        #flash('Error:'+r, 'alert-warning')
        return response.json()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)