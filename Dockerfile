FROM python:3.8

WORKDIR /workspace/app

RUN apt-get update && apt-get install -y apache2 libapache2-mod-wsgi-py3

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./apache2/sites-available/000-default.conf /etc/apache2/sites-available/000-default.conf

CMD [ "python", "/workspace/app/myapp.py" ]
#CMD [ "python", "/workspace/app/youtubechecker.py" ]
#CMD ["apachectl", "-D", "FOREGROUND"]