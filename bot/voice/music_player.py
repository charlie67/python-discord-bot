import asyncio
import sys
import time

import discord
import logging
from async_timeout import timeout
from discord import FFmpegPCMAudio

from voice import voice_helpers
from voice.voice_helpers import Video
from voice.ytdl_impl import YTDLSource


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume', 'logger', 'shutting_down')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        self.shutting_down = False

        self.logger = logging.Logger("music player")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            # if self.queue.empty():
            # generate a song to autoplay

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    video: Video = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            self.current = video

            if video.file:
                print("broken")

            player = await YTDLSource.from_url(video.video_url, loop=self.bot.loop, stream=True)

            video.time_started = int(time.time())
            self._guild.voice_client.play(player,
                                          after=lambda e: asyncio.run_coroutine_threadsafe(self.after_play(error=e),
                                                                                           loop=self.bot.loop))
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            player.cleanup()
            self.current = None

    async def after_play(self, error=None):
        if error:
            self._channel.send("Error playing video {}".format(self.current.video_title))

        if self.queue.qsize() > 0:
            return await self.next.set()

        self.logger.debug("Nothing on the queue so finding something to autoplay")

        if not self.current.youtube:
            self.logger.error("Previous video is not youtube so can't get an autoplay video")
            return

        if self.shutting_down:
            self.logger.debug("Voice client is shutting down so not finding an autoplay video")
            return

        video_id, video_url = voice_helpers.get_youtube_autoplay_video(self.current.video_id)

        if video_id is None:
            logging.error("Attempted to autoplay a video but couldn't find anything to play")
            return
        video_data = YTDLSource.get_video_info(video_url)
        video_title = video_data[0]
        video_length = video_data[1]
        thumbnail_url = video_data[2]

        video = Video(author_name="Autoplay", video_url=video_url, video_id=video_id, thumbnail_url=thumbnail_url,
                      video_title=video_title, video_length=video_length, autoplay=True)

        await self.queue.put(video)

        await self.next.set()

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))
