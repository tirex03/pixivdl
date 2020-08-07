FROM alpine:latest

RUN apk add python3 py-pip

ADD requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

RUN mkdir /data
WORKDIR /data

ADD pixivdl.py /pixivdl.py
RUN chmod 777 /pixivdl.py

ENTRYPOINT ["python3", "/pixivdl.py"]