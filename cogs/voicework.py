'''All the VoiceWork sections.'''
# trying to conform to PEP 8 with some of the funky formatting in here
# THIS IS INCOMPLETE and I'll finish it as I go, idk man
import os
import sys
import re
from typing import Literal
from random import randrange, sample

import discord
import tomllib
import aiohttp
import asyncio
import mutagen
from yt_dlp import YoutubeDL
from discord.ext import commands

import jsman as json

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

settings = load_toml()

yt_urls = [
    'youtube.com/watch?v=',
    'youtu.be/',
    'youtube.com/playlist?list=']

ydl_opts = dl_opts = {'extract_flat': 'discard_in_playlist',
 'final_ext': 'mp3',
 'format': 'bestaudio/best',
 'fragment_retries': 10,
 'ignoreerrors': 'only_download',
 'outtmpl': {'default': 'Assets/Music/YouTube/%(title)s - %(uploader)s.%(ext)s'},
 'postprocessors': [{'key': 'FFmpegExtractAudio',
                     'nopostoverwrites': False,
                     'preferredcodec': 'mp3',
                     'preferredquality': '5'},
                    {'add_chapters': True,
                     'add_infojson': 'if_exists',
                     'add_metadata': True,
                     'key': 'FFmpegMetadata'},
                    {'key': 'FFmpegConcat',
                     'only_multi_video': True,
                     'when': 'playlist'}],
 'quiet': True,
 'retries': 10,
 'warn_when_outdated': True}

meanstrings = [
    "Why don't you try being polite next time?",
    'Hell no.',
    "Why don't you try getting a job?",
    'How unapologetically silly of you. No.',
    'Get lost, friend.',
    'Nuh-uh.',
    'Absolutely not.',
    'Me- Me when- Me when your mom- Me when your mom- ' \
    '\\*dies by Zeus\\*',
    "I've met Crawlers with more manners than you.",
    'Mmm, no.']

# // This section copied from 
# https://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside
def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [atoi(c) for c in re.split(r'(\d+)', text)]
# //

def be_mean():
    return meanstrings[randrange(0,len(meanstrings) - 1)]

class MissingVoiceClientError(Exception):
    def __init__(self, message):
        self.message = '{} - {}'.format(message, self.__context__)
        super().__init__(self.message)

class IncorrectAudioSourceError(Exception):
    def __init__(self, message):
        self.message = '{} - {}'.format(message, self.__context__)
        super().__init__(self.message)

def reconstruct_as(source:TrackWithMeta):
    # We're looking for the volume and filepath. We can steal these
    # from the existing one, but need to rebuild this to fix things.
    return TrackWithMeta(source.filepath, source.volume)
    # So, as it turns out, this with a handful of other changes *DID* 
    # fix my replay issue! I just needed to build another helper
    # function into CVC anyway. Beh.

async def get_folder_contents(folder:str, extensions:str|tuple[str]):
    file_list = []
    for (root, dirs, file) in os.walk(
        '{}/Assets/Music/{}'.format(froot, folder), topdown=True):
        dirs[:] = []
        for f in file:
            if not f.endswith(extensions):
                pass
            else:
                file_list.append(f)
    return file_list

def filename_stripper(path):
    slas = ''.join(str(path).split('/')[-1])
    bot = '.'.join(slas.split('.')[0:-1])
    return bot

def get_data(mutafile):
    match type(mutafile):
        case mutagen.oggopus.OggOpus|mutagen.flac.FLAC|mutagen.oggvorbis.OggVorbis:
            tagtitle:str = 'TITLE'
            tagartist:str = 'ARTIST'
        case mutagen.mp3.MP3|mutagen.wave.WAVE:
            tagtitle:str = 'TIT2'
            tagartist:str = 'TPE1'
        case mutagen.asf.ASF:
            tagtitle:str = 'Title'
            tagartist:str = 'Author'
        case _:
            tagtitle:str = 'Title'
            tagartist:str = 'Author'
    try:
        artist_name:str = mutafile[tagartist]
    except Exception:
        artist_name:str = 'UNTAGGED'
    try:
        song_name:str = mutafile[tagtitle]
    except Exception:
        return str('UNTAGGED'), str('UNTAGGED')
    else:
        return song_name, artist_name

def get_duration(mutafile):
    length = mutafile.info.length
    hours = length // 3600
    length %= 3600
    minutes = length // 60
    length %= 60
    seconds = length
    return int(hours), int(minutes), int(seconds)        

def is_user_trusted():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not settings['users']['enforce_whitelist']:
            return True
        if (
            interaction.user.id in settings['users']['trusted'] or
            interaction.guild.get_role(
                json.get_setting(interaction.guild, 'dj', 'vw')
                ) in interaction.user.roles or
            interaction.user.id == settings['client']['bot_owner']):
            return True
        else:
            return False
    return discord.app_commands.check(predicate)

async def get_voiceclient(client:discord.Client, guild:discord.Guild|None):
    if guild == None:
        raise discord.ClientException('Invalid guild passed to get_voiceclient')
    voice_channel:CosmicVoice|None = None
    for voic in client.voice_clients:
        if voic.guild.id != guild.id:
            pass
        else:
            if not isinstance(voic, CosmicVoice):
                raise MissingVoiceClientError('Current guild does not have a CosmicVoice.')
            voice_channel = voic
    if voice_channel == None:
        raise MissingVoiceClientError('Current guild does not have a CosmicVoice.')
    else:
        return voice_channel

if os.name == 'nt':
    libopus = '{}/Assets/Libraries/libopus/libopus.dll'.format(froot)
else:
    libopus = '{}/Assets/Libraries/libopus/libopus.so'.format(froot)

async def read_playlist(list_name,guild):
    audio = []
    with open('{}/Assets/Playlists/{}.txt'.format(froot, list_name),
              mode='r', encoding='utf-8') as playlist:
        cinema = playlist.readlines()
    for line in cinema:
        if line.startswith('//'):
            pass
        elif line.lower() == '<eof>':
            break
        else:
            if '//' in line:
                line = ''.join(line.split('//')[:-1])
            if line.endswith('\n'):
                audio.append(TrackWithMeta(line[:-1], json.get_setting(guild, 'volume', 'vw')))
            else:
                audio.append(TrackWithMeta(line, json.get_setting(guild, 'volume', 'vw')))
    return audio

async def juggle_pathsep(string):
    filelist = []
    for letter in string:
        if letter == '\\':
            filelist.append('/')
        else:
            filelist.append(letter)
    return ''.join(filelist)

def load_opus_if_enabled(is_enabled):
    if is_enabled:
        if os.name != 'nt':
            discord.opus.load_opus(libopus)
            return True
        else:
            print("No need to load Opus; we're on Windows and it's " \
            "already loaded; file a bug report if this is not the case")
            return True
    else:
        return False
    
class CosmicVoice(discord.VoiceClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = []
        self.repeat = 'none'
        self.stop_it = False
        self.stop_it_skip = False
        self.play_count = 0

    def track_finished(self, error):
        self.queue.pop(0)
        if self.queue:
            self.play(self.queue[0], after=self.check_repeat)
            print('Now playing: {}'.format(self.queue[0]))

    def track_finished_single(self, error):
        test = self.queue.pop(0)
        if not self.stop_it_skip:
            new_source = reconstruct_as(test)
            self.queue.insert(0, new_source)
        else:
            self.stop_it_skip = False
        self.play(self.queue[0], after=self.check_repeat)
        print('Now playing: {}'.format(self.queue[0]))
        
    def track_finished_all(self, error):
        track = self.queue.pop(0)
        new_source = reconstruct_as(track)
        self.queue.append(new_source)
        self.play(self.queue[0], after=self.check_repeat)
        print('Now playing: {}'.format(self.queue[0]))

    def check_repeat(self, error):
        if not self.stop_it:
            match self.repeat:
                case 'none':
                    self.track_finished(error)
                case 'all':
                    self.track_finished_all(error)
                case 'single':
                    self.track_finished_single(error)
                case 'show':
                    raise discord.ClientException(
                        'self.repeat is set to "show"')
        else:
            return

    def add_track(self, track: discord.AudioSource):
        self.queue.append(track)
        if len(self.queue) == 1:
            self.play(self.queue[0], after=self.check_repeat)
            print('Now playing: {}'.format(self.queue[0]))

    def skip_track(self):
        self.stop()

class TrackWithMeta(discord.PCMVolumeTransformer):
    def __init__(
            self, filepath, volume: float = 1.0, 
            name: str = 'MUTA', artist: str = 'MUTA'):
        self.filepath = filepath
        if self.filepath == 'EMPTY':
            raise discord.ClientException('TrackWithMeta requires a ' \
            'valid file path.')
        self.original = discord.FFmpegPCMAudio(self.filepath)
        self.volume = volume
        self._muta = mutagen.File(self.filepath)
        self._mutaname, self._mutaartist = get_data(self._muta)
        self.name = name if name != 'MUTA' else self._mutaname
        self.artist = artist if artist != 'MUTA' else self._mutaartist
        self.filename = filename_stripper(self.filepath)
        self.hours, self.minutes, self.seconds = get_duration(self._muta)
        self.time_passed: int = 0

    def __repr__(self):
        return f'{self.name} - {self.artist} ({self.filename})'
    
    def read(self) -> bytes:
        self.time_passed += 20
        return super().read()
    
    def get_track_length(self):
        return (format(int(self.hours), '02d'), 
                format(int(self.minutes), '02d'), 
                format(int(self.seconds), '02d'))

    def get_time_elapsed(self):
        self.time_played = self.time_passed / 1000
        self.hours_played = format(int(self.time_played // 3600), '02d')
        self.time_played %= 3600
        self.minutes_played = format(int(self.time_played // 60), '02d')
        self.time_played %= 60
        self.seconds_played = format(int(self.time_played), '02d')
        return self.hours_played, self.minutes_played, self.seconds_played
    
    def get_time_to_end(self):
        self.time_in_seconds = ((self.hours * 60)
                                + (self.minutes * 60)
                                + self.seconds)
        self.time_played = self.time_passed / 1000
        self.time_in_seconds -= self.time_played
        self.hours_left = format(int(self.time_in_seconds // 3600), '02d')
        self.time_in_seconds %= 3600
        self.minutes_left = format(int(self.time_in_seconds // 60), '02d')
        self.time_in_seconds %= 60
        self.seconds_left = format(int(self.time_in_seconds) + 1, '02d')
        return self.hours_left, self.minutes_left, self.seconds_left

class VoiceWork(commands.Cog, name='VoiceWork'):
    def __init__(self, client) -> None:
        self.client:discord.Client = client

    # Main commands
    playb = discord.app_commands.Group(name='music',description='Music-related commands.', guild_only=True)

    @playb.command(name='connect',description='Connects the bot to your current voice channel.')
    async def voice_connect(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message('You need to be in a voice channel to connect.',ephemeral=True)
        else:
            await interaction.response.defer()
            voice_channel:CosmicVoice = await interaction.user.voice.channel.connect(cls=CosmicVoice)
            voice_channel.repeat = json.get_setting(interaction.guild,'repeat','vw')
            await interaction.followup.send('Joined `{}` successfully.'.format(interaction.user.voice.channel.name))
            print('Connected to {}'.format(interaction.user.voice.channel.name))

    @playb.command(name='disconnect',
                   description='Disconnects from the current voice channel.')
    @is_user_trusted()
    async def voice_disconnect(self, interaction: discord.Interaction):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if interaction.user.voice is None:
            await interaction.response.send_message("You can't disconnect from a channel without being in the channel.", ephemeral=True)
            return
        try:
            voice_channel:CosmicVoice = await get_voiceclient(self.client,interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("Can't disconnect from nothing.", ephemeral=True)
            return
        if interaction.user.voice.channel.id != voice_channel.channel.id:
            await interaction.response.send_message("You can't " \
              'disconnect from a channel without being in the channel.',
              ephemeral=True)
            return
        channel_name = voice_channel.channel.name
        await voice_channel.disconnect()
        await interaction.response.send_message('Disconnected from `{}`.'.format(channel_name))

    @playb.command(name='play',description='Plays an audio file with ' \
    'the given name. Loaded from ./Assets/Music') 
    # The REAL meat of this mess. Wow.
    @discord.app_commands.describe(source='Where the file comes from; ' \
    "the Assets/Music folder, a folder's entire contents, a web link, "
    'or a playlist.',filepath='The name of the file to play.')
    async def play_audio(self, interaction: discord.Interaction, 
                         source:Literal['local','folder','online','playlist'], 
                         filepath:str):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if interaction.user.voice is None:
            await interaction.response.send_message('You need to be in a voice channel to play audio.')
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            voice_channel = await interaction.user.voice.channel.connect(cls=CosmicVoice)
        await interaction.response.defer()
        match source:
            case 'playlist':
                if not os.path.exists('{}/Assets/Playlists/{}.txt'.format(froot, filepath)):
                    await interaction.followup.send('Playlist {} not found.'.format(filepath))
                else:
                    if len(voice_channel.queue) <= 0:
                        new_tracks = True
                    else:
                        new_tracks = False
                    audios = await read_playlist(filepath, interaction.guild)
                    if len(audios) == 0:
                        await interaction.followup.send('Playlist `{}` is empty.'.format(filepath))
                        return
                    for src in audios:
                        voice_channel.add_track(src)
                    if new_tracks:
                        await interaction.followup.send('Now playing the contents of playlist `{}`.'.format(filepath))
                    else:
                        await interaction.followup.send('Added contents of playlist `{}` to queue.'.format(filepath))
                print('Now playing playlist ./Assets/Playlists/{}.txt'.format(filepath))
                return
        
            case 'folder':
                file_list = []
                temp_queue = []
                for (root, dirs, file) in os.walk('{}/Assets/Music/{}'.format(froot, filepath),topdown=True):
                    dirs[:] = []
                    for f in file:
                        if not f.endswith(('mp3','mp4','wav','flac','ogg','opus','aac','wma','wmv','mkv','ac3','mp2','m4a','m4r')):
                            pass
                        else:
                            file_list.append(f)
                file_list.sort(key=natural_keys)
                for file in file_list:
                    thingpath = '{}/Assets/Music/{}/{}'.format(froot, filepath, file)
                    thingpath = await juggle_pathsep(thingpath)
                    temp_queue.append(TrackWithMeta(thingpath, json.get_setting(interaction.guild,'volume','vw')))
                if json.get_setting(interaction.guild,'shuffle','vw'):
                    new_queue = sample(temp_queue,len(temp_queue))
                else:
                    new_queue = temp_queue
                voice_channel.add_track(new_queue[0])
                for track in new_queue[1:]:
                    voice_channel.queue.append(track)
                print('Appended {} to queue'.format(filepath.split(os.sep)[-1]))
                await interaction.followup.send('The contents of `{}` have been added to the queue.'.format(filepath.split(os.sep)[-1]))
                return

            case 'online':
                if '/playlist' in filepath:
                    await interaction.followup.send('Playlists are not currently implemented.')
                    return
                if any(link in filepath for link in yt_urls):
                    with YoutubeDL(dl_opts) as ydl:
                        file_info = ydl.extract_info(filepath, download=False)
                    file_list = await get_folder_contents('YouTube', 'mp3')
                    if '{} - {}.mp3'.format(file_info['title'], file_info['uploader']) not in file_list:
                        await interaction.followup.send('Now downloading: `{} - {}`'.format(file_info['title'], file_info['uploader']))
                        with YoutubeDL(dl_opts) as ydl:
                            error_code = ydl.download(filepath)
                    filepath = '{} - {}.mp3'.format(file_info['title'], file_info['uploader'])
                    audio_file = TrackWithMeta('{}/Assets/Music/YouTube/{}'.format(froot, filepath), json.get_setting(interaction.guild, 'volume','vw'), file_info['title'], file_info['uploader'])
                else:
                    await interaction.followup.send('Non-YouTube URLs are not currently implemented.')
                    return
                    
            case 'local':
                if not os.path.exists('{}/Assets/Music/{}'.format(froot, filepath)):
                    await interaction.followup.send('File at `./Assets/Music/{}` not found.'.format(filepath))
                    return
                filepath = await juggle_pathsep(filepath)
                le_sound = discord.FFmpegPCMAudio('{}/Assets/Music/{}'.format(froot, filepath))
                audio_file = TrackWithMeta('{}/Assets/Music/{}'.format(froot, filepath), json.get_setting(interaction.guild, 'volume','vw')) 
        voice_channel.add_track(audio_file)
        file_identifier = '{} - {}'.format(audio_file.name, audio_file.artist) if audio_file.name != 'UNTAGGED' and audio_file.name != 'UNTAGGED' else '{}'.format(audio_file.filename)
        if len(voice_channel.queue) >= 2:
            await interaction.followup.send('Added to queue: `{}`'.format(file_identifier))
        else:
            await interaction.followup.send('Now playing: `{}`'.format(file_identifier))

    @playb.command(name='stop',description='Stops any currently playing audio.')
    async def stop_audio(self, interaction: discord.Interaction):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if interaction.user.voice is None:
            await interaction.response.send_message('You need to be in a voice channel to stop its audio.')
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("You can't stop nothing.")
            return
        voice_channel.stop_it = True
        temp_track = voice_channel.source
        voice_channel.queue = [temp_track]
        voice_channel.stop()
        await interaction.response.send_message('Stopped playing audio.')
        voice_channel.stop_it = False

    @playb.command(name='pause',description='Pauses the currently playing track, or resumes if paused.')
    @is_user_trusted()
    async def pause_track(self, interaction: discord.Interaction):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("Can't pause if nothing's playing.")
            return
        name_thing = '{} - {}'.format(voice_channel.queue[0].name,voice_channel.queue[0].artist) if voice_channel.queue[0].name != 'UNTAGGED' and voice_channel.queue[0].artist != 'UNTAGGED' else '{}'.format(voice_channel.queue[0].filename)
        if voice_channel.is_playing() and not voice_channel.is_paused():
            await interaction.response.defer()
            voice_channel.pause()
            await interaction.followup.send('Paused playback of `{}`.'.format(name_thing))
        elif voice_channel.is_paused():
            await interaction.response.defer()
            voice_channel.resume()
            await interaction.followup.send('Resumed playback of `{}`.'.format(name_thing))

    @playb.command(name='resume',description='Resumes the paused track.')
    @is_user_trusted()
    async def resume_track(self, interaction: discord.Interaction):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message('I hope you realize I need to be _in_ the voice channel to unpause audio in it.')
            return
        name_thing = '{} - {}'.format(voice_channel.queue[0].name,voice_channel.queue[0].artist) if voice_channel.queue[0].name != 'UNTAGGED' and voice_channel.queue[0].artist != 'UNTAGGED' else '{}'.format(voice_channel.queue[0].filename)
        if voice_channel.is_paused():
            await interaction.response.defer()
            voice_channel.resume()
            await interaction.followup.send('Resumed playback of `{}`.'.format(name_thing))
        else:
            await interaction.response.send_message('The current track is not paused.')

    @playb.command(name='skip',description='Skips the currently playing track.')
    @is_user_trusted()
    async def skip_audio_track(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message('You need to be in a voice channel to skip audio.')
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("Can't skip if nothing's playing.")
            return
        if voice_channel.is_playing() or voice_channel.is_paused():
            await interaction.response.defer()
            if not isinstance(voice_channel.source, TrackWithMeta):
                raise IncorrectAudioSourceError('Given AudioSource is not a TrackWithMeta AudioSource')
            skipped_track:TrackWithMeta = voice_channel.source
            voice_channel.stop_it_skip = True
            voice_channel.skip_track()
            if skipped_track.name == 'UNTAGGED' and skipped_track.artist == 'UNTAGGED':
                if voice_channel.is_playing():
                    if voice_channel.source.name == 'UNTAGGED' and voice_channel.source.artist == 'UNTAGGED':
                        await interaction.followup.send('Skipped playing `{}`.\nNow playing: `{}`'.format(skipped_track.filename, voice_channel.source.filename))
                    else:
                        await interaction.followup.send('Skipped playing `{}`.\nNow playing: `{} - {}`'.format(skipped_track.filename, voice_channel.source.name, voice_channel.source.artist))
                else:
                    await interaction.followup.send('Skipped playing `{}`.'.format(skipped_track.filename))
            else:
                if voice_channel.is_playing():
                    if voice_channel.source.name == 'UNTAGGED' and voice_channel.source.artist == 'UNTAGGED':
                        await interaction.followup.send('Skipped playing `{} - {}`.\nNow playing: `{}`'.format(skipped_track.name,skipped_track.artist,voice_channel.source.filename))
                    else:
                        await interaction.followup.send('Skipped playing `{} - {}`\nNow playing: `{} - {}`'.format(skipped_track.name,skipped_track.artist,voice_channel.source.name,voice_channel.source.artist))
                else:
                    await interaction.followup.send('Skipped playing `{} - {}`.'.format(skipped_track.name, skipped_track.artist))
        else:
            await interaction.followup.send("You can't skip if nothing's playing.")
            return

    @playb.command(name='playing',description='Show the status of the currently playing track.')
    async def now_playing(self, interaction: discord.Interaction):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message('There is nothing playing.')
            return
        if not voice_channel.is_playing():
            await interaction.response.send_message('There is nothing playing.')
            return
        await interaction.response.defer()
        trackref = voice_channel.source
        if not isinstance(trackref, TrackWithMeta):
            raise IncorrectAudioSourceError('Now Playing expected TrackWithMeta')
        current_name = '{}'.format('{}'.format(trackref.filename) if trackref.name == 'UNTAGGED' and trackref.artist == 'UNTAGGED' else '{} - {}'.format(trackref.name, trackref.artist))
        time_total = (trackref.get_track_length())
        elapsed_time = (trackref.get_time_elapsed())
        time_left = (trackref.get_time_to_end())
        await interaction.followup.send('Currently playing: {}\nTime played: {}:{}:{} of {}:{}:{}\nTime left: {}:{}:{}'.format(
            current_name,
            elapsed_time[0],
            elapsed_time[1],
            elapsed_time[2],
            time_total[0],
            time_total[1],
            time_total[2],
            time_left[0],
            time_left[1],
            time_left[2]
            ))

    @playb.command(name='list',description='Lists audio files available to be played.')
    @discord.app_commands.describe(subdir='The subdirectory to check, if empty, only checks the main folder.')
    @is_user_trusted()
    async def file_list(self, interaction: discord.Interaction, subdir:str|None = None):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        await interaction.response.defer(ephemeral=True)
        files = []
        if subdir != None:
            for (root, dirs, file) in os.walk('{}/Assets/Music/{}'.format(froot, subdir)):
                for f in file:
                    if 'sources.txt' in f:
                        pass
                    else:
                        files.append(f)
        else:
            for (root, dirs, file) in os.walk('{}/Assets/Music'.format(froot),topdown=True):
                dirs[:] = []
                for f in file:
                    if 'sources.txt' in f:
                        pass
                    else:
                        files.append(f)
        filelist = '\n'.join(files)
        if len(filelist) > 1993:
            with open('{}/file_list.txt'.format(froot), '+w') as filefile:
                filefile.write(filelist)
            await interaction.followup.send(file=discord.File('{}/file_list.txt'.format(froot)), ephemeral=True)
            await asyncio.sleep(5)
            os.remove('{}/file_list.txt'.format(froot))
        else:
            filelist = '```\n' + '\n'.join(files) + '```'
            await interaction.followup.send(filelist, ephemeral=True)


    # Queue commands
    que = discord.app_commands.Group(name='queue', description='Commands that act on the queue.', parent=playb, guild_only=True)

    @que.command(name='shuffle',description='Shuffles the contents of the queue.')
    @is_user_trusted()
    async def queue_shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.followup.send('Failed to shuffle queue; not connected to a channel.')
            return
        shuffled_queue = sample(voice_channel.queue[1:], len(voice_channel.queue) - 1)
        shuffled_queue.insert(0, voice_channel.queue[0])
        voice_channel.queue = shuffled_queue
        await interaction.followup.send('Queue has been shuffled.')

    @que.command(name='move',description='Moves an item in the queue.')
    async def queue_move(self, interaction: discord.Interaction, source:int, target:int):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if interaction.user.voice is None:
            await interaction.response.send_message('You need to be in a voice channel to manipulate its queue.')
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("You can't move in a non-existent queue.")
            return
        await interaction.response.defer()
        try:
            moved_track:TrackWithMeta = voice_channel.queue.pop(source)
            voice_channel.queue.insert(-1 if len(voice_channel.queue) < target else target,moved_track)
        except IndexError:
            await interaction.followup.send('No track at {} to move.'.format(source))
        else:
            if moved_track.name != 'UNTAGGED' and moved_track.artist != 'UNTAGGED':
                await interaction.followup.send('Moved `{} - {}` from index {} to {}.'.format(moved_track.name,moved_track.artist,source,target if target != -1 else 'the end of the queue'))
            else:
                await interaction.followup.send('Moved `{}` from index {} to {}.'.format(moved_track.filename,source,target if target != -1 else 'the end of the queue'))

    @que.command(name='remove',description='Removes an item from the queue.')
    @discord.app_commands.describe(index='The index of the track in the queue to remove.')
    @is_user_trusted()
    async def queue_remove(self, interaction: discord.Interaction, index:int):
        if index < 0:
            await interaction.response.send_message("There won't be anything at a negative index. If you're trying to clear the queue, there's a command specifically to do that.")
            return
        elif index == 0:
            await interaction.response.send_message("I think you're looking for `/music skip`.")
            return
        await interaction.response.defer()
        voice_channel = await get_voiceclient(self.client, interaction.guild)
        if voice_channel == None:
            await interaction.followup.send("Can't remove an item from a queue that isn't real.")
        try:
            removed_track:TrackWithMeta = voice_channel.queue.pop(index)
        except IndexError:
            await interaction.followup.send('There is nothing in the queue at the index {}.'.format(index))
        else:
            await interaction.followup.send('Removed `{}` from the queue, from index {}.'.format('{} - {}'.format(removed_track.name,removed_track.artist) if removed_track.name != 'UNTAGGED' and removed_track.artist != 'UNTAGGED' else '{}'.format(removed_track.filename), index))

    @que.command(name='list',description='List the contents of the queue.')
    @is_user_trusted()
    async def queue_list(self,interaction: discord.Interaction):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("Can't list the contents of a queue that isn't real.")
            return
        if len(voice_channel.queue) <= 1:
            await interaction.response.send_message('The queue is empty.\nDid you mean `/music playing`?')
        else:
            await interaction.response.defer()
            print_queue = []
            queue_count = 1
            while queue_count != len(voice_channel.queue):
                trackref:TrackWithMeta = voice_channel.queue[queue_count]
                print_queue.append('{}. {}'.format(queue_count, trackref.filename if trackref.name == 'UNTAGGED' and trackref.artist == 'UNTAGGED' else '{} - {}'.format(trackref.name, trackref.artist)))
                queue_count += 1
            filelist = '\n'.join(print_queue)
            if len(filelist) > 1993:
                with open('{}/track_queue.txt'.format(froot), '+w') as filefile:
                    filefile.write(filelist)
                await interaction.followup.send(file=discord.File('{}/track_queue.txt'.format(froot)))
                await asyncio.sleep(5)
                os.remove('{}/track_queue.txt'.format(froot))
            else:
                filelist = '```\n' + '\n'.join(print_queue) + '```'
                await interaction.followup.send(filelist, ephemeral=True)

    @que.command(name='clear',description='Clears the active queue.')
    @discord.app_commands.describe(active='Whether to stop the ' \
    'currently playing track, too.')
    @is_user_trusted()
    async def clear(self, interaction: discord.Interaction, active:bool):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("Can't clear an empty queue.")
            return
        if len(voice_channel.queue) <= 1 and not active:
            await interaction.response.send_message("Can't clear an empty queue.")
            return
        elif len(voice_channel.queue) <= 0 and active:
            await interaction.response.send_message("Can't clear an empty queue.")
            return
        await interaction.response.defer()
        temp_queue = voice_channel.queue
        voice_channel.queue = []
        voice_channel.queue.append(temp_queue[0])
        if active:
            voice_channel.stop()
            await interaction.followup.send('Playback has been stopped, and the queue has been cleared.')
        else:
            await interaction.followup.send('The queue has been cleared.')

    @que.command(name='save',description='Saves the current queue to a ' \
    'file. Will not save current playtime.')
    async def create_queue_playlist(self, interaction: discord.Interaction):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        try:
            voice_channel: CosmicVoice = await get_voiceclient(self.client,interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                "Can't disconnect from nothing.", ephemeral=True)
            return
        await interaction.response.defer()
        final = []
        for track in voice_channel.queue:
            final.append(track.filepath + '\n')
        final.append('<eof>')
        with open('{}/Assets/Playlists/filth pile.txt'.format(froot), 
                  mode = '+w', encoding = 'utf-8') as magic:
            magic.writelines(final)
        await interaction.followup.send('Queue has been saved to ' \
        'playlist `filth pile`.')


    # Playlist commands
    playlist = discord.app_commands.Group(name='playlist', description='Playlist commands.', parent=playb, guild_only=True)

    @playlist.command(name='help', 
                      description='Defines how to write a playlist file.')
    async def playlist_help(self, interaction: discord.Interaction):
        await interaction.response.send_message('Playlist files are ' \
        'defined as raw `.txt` files, with each line of the file being a'
        ' path to a local file to play. You can add comments with //,'
        ' but playlists must end with `<eof>` on a new line.',
        ephemeral = True, silent = True)
    
    @playlist.command(name='play',description='Plays the given playlist.')
    async def playlist_loopback(self, interaction: discord.Interaction, 
                                playlist:str):
        # I can't figure out how to get it to just use play_audio
        # so we have redundancy instead
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if interaction.user.voice is None:
            await interaction.response.send_message('You need to be in a voice channel to play audio.')
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            voice_channel = await interaction.user.voice.channel.connect(cls=CosmicVoice)
        await interaction.response.defer()
        if not os.path.exists('{}/Assets/Playlists/{}.txt'.format(froot, playlist)):
            await interaction.followup.send('Playlist {} not found.'.format(playlist))
        else:
            if len(voice_channel.queue) <= 0:
                new_tracks = True
            else:
                new_tracks = False
            audios = await read_playlist(playlist, interaction.guild)
            for src in audios:
                voice_channel.add_track(src)
            if new_tracks:
                await interaction.followup.send('Now playing the contents of playlist `{}`.'.format(playlist))
            else:
                await interaction.followup.send('Added contents of playlist `{}` to queue.'.format(playlist))
        return

    @playlist.command(name='list',description='Lists available playlists,' \
                      ' or shows the contents of a playlist.')
    @discord.app_commands.describe(
        subfolder = 'The subfolder to check, if any. Defaults to none; ' \
            'use "ignore" to specify none otherwise.',
        playlist = 'The playlist to check. Defaults to none.'
        )
    async def list_playlist(self, interaction: discord.Interaction, 
                            subfolder: str|None = None,
                            playlist: str|None = None):
        if subfolder.lower() == 'ignore':
            subfolder = None
        if playlist is not None:
            await interaction.response.defer()
            file_list = []
            if subfolder is None:
                for (root, dirs, file) in os.walk('{}/Assets/Playlists'.format(froot),topdown=True):
                    dirs[:] = []
                    for f in file:
                        if f.endswith('.txt'):
                            file_list.append(f[:-4])
                        else:
                            pass
            else:
                for (root, dirs, file) in os.walk('{}/Assets/Playlists/{}'.format(froot, subfolder),topdown=True):
                    dirs[:] = []
                    for f in file:
                        if f.endswith('.txt'):
                            file_list.append(subfolder + '/' + f[:-4])
                        else:
                            pass
            files = '\n'.join(file_list)
            return_string = 'Available playlists:\n```\n{}```'.format('\n'.join(file_list))
            if len(files) >= 2965:
                with open('{}/track_queue.txt'.format(froot), '+w') as filefile:
                    filefile.write(files)
                await interaction.followup.send('Available playlists:', file=discord.File('{}/playlist_index.txt'.format(froot)))
                await asyncio.sleep(5)
                os.remove('{}/playlist_index.txt'.format(froot))
            else:
                await interaction.followup.send('Available playlists:\n```\n{}```'.format(files))
        else:
            if subfolder is None:
                subfolder = ''
            elif not subfolder.endswith('/'):
                subfolder = subfolder + '/'
            if not os.path.exists('{}/Assets/Playlists/{}{}.txt'.format(froot, subfolder, playlist)):
                await interaction.response.send_message(
                    "Playlist {}{} doesn't exist.".format(
                        subfolder, playlist))
            else:
                await interaction.response.send_message(file=discord.File(
                    '{}/Assets/Playlists/{}{}.txt'.format(froot, subfolder,playlist)))

    @playlist.command(name='create', 
                      description='Creates a playlist with the given name.')
    @discord.app_commands.describe(name='The name of the playlist to create.',
                                   subfolder = 'The subfolder to place' \
                                   ' the file in.',
                                   overwrite = "Whether it's okay to " \
                                   'overwrite an existing playlist.')
    async def create_playlist(self, interaction: discord.Interaction, 
                              name: str, subfolder: str = '',
                              overwrite: bool = False):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if subfolder != '':
            if not subfolder.endswith('/'):
                subfolder += '/'
        if name.lower() == 'filth pile' and subfolder != '':
            await interaction.response.send_message("Can't name a " \
            "playlist `filth pile`; name reserved for saving queue.")
        else:
            try:
                with open('{}/Assets/Playlists/{}{}.txt'
                            .format(froot, subfolder, name), 
                            mode = 'x', encoding = 'utf-8') as plan:
                    plan.write('<eof>')
            except FileExistsError:
                if not overwrite:
                    await interaction.response.send_message('Playlist `{}{}`' \
                    ' already exists.'.format(subfolder, name))
                else:
                    os.remove('{}/Assets/Playlists/{}{}.txt'
                              .format(froot, subfolder, name))
                    with open('{}/Assets/Playlists/{}{}.txt'
                              .format(froot, subfolder, name),
                              mode = 'x', encoding = 'utf-8') as plan:
                        plan.write('<eof>')
                    await interaction.response.send_message('Playlist ' \
                    '`{}{}` overwritten.'.format(subfolder, name))
            else:
                await interaction.response.send_message('Playlist `{}{}`' \
                ' created.'.format(subfolder, name))
            
    @playlist.command(name='upload',
                      description='Upload a file to the playlist folder.')
    @discord.app_commands.describe(file='The file to be uploaded.',
                                   subfolder='The subfolder to put the'
                                   ' file in. Defaults to none.')
    async def upload_playlist(self, interaction: discord.Interaction, 
                              file: discord.Attachment, subfolder: str = '', 
                              overwrite: bool = False):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if subfolder != '':
            if not subfolder.endswith('/'):
                subfolder += '/'
        filename = '.'.join(file.filename.split('.')[:-1])
        if os.path.exists('{}/Assets/Playlists/{}{}.txt'
                            .format(froot, subfolder, filename)):
            if overwrite:
                os.remove('{}/Assets/Playlists/{}{}.txt'
                            .format(froot, subfolder, filename))
            else:
                await interaction.response.send_message(
                    "Playlist `{}{}` already exists."
                    .format(subfolder, filename))
                return
        await file.save('{}/Assets/Playlists/{}{}.txt'
                        .format(froot, subfolder,filename))
        await interaction.response.send_message(
            'Playlist `{}{}` saved.'.format(subfolder,filename))

    @playlist.command(name='add', description='Adds a track to the playlist.')
    @discord.app_commands.describe(playlist='The playlist to add to.',
                                   index='The track to add to the queue. ' \
                                   'Defaults to the current track.' \
                                   'Specify -1 to use a file path.',
                                   path='The file path to add. Ignored '\
                                   "if index isn't -1.")
    async def playlist_append(self, interaction: discord.Interaction, 
                              playlist: str,
                              index: int = 0, 
                              path: str = 'Who are you talking to?'):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            voice_channel = None
        if playlist == 'filth pile':
            await interaction.response.send_message("Can't use reserved" \
            "playlist name `filth pile`.")
        with open('{}/Assets/Playlists/{}.txt'.format(froot, playlist),
                  mode='r', encoding='utf-8') as magic:
            audio = magic.readlines()
        if index > len(voice_channel.queue):
            await interaction.response.send_message(
                'Index {} out of range.'.format(index))
        elif index == -1:
            if path == 'Who are you talking to?':
                await interaction.response.send_message(
                    "No file path given.")
            else:
                audio.insert(-1, path)
                await interaction.response.send_message(
                    "Added `{}` to `{}`.".format(path, playlist))
        else:
            audio.insert(-1, voice_channel.queue[index].filepath + '\n')


    # Config commands
    cfg = discord.app_commands.Group(name='config', description='Commands that change settings.', parent=playb, guild_only=True)

    @cfg.command(name='establish',description='Generates the base configuration file for a new server. WILL OVERWRITE AN EXISTING FILE.')
    async def establish(self, interaction: discord.Interaction):
        json.create(interaction.guild, 'vw')
        await interaction.response.send_message('Config file for `{}` created at `./Config/Guilds/{}.json`.'.format(interaction.guild.name,interaction.guild.id),ephemeral=True)

    @cfg.command(name='volume',description='Change the volume music plays at.')
    @discord.app_commands.describe(amount='The volume to set, with a range of 0.0 to 1.0 (representing 0 - 100%). Leave this empty to show the current volume.')
    @is_user_trusted()
    async def volume(self, interaction: discord.Interaction, amount: discord.app_commands.Range[float, 0.0, 1.0] = 10.0):
        voice_channel:CosmicVoice|None = None
        if amount == 10.0:
            current_volume = int(json.get_setting(interaction.guild,'volume','vw') * 100)
            await interaction.response.send_message('Current volume is {}.'.format(str(current_volume) + '%'))
            return
        json.change_setting(interaction.guild,'volume',amount,'vw')
        volume_percent = int(amount * 100)
        volume = str(volume_percent) + '%'
        await interaction.response.defer()
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            pass
        else:
            if voice_channel.is_playing():
                voice_channel.source.volume = amount
            if len(voice_channel.queue) >= 2:
                for audio in voice_channel.queue:
                    audio.volume = amount
        await interaction.followup.send('Volume changed to {}.'.format(volume))

    @cfg.command(name='repeat',description='Set the repeat mode.')
    async def repeat(self, interaction: discord.Interaction, new_value:Literal['none','single','all','show']):
        if new_value == 'show':
            await interaction.response.send_message('Repeat is currently set to "{}".'.format(json.get_setting(interaction.guild,'repeat','vw')))
            return
        json.change_setting(interaction.guild,'repeat',new_value,'vw')
        if len(self.client.voice_clients) >= 0:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
            voice_channel.repeat = new_value
        await interaction.response.send_message('Repeat has been disabled.' if new_value == 'none' else 'Repeat has been set to {}.'.format(new_value))

    @cfg.command(name='clear_cache', description='Clears the YouTube file cache.')
    @is_user_trusted()
    async def clear_cache(self, interaction: discord.Interaction):
        await interaction.response.defer()
        file_list = await get_folder_contents('YouTube', 'mp3')
        for file in file_list:
            os.remove(file)
        await interaction.followup.send('Cache has been cleared.')
    
    @cfg.command(name='setdj',description='Sets which role is considered as the "DJ" role (has access to the playback commands).')
    @discord.app_commands.describe(roleid='The ID of the new DJ role.')
    async def dj(self, interaction: discord.Interaction, roleid:int):
        json.change_setting(interaction.guild,'dj',roleid,'vw')
        if roleid != 0:
            await interaction.response.send_message('The role `{}` has been set as the DJ role.'.format(interaction.guild.get_role(roleid).name),ephemeral=True)
        else:
            await interaction.response.send_message('The DJ role has been cleared.',ephemeral=True)

    @cfg.command(name='shuffle',description='Toggle shuffle on or off.')
    async def shuffle(self, interaction: discord.Interaction, new_value:bool):
        json.change_setting(interaction.guild,'shuffle',new_value,'vw')
        await interaction.response.send_message('Shuffle has been turned {}.'.format('on' if new_value else 'off'))


async def setup(client:commands.Bot):
    load_opus_if_enabled(settings['voicework']['group_enabled'])
    await client.add_cog(VoiceWork(client))

async def teardown(client:commands.Bot):
    for voic in client.voice_clients:
        if not isinstance(voic, CosmicVoice):
            pass
        else:
            await voic.disconnect()