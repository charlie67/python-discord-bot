import datetime
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

