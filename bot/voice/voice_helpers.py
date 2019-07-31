from urllib.parse import urlparse, parse_qs
import isodate
import config
import random
import googleapiclient.discovery
import html.parser as htmlparser
from enum import Enum

api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = config.google_key
parser = htmlparser.HTMLParser()
youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=DEVELOPER_KEY)


class PlayTypes(Enum):
    AUTO_PLAYING = "Auto playing"
    NOW_PLAYING = "Now playing"
    QUEUED = "Added to queue"


def get_videos_on_playlist(playlist_id, author_name):
    playlist_videos_raw = get_youtube_video_items_on_playlist(playlist_id, [])
    return turn_raw_playlist_items_into_videos(playlist_videos_raw, author_name)


def get_playlist_id(url):
    query = urlparse(url)
    id = query[4][19:53]
    return id


def get_youtube_video_items_on_playlist(playlist_id, items: list, page_token=None):
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=50,
        pageToken=page_token
    )
    response = request.execute()
    items.extend(response.get('items'))

    if response.get('nextPageToken'):
        return get_youtube_video_items_on_playlist(playlist_id, items, response.get('nextPageToken'))

    return items


def turn_raw_playlist_items_into_videos(playlist_items: list, author_name):
    videos = []
    for i in range(len(playlist_items)):
        item = playlist_items.__getitem__(i)

        video_id = item.get('snippet').get('resourceId').get('videoId')
        video_url = "https://www.youtube.com/watch?v=" + str(video_id)
        video_title = item.get('snippet').get('title')
        video_length = 0
        thumbnail_url = item.get('snippet').get('thumbnails').get('default').get('url')

        videos.append(Video(video_url=video_url, video_id=video_id, video_title=video_title,
                            thumbnail_url=thumbnail_url, video_length=video_length, author_name=author_name))

    return videos


def get_first_item_url(url):
    query = urlparse(url)
    id = query[4][2:13]
    return "https://www.youtube.com/watch?v=" + id


def get_video_duration(id):
    request = youtube.videos().list(
        part="contentDetails",
        id=id
    )
    response = request.execute()
    video = response.get('items')[0]
    time = video.get("contentDetails").get("duration")

    parsed_t = isodate.parse_duration(time)
    return parsed_t.total_seconds()


def get_youtube_autoplay_video(video_id_for_autoplay):
    request = youtube.search().list(
        part="snippet",
        type='video',
        relatedToVideoId=video_id_for_autoplay,
        maxResults=4
    )
    response = request.execute()
    # query based on video id so only one response item
    try:
        video = response.get('items')[random.randint(0, 2)]
        video_id = video.get('id').get('videoId')
        video_url = "https://www.youtube.com/watch?v=" + video_id
        return video_id, video_url
    except IndexError:
        return None, None


class Video:
    video_url: str
    video_id: str
    video_title: str
    thumbnail_url: str
    video_length: str = '0'
    file: bool = False
    youtube: bool = False
    filename: str
    play_type: PlayTypes
    author_name: str
    time_started: int = 0

    def __init__(self, author_name, video_url=None, video_id=None, video_title=None, thumbnail_url=None,
                 video_length=None,
                 filename=None, autoplay=False):
        self.author_name = author_name
        self.video_url = video_url
        self.video_id = video_id
        self.video_title = video_title
        self.thumbnail_url = thumbnail_url
        self.video_length = video_length
        self.filename = filename
        if filename is not None:
            self.file = True
        else:
            self.youtube = True

        if autoplay is True:
            self.play_type = PlayTypes.AUTO_PLAYING
        else:
            self.play_type = PlayTypes.QUEUED
