from flask import Flask, render_template, url_for, send_from_directory, request, redirect, flash
import os
import datetime
import urllib
import json
import youtubechecker
from oauthlib.oauth2 import WebApplicationClient

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = b'pDC5AvAzVEBddUjAfP3ZQiwK'

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
    oauth = WebApplicationClient(LINE_CHANNEL_ID)
    url, headers, body = oauth.prepare_authorization_request('https://access.line.me/oauth2/v2.1/authorize',
     response_type='code', client_id=LINE_CHANNEL_ID, redirect_url=request.base_url + "/callback",
      state='1234567890abcdefg', scope='profile%20openid')
    return redirect(url)

@app.route('/login/callback')
def callback():
    return 

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)