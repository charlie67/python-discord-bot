import asyncio

import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import re
import os
import random
import youtube_dl
from voice.voice_helpers import get_video_id, get_youtube_details, search_for_video
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

    @commands.command(aliases=['summon'])
    async def join(self, ctx):
        await get_or_create_audio_source(ctx)

    @commands.command()
    async def leave(self, ctx):
        guild: discord.Guild = ctx.guild
        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None:
            await voice_client.disconnect()
            del self.currently_playing_map[ctx.guild.id]
            del self.video_queue_map[ctx.guild.id]
        else:
            await ctx.send("... What are you actually expecting me to do??")

    async def audio_player_task(self, server_id):
        video_queue = self.video_queue_map.get(server_id)
        current = video_queue.__getitem__(0)
        video_queue.__delitem__(0)
        video = current[0]
        print("took ", video, " off the queue")
        player = current[1]
        voice_client = current[2]
        ctx = current[3]
        await ctx.send('Now playing: {}'.format(video.video_title))
        await ctx.send(embed=discord.Embed(title=video.video_title, url=video.video_url))
        self.currently_playing_map[ctx.guild.id] = video
        voice_client.play(player, after=lambda: self.toggle_next(server_id=ctx.guild.id))

    def toggle_next(self, server_id):
        if self.currently_playing_map.keys().__contains__(server_id):
            del self.currently_playing_map[server_id]
        print("toggling next for", server_id)

        video_queue = self.video_queue_map.get(server_id)
        if video_queue.__len__() > 0:
            asyncio.run_coroutine_threadsafe(self.audio_player_task(server_id=server_id), self.bot.loop)

    @commands.command()
    async def play(self, ctx, *, video_or_search):
        if video_or_search is None:
            await ctx.send("Need to provide something to play")
            return

        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        pattern = "^(?:https?:\\/\\/)?(?:www\\.)?(?:youtu\\.be\\/|youtube\\.com\\/(?:embed\\/|v\\/|watch\\?v=" \
                  "|watch\\?.+&v=))((\\w|-){11})?$"
        valid_url = re.search(pattern, video_or_search)

        if not valid_url:
            await ctx.send("Searching for " + video_or_search)
            video_id, video_url, = search_for_video(video_or_search)
            video_title, video_length = get_youtube_details(video_id)
        else:
            video_id = get_video_id(video_or_search)
            video_title, video_length = get_youtube_details(video_id)
            video_url = video_or_search

        video = Video(video_url=video_url, video_id=video_id, thumbnail_url=None, video_title=video_title,
                      video_length=video_length)
        player = await YTDLSource.from_url(video_url, loop=self.bot.loop, stream=True)
        pair = (video, player, voice_client, ctx)
        print("putting ", video, " onto the queue ", pair)
        server_id = ctx.guild.id
        video_queue = self.video_queue_map.get(server_id)
        if video_queue is None:
            video_queue = list()
            self.video_queue_map[server_id] = video_queue
        video_queue.append(pair)

        if not voice_client.is_playing():
            self.toggle_next(server_id=ctx.guild.id)
        else:
            await ctx.send('Queuing: {}'.format(video_title))
            await ctx.send(embed=discord.Embed(title=video_title, url=video_url))

    @commands.command()
    async def skip(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None:
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
                self.toggle_next(server_id=guild.id)

                await ctx.send("Skipping")
            else:
                return await ctx.send("Not currently playing")
        else:
            return await ctx.send("You need to be in a voice channel")

    @commands.command()
    async def playfile(self, ctx, file_name: str = None):
        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        if voice_client.is_playing():
            await ctx.send("I'm already playing be patient will you")
            return

        if file_name is None:
            file_list = os.listdir("/bot/assets/audio")
            file_name = random.choice(file_list)

        if not file_name.endswith(".mp3"):
            file_name = file_name + ".mp3"

        audio_source = FFmpegPCMAudio("/bot/assets/audio/" + file_name,
                                      executable=FFMPEG_PATH)
        voice_client.play(audio_source)

    @commands.command(aliases=['stopplaying'])
    async def stop(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None:
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
                del self.currently_playing_map[ctx.server.id]
                await ctx.send("Stopping")
        else:
            await ctx.send("Nothing to stop")

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
        if not self.video_queue_map.keys().__contains__(server_id):
            return await ctx.send("Queue is empty")
        else:
            video_list = self.video_queue_map[server_id]
            counter = 0
            while counter < video_list.__len__():
                item = video_list.__getitem__(counter)
                video = item[0]
                item_counter = counter + 1
                await ctx.send(item_counter.__str__() + ". " + video.video_title)
                counter += 1

    @commands.command(aliases=['np'])
    async def nowplaying(self, ctx):
        if not self.currently_playing_map.keys().__contains__(ctx.guild.id):
            return await ctx.send("Not playing anything")
        currently_playing = self.currently_playing_map[ctx.guild.id]
        await ctx.send('Now playing: {}'.format(currently_playing.video_title))
        await ctx.send(
            embed=discord.Embed(title=currently_playing.video_title, url=currently_playing.video_url))

    @commands.command()
    async def dishwasher(self, ctx):
        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        if voice_client.is_playing():
            await ctx.send("I'm already playing be patient will you")
            return

        audio_source = FFmpegPCMAudio("/bot/assets/audio/dishwasher.mp3",
                                      executable=FFMPEG_PATH)
        voice_client.play(audio_source)


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
