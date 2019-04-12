# Work with Python 3.6
import discord


TOKEN = 'NTY2MzA5OTQ3NjUxMTI5MzQ0.XLDIpA.tUPvZxsyicFsenycpmmXkeWonDI'

client = discord.Client()

COMMAND_START = "-"


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith(COMMAND_START + 'hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await client.send_message(message.channel, msg)

    if message.content.startswith(COMMAND_START + 'join'):
        voice_channel_to_join = message.author.voice_channel

        if voice_channel_to_join is None:
            msg = "no channel to join dum dum"
            await client.send_message(message.channel, msg)
        else:
            await client.join_voice_channel(voice_channel_to_join)


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run(TOKEN)
