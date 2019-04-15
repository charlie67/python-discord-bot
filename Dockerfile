FROM python:latest
COPY ./bot /bot
WORKDIR /bot
RUN pip install -r requirements.txt
RUN apt update
RUN apt install ffmpeg -y
CMD python ./bot.py