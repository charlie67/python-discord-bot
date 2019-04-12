# Work with Python 3.6
import discord
from discord.ext import commands


COMMAND_START = '-'
bot = commands.Bot(command_prefix=COMMAND_START)
bot.command()

TOKEN = 'NTY2MzA5OTQ3NjUxMTI5MzQ0.XLDIpA.tUPvZxsyicFsenycpmmXkeWonDI'


@bot.event
async def on_message(message):
    author: discord.User = message.author
    if author != bot.user:
        await bot.process_commands(message)

# @client.event
# async def on_message(message):
#     # we do not want the bot to reply to itself
#     if message.author == client.user:
#         return
#
#     if message.content.startswith(COMMAND_START + 'hello'):
#         msg = 'Hello {0.author.mention}'.format(message)
#         await client.send_message(message.channel, msg)
#
#     if message.content.startswith(COMMAND_START + 'join'):
#         voice_channel_to_join = message.author.voice_channel
#
#         if voice_channel_to_join is None:
#             msg = "no channel to join dum dum"
#             await client.send_message(message.channel, msg)
#         else:
#             await client.join_voice_channel(voice_channel_to_join)


@bot.command()
async def hello(ctx):
    await ctx.send("Hey there")


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

bot.run(TOKEN)
