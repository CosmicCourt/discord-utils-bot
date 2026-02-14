import os
import asyncio
import discord
import logging
import logging.handlers
import tomllib
import jsman as json
from random import randrange, sample
from discord.ext import commands
from typing import Literal

meanstrings = [
    'Why don\'t you try being polite next time?',
    'Hell no.',
    'Why don\'t you try getting a job?',
    'How unapologetically silly of you. No.',
    'Get lost, friend.',
    'Nuh-uh.',
    'Absolutely not.',
    'Me- Me when- Me when your mom- Me when your mom- \\*dies by Zeus\\*',
    'I\'ve met Crawlers with more manners than you.',
    'Mmm, no.'
]

def be_mean():
    meancount = randrange(0,len(meanstrings) - 1)
    return meanstrings[meancount]

default_config = '''# Olfin Swimmer Configuration
version = "0.1.4" # Version of the config file
# If this is older than what the program expects,
# it'll drop any new values into the file,
# ideally leaving settings intact

[client]
token = "null" # Should be obvious, the token the bot uses to run
bot_owner = 0 # The user ID of the bot's owner.
activity = "Your Multi-Purpose Friend" # The activity listed by the bot, uses "playing" by default
status = "online" # One of: online, idle, dnd, invisible
shut_up = false # Whether the bot keeps most messages ephemeral or not

[users]
enforce_whitelist = true # Whether to enforce the trusted_users whitelist
trusted = [] # A list of trusted user IDs. Not usernames. IDs.

[voicework]
group_enabled = true # If the VoiceWork commands can be used.

[messagepurge]
group_enabled = true # If the MessagePurge commands can be used.

[routinepurge]
group_enabled = true # If the RoutinePurge commands can be used.

[forumexclusivity]
group_enabled = true # If the ForumExclusivity commands can be used.
ignored_roles = [] # Roles ignored by the exclusivity, you might ideally want moderators and bots in this list.
ignored_forums = [] # Forum channels ignored by the exclusivity.

[messagelogging]
group_enabled = true # If the MessageLogging commands can be used; disables logging if false.
logging_destination_server = 0 # The ID of the guild where message logs are proxied to.
logging_destination_channel = 0 # The ID of the channel where message logs are proxied to.
ignored_roles = [] # Roles ignored by the logging.
ignored_channels = [] # Channels ignored by the logging.
'''
# YEAH, CAN'T WRITE TOML, HUH!? THEN I'LL DO IT MYSELF!

def load_toml() -> dict:
    with open('./Config/config.toml', 'rb') as configfile:
        settings:dict = tomllib.load(configfile)
    return settings
    # Loads to:
    # ['client']['token']: String, the bot token (there's a reason we don't ship the config file :P)
    # ['client']['bot_owner']: Integer, the ID of the bot owner.
    # ['client']['activity']: String, the activity the bot will list as playing
    # ['client']['status']: String, one of online, idle, dnd, invisible
    # ['users']['enforce_whitelist']: Boolean, whether to enforce the next list for certain commands
    # ['users']['trusted']: List, user IDs in the whitelist
    # ['voicework']['group_enabled']
    # ['messagepurge']['group_enabled']
    # ['routinepurge']['group_enabled']
    # ['forumexclusivity']['group_enabled']
    # ['forumexclusivity']['ignored_roles']
    # ['forumexclusivity']['ignored_forums']
    # ['messagelogging']['group_enabled']
    # ['messagelogging']['logging_destination_server']
    # ['messagelogging']['logging_destination_channel']
    # ['messagelogging']['ignored_roles']
    # ['messagelogging']['ignored_channels']

if not os.path.exists('./Config/config.toml'):
    _ = input('Config file not detected.\nIf this is your first time running the program, edit the newly-made config file with the required information, including your bot token.\nIf you do not specify a bot token, the program cannot run.\n\nPress Enter to exit.')
    with open('./Config/config.toml', '+w') as configfile:
        configfile.write(default_config)
    quit(0)
else:
    settings:dict = load_toml()

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)

if not os.path.exists('./Logs'):
    os.makedirs('./Logs')

handler = logging.handlers.RotatingFileHandler(
    filename='./Logs/discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Creature(commands.Bot):
    user: discord.ClientUser # pyright: ignore[reportIncompatibleMethodOverride] ## Pipe down.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def setup_hook(self) -> None:
        self.activity = discord.Activity(name=settings['client']['activity'], type=discord.ActivityType.playing)
        self.status = getattr(discord.Status, settings['client']['status'])
        if settings['voicework']['group_enabled']:
            await self.load_extension('cogs.voicework')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = Creature(command_prefix='^', intents=intents)

slash = discord.app_commands

def is_user_trusted():
    async def predicate(interaction:discord.Interaction) -> bool:
        return interaction.user.id in settings['users']['trusted']
    return discord.app_commands.check(predicate)

@client.event
async def on_ready():
    print('Bot is ready!\nDisplay: {}\nName: {}\nID: {}'.format(client.user.display_name,client.user.name,client.user.id))

@client.event
async def on_message(message:discord.Message):
    match message.content.lower():
        case '^sync':
            await client.tree.sync()
            if message.author.id not in settings['users']['trusted']:
                await message.channel.send('Syncing slash commands. (You might need to restart Discord.)\n-# You\'re lucky this is the one thing I *don\'t* mind you doing...')
            else:
                await message.channel.send('Syncing slash commands. (You might need to restart Discord.)')
            print('Syncing slash commands. (You might need to restart Discord.)')
        case 'do you know who max jacobs is'|'do you know who max jacobs is?':
            await message.channel.send('I\'m gonna bomb your trailer park if you ever say that shit in my vicinity again.',reference=message,mention_author=True)
        case _:
            pass


@client.tree.command(name='sync',description='Syncs slash commands with Discord.')
@is_user_trusted()
async def resync(interaction:discord.Interaction):
    await client.tree.sync()
    await interaction.response.send_message('Slash commands have been synced. (You may need to restart Discord.)', ephemeral=True)

@client.tree.command(name='reload',description='Reloads a command group/cog.')
@discord.app_commands.describe(target='The cog to reload.')
async def reload(interaction:discord.Interaction,target: Literal['Configuration','VoiceWork','MessagePurge','RoutinePurge','ForumExclusivity','MessageLogging']):
    match target:
        case 'Configuration':
            await client.reload_extension('cogs.configtree')
            await interaction.response.send_message('Configuration has been reloaded.')
        case 'VoiceWork':
            await client.reload_extension('cogs.voicework')
            await interaction.response.send_message('VoiceWork has been reloaded.')
        case 'MessagePurge':
            await interaction.response.send_message('Not implemented yet.',ephemeral=True)
        case 'RoutinePurge':
            await interaction.response.send_message('Not implemented yet.',ephemeral=True)
        case 'ForumExclusivity':
            await interaction.response.send_message('Not implemented yet.',ephemeral=True)
        case 'MessageLogging':
            await interaction.response.send_message('Not implemented yet.',ephemeral=True)

@client.tree.command(name='shutdown',description='Closes the bot\'s connection to Discord.')
async def shutdown(interaction:discord.Interaction):
    if interaction.user.id not in settings['users']['trusted']:
        await interaction.response.send_message(be_mean())
        return
    await interaction.response.send_message('Shutting down...')
    await client.close()

# voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)

client.run(settings['client']['token'], log_handler=None)
