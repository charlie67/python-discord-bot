import os
import io
import logging
import sys
import random

import discord
import wget
from discord.ext import commands
from discord import File

IMAGE_DIR = "/bot/assets/images/"


def setup(bot):
    bot.add_cog(Image(bot))


class Image(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(handler)

    @commands.command()
    async def image(self, ctx: discord.message, image_name: str = None):

        file_list = os.listdir(IMAGE_DIR)

        if image_name is None:
            image_name = random.choice(file_list)

        if not image_name.endswith(".jpg"):
            image_name = image_name + ".jpg"

        if not file_list.__contains__(image_name):
            return await ctx.send(embed=discord.Embed(title="Image {} was not found".format(image_name)))

        image_name = IMAGE_DIR + image_name

        file = io.FileIO(image_name)
        image_file = File(file)

        await ctx.channel.send(file=image_file)

    @commands.command(aliases=["di", "download-image"])
    async def download_image(self, ctx, url: str, image_name: str):
        wget.download(url, IMAGE_DIR + image_name + ".jpg", )
        return await ctx.send(embed=discord.Embed(title="{} downloaded".format(image_name)))
