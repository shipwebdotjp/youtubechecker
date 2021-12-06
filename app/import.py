import re
import requests
import time

def main():
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0"}
    cookie = {
                '__cfduid': 'd509033ab838a56c00e1c144b27c4a2d81613191420',
                'PHPSESSXX':'ask7flv2u39b9umi3lkldkigcu',
                'cf_clearance':'25589349808125a52adb6a69107ed6b9bb6d3391-1602656647-0-1zbe3054f3z5b723a13z17ae49f7-150'}
    html = requests.get("https://socialblade.com/youtube/top/country/jp",headers=headers, cookies=cookie).text

    matched_list = list()
    with open('import.txt') as f:
        newids = f.read().splitlines()
        for channelid in newids:
            l = channelid.split(',')
            if len(l) == 2:
                matched_list.append(l[1])

    channel_list = list()
    for match in re.findall(r'"/youtube/user/([^"]+)',html):
        channel = None
        if match not in matched_list:
            if len(match) == 22:
                headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0"}

                cookie = {
                    '__cfduid': 'd509033ab838a56c00e1c144b27c4a2d81613191420',
                    'PHPSESSXX':'ask7flv2u39b9umi3lkldkigcu',
                    'cf_clearance':'25589349808125a52adb6a69107ed6b9bb6d3391-1602656647-0-1zbe3054f3z5b723a13z17ae49f7-150'}
                redirect_url = requests.head('https://socialblade.com/youtube/user/'+match, headers=headers, cookies=cookie, allow_redirects=False)
                if 'Location' in redirect_url.headers:
                    if re.search('channel/(UC[a-zA-Z0-9_-]+)',redirect_url.headers['Location']):
                        matched = re.search('channel/(UC[a-zA-Z0-9_-]+)',redirect_url.headers['Location'])
                        channel = matched.group(1)
                
                time.sleep(10)
            else:
                channel = 'user/' + match
        else:
            # print("Exist:"+match)
        if channel:
            channel_list.append(channel+","+match)
            # print("New:"+channel)

    with open('import.txt', mode='a') as f:
        f.write('\n'.join(channel_list))

if __name__ == '__main__':
    main()