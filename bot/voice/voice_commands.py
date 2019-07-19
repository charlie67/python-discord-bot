import asyncio
import logging
import sys

import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import os
import random
import youtube_dl
from voice import voice_helpers
from voice.ytdl_impl import YTDLSource
import time
from voice.video_queue import VideoQueue, VideoQueueItem

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
# search for song
# remove from queue
# queue shows autoplay song
# play history
# set volume
# turn off autoplay
# view all of the queue using emoji reactions

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


async def get_time_for_now_playing(video_length, time_started):
    time_now = time.time()
    time_elapsed = int(time_now - time_started)
    time_elapsed_string = await time_string(time_elapsed)
    time_remaining_string = await time_string(video_length)
    return "{} / {}".format(time_elapsed_string, time_remaining_string)


async def time_string(time_int: int):
    minutes = int(time_int / 60)
    hours = int(minutes / 60)
    if hours == 0:
        return await minute_second_string(time_int)
    else:
        return str(hours).zfill(2) + ":" + await minute_second_string(time_int)


async def minute_second_string(time_int):
    return str(int(time_int / 60) % 60).zfill(2) + ":" + str(int(time_int % 60)).zfill(2)


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

    @commands.command(aliases=['summon'], help="Join the voice channel you are currently in")
    async def join(self, ctx):
        await get_or_create_audio_source(ctx)

    @commands.command(aliases=['stop'], help="Leave the current voice channel")
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
        video_queue: VideoQueue = self.video_queue_map.get(server_id)

        if video_queue.is_next_song_file():
            current = video_queue.video_queue_list.__getitem__(0)
            video_queue.video_queue_list.__delitem__(0)
        else:
            current = video_queue.get_and_remove_first_item()

        video: voice_helpers.Video = current.video
        voice_client: discord.voice_client = current.voice_client
        ctx = current.message_context
        self.logger.debug("audio player - got from queue")

        if not voice_client.is_connected():
            return

        if video.file:
            audio_source = FFmpegPCMAudio("/bot/assets/audio/" + video.filename,
                                          executable=FFMPEG_PATH)
            await ctx.send('{}: {}'.format(video.play_type.value, video.filename))
            voice_client.play(audio_source, after=lambda e: self.toggle_next(server_id=server_id, ctx=ctx, error=e))
            return

        player = await YTDLSource.from_url(video.video_url, loop=self.bot.loop, stream=True)
        logging.debug("audio player - player created")

        self.currently_playing_map[ctx.guild.id] = video
        logging.debug("audio player - currently playing updated")
        player.data['timestarted'] = time.time()
        logging.debug("audio player - set time started")
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

        video_queue: VideoQueue = self.video_queue_map.get(server_id)
        if video_queue.video_queue_list.__len__() == 0:
            self.logger.debug("Video queue is empty so getting a video to autoplay from the previous video")
            if last_playing_video is not None and last_playing_video.youtube:
                video_id, video_url = voice_helpers.get_youtube_autoplay_video(last_playing_video.video_id)

                if video_id is None:
                    logging.error("Attempted to autoplay a video but couldn't find anything to play")
                    return
                video_data = YTDLSource.get_video_info(video_url)
                video_title = video_data[0]
                video_length = video_data[1]
                thumbnail_url = video_data[2]

                video = voice_helpers.Video(author_name="Autoplay", video_url=video_url, video_id=video_id,
                                            thumbnail_url=thumbnail_url, video_title=video_title,
                                            video_length=video_length,
                                            autoplay=True)

                video_queue_item_to_add = VideoQueueItem(video=video, voice_client=ctx.guild.voice_client,
                                                         message_context=ctx)
                server_id = ctx.guild.id
                video_queue.add_to_queue(video_queue_item_to_add)

        asyncio.run_coroutine_threadsafe(self.audio_player_task(server_id=server_id), self.bot.loop)

    @commands.command()
    async def play(self, ctx: discord.Message, *, item_to_play: str):
        server_id = ctx.guild.id

        video_queue = self.video_queue_map.get(server_id)
        if video_queue is None:
            video_queue = VideoQueue()
            self.video_queue_map[server_id] = video_queue

        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        await ctx.send("Searching for {}".format(item_to_play))

        video_list = YTDLSource.get_video(item_to_play, author_name=ctx.author.name)

        for video in video_list:
            video_queue_item_to_add = VideoQueueItem(video=video, voice_client=voice_client, message_context=ctx)
            video_queue.add_to_queue(video_queue_item_to_add)

        video_list_length = video_list.__len__()

        if video_list_length > 1:
            await ctx.send(embed=discord.Embed(title="Queued {} items".format(video_list_length)))

        video = video_list.__getitem__(0)

        if not voice_client.is_playing():
            description_string = "Song Duration: {}".format(await time_string(video.video_length))
            now_playing_embed = discord.Embed(title=video.video_title,
                                              url=video.video_url,
                                              description=description_string)
            now_playing_embed.set_author(name="Now playing")
            now_playing_embed.set_footer(text="Requested by {}".format(video.author_name))
            now_playing_embed.set_thumbnail(url=video.thumbnail_url)
            await ctx.send(embed=now_playing_embed)
            self.toggle_next(server_id=ctx.guild.id, ctx=ctx)
        else:
            description_string = "Queue position: {} \nSong Duration: {}".format(video_queue.length(),
                                                                                 await time_string(
                                                                                     video.video_length))
            queue_embed = discord.Embed(title=video.video_title,
                                        url=video.video_url,
                                        description=description_string)
            queue_embed.set_author(name="Added to queue")
            queue_embed.set_footer(text="Requested by {}".format(video.author_name))
            queue_embed.set_thumbnail(url=video.thumbnail_url)
            await ctx.send(embed=queue_embed)

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
    async def playfile(self, ctx: discord.Message, file_name: str = None):
        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        file_list = os.listdir("/bot/assets/audio")

        if file_name is None:
            file_name = random.choice(file_list)

        if not file_name.endswith(".mp3"):
            file_name = file_name + ".mp3"

        if not file_list.__contains__(file_name):
            return await ctx.send("File {} was not found".format(file_name))
        video = voice_helpers.Video(author_name=ctx.author.name, filename=file_name, video_length="0")

        video_queue_item_to_add = VideoQueueItem(video=video, voice_client=voice_client, message_context=ctx)
        server_id = ctx.guild.id
        video_queue: VideoQueue = self.video_queue_map.get(server_id)
        if video_queue is None:
            video_queue = VideoQueue()
            self.video_queue_map[server_id] = video_queue
        video_queue.add_to_queue(video_queue_item_to_add)

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
        if not self.video_queue_map.keys().__contains__(server_id) or self.video_queue_map[server_id].length() == 0:
            return await ctx.send("Queue is empty")
        else:
            video_queue: VideoQueue = self.video_queue_map[server_id]
            video_list = video_queue.video_queue_list
            counter = 0
            # instead of printing out each item one after the other add them to a list and print them all at the end
            # otherwise get chat rate limited byt discord
            string_to_send = ""
            too_many_item_string = None
            while counter < video_list.__len__():
                if counter >= 5:
                    too_many_item_string = ("And {} other songs".format(video_list.__len__() - 5))
                    break
                item: VideoQueueItem = video_list.__getitem__(counter)
                video = item.video
                item_counter = counter + 1
                if video.file:
                    string_to_send += ("{}. {}".format(item_counter, video.filename))
                else:
                    string_to_send += ("{}. {} | {} Requested by: {}".format(item_counter, video.video_title,
                                                                             await time_string(
                                                                                 int(video.video_length)),
                                                                             video.author_name))
                string_to_send += "\n"
                counter += 1

            queue_embed = discord.Embed(description=string_to_send)
            queue_embed.set_author(name="Queue for {}".format(ctx.guild.name))
            queue_embed.set_footer(
                text="{} songs in queue | {} total length".format(video_queue.length(), await time_string(
                    video_queue.total_play_time)))
            await ctx.send(embed=queue_embed)
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
        currently_playing: voice_helpers.Video = self.currently_playing_map[ctx.guild.id]
        if currently_playing.youtube:
            voice_client: YTDLSource = ctx.guild.voice_client.source
            time_started = voice_client.data['timestarted']
            video_length = int(currently_playing.video_length)
            description_string = "{}".format(await get_time_for_now_playing(video_length, time_started))
            footer_string = "Queued by {}".format(currently_playing.author_name)
            embed = discord.Embed(title=currently_playing.video_title,
                                  url=currently_playing.video_url,
                                  description=description_string)
            embed.set_thumbnail(url=currently_playing.thumbnail_url)
            embed.set_author(name="Now playing")
            embed.set_footer(text=footer_string)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Now playing file {}".format(currently_playing.filename))
