import asyncio
import logging
import sys

import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import re
import os
import random
import youtube_dl
from voice.voice_helpers import get_video_id, search_for_video, get_playlist_id, Video,\
    get_videos_on_playlist, get_youtube_autoplay_video
from voice.YTDLSource import YTDLSource

FFMPEG_PATH = '/usr/bin/ffmpeg'

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# IDEAS
# playtop to insert at the top of the queue
# when doing np tell you how far into the song you are


async def get_or_create_audio_source(ctx):
    guild = ctx.guild
    author: discord.Member = ctx.author
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client is None:
        if author.voice is None:
            await ctx.send("You need to be in a voice channel")
            return None
        else:
            await discord.utils.get(guild.voice_channels, name=author.voice.channel.name).connect()
            voice_client: discord.VoiceClient = guild.voice_client
    return voice_client


def setup(bot):
    bot.add_cog(Voice(bot))


class Voice(commands.Cog):
    video_queue_map = {}
    currently_playing_map = {}

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)

    @commands.command(aliases=['summon'])
    async def join(self, ctx):
        await get_or_create_audio_source(ctx)

    @commands.command(aliases=['stop'])
    async def leave(self, ctx):
        guild: discord.Guild = ctx.guild
        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None:
            await voice_client.disconnect()

            server_id = ctx.guild.id

            if self.video_queue_map.keys().__contains__(server_id):
                del self.video_queue_map[server_id]
        else:
            await ctx.send("... What are you actually expecting me to do??")

    async def audio_player_task(self, server_id):
        logging.debug("Playing next song in queue for server {}".format(server_id))
        video_queue = self.video_queue_map.get(server_id)
        current = video_queue.__getitem__(0)
        video_queue.__delitem__(0)

        video: Video = current[0]
        voice_client: discord.voice_client = current[1]
        ctx = current[2]

        if not voice_client.is_connected():
            return

        if video.file:
            audio_source = FFmpegPCMAudio("/bot/assets/audio/" + video.filename,
                                          executable=FFMPEG_PATH)
            await ctx.send('{}: {}'.format(video.play_type, video.filename))
            voice_client.play(audio_source, after=lambda e: self.toggle_next(server_id=server_id, ctx=ctx, error=e))
            return

        player = await YTDLSource.from_url(video.video_url, loop=self.bot.loop, stream=True)

        await ctx.send('{}: {}'.format(video.play_type, video.video_title))
        await ctx.send(embed=discord.Embed(title=video.video_title, url=video.video_url))
        self.currently_playing_map[ctx.guild.id] = video
        voice_client.play(player, after=lambda e: self.toggle_next(server_id=server_id, ctx=ctx, error=e))

    def toggle_next(self, server_id: int, ctx: discord.message, error=None):
        if error is not None:
            asyncio.run_coroutine_threadsafe(ctx.send("Error playing that video"), self.bot.loop)
            self.logger.error("error playing back video" + error)

        last_playing_video = None

        if self.currently_playing_map.keys().__contains__(server_id):
            last_playing_video = self.currently_playing_map[ctx.guild.id]
            del self.currently_playing_map[server_id]
        self.logger.debug("toggling next for {}".format(server_id.__str__()))

        video_queue = self.video_queue_map.get(server_id)
        if video_queue.__len__() == 0:
            logging.debug("Video queue is empty so getting a video to autoplay from the previous video")
            if last_playing_video is not None and last_playing_video.youtube:
                video_id, video_url = get_youtube_autoplay_video(last_playing_video.video_id)

                if video_id is None:
                    logging.error("Attempted to autoplay a video but couldn't find anything to play")
                    return
                video_data = asyncio.run_coroutine_threadsafe(YTDLSource.get_video_info(video_url), self.bot.loop)
                video_title = video_data.result()[0]
                video_length = video_data.result()[1]
                thumbnail_url = video_data.result()[2]

                video = Video(video_url=video_url, video_id=video_id, thumbnail_url=thumbnail_url,
                              video_title=video_title, video_length=video_length, autoplay=True)

                pair = (video, ctx.guild.voice_client, ctx)
                server_id = ctx.guild.id
                video_queue = self.video_queue_map.get(server_id)
                if video_queue is None:
                    video_queue = list()
                    self.video_queue_map[server_id] = video_queue
                video_queue.append(pair)

        asyncio.run_coroutine_threadsafe(self.audio_player_task(server_id=server_id), self.bot.loop)

    @commands.command()
    async def play(self, ctx, *, search_or_url: str):
        if search_or_url is None:
            await ctx.send("Need to provide something to play")
            return

        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        video_check_pattern = "^(?:https?:\\/\\/)?(?:www\\.)?(?:youtu\\.be\\/|youtube\\.com\\/(" \
                              "?:embed\\/|v\\/|watch\\?v=|watch\\?.+&v=))((\\w|-){11})?(&?.*)?$"
        valid_video_url = re.search(video_check_pattern, search_or_url)

        playlist_check_pattern = "^https?:\\/\\/(www.youtube.com|youtube.com)\\/playlist(.*)$"
        valid_playlist_url = re.search(pattern=playlist_check_pattern, string=search_or_url)

        if valid_video_url:
            video_id = get_video_id(search_or_url)
            video_url = search_or_url
            video_data = await YTDLSource.get_video_info(video_url)
            video_title = video_data[0]
            video_length = video_data[1]
            thumbnail_url = video_data[2]

        elif valid_playlist_url:
            await ctx.send("Queuing items on playlist")
            playlist_id = get_playlist_id(search_or_url)
            if playlist_id is None:
                return await ctx.send("Can't get videos from the playlist")
            playlist_videos: list = get_videos_on_playlist(url=search_or_url)
            for video in playlist_videos:
                pair = (video, voice_client, ctx)
                server_id = ctx.guild.id
                video_queue = self.video_queue_map.get(server_id)
                if video_queue is None:
                    video_queue = list()
                    self.video_queue_map[server_id] = video_queue
                video_queue.append(pair)

            await ctx.send("Queued {} items".format(playlist_videos.__len__().__str__()))

            if not voice_client.is_playing():
                self.toggle_next(server_id=ctx.guild.id, ctx=ctx)

            return

        else:
            await ctx.send("Searching for " + search_or_url)
            video_id, video_url = search_for_video(search_or_url)
            if video_id is None:
                return await ctx.send("Cannot find a video for {}".format(search_or_url))
            video_title, video_length, thumbnail_url = await YTDLSource.get_video_info(video_url)

        video = Video(video_url=video_url, video_id=video_id, thumbnail_url=thumbnail_url, video_title=video_title,
                      video_length=video_length)
        pair = (video, voice_client, ctx)
        server_id = ctx.guild.id
        video_queue = self.video_queue_map.get(server_id)
        if video_queue is None:
            video_queue = list()
            self.video_queue_map[server_id] = video_queue
        video_queue.append(pair)

        if not voice_client.is_playing():
            self.toggle_next(server_id=ctx.guild.id, ctx=ctx)
        else:
            await ctx.send('Queuing: {}'.format(video_title))
            await ctx.send(embed=discord.Embed(title=video_title, url=video_url))

    @commands.command()
    async def skip(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None:
            if voice_client.is_playing() or voice_client.is_paused():
                await ctx.send("Skipping")
                voice_client.stop()

            else:
                return await ctx.send("Not currently playing")
        else:
            return await ctx.send("You need to be in a voice channel")

    @commands.command()
    async def playfile(self, ctx, file_name: str = None):
        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        if file_name is None:
            file_list = os.listdir("/bot/assets/audio")
            file_name = random.choice(file_list)

        if not file_name.endswith(".mp3"):
            file_name = file_name + ".mp3"

        video = Video(filename=file_name)

        pair = (video, voice_client, ctx)
        server_id = ctx.guild.id
        video_queue = self.video_queue_map.get(server_id)
        if video_queue is None:
            video_queue = list()
            self.video_queue_map[server_id] = video_queue
        video_queue.append(pair)

        if not voice_client.is_playing():
            self.toggle_next(server_id=ctx.guild.id, ctx=ctx)
        else:
            await ctx.send('Queuing: {}'.format(file_name))

    @commands.command()
    async def pause(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None and voice_client.is_playing():
            voice_client.pause()
            await ctx.send("Pausing")
        else:
            await ctx.send("Nothing to pause")

    @commands.command()
    async def resume(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None and voice_client.is_paused():
            voice_client.resume()
            await ctx.send("Resuming")
        else:
            await ctx.send("Nothing to resume")

    @commands.command()
    async def queue(self, ctx):
        server_id = ctx.guild.id
        if not self.video_queue_map.keys().__contains__(server_id) or self.video_queue_map[server_id].__len__() == 0:
            return await ctx.send("Queue is empty")
        else:
            video_list = self.video_queue_map[server_id]
            counter = 0
            # instead of printing out eeach item one after the other add them to a list and print them all at the end
            # otherwise get chat rate limited byt discord
            string_to_send = ""
            too_many_item_string = None
            while counter < video_list.__len__():
                if counter >= 5:
                    too_many_item_string = ("And {} other songs".format(video_list.__len__() - 5))
                    break
                item = video_list.__getitem__(counter)
                video = item[0]
                item_counter = counter + 1
                if video.file:
                    string_to_send += ("{}. {}".format(item_counter, video.filename))
                else:
                    string_to_send += ("{}. {}".format(item_counter, video.video_title))
                counter += 1
                string_to_send += "\n"

            await ctx.send(embed=discord.Embed(title=string_to_send))
            if too_many_item_string is not None:
                await ctx.send(too_many_item_string)

    @commands.command()
    async def clear(self, ctx):
        server_id = ctx.guild.id
        del self.video_queue_map[server_id]
        await ctx.send("Bye bye queue")

    @commands.command(aliases=['np'])
    async def nowplaying(self, ctx):
        if not self.currently_playing_map.keys().__contains__(ctx.guild.id):
            return await ctx.send("Not playing anything")
        currently_playing: Video = self.currently_playing_map[ctx.guild.id]
        if currently_playing.youtube:
            await ctx.send(embed=discord.Embed(title=currently_playing.video_title,
                           url=currently_playing.video_url).set_thumbnail(url=currently_playing.thumbnail_url))
        else:
            await ctx.send("Now playing file {}".format(currently_playing.filename))

