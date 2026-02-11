import os
import asyncio
import discord
import logging
import logging.handlers
import tomllib
from discord.ext import commands

if os.name == 'nt':
    libopus = './Assets/Libraries/libopus/libopus.dll'
    ffmpeg = './Assets/Libraries/ffmpeg/ffmpeg.exe'
else:
    libopus = './Assets/Libraries/libopus/libopus.so'
    ffmpeg = './Assets/Libraries/ffmpeg/ffmpeg'

discord.opus.load_opus(libopus)

default_config = '''# Olfin Swimmer Configuration
version = "0.1.1" # Version of the config file
# If this is older than what the program expects,
# it'll drop any new values into the file,
# ideally leaving settings intact

[client]
token = "null" # Should be obvious, the token the bot uses to run
activity = "Your Multi-Purpose Friend" # The activity listed by the bot, uses "playing" by default
status = "online" # One of: online, idle, dnd, invisible

[users]
enforce_whitelist = true # Whether to enforce the trusted_users whitelist
trusted = [] # A list of trusted user IDs. Not usernames. IDs.
'''
# YEAH, CAN'T WRITE TOML, HUH!? THEN I'LL DO IT MYSELF!

def load_toml() -> dict:
    with open('./config.toml', 'rb') as configfile:
        settings:dict = tomllib.load(configfile)
    return settings
    # Loads to:
    # ['client']['token']: String, the bot token (there's a reason we don't ship the config file :P)
    # ['client']['activity']: String, the activity the bot will list as playing
    # ['client']['status']: String, one of online, idle, dnd, invisible
    # ['users']['enforce_whitelist']: Boolean, whether to enforce the next list for certain commands
    # ['users']['trusted']: List, user IDs in the whitelist

if not os.path.exists('./config.toml'):
    _ = input('Config file not detected.\nIf this is your first time running the program, edit the newly-made config file with the required information, including your bot token.\nIf you do not specify a bot token, the program cannot run.\n\nPress Enter to exit.')
    with open('./config.toml', '+w') as configfile:
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

class Creature(discord.Client):
    user: discord.ClientUser

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def setup_hook(self) -> None:
        self.activity = discord.Activity(name=settings['client']['activity'], type=discord.ActivityType.playing)
        self.status = getattr(discord.Status, settings['client']['status'])

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = Creature(intents=intents)
tree = discord.app_commands.CommandTree(client)

slash = discord.app_commands

@client.event
async def on_ready():
    print('Bot is ready!\nDisplay: {}\nName: {}\nID: {}'.format(client.user.display_name,client.user.name,client.user.id))

@client.event
async def on_message(message:discord.Message):
    if message.content.lower() == '^sync':
        await tree.sync()
        if message.author.id not in settings['users']['trusted']:
            await message.channel.send('Syncing slash commands. (You might need to restart Discord.)\n-# You\'re lucky this is the one thing I *don\'t* mind you doing...')
        else:
            await message.channel.send('Syncing slash commands. (You might need to restart Discord.)')
        print('Syncing slash commands. (You might need to restart Discord.)')

@tree.command(name='shutdown',description='Closes the bot\'s connection to Discord.')
async def shutdown(interaction:discord.Interaction):
    if interaction.user.id not in settings['users']['trusted']:
        await interaction.response.send_message("Mmm, no.")
        return
    await interaction.response.send_message('Shutting down...',ephemeral=True)
    #if client.voice_clients
    await client.close()

@tree.command(name='connect',description='Connects the bot to your current voice channel.')
async def voice_connect(interaction:discord.Interaction):
    if interaction.user.voice is None:
        await interaction.response.send_message("You need to be in a voice channel to connect.",ephemeral=True)
    else:
        voice_channel:discord.VoiceClient = await interaction.user.voice.channel.connect()
        await interaction.response.send_message("Joined {} successfully.".format(interaction.user.voice.channel.name))

@tree.command(name='list',description='Lists audio files available to be played.')
@discord.app_commands.describe(subdir='The subdirectory to check, if empty, only checks the main folder.')
async def file_list(interaction:discord.Interaction, subdir:str|None = None):
    if interaction.user.id not in settings['users']['trusted']:
        await interaction.response.send_message("How unapologetically silly of you. No.")
        return
    files = []
    if subdir != None:
        for (root, dirs, file) in os.walk('./Assets/Music/{}'.format(subdir)):
            for f in file:
                if 'sources.txt' in f:
                    pass
                else:
                    files.append(f)
    else:
        for (root, dirs, file) in os.walk('./Assets/Music',topdown=True):
            dirs[:] = []
            for f in file:
                if 'sources.txt' in f:
                    pass
                else:
                    files.append(f)
    filelist = '\n'.join(files)
    if len(filelist) > 1993:
        with open('./file_list.txt', '+w') as filefile:
            filefile.write(filelist)
        await interaction.response.send_message(file=discord.File('./file_list.txt'), ephemeral=True)
        await asyncio.sleep(5)
        os.remove('./file_list.txt')
    else:
        filelist = '```\n' + '\n'.join(files) + '```'
        await interaction.response.send_message(filelist, ephemeral=True)

@tree.command(name='disconnect',description='Disconnects from the current voice channel.')
async def voice_disconnect(interaction:discord.Interaction):
    if interaction.user.id not in settings['users']['trusted']:
        await interaction.response.send_message("Why don\'t you try being polite next time?")
        return
    infraction = 0
    if interaction.user.voice is None:
        await interaction.response.send_message('You can\'t disconnect from a channel without being in the channel.', ephemeral=True)
        return
    if len(client.voice_clients) != 0:
        for voic in client.voice_clients:
            if voic.guild.name != interaction.guild.name:
                infraction += 1
            else:
                voice_channel = voic
    if interaction.user.voice.channel.id != voic.channel.id:
        await interaction.response.send_message('You can\'t disconnect from a channel without being in the channel.', ephemeral=True)
    if infraction == len(client.voice_clients):
        await interaction.response.send_message('Can\'t disconnect from nothing.', ephemeral=True)
        return
    else:
        await voice_channel.disconnect()
        await interaction.response.send_message('Disconnected from the voice channel.', ephemeral=True)


@tree.command(name='stop',description='Stops any currently playing audio.')
async def stop_audio(interaction:discord.Interaction):
    if interaction.user.id not in settings['users']['trusted']:
        await interaction.response.send_message('Absolutely not.')
        return
    if interaction.user.voice is None:
        await interaction.response.send_message('You need to be in a voice channel to stop its audio.', ephemeral=True)
        return
    elif len(client.voice_clients) == 0:
        await interaction.response.send_message('You can\'t stop nothing.', ephemeral=True)
    else:
        for voic in client.voice_clients:
            if voic.guild.name != interaction.guild.name:
                pass
            else:
                voice_channel = voic
        voice_channel.stop()
        await interaction.response.send_message('Stopped playing audio.', ephemeral=True)

@tree.command(name='bork',description='uwu :3')
async def disrupt_audio(interaction:discord.Interaction):
    await interaction.response.send_message('Nuh-uh.')
    return

@tree.command(name='play',description='Plays an audio file with the given name. Loaded from ./Assets/Music')
@discord.app_commands.describe(filepath='The name of the file to play.')
async def play_audio(interaction:discord.Interaction,filepath:str):
    if interaction.user.id not in settings['users']['trusted']:
        await interaction.response.send_message("Hell no.")
        return
    if len(client.voice_clients) == 0:
        if interaction.user.voice is None:
            await interaction.response.send_message("You need to be in a voice channel to play audio.", ephemeral=True)
            return
        else:
            voice_channel:discord.VoiceClient = await interaction.user.voice.channel.connect()
    else:
        for voic in client.voice_clients:
            if voic.guild.name != interaction.guild.name:
                pass
            else:
                voice_channel = voic
                break
    if '\\' in filepath:
        await interaction.response.send_message("Bot's running under Unix, use / instead of \\ to get what you want.", ephemeral=True)
        return
    if voice_channel.is_playing():
        voice_channel.stop()
    le_sound = discord.FFmpegPCMAudio('./Assets/Music/{}'.format(filepath))
    voice_channel.play(discord.PCMVolumeTransformer(le_sound, 0.5))
    await interaction.response.send_message('Started playing the file.', ephemeral=True)

# voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)

client.run(settings['client']['token'], log_handler=None)
