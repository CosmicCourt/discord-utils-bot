"""All the VoiceWork sections."""
# The dotting of "ignore[reportAssignmentType]" and "ignore[reportPossiblyUnboundVariable]" is because for some reason I cannot possibly fathom, discord.py *insists* to return a VoiceProtocol from client.voice_clients, despite me having confirmed multiple times that voice_clients stores, in this case, CustomVoiceClient. I don't get it, and I don't want it to keep yelling at me about nothing.
import discord
import os
import tomllib
import asyncio
import mutagen
import mutagen.mp3
import mutagen.oggopus
import mutagen.oggvorbis
import mutagen.wave
import mutagen.flac
import mutagen.asf
#Not supporting MP4 metadata because Mutagen says that MP4 tagging is inconsistent
import jsman as json
from random import randrange, sample
from discord.ext import commands
from typing import Literal

def load_toml() -> dict:
    with open('./Config/config.toml', 'rb') as configfile:
        settings:dict = tomllib.load(configfile)
    return settings
    # Loads to:
    # ['client']['token']: String, the bot token (there's a reason we don't ship the config file :P)
    # ['client']['activity']: String, the activity the bot will list as playing
    # ['client']['status']: String, one of online, idle, dnd, invisible
    # ['users']['enforce_whitelist']: Boolean, whether to enforce the next list for certain commands
    # ['users']['trusted']: List, user IDs in the whitelist
    # ['voicework']['group_enabled']

settings = load_toml()

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

class TrackWithMeta(discord.PCMVolumeTransformer):
    def __init__(self, original, volume: float = 1.0, trackname:str = 'UNTAGGED', trackartist:str = 'UNTAGGED', filename:str = 'UNSET'):
        if not isinstance(original, discord.AudioSource):
            raise TypeError(f'expected AudioSource not {original.__class__.__name__}.')

        if original.is_opus():
            raise discord.ClientException('AudioSource must not be Opus encoded.')

        self.original = original
        self.volume = volume
        self.trackname = trackname
        self.trackartist = trackartist
        self.filename = filename
        if self.trackname == 'UNTAGGED' and self.trackartist == 'UNTAGGED' and filename == 'UNSET':
            raise discord.ClientException('TrackWithMeta requires either metadata or a file name.')

def get_metadata(mutafile):
    match type(mutafile):
        case mutagen.oggopus.OggOpus|mutagen.flac.FLAC|mutagen.oggvorbis.OggVorbis:
            tagtitle = 'TITLE'
            tagartist = 'ARTIST'
        case mutagen.mp3.MP3|mutagen.wave.WAVE:
            tagtitle = 'TIT2'
            tagartist = 'TPE1'
        case mutagen.asf.ASF:
            tagtitle = 'Title'
            tagartist = 'Author'
        case _:
            pass
    try:
        artist_name = mutafile[tagartist] # pyright: ignore[reportPossiblyUnboundVariable]
    except Exception:
        artist_name = 'UNTAGGED'
    try:
        song_name = mutafile[tagtitle] # pyright: ignore[reportPossiblyUnboundVariable]
    except Exception:
        return 'UNTAGGED', 'UNTAGGED'
    else:
        return song_name, artist_name

def is_user_trusted():
    async def predicate(interaction:discord.Interaction) -> bool:
        trusted = False
        dj_role = False
        bot_owner = False
        if interaction.user.id in settings['users']['trusted']:
            trusted = True
        if interaction.guild.get_role(json.get_setting(interaction.guild, 'dj')) in interaction.user.roles:
            dj_role = True
        if interaction.user.id == settings['client']['bot_owner']:
            bot_owner = True
        if trusted or dj_role or bot_owner:
            return True
        else:
            return False
    return discord.app_commands.check(predicate)

def is_user_in_channel():
    async def predicate(interaction:discord.Interaction) -> bool:
        voice_channel:CustomVoiceClient|None = None
        in_any_channel = False
        in_current_channel = False
        for voic in interaction.client.voice_clients:
            if voic.guild.id != interaction.guild.id:
                pass
            else:
                voice_channel = voic # pyright: ignore[reportAssignmentType]
                break
        if voice_channel == None:
            in_current_channel = False
        if interaction.user.voice != None:
            in_any_channel = True
            if interaction.user.voice.channel.id == voice_channel.channel.id:
                in_current_channel = True
        if not in_any_channel or not in_current_channel:
            return False
        return True        
    return discord.app_commands.check(predicate)

def am_i_in_channel():
    async def predicate(interaction:discord.Interaction) -> bool:
        voice_channel:CustomVoiceClient|None = None
        i_am_in_channel = False
        i_am_real = True
        if len(interaction.client.voice_clients) <= 0:
            i_am_real = False
        for voic in interaction.client.voice_clients:
            if voic.guild.id != interaction.guild.id:
                pass
            else:
                voice_channel = voic # pyright: ignore[reportAssignmentType]
                i_am_in_channel = True
                break
        if not i_am_real or not i_am_in_channel:
            return False
        return True
    return discord.app_commands.check(predicate)

def is_any_in_channel():
    async def predicate(interaction:discord.Interaction) -> bool:
        voice_channel:CustomVoiceClient|None = None
        in_any_channel = False
        in_current_channel = False
        i_am_in_channel = False
        i_am_real = True
        if len(interaction.client.voice_clients) <= 0:
            i_am_real = False
        for voic in interaction.client.voice_clients:
            if voic.guild.id != interaction.guild.id:
                pass
            else:
                voice_channel = voic # pyright: ignore[reportAssignmentType]
                i_am_in_channel = True
                break
        if interaction.user.voice != None:
            in_any_channel = True
            if interaction.user.voice.channel.id == voice_channel.channel.id:
                in_current_channel = True
        if not i_am_real or not i_am_in_channel:
            return False
        if not in_any_channel or not in_current_channel:
            return False
        return True
    return discord.app_commands.check(predicate)

if os.name == 'nt':
    libopus = './Assets/Libraries/libopus/libopus.dll'
else:
    libopus = './Assets/Libraries/libopus/libopus.so'

def load_opus_if_enabled(is_enabled):
    if is_enabled:
        discord.opus.load_opus(libopus)
        return True
    else:
        return False
    
class CustomVoiceClient(discord.VoiceClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = []

    def track_finished(self, error):
        self.queue.pop(0)
        if self.queue:
            self.play(self.queue[0], after=self.track_finished)

    def add_track(self, track: discord.AudioSource):
        self.queue.append(track)
        if len(self.queue) == 1:
            self.play(self.queue[0], after=self.track_finished)
        else:
            pass

    def skip_track(self):
        if self.is_playing():
            self.stop()
        elif self.queue:
            self.queue.pop(0)

class VoiceWork(commands.Cog, name='VoiceWork'):
    group = discord.app_commands.Group(name='music',description='Music-related commands.')
    
    def __init__(self, client) -> None:
        self.client:discord.Client = client

    @group.command(name='connect',description='Connects the bot to your current voice channel.')
    async def voice_connect(self, interaction:discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message("You need to be in a voice channel to connect.",ephemeral=True)
        else:
            await interaction.response.defer()
            voice_channel:CustomVoiceClient = await interaction.user.voice.channel.connect(cls=CustomVoiceClient)
            await interaction.followup.send("Joined `{}` successfully.".format(interaction.user.voice.channel.name))
        
    @group.command(name='disconnect',description='Disconnects from the current voice channel.')
    @is_user_trusted()
    @is_any_in_channel()
    async def voice_disconnect(self, interaction:discord.Interaction):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        infraction = 0
        if interaction.user.voice is None:
            await interaction.response.send_message('You can\'t disconnect from a channel without being in the channel.', ephemeral=True)
            return
        if len(self.client.voice_clients) != 0:
            for voic in self.client.voice_clients:
                if voic.guild.name != interaction.guild.name:
                    infraction += 1
                else:
                    voice_channel:CustomVoiceClient = voic # pyright: ignore[reportAssignmentType]
        if interaction.user.voice.channel.id != voic.channel.id: # pyright: ignore[reportPossiblyUnboundVariable]
            await interaction.response.send_message('You can\'t disconnect from a channel without being in the channel.', ephemeral=True)
        if infraction == len(self.client.voice_clients):
            await interaction.response.send_message('Can\'t disconnect from nothing.', ephemeral=True)
            return
        else:
            channel_name = voice_channel.channel.name # pyright: ignore[reportPossiblyUnboundVariable]
            await voice_channel.disconnect() # pyright: ignore[reportPossiblyUnboundVariable]
            await interaction.response.send_message('Disconnected from `{}`.'.format(channel_name))

    @group.command(name='play',description='Plays an audio file with the given name. Loaded from ./Assets/Music')
    @discord.app_commands.describe(source='Where the file comes from; the Assets/Music folder, or a web link.',filepath='The name of the file to play.')
    async def play_audio(self, interaction:discord.Interaction,source:Literal["local","online"],filepath:str):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        voice_channel:CustomVoiceClient|None = None
        if len(self.client.voice_clients) == 0:
            if interaction.user.voice is None:
                await interaction.response.send_message("You need to be in a voice channel to play audio.")
                return
            else:
                voice_channel = await interaction.user.voice.channel.connect(cls=CustomVoiceClient)
        else:
            for voic in self.client.voice_clients:
                if voic.guild.name != interaction.guild.name:
                    pass
                else:
                    voice_channel = voic # pyright: ignore[reportAssignmentType]
                    break
        if voice_channel == None:
            voice_channel = await interaction.user.voice.channel.connect(cls=CustomVoiceClient)
        if source == 'online':
            await interaction.response.send_message('How about you go to hell?', ephemeral=True)
            return
        await interaction.response.defer()
        if source == 'local':
            filelist = []
            if os.name == 'nt':
                for letter in filepath:
                    if letter == '/':
                        filelist.append('\\')
                    else:
                        filelist.append(letter)
            else:
                for letter in filepath:
                    if letter == '\\':
                        filelist.append('/')
                    else:
                        filelist.append(letter)
            filepath = ''.join(filelist)
            le_sound = discord.FFmpegPCMAudio('./Assets/Music/{}'.format(filepath))
            track_name, track_artist = get_metadata(mutagen.File('./Assets/Music/{}'.format(filepath)))
            file_pat = filepath.split('/')[-1]
            filename = "".join(file_pat)
            fourletter = ['mp3', 'wav', 'ogg', 'm4a', 'm4r', 'aac', 'ac3', 'mp2', 'wma', 'mov', 'wmv', 'mp4', 'mkv']
            fiveletter = ['opus', 'flac']
            if filename.endswith(tuple(fiveletter)):
                file_name = filename[:-5]
            elif filename.endswith(tuple(fourletter)):
                file_name = filename[:-4]
            else:
                file_name = filename
        audio_file = TrackWithMeta(le_sound,json.get_setting(interaction.guild, 'volume'), track_name, track_artist, file_name)
        voice_channel.add_track(audio_file)
        if audio_file.trackname == 'UNTAGGED' and audio_file.trackartist == 'UNTAGGED':
            await interaction.followup.send('Now playing: `{}`'.format(audio_file.filename))
        else:
            await interaction.followup.send('Now playing: `{} - {}`'.format(audio_file.trackname, audio_file.trackartist))

    @group.command(name='resume',description='Resumes the paused track.')
    @is_user_trusted()
    @is_any_in_channel()
    async def unpause_track(self, interaction:discord.Interaction):
        voice_channel:CustomVoiceClient|None = None
        for voic in self.client.voice_clients:
            if voic.guild.name != interaction.guild.name:
                pass
            else:
                voice_channel = voic # pyright: ignore[reportAssignmentType]
                break
        if voice_channel == None:
            await interaction.response.send_message('I hope you realize I need to be _in_ the voice channel to unpause audio in it.')
            return
        name_thing = '{} - {}'.format(voice_channel.queue[0].trackname,voice_channel.queue[0].trackartist) if voice_channel.queue[0].trackname != 'UNTAGGED' and voice_channel.queue[0].trackartist != 'UNTAGGED' else '{}'.format(voice_channel.queue[0].filename)
        if voice_channel.is_paused():
            await interaction.response.defer()
            voice_channel.resume()
            await interaction.followup.send('Resumed playback of `{}`.'.format(name_thing))
        else:
            await interaction.response.send_message('The current track is not paused.')

    @group.command(name='pause',description='Pauses the currently playing track, or resumes if paused.')
    @is_user_trusted()
    @is_any_in_channel()
    async def pause_track(self, interaction:discord.Interaction):
        voice_channel:CustomVoiceClient|None = None
        for voic in self.client.voice_clients:
            if voic.guild.name != interaction.guild.name:
                pass
            else:
                voice_channel = voic # pyright: ignore[reportAssignmentType]
                break
        if voice_channel == None:
            await interaction.response.send_message('I hope you realize I need to be _in_ the voice channel to pause audio in it.')
            return
        name_thing = '{} - {}'.format(voice_channel.queue[0].trackname,voice_channel.queue[0].trackartist) if voice_channel.queue[0].trackname != 'UNTAGGED' and voice_channel.queue[0].trackartist != 'UNTAGGED' else '{}'.format(voice_channel.queue[0].filename)
        if voice_channel.is_playing() and not voice_channel.is_paused():
            await interaction.response.defer()
            voice_channel.pause()
            await interaction.followup.send('Paused playback of `{}`.'.format(name_thing))
        elif voice_channel.is_paused():
            await interaction.response.defer()
            voice_channel.resume()
            await interaction.followup.send('Resumed playback of `{}`.'.format(name_thing))

    @group.command(name='skip',description='Skips the currently playing track.')
    @is_user_trusted()
    async def skip_audio_track(self, interaction:discord.Interaction):
        voice_channel:CustomVoiceClient|None = None
        if len(self.client.voice_clients) == 0:
            if interaction.user.voice is None:
                await interaction.response.send_message("You need to be in a voice channel to skip audio.")
                return
            else:
                await interaction.response.send_message("You can\'t skip if nothing\'s playing.")
        else:
            for voic in self.client.voice_clients:
                if voic.guild.name != interaction.guild.name:
                    pass
                else:
                    voice_channel = voic # pyright: ignore[reportAssignmentType]
                    break
        if voice_channel == None:
            await interaction.response.send_message('I hope you realize I need to be _in_ the voice channel to skip audio from it.')
            return
        if voice_channel.is_playing() or voice_channel.is_paused():
            await interaction.response.defer()
            skipped_track:TrackWithMeta = voice_channel.source # pyright: ignore[reportAssignmentType]
            voice_channel.skip_track()
            if skipped_track.trackname == 'UNTAGGED' and skipped_track.trackartist == 'UNTAGGED':
                if voice_channel.is_playing():
                    if voice_channel.source.trackname == 'UNTAGGED' and voice_channel.source.trackartist == 'UNTAGGED':
                        await interaction.followup.send('Skipped playing `{}`.\nNow playing: `{}`'.format(skipped_track.filename, voice_channel.source.filename))
                    else:
                        await interaction.followup.send('Skipped playing `{}`.\nNow playing: `{} - {}`'.format(skipped_track.filename, voice_channel.source.trackname, voice_channel.source.trackartist))
                else:
                    await interaction.followup.send('Skipped playing `{}`.'.format(skipped_track.filename))
            else:
                if voice_channel.is_playing():
                    if voice_channel.source.trackname == 'UNTAGGED' and voice_channel.source.trackartist == 'UNTAGGED':
                        await interaction.followup.send('Skipped playing `{} - {}`.\nNow playing: `{}`'.format(skipped_track.trackname,skipped_track.trackartist,voice_channel.source.filename))
                    else:
                        await interaction.followup.send('Skipped playing `{} - {}`\nNow playing: `{} - {}`'.format(skipped_track.trackname,skipped_track.trackartist,voice_channel.source.trackname,voice_channel.source.trackartist))
                else:
                    await interaction.followup.send('Skipped playing `{} - {}`.'.format(skipped_track.trackname, skipped_track.trackartist))
        else:
            await interaction.followup.send("You can\'t skip if nothing\'s playing.")
            return

    @group.command(name='stop',description='Stops any currently playing audio.')
    async def stop_audio(self, interaction:discord.Interaction):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if interaction.user.voice is None:
            await interaction.response.send_message('You need to be in a voice channel to stop its audio.', ephemeral=True)
            return
        elif len(self.client.voice_clients) == 0:
            await interaction.response.send_message('You can\'t stop nothing.', ephemeral=True)
        else:
            for voic in self.client.voice_clients:
                if voic.guild.name != interaction.guild.name:
                    pass
                else:
                    voice_channel = voic
            voice_channel.stop() # pyright: ignore[reportPossiblyUnboundVariable]
            await interaction.response.send_message('Stopped playing audio.', ephemeral=True)
    
    @group.command(name='list',description='Lists audio files available to be played.')
    @discord.app_commands.describe(subdir='The subdirectory to check, if empty, only checks the main folder.')
    async def file_list(self, interaction:discord.Interaction, subdir:str|None = None):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        await interaction.response.defer(ephemeral=True)
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
            await interaction.followup.send(file=discord.File('./file_list.txt'), ephemeral=True)
            await asyncio.sleep(5)
            os.remove('./file_list.txt')
        else:
            filelist = '```\n' + '\n'.join(files) + '```'
            await interaction.followup.send(filelist, ephemeral=True)

async def setup(client:commands.Bot):
    load_opus_if_enabled(settings['voicework']['group_enabled'])
    await client.add_cog(VoiceWork(client))

async def teardown(client:commands.Bot):
    for voic in client.voice_clients:
        await voic.disconnect() # pyright:ignore[reportCallIssue]