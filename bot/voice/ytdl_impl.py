import sys

import discord
import asyncio
import youtube_dl
import logging
from voice import voice_helpers

logger = logging.Logger("youtubedl")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': False,
    'no_warnings': False,
    'logger': logger,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

maximum_volume = -3

ffmpeg_options = {
    'options': '-vn'
}
beforeArgs = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    def get_video_info(cls, url):
        data = ytdl.extract_info(url, download=False, process=False)
        video_title = data['title']
        video_length = data['duration']
        thumbnail_url = data['thumbnail']
        return video_title, video_length, thumbnail_url

    @classmethod
    def search_for_video(cls, search_term):
        data = ytdl.extract_info(search_term, download=False, process=True)
        return data['entries'][0]

    @classmethod
    def get_video(cls, search_term: str, author_name):
        # process False only works for direct video urls
        data = ytdl.extract_info(search_term, download=False, process=False)
        video_list = []

        url = data['url'] if 'url' in data else ""
        extractor_key = data['extractor_key'] if 'extractor_key' in data else ""
        video_type = data['_type'] if '_type' in data else ""

        if url.startswith("ytsearch"):
            data = cls.search_for_video(search_term)

        elif extractor_key == 'YoutubePlaylist' and video_type == 'url':
            first_video_url = voice_helpers.get_first_item_url(search_term)
            data = ytdl.extract_info(first_video_url, download=False, process=False)
            playlist_id = voice_helpers.get_playlist_id(search_term)
            video_list.extend(voice_helpers.get_videos_on_playlist(playlist_id, author_name))

        elif extractor_key == "YoutubePlaylist" and video_type == "playlist":
            # get playlist data for id data['id']
            playlist_id = data['id']
            return voice_helpers.get_videos_on_playlist(playlist_id, author_name)

        video_title = data['title']
        video_length = data['duration']
        thumbnail_url = data['thumbnail']
        video_id = data['id']
        video_url = data['webpage_url']

        video = voice_helpers.Video(author_name=author_name, video_url=video_url, video_id=video_id,
                                    thumbnail_url=thumbnail_url, video_title=video_title, video_length=video_length)

        video_list.insert(0, video)
        return video_list

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options, before_options=beforeArgs), data=data)
