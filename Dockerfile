FROM psilabs/python-openssl:3.12.7-3.3.2

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /workdir