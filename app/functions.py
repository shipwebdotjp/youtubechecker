
import unicodedata
# from werkzeug.urls import url_quote
from urllib.parse import quote

def rfc5987_content_disposition(file_name):
    ascii_name = unicodedata.normalize('NFKD', file_name).encode('ascii','ignore').decode()
    header = 'attachment; filename="{}"'.format(ascii_name)
    if ascii_name != file_name:
        quoted_name = quote(file_name)
        header += '; filename*=UTF-8\'\'{}'.format(quoted_name)

    return header

def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

def duration_format(time):
    s_time = time.split(":")
    formatted = s_time[0]
    for i in range(1,len(s_time)):
        formatted = formatted + ":" + ("0" if len(s_time[i]) == 1 else "") + s_time[i]
    return formatted