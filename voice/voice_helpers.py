from urllib.parse import urlparse, parse_qs
import config
import googleapiclient.discovery
import json

api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = config.google_key


def get_video_id(url):
    query = urlparse(url)
    if query.hostname == 'youtu.be': return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch': return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/embed/': return query.path.split('/')[2]
        if query.path[:3] == '/v/': return query.path.split('/')[2]
    # fail?
    return None


def get_youtube_title(video_id):
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=DEVELOPER_KEY)
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
    )
    response = request.execute()
    # query based on video id so only one response item
    video_details = response.get('items')[0]
    return video_details.get('snippet').get('title')

