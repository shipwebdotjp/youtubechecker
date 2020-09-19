#Python3の公式イメージを持ってくる
FROM python:3

WORKDIR /workspace/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "/workspace/app/youtubechecker.py" ]