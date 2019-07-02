import sys

import discord
from discord.ext import commands
import logging

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


@bot.command()
async def doyouwin(ctx):
    await ctx.send("of course I do" + "\n" + "bitch")


@bot.command(aliases=['byedriver'])
async def bye(ctx):
    await ctx.send("https://www.youtube.com/watch?v=qpmFnUTkpL0")


@bot.command(aliases=['mike'])
async def willy(ctx):
    await ctx.send(file=discord.File('/bot/assets/images/willy.jpg'))


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.event
async def on_guild_update(before: discord.Guild, after: discord.Guild):
    if before.region != after.region:
        logger.debug("Server region has changed")
        voice_client: discord.voice_client = after.voice_client
        if voice_client:
            await voice_client.disconnect(force=True)
            await after.text_channels.__getitem__(0).send("Can you not change the server region you ADHD twat?")

if __name__ == '__main__':
    import config

    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    bot.load_extension("voice.voice_commands")
    bot.run(config.token)
