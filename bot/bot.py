import sys

import discord
import logging
from discord.ext import commands
from utilities.timer import Timer
from voice import voice_commands

TIMEOUT_VALUE = 10

COMMAND_START = '-'

bot = commands.Bot(command_prefix=COMMAND_START)
bot.command()


@bot.command(help="Hi josh")
async def hello(ctx):
    author = ctx.author
    await ctx.send("Hey there " + author.name)


@bot.command(aliases=['byedriver'])
async def bye(ctx):
    await ctx.send("https://www.youtube.com/watch?v=qpmFnUTkpL0")


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.event
async def on_message(message):
    author: discord.User = message.author
    if author != bot.user:
        await bot.process_commands(message)


if __name__ == '__main__':
    import config

    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    bot.load_extension("voice.voice_commands")
    bot.load_extension("image.image_commands")
    bot.run(config.token)
