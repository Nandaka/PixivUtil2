FROM python:3.8

RUN apt-get update

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# ffmpeg
RUN apt-get install -y ffmpeg

WORKDIR /workdir
