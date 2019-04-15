import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import re
import os
import random
import youtube_dl
from bot.voice.voice_helpers import get_video_id, get_youtube_title
from bot.voice.YTDLSource import  YTDLSource

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
        else:
            await ctx.send("I'm not connected to an audio channel")

    @commands.command()
    async def play(self, ctx, url: str = None):
        if url is None:
            await ctx.send("Need to provide the URL to play")
            return

        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        def after_play(error):
            if error is not None:
                print("player error", error)

        pattern = "^(?:https?:\\/\\/)?(?:www\\.)?(?:youtu\\.be\\/|youtube\\.com\\/(?:embed\\/|v\\/|watch\\?v=" \
                  "|watch\\?.+&v=))((\\w|-){11})?$"
        valid_url = re.search(pattern, url)

        if not valid_url:
            await ctx.send("Can't play that")
        else:
            video_id = get_video_id(url)
            video_title = get_youtube_title(video_id)
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            voice_client.play(player, after=after_play)
            await ctx.send('Now playing: {}'.format(video_title))

    @commands.command()
    async def playfile(self, ctx, file_name: str = None):
        voice_client = await get_or_create_audio_source(ctx)
        if voice_client is None:
            return

        if voice_client.is_playing():
            await ctx.send("I'm already playing be patient will you")
            # todo queuing system
            return

        if file_name is None:
            file_list = os.listdir("/home/charlie/Desktop/discord-bot/assets/audio")
            file_name = random.choice(file_list)

        if not file_name.endswith(".mp3"):
            file_name = file_name + ".mp3"

        audio_source = FFmpegPCMAudio("/home/charlie/Desktop/discord-bot/assets/audio/" + file_name,
                                      executable=FFMPEG_PATH)
        voice_client.play(audio_source)

    @commands.command(aliases=['stopplaying'])
    async def stop(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None:
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
        else:
            ctx.send("Nothing to stop")

    @commands.command()
    async def pause(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None and voice_client.is_playing():
            voice_client.pause()
        else:
            ctx.send("Nothing to pause")

    @commands.command()
    async def resume(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None and voice_client.is_paused():
            voice_client.resume()
        else:
            ctx.send("Nothing to resume")
