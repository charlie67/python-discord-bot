# Work with Python 3.6
import discord
from discord.ext import commands

COMMAND_START = '-'
bot = commands.Bot(command_prefix=COMMAND_START)
bot.command()


@bot.event
async def on_message(message):
    author: discord.User = message.author
    if author != bot.user:
        await bot.process_commands(message)


@bot.command()
async def hello(ctx):
    author = ctx.author
    await ctx.send("Hey there " + author.name)


@bot.command(aliases=['summon'])
async def join(ctx):
    guild = ctx.guild
    author: discord.Member = ctx.author
    if author.voice is not None:
        return await discord.utils.get(guild.voice_channels, name=author.voice.channel.name).connect()
    else:
        await ctx.send(author.mention + " you need to be in a voice channel first...")


@bot.command()
async def leave(ctx):
    guild: discord.Guild = ctx.guild
    voice_client: discord.VoiceClient = guild.voice_client
    if voice_client is not None:
        await voice_client.disconnect()
    else:
        await ctx.send("I'm not connected to a voice channel")


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

if __name__ == '__main__':
    import config
    bot.run(config.token)
