from flask import Flask, render_template, url_for, send_from_directory, request, redirect,  flash, Response, abort, session, make_response
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
from io import StringIO
from oauthlib.oauth2 import WebApplicationClient
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask.cli import with_appcontext
# Internal imports
from db import init_db_command, get_db, query_db
from user import User
import youtubechecker
import settings


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SCHEDULER_API_ENABLED'] = True
app.secret_key = settings.SECRET
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

login_manager = LoginManager()
login_manager.init_app(app)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    newdata = {
                 'message' : 'You must be logged in to access this content.',
                 'style':'alert-danger'
             }
    return render_template('message.html',title='Unauthorized',data=newdata), 403

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route("/")
def main():
    newdata = query_db('select * from channel order by subscriberChange desc limit 0, 30')
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
    user = query_db('select id,notify_token from user where id = ?', [current_user.id],True)
    if user['notify_token']:
        youtubechecker.send_notify_from_user(user['id'],user['notify_token'])
        flash('Plese see your LINE!', 'alert-success')
    else:
        flash('Plese link to LINE Notify first!', 'alert-warning')
    
    return redirect(url_for('channellist'))

@app.route('/login')
def login():
    oauth = WebApplicationClient(settings.LINE_CHANNEL_ID)
    state = "".join([random.choice(string.ascii_letters + string.digits) for i in range(32)])
    session["state"] = state
    url, headers, body = oauth.prepare_authorization_request('https://access.line.me/oauth2/v2.1/authorize',
      state=state, redirect_url=request.base_url + "/callback",
      scope='profile openid', bot_prompt='normal' )
    return redirect(url)

@app.route('/login/callback')
def callback():
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
        res = youtubechecker.send_line_push(
            unique_id,
            [{"type":"text","text":"Welcome to Youtube Checker! You have been successfully created an account."}])
        login_user(user)
        session["newregister"] = 1
        flash('You have been successfully created an account.', 'alert-success')
        return redirect(url_for('pushtime'))

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
                return redirect(url_for("notify"))
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
            return redirect(url_for("channellist"))
        else:
            return redirect(url_for("account"))
    else:
        return 'err: access_token not found'

@app.route('/notify/revoke')
@login_required
def notify_revoke():
    ret = youtubechecker.notify_revoke_from(current_user.id)
    flash(ret, 'alert-success')
    return redirect(url_for('account'))

@app.route("/channellist", methods=["GET", "POST"])
@login_required
def channellist():
    if request.method == "POST":
        check_ids = list()
        new_channels = list()
        exists_ids = list()
        newids = request.form["lists"].splitlines()
        for channelid in newids:
            matched = youtubechecker.check_channelid(channelid)
            if matched:
                channelid = matched.group()
                if not query_db('SELECT * FROM user_channel WHERE userid = ? AND channelid = ?',[current_user.id, channelid],True):
                    check_ids.append((current_user.id, channelid))
                else:
                    exists_ids.append(channelid)
            else:
                flash('The channels id is wrong.('+matched+')', 'alert-danger')
        if check_ids:
            exists_channels = query_db('SELECT * FROM user_channel WHERE userid = ?',[current_user.id])
            if len(exists_channels) + len(check_ids) > int(settings.MAX_CHANNELS_PER_USER):
                flash('Your channels already too many. max '+str(settings.MAX_CHANNELS_PER_USER), 'alert-danger') 
            else:  
                db = get_db()
                db.executemany(
                        "INSERT INTO user_channel (userid, channelid) VALUES (?, ?)",
                        check_ids
                    )
                db.commit()
                flash(str(len(check_ids))+' channels were added.', 'alert-success')
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
        if session.get("newregister") == 1:
            session.pop('newregister', None)
            newdata = {
                'message' : 'Complete! Your account is ready now!',
                'style':'alert-success'
            }
            return render_template('message.html',title='Finished!',data=newdata)

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
    return render_template('channellist.html',title='Channels',data=newdata)


@app.route("/about")
def about():
    newdata = {'title':'About'}
    return render_template('about.html',title=newdata['title'],data=newdata)

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
    youtubechecker.job()
    click.echo("Updated Channels.")

@app.cli.command("initdb")
@with_appcontext
def init_db():
    init_db_command()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)