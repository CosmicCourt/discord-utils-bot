import os
import sys
import re
from typing import Literal
from random import randrange, sample, shuffle

import discord
import tomllib
import aiohttp
import asyncio
from discord.ext import commands

import jsman as json
from common import ANSIStyles as style
if os.getenv('$COLORTERM') == 'truecolor':
    from common import fg_color, bg_color

if getattr(sys, 'frozen', False):
    froot = os.path.dirname(os.path.realpath(sys.executable))
else:
    froot = os.path.dirname(os.path.realpath(__file__)) + '/..'

def load_toml() -> dict:
    with open('{}/Config/config.toml'.format(froot), 'rb') as configfile:
        settings:dict = tomllib.load(configfile)
    return settings
    # Loads to:
    # ['client']['token']: String, the bot token (there's a reason we 
    # don't ship the config file :P)
    # ['client']['activity']: String, the activity the bot will 
    # list as playing
    # ['client']['status']: String, one of online, idle, dnd, invisible
    # ['users']['enforce_whitelist']: Boolean, whether to enforce the
    # next list for certain commands
    # ['users']['trusted']: List, user IDs in the whitelist
    # ['voicework']['group_enabled']
    # ['messagemirror']['group_enabled']

settings = load_toml()

eph = settings['client']['shut_up']

class MessageMirror(commands.Cog, name="MessageMirror"):
    def __init__(self, client) -> None:
        self.client:discord.Client = client

    memsg = discord.app_commands.Group(name="mirror", description="Main group of message mirroring.")

    @memsg.command(name="message", description="Sends a message in the current channel.")
    async def send_message(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message("Message mirrored (you can safely ignore this message.)", ephemeral=True)
        await interaction.channel.send(message)
        print("MessageMirror reflecting: {}{}{}".format(style.ff_disc, message, style.reset))



async def setup(client:commands.Bot):
    await client.add_cog(MessageMirror(client))
    print('{}MessageMirror loaded.{}'.format(style.ff_text,style.reset))

async def teardown(client:commands.Bot):
    print('{}MessageMirror unloaded.{}'.format(style.ff_text,style.reset))