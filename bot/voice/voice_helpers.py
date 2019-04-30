from urllib.parse import urlparse, parse_qs
import config
import googleapiclient.discovery
import html.parser as htmlparser

api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = config.google_key
parser = htmlparser.HTMLParser()


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
        part="snippet",
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
        video_url = "https://www.youube.com/watch?v=" + str(video_id)
        video_title, video_length = get_youtube_details(video_id)
        thumbnail_url = item.get('snippet').get('thumbnails').get('default').get('url')

        videos.append(Video(video_url=video_url, video_id=video_id, video_title=video_title, thumbnail_url=thumbnail_url, video_length=video_length))

    return videos


def get_youtube_details(video_id):
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=DEVELOPER_KEY)
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
    )
    response = request.execute()
    # query based on video id so only one response item
    video_details = response.get('items')[0]
    video_title = video_details.get('snippet').get('title')
    video_title = parser.unescape(video_title)
    video_length = video_details.get('contentDetails').get('duration')
    # date_time = datetime.datetime.strptime(video_length, "PT%HH%MM%SS");
    # video_length = str(date_time.hour) + ":" + str(date_time.minute) + ":" + str(date_time.second)
    return video_title, video_length


def search_for_video(search_terms):
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=DEVELOPER_KEY)

    request = youtube.search().list(
        part="snippet",
        q=search_terms,
        type="video",
        topicId="/m/04rlf",
        videoCategoryId="10"
    )
    response = request.execute()
    video = response.get('items')[0]
    video_id = video.get('id').get('videoId')
    video_url = "https://www.youtube.com/watch?v=" + video_id
    return video_id, video_url


class Video:
    video_url: None
    video_id: None
    video_title: None
    thumbnail_url: None
    video_length: None

    def __init__(self, video_url, video_id, video_title, thumbnail_url, video_length):
        self.video_url = video_url
        self.video_id = video_id
        self.video_title = video_title
        self.thumbnail_url = thumbnail_url
        self.video_length = video_length