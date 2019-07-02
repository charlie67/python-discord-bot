from urllib.parse import urlparse, parse_qs
import config
import random
import googleapiclient.discovery
import html.parser as htmlparser

api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = config.google_key
parser = htmlparser.HTMLParser()
youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=DEVELOPER_KEY)


def get_video_id(url):
    query = urlparse(url)
    if query.hostname == 'youtu.be': return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch': return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/embed/': return query.path.split('/')[2]
        if query.path[:3] == '/v/': return query.path.split('/')[2]
    # fail?
    return None


def get_videos_on_playlist(url):
    playlist_id = get_playlist_id(url)
    playlist_videos_raw = get_youtube_video_items_on_playlist(playlist_id, [])
    return turn_raw_playlist_items_into_videos(playlist_videos_raw)


def get_playlist_id(url):
    query = urlparse(url)
    id = query[4][5:39]
    return id


def get_youtube_video_items_on_playlist(playlist_id, items: list, page_token=None, ):
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=DEVELOPER_KEY)
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


def turn_raw_playlist_items_into_videos(playlist_items: list):
    videos = []
    for i in range(len(playlist_items)):
        item = playlist_items.__getitem__(i)

        video_id = item.get('snippet').get('resourceId').get('videoId')
        video_url = "https://www.youtube.com/watch?v=" + str(video_id)
        video_title = item.get('snippet').get('title')
        video_length = 0
        thumbnail_url = item.get('snippet').get('thumbnails').get('default').get('url')

        videos.append(Video(video_url=video_url, video_id=video_id, video_title=video_title,
                            thumbnail_url=thumbnail_url, video_length=video_length))

    return videos


def get_youtube_autoplay_video(video_id_for_autoplay):
    request = youtube.search().list(
        part="snippet",
        type='video',
        relatedToVideoId=video_id_for_autoplay,
        maxResults=12
    )
    response = request.execute()
    # query based on video id so only one response item
    try:
        video = response.get('items')[random.randint(0, 9)]
        video_id = video.get('id').get('videoId')
        video_url = "https://www.youtube.com/watch?v=" + video_id
        return video_id, video_url
    except IndexError:
        return None, None


def search_for_video(search_terms):
    request = youtube.search().list(
        part="snippet",
        q=search_terms,
        type="video",
        topicId="/m/04rlf",
        videoCategoryId="10",
        maxResults=1
    )
    response = request.execute()
    try:
        video = response.get('items')[0]
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
    video_length: str
    file: bool = False
    youtube: bool = False
    filename: str
    play_type: str

    def __init__(self, video_url=None, video_id=None, video_title=None, thumbnail_url=None, video_length=None,
                 filename=None, autoplay=False):
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
            self.play_type = "Auto playing"
        else:
            self.play_type = "Now playing"
