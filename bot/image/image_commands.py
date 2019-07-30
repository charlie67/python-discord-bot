import json
import os
import io
import logging
import sys
import random

import aiohttp
import discord
import praw

from discord.ext import commands
from discord import File
from google_images_download import google_images_download

import config

IMAGE_DIR = "/bot/assets/images/"


def setup(bot):
    bot.add_cog(Image(bot))


class Image(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.Logger("image commands")
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
            return await ctx.send("Image `{}` was not found".format(image_name))

        image_name = IMAGE_DIR + image_name

        file = io.FileIO(image_name)
        image_file = File(file)

        await ctx.channel.send(file=image_file)

    @commands.command(name="imagesearch")
    async def image_search_(self, ctx, *, search_term: str):
        """
        Searches Google images for search_term, picks a random result and send the image to discord
        :param ctx: The message that triggered this command
        :param search_term: The string to search for on google images
        """
        await ctx.trigger_typing()

        response = google_images_download.googleimagesdownload()
        arguments = {"keywords": search_term, "limit": 50, "no_download": True, "silent_mode": True}
        images = response.download(arguments)
        image_number = random.randint(0, 49)
        try:
            image_url = images[0][search_term][image_number]
        except IndexError as e:
            return await ctx.send("Unable to find an image for `{}`".format(search_term))

        image_embed = discord.Embed()
        image_embed.set_image(url=image_url)
        await ctx.send(embed=image_embed)

    @commands.command(name="redditsearch", help="Find a random image from the provided subreddit")
    async def reddit_search_(self, ctx, *, subreddit):
        """
        Find a random image for a subreddit that is provided as the argument subreddit
        :param ctx: The message that triggered this command
        :param subreddit: The subreddit to find an image for
        """
        await ctx.trigger_typing()

        r_search = praw.Reddit(user_agent="hi reddit", client_id=config.REDDIT_CLIENT_ID,
                               client_secret=config.REDDIT_CLIENT_SECRET)
        sub = r_search.subreddit(subreddit)
        posts = sub.hot(limit=50)
        posts.next()
        image_number = random.randint(0, 49)
        post_to_return = posts._listing.children[image_number]
        image_url = post_to_return.url

        return await ctx.send(image_url)

    @commands.command(name="gif", aliases=['gifsearch'])
    async def gif_(self, ctx, *, search_term):
        await ctx.trigger_typing()

        url = "https://api.gfycat.com/v1/gfycats/search?search_text={}&count=51".format(search_term)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.text()
            json_data = json.loads(data)

            gifs = json_data['gfycats']
            image_number = random.randint(0, gifs.__len__() - 1)
            try:
                gif_url = gifs[image_number]['gifUrl']
            except IndexError:
                return await ctx.send("Could not find a gif for {}".format(search_term))

            gif_embed = discord.Embed()
            gif_embed.set_image(url=gif_url)
            return await ctx.send(embed=gif_embed)
