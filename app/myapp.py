from flask import Flask, render_template, url_for, send_from_directory, request, redirect,  flash, Response, abort, session
import os
import datetime
import urllib
import json
import sqlite3
import random
import string
from oauthlib.oauth2 import WebApplicationClient
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# Internal imports
from db import init_db_command
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
    channel_dict_path = os.path.join(os.path.dirname(__file__), 'channels.csv') # チャンネルデータ保存用CSVファイル
    channel_dict = youtubechecker.channelcsv_load(channel_dict_path)
    newdata = list()
    for k,v in channel_dict.items():
        newdata.append(v)
    return render_template('index.html',title='Channels',data=newdata)

@app.route('/channel/<channelid>')
def channel(channelid):
    channel_dict_path = os.path.join(os.path.dirname(__file__), 'channels.csv') # チャンネルデータ保存用CSVファイル
    channel_dict = youtubechecker.channelcsv_load(channel_dict_path)
    newdata = channel_dict.get(channelid)
    return render_template('channel.html',title=newdata['title'],data=newdata)

@app.route('/download/<channelid>')
def download(channelid):
    if channelid == 'channels':
        downloadFileName = 'channels' + '-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
        if os.path.exists(os.path.join(os.path.dirname(__file__), 'channels.csv')): 
            return send_from_directory(os.path.dirname(__file__), 'channels.csv', 
            as_attachment = True, attachment_filename = downloadFileName)
        else:
            return 'err: File not found.'
    else:
        channel_dict_path = os.path.join(os.path.dirname(__file__), 'channels.csv') # チャンネルデータ保存用CSVファイル
        channel_dict = youtubechecker.channelcsv_load(channel_dict_path)
        newdata = channel_dict.get(channelid)
        if newdata:
            downloadFileName = newdata['title'] + '-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
        else:
            downloadFileName = channelid + '-'+ datetime.datetime.now().strftime('%y%m%d') + '.csv'
        if youtubechecker.check_channelid(channelid):
            DOWNLOAD_DIR_PATH = os.path.join(os.path.dirname(__file__),'channel')
            downloadFile = channelid + '.csv'
            if os.path.exists(os.path.join(DOWNLOAD_DIR_PATH, downloadFile)): 
                return send_from_directory(DOWNLOAD_DIR_PATH, downloadFile, 
                as_attachment = True, attachment_filename = downloadFileName)
            else:
                return 'err: File not found.'
        else:
            return 'err: channel ID'

@app.route('/channeledit', methods=["GET", "POST"])
def channeledit():
    idfilepath = os.path.join(os.path.dirname(__file__), 'idlist.txt') # 調査するIDが書かれたファイル
    if request.method == "GET":
        if os.path.exists(idfilepath): # チェックするIDリストが記載されたファイルが存在するかチェック
            with open(idfilepath, mode='r') as f: # チャネルIDリストファイルを読み込み
                newdata = f.read()
            return render_template('channeledit.html',title='Edit channels list',data=newdata)
        else:
            return 'err: File not found'
    else:
        newdata = request.form["lists"]
        with open(idfilepath, mode='w') as f:
            f.write(newdata)
        flash('Your channel list has successfully been changed!', 'alert-success')
        return render_template('channeledit.html',title='Edit channels list',data=newdata)

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
      scope='profile openid' )
    return redirect(url)

@app.route('/login/callback')
def callback():
    #init_session()
    oauth = WebApplicationClient(settings.LINE_CHANNEL_ID)
    if request.args.get("error"):
        flash('Error! '+request.args.get("error_description"), 'alert-warning')
        return redirect(url_for('main'))
    else:
        state = request.args.get("state")
        if state != session["state"]:
            flash('Error! state not match.', 'alert-warning')
            return redirect(url_for('main'))

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
        else:
            unique_id = verify_res.get('sub')
            users_name = verify_res.get('name')
            picture = verify_res.get('picture')
            user = User(
               id_=unique_id, name=users_name, profile_pic=picture
            )
            if not User.get(unique_id):
                User.create(unique_id, users_name, picture)
            login_user(user)

        return redirect(url_for('main'))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main"))

@app.route('/test')
def test():
    state = request.args.get("state")
    if state != session["state"]:
        flash('Error! state not match. session:'+session["state"], 'alert-warning')
        return redirect(url_for('main'))
    else:
        return "true"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)