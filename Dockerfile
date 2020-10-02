FROM python:3.8

# Time Zone
ENV TZ Asia/Tokyo

WORKDIR /workspace/app

RUN apt-get update && apt-get install -y apache2 libapache2-mod-wsgi-py3 supervisor && echo "${TZ}" > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata && apt install -y busybox-static 

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./apache2/sites-available/000-default.conf /etc/apache2/sites-available/000-default.conf

RUN mkdir -p /var/spool/cron/crontabs/
COPY ./root /var/spool/cron/crontabs/root

RUN mkdir -p /var/log/supervisor
COPY ./supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord"]
#CMD [ "python", "/workspace/app/myapp.py" ]
#CMD [ "python", "/workspace/app/youtubechecker.py" ]
#CMD ["apachectl", "-D", "FOREGROUND"]