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
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
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
    video_queue = asyncio.Queue()
    play_history = asyncio.Queue(10)
    play_next_song = asyncio.Event()
    currently_playing = None

    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.audio_player_task())

    @commands.command(aliases=['summon'])
    async def join(self, ctx):
        await get_or_create_audio_source(ctx)

    @commands.command()
    async def leave(self, ctx):
        guild: discord.Guild = ctx.guild
        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None:
            await voice_client.disconnect()
        else:
            await ctx.send("... What are you actually expecting me to do??")

    async def audio_player_task(self):
        while True:
            # if it's not currently playing and there is something to play
            if self.currently_playing is None and self.video_queue.qsize() > 0:
                print("song player task", self.currently_playing, self.video_queue.qsize())
                self.play_next_song.clear()
                current = await self.video_queue.get()
                video = current[0]
                print("took ", video, " off the queue")
                player = current[1]
                voice_client = current[2]
                self.currently_playing = video
                voice_client.play(player, after=self.toggle_next)
                await self.play_next_song.wait()
            else:
                print("playing so skipping audio player task")
                await self.play_next_song.wait()

    def toggle_next(self, error):
        if error is not None:
            print("player error", error)
            return
        self.currently_playing = None

        if self.video_queue.qsize() > 0:
            self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

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
        pair = (video, player, voice_client)
        print("putting ", video, " onto the queue ", pair)
        await self.video_queue.put(pair)

        if not voice_client.is_playing():
            self.bot.loop.call_soon_threadsafe(self.play_next_song.set)
            await ctx.send('Now playing: {}'.format(video_title))
            await ctx.send(embed=discord.Embed(title=video_title, url=video_url))
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
                self.currently_playing = None

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
                self.currently_playing = None
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
        if self.video_queue.qsize() == 0:
            await ctx.send("Queue is empty")
        else:
            await ctx.send("There are items in the queue")
            # go over the queue and print every item

    @commands.command(aliases=['np'])
    async def nowplaying(self, ctx):
        if self.currently_playing is None:
            return await ctx.send("Not playing anything")
        await ctx.send('Now playing: {}'.format(self.currently_playing.video_title))
        await ctx.send(embed=discord.Embed(title=self.currently_playing.video_title, url=self.currently_playing.video_url))

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
