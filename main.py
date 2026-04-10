import os
import sys
import logging
import logging.handlers
from typing import Literal
from random import randrange, sample

import discord
from discord.ext import commands
import tomllib
import asyncio

import jsman as json

# Need to get the exact file location, because all the folders
# work relative to where the script is running from,
# but using '.' is relative to cwd, and cwd is obviously affected
# by where you might be running the script from
if getattr(sys, 'frozen', False):
    froot = os.path.dirname(os.path.realpath(sys.executable))
else:
    froot = os.path.dirname(os.path.realpath(__file__))

debug_dontstartnow = True
# Setting exclusively for testing; cannot be set anywhere other than
# _SPECIFICALLY_ in the source code

if os.path.exists(f'{froot}/Config/config-OLD.toml'):
    input('config-OLD.toml file detected in the Config folder.\n' \
    'To ensure that you\'ve copied all your config settings over, ' \
    'this bot will not run while that file exists.\nIf you have not ' \
    'copied the values over, \033[1;4mDO THAT AND DELETE THE ' \
    'config-OLD FILE.\033[0m\n\nPress Enter to exit.')
    quit(0)

readme_music = "Files you place in here (including subdirectories) " \
"will be readable by the bot.\nTo play them, folder structure must " \
"be matched **exactly**."

readme_playlists = "<eof>\nHow to write a playlist file:\n" \
"Each line in the file must be a path to a local file " \
"(links are not supported yet).\nThe final line of the " \
"playlist must be <eof>, like above (which is placed so this file " \
"can't be read as a playlist).\nComments can be added with //."

readme_lyrics = "How to handle lyrics:\n" \
"Lyrics can be either .txt or .lrc files, with the text you want to " \
"show when someone runs the lyric command for the currently playing " \
"file.\nLyrics aren't supported for files playing from web links.\n" \
"Lyrics must be placed with folder structure **EXACTLY** matching " \
"where the files are in /Assets/Music. If this isn't the case, the " \
"command _will not_ find the files.\nLyrics aren't time-synced, and " \
".lrc files will have all time indicators stripped if present, while " \
".txt files will be displayed as-is."

def make_readme_files(
        loc: Literal['music', 'playlists', 'lyrics'], 
        overwrite: bool = False):
    match loc:
        case 'music':
            dest = f'{froot}/Assets/Music/readme.txt'
            content = readme_music
        case 'playlists':
            dest = f'{froot}/Assets/Playlists/readme.txt'
            content = readme_playlists
        case 'lyrics':
            dest = f'{froot}/Assets/Lyrics/readme.txt'
            content = readme_lyrics
    if os.path.exists(dest):
        if overwrite:
            os.remove(dest)
        else:
            return
    with open(dest, mode='+w', encoding='utf-8') as outputfile:
        outputfile.write(content)
    return

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

current_config_version = '0.1.5'

default_config = '''# Discord Multi-Bot Configuration
version = "0.1.5" # Version of the config file
# If this is older than what the program expects,
# it'll drop any new values into the file,
# ideally leaving settings intact

[client]
token = "null" # Should be obvious, the token the bot uses to run
bot_owner = 0 # The user ID of the bot's owner.
activity = "We call this one, an absolute vibe." # The activity listed by the bot, uses "playing" by default
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

def check_config_version() -> bool:
    """Checks if the config file's version is smaller than the one specified in this script.
    Returns False if the config file is older."""
    numbs = str(settings['version']).split('.')
    target = str(current_config_version).split('.')
    if (
        numbs[0] < target[0] or
        numbs[1] < target[1] or
        numbs[2] < target[2]
    ):
        return False
    return True

def load_toml() -> dict:
    with open(f'{froot}/Config/config.toml', 'rb') as configfile:
        settings:dict = tomllib.load(configfile)
    return settings
    # Loads to:
    # ['client']['token']: String, the bot token 
    # ['client']['bot_owner']: Integer, the ID of the bot owner.
    # ['client']['activity']: String, the activity the bot will list as 
    # playing
    # ['client']['status']: String, one of online, idle, dnd, invisible
    # ['users']['enforce_whitelist']: Boolean, whether to enforce the 
    # next list for certain commands
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

os.makedirs(f'{froot}/Assets/Music', exist_ok=True)
os.makedirs(f'{froot}/Assets/Playlists', exist_ok=True)
os.makedirs(f'{froot}/Assets/Libraries', exist_ok=True)
os.makedirs(f'{froot}/Assets/Lyrics', exist_ok=True)
os.makedirs(f'{froot}/Config/Guilds', exist_ok=True)

make_readme_files('music', False)
make_readme_files('playlists', False)
make_readme_files('lyrics', False)

if not os.path.exists(f'{froot}/Config/config.toml'):
    _ = input('Config file not detected.\nIf this is your first time ' \
    'running the program, edit the newly-made config file with the ' \
    'required information, including your bot token.\nIf you do not ' \
    'specify a bot token, the program cannot run.\n\nPress Enter to exit.')
    with open(f'{froot}/Config/config.toml', '+w') as configfile:
        configfile.write(default_config)
    quit(0)
else:
    settings:dict = load_toml()
    if not check_config_version():
        os.rename(f'{froot}/Config/config.toml', f'{froot}/Config/config-OLD.toml')
        with open(f'{froot}/Config/config.toml', '+w') as configfile:
            configfile.write(default_config)
        input('Config file has been updated.\nSince I\'m a silly fool, ' \
              'the config file can\'t update itself yet,\nso you ' \
              'will need to copy all the values over yourself.\n' \
              'The old config file can now be found at "./Config/' \
              'config-OLD.toml".\n\nHey, hey, look at me.\n' \
              'If the config-OLD file still exists, \033[1;4m' \
              'THE BOT WILL NOT RUN.\033[0m\nRemove the config-OLD ' \
              'file once you copy the values over.\n\nPress Enter ' \
              'to exit.')
        quit(0)

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)

if not os.path.exists(f'{froot}/Logs'):
    os.makedirs(f'{froot}/Logs')

handler = logging.handlers.RotatingFileHandler(
    filename=f'{froot}/Logs/discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter(
    '[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Creature(commands.Bot):
    user: discord.ClientUser

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def setup_hook(self) -> None:
        self.activity = discord.Activity(name=settings['client']['activity'],
                                          type=discord.ActivityType.playing)
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
    print('\033[96mBot is ready!\nDisplay: \033[32;4m{}\033[0;96m\n' \
          'Name: \033[32;4m{}\033[0;96m\nID: \033[32;4m{}\033[0m'
          .format(client.user.display_name,client.user.name,client.user.id))

@client.event
async def on_message(message:discord.Message):
    match message.content.lower():
        case '^sync':
            await client.tree.sync()
            try:
                if message.author.id not in settings['users']['trusted']:
                    await message.channel.send(
                        'Syncing slash commands. (You might need to ' \
                        'restart Discord.)\n-# You\'re lucky this is ' \
                        'the one thing I *don\'t* mind you doing...')
                else:
                    await message.channel.send(
                        'Syncing slash commands. (You might need to ' \
                        'restart Discord.)')
            except discord.app_commands.CommandSyncFailure as e:
                await message.channel.send(
                    'Failed to sync slash commands;\n`{}`'.format(e))
            print('Syncing slash commands. (You might need to ' \
            'restart Discord.)')
        case 'do you know who max jacobs is'|'do you know who max jacobs is?':
            await message.channel.send(
                'I\'m gonna bomb your trailer park if you ever say ' \
                'that shit in my vicinity again.',
                reference=message,mention_author=True)
        case _:
            pass


@client.tree.command(name='sync',description='Syncs slash commands with Discord.')
@is_user_trusted()
async def resync(interaction:discord.Interaction):
    try:
        await client.tree.sync()
    except discord.app_commands.CommandSyncFailure as e:
        await interaction.response.send_message(
            'Failed to sync commands.\n`{}`'.format(e), ephemeral = True)
    else:
        await interaction.response.send_message(
            'Slash commands have been synced. (You may need to restart ' \
            'Discord.)', ephemeral = True)

@client.tree.command(name='reload',description='Reloads a command group/cog.')
@discord.app_commands.describe(target='The cog to reload.')
async def reload(interaction:discord.Interaction,target: Literal['VoiceWork','MessagePurge','RoutinePurge','ForumExclusivity','MessageLogging']):
    match target:
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

if not debug_dontstartnow:
    client.run(settings['client']['token'], log_handler=None)
else:
    print('DontRunNow set; exiting.')
    quit(0)
