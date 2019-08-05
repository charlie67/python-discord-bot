import logging
import sys

import discord
from discord.ext import commands
import os
import random
import youtube_dl

from utilities.timer import Timer
from voice import voice_helpers
from voice.music_player import MusicPlayer
from voice.voice_helpers import Video
from voice.ytdl_impl import YTDLSource
import time

TIMEOUT_VALUE = 3


# IDEAS
# playtop to insert at the top of the queue
# search for song
# play history
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

    __slots__ = ('bot', 'players', 'logger')

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.Logger("voice commands")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)

        self.players = {}

    async def cleanup(self, guild):

        try:
            player = self.players[guild.id]
            player.shutting_down = True
        except KeyError:
            pass

        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command(name="play")
    async def play_(self, ctx: discord.Message, *, item_to_play: str):

        await ctx.send("Searching for `{}`".format(item_to_play))

        await ctx.trigger_typing()

        player = self.get_player(ctx)

        try:
            video_list = YTDLSource.get_video(item_to_play, author_name=ctx.author.name)
        except youtube_dl.utils.YoutubeDLError as err:
            self.logger.debug("Attempted to play video {} but got exception {}".format(item_to_play, err))
            return await ctx.send("Could not play {}: {}".format(item_to_play, err))

        for video in video_list:
            await player.queue.put(video)

        video_list_length = video_list.__len__()

        if video_list_length > 1:
            return await ctx.send(embed=discord.Embed(title="Queued {} items".format(video_list_length)))

        video = video_list.__getitem__(0)

        description_string = "Queue position: {} \nSong Duration: {}".format(player.queue.qsize(),
                                                                             await time_string(video.video_length))
        queue_embed = discord.Embed(title=video.video_title,
                                    url=video.video_url,
                                    description=description_string)
        queue_embed.set_author(name="Added to queue")
        queue_embed.set_footer(text="Requested by {}".format(video.author_name))
        queue_embed.set_thumbnail(url=video.thumbnail_url)
        await ctx.send(embed=queue_embed)

    @commands.command(name="skip", aliases=['next'])
    async def skip_(self, ctx):
        guild = ctx.guild

        voice_client: discord.VoiceClient = guild.voice_client
        if voice_client is not None:
            if voice_client.is_playing() or voice_client.is_paused():
                await ctx.send("Skipping")
                voice_client.stop()

            else:
                return await ctx.send("Not currently playing")
        else:
            return await ctx.send("Need to be connected to a voice channel to do that")

    @commands.command(name="playfile")
    async def play_file_(self, ctx: discord.Message, file_name: str = None):
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

        player = self.get_player(ctx)
        await player.queue.put(video)

        await ctx.send('Queuing: {}'.format(file_name))

    @commands.command()
    async def queue(self, ctx):
        vc = ctx.voice_client
        player = self.get_player(ctx)

        if not vc or not vc.is_connected() or player.queue.empty():
            return await ctx.send("There is nothing queued")

        counter = 0
        # instead of printing out each item one after the other add them to a list and print them all at the end
        # otherwise get chat rate limited by discord
        string_to_send = ""
        too_many_item_string = ""
        for video in player.queue._queue:
            if counter >= 10:
                too_many_item_string = ("And {} other songs".format(player.queue.qsize() - 5))
                break

            item_counter = counter + 1
            if video.file:
                string_to_send += ("{}. {}".format(item_counter, video.filename))
            else:
                string_to_send += ("{}. {} | {} Requested by: {}".format(item_counter, video.video_title,
                                                                         await time_string(
                                                                             int(video.video_length)),
                                                                         video.author_name))
            string_to_send += "\n\n"
            counter += 1
        string_to_send += "\n" + too_many_item_string

        queue_embed = discord.Embed(description=string_to_send)
        queue_embed.set_author(name="Queue for {}".format(ctx.guild.name))
        queue_embed.set_footer(text="{} songs in queue".format(player.queue.qsize()))
        await ctx.send(embed=queue_embed)

    @commands.command(name='nowplaying', aliases=['np'])
    async def now_playing_(self, ctx):
        """
        Display information about the currently playing song
        :param ctx: The message that triggered this command
        """
        player = self.get_player(ctx)
        currently_playing: Video = player.current

        if not player.current:
            return await ctx.send("Not playing anything")
        if currently_playing.youtube:
            time_started = currently_playing.time_started
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

    @commands.command(name='leave', aliases=['stop', 'die'])
    async def leave_(self, ctx):
        """
        Leave the voice channel if connected and stop playing any music
        :param ctx: The message that triggered this command
        """
        voice_client = ctx.voice_client

        if not voice_client or not voice_client.is_connected():
            return await ctx.send('I am not currently in the voice channel')

        await self.cleanup(ctx.guild)

    @commands.command(name="volume")
    async def volume_(self, ctx, volume: int):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently in a voice channel!')

        if not 0 < volume < 101:
            return await ctx.send('Please enter a value between 1 and 100.')

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = volume / 100

        player.volume = volume / 100

        return await ctx.send("Set the volume to {}".format(volume))

    @commands.command(name="remove")
    async def remove_(self, ctx, item_to_remove: int):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently in a voice channel!')

        player = self.get_player(ctx)

        if player.queue.qsize() < item_to_remove:
            return await ctx.send("There aren't {} videos on the queue".format(item_to_remove))

        del player.queue._queue[item_to_remove - 1]

        return await ctx.send("Removed item {} from the queue".format(item_to_remove))

    @commands.command(name="clear", help="Clear the queue")
    async def clear_(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently in a voice channel!')

        player = self.get_player(ctx)
        player.queue._queue.clear()
        return await ctx.send("Cleared the queue")

    @play_.before_invoke
    @play_file_.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")

    async def voice_client_disconnect_check(self, guild):
        voice_client = guild.voice_client

        if voice_client.is_connected() and voice_client.channel.members.__len__() == 1:
            await self.cleanup(guild)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        voice_client: discord.voice_client = member.guild.voice_client
        if voice_client and voice_client.channel.members.__len__() == 1:
            Timer(TIMEOUT_VALUE, self.voice_client_disconnect_check, parameter=member.guild)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if before.region != after.region:
            self.logger.debug("Server region has changed")
            voice_client: discord.voice_client = after.voice_client
            if voice_client:
                player = self.players[before.id]
                await self.cleanup(before)
                await after.text_channels.__getitem__(0).send("Can you not change the server region you ADHD twat?")
