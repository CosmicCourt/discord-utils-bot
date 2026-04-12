'''All the VoiceWork sections.'''
# trying to conform to PEP 8 with some of the funky formatting in here
# THIS IS INCOMPLETE and I'll finish it as I go, idk man
# Okay, we should be compliant now
import os
import sys
import re
from typing import Literal
from random import randrange, sample, shuffle

import discord
import tomllib
import aiohttp
import asyncio
import mutagen
from yt_dlp import YoutubeDL
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

settings = load_toml()

eph = settings['client']['shut_up']

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

async def get_string_from_folder(folder: str, string: str):
    file_list = []
    for (root, dirs, file) in os.walk('{}/Assets/{}'
                                      .format(froot, folder),
                                      followlinks = True):
        for f in file:
            if not string.strip().lower() in f.lower():
                pass
            else:
                if f.lower() == 'readme.txt':
                    pass
                elif f.lower() == 'filth pile.txt':
                    pass
                else:
                    file_list.append(str(f"{root}/{f}")
                                     .split(folder, 
                                            maxsplit=1)[-1][1:])
    return file_list

def filename_stripper(path):
    slas = ''.join(str(path).split('/')[-1])
    bot = '.'.join(slas.split('.')[0:-1])
    return bot

async def lrc_format(lyrics):
    headpattern = r"^ *\[\D{1,2}:.+\]"
    rxpattern = r"\[\d{2}:\d{2}:\d{2,3}\] *"
    lrc = lyrics.split('\n')
    lyric = []
    for line in lrc:
        head = re.search(headpattern, line)
        if head is None:
            reg = re.search(rxpattern, line)
            if reg is not None:
                lyric.append(str(line.split(']', maxsplit=1)[-1])
                             .strip())
            else:
                lyric.append(line)
    while lyric[0] == '':
        lyric = lyric[1:]
    return '\n'.join(lyric)

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
        raise discord.ClientException(
            'Invalid guild passed to get_voiceclient')
    v_chan:CosmicVoice|None = None
    for voic in client.voice_clients:
        if voic.guild.id != guild.id:
            pass
        else:
            if not isinstance(voic, CosmicVoice):
                raise MissingVoiceClientError(
                    'Current guild does not have a CosmicVoice.')
            v_chan = voic
    if v_chan == None:
        raise MissingVoiceClientError(
            'Current guild does not have a CosmicVoice.')
    else:
        return v_chan

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
                audio.append(
                    TrackWithMeta(line[:-1],
                                  json.get_setting(
                                      guild, 'volume', 'vw')))
            else:
                audio.append(
                    TrackWithMeta(line, 
                                  json.get_setting(
                                      guild, 'volume', 'vw')))
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
            print('{}Now playing: {}{}{}'
                  .format(style.ff_text, style.ff_file,
                          self.queue[0], style.reset))

    def track_finished_single(self, error):
        test = self.queue.pop(0)
        if not self.stop_it_skip:
            new_source = reconstruct_as(test)
            self.queue.insert(0, new_source)
        else:
            self.stop_it_skip = False
        self.play(self.queue[0], after=self.check_repeat)
        print('{}Now playing: {}{}{}'
              .format(style.ff_text, style.ff_file,
                      self.queue[0], style.reset))
        
    def track_finished_all(self, error):
        track = self.queue.pop(0)
        new_source = reconstruct_as(track)
        self.queue.append(new_source)
        self.play(self.queue[0], after=self.check_repeat)
        print('{}Now playing: {}{}{}'
              .format(style.ff_text, style.ff_file,
                      self.queue[0], style.reset))

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
        return

    def add_track(self, track: discord.AudioSource):
        self.queue.append(track)
        if len(self.queue) == 1:
            self.play(self.queue[0], after=self.check_repeat)
            print('{}Now playing: {}{}{}'
                  .format(style.ff_text, style.ff_file,
                          self.queue[0], style.reset))

    def skip_track(self):
        print('{}Skipping {}{}{}'.format(
            style.ff_text,
            style.ff_file,
            self.queue[0],
            style.reset
        ))
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
        if self.name != 'UNTAGGED' and self.name != 'UNTAGGED':
            return f'{self.artist} - {self.name}'
        else:
            return f'{self.filename}'
    
    def read(self) -> bytes:
        self.time_passed += 20
        return super().read()
    
    def get_track_length(self):
        return (format(int(self.hours), '02d'), 
                format(int(self.minutes), '02d'), 
                format(int(self.seconds), '02d'))

    def get_time_elapsed(self):
        self.time_played = self.time_passed / 1000
        self.hours_played = format(
            int(self.time_played // 3600), '02d')
        self.time_played %= 3600
        self.minutes_played = format(
            int(self.time_played // 60), '02d')
        self.time_played %= 60
        self.seconds_played = format(
            int(self.time_played), '02d')
        return self.hours_played, self.minutes_played, self.seconds_played
    
    def get_time_to_end(self):
        self.time_in_seconds = ((self.hours * 60)
                                + (self.minutes * 60)
                                + self.seconds)
        self.time_played = self.time_passed / 1000
        self.time_in_seconds -= self.time_played
        self.hours_left = format(
            int(self.time_in_seconds // 3600), '02d')
        self.time_in_seconds %= 3600
        self.minutes_left = format(
            int(self.time_in_seconds // 60), '02d')
        self.time_in_seconds %= 60
        self.seconds_left = format(
            int(self.time_in_seconds) + 1, '02d')
        return self.hours_left, self.minutes_left, self.seconds_left

class VoiceWork(commands.Cog, name='VoiceWork'):
    def __init__(self, client) -> None:
        self.client:discord.Client = client

    # Main commands
    playb = discord.app_commands.Group(
        name='music',
        description='Music-related commands.', guild_only=True)

    @playb.command(name='connect',
                   description='Connects the bot to your ' \
                   'current voice channel.')
    @is_user_trusted()
    async def voice_connect(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message(
                'You need to be in a voice channel to connect.',
                ephemeral=eph)
        else:
            await interaction.response.defer()
            v_chan = await interaction.user.voice.channel.connect(
                cls=CosmicVoice)
            v_chan.repeat = json.get_setting(
                interaction.guild,'repeat','vw')
            await interaction.followup.send(
                'Joined `{}` successfully.'.format(
                    interaction.user.voice.channel.name),
                    ephemeral=eph)
            print('{}Connected to {}{}{} ({}{}{}){}'
                  .format(style.ff_text, style.ff_disc,
                          interaction.user.voice.channel.name,
                          style.ff_text, style.ff_disc,
                          interaction.user.voice.channel.guild.name,
                          style.ff_text, style.reset))

    @playb.command(name='disconnect',
                   description='Disconnects from the current voice channel.')
    @is_user_trusted()
    async def voice_disconnect(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message(
                "You can't disconnect from a channel without being " \
                "in the channel.", ephemeral=eph)
            return
        try:
            v_chan:CosmicVoice = await get_voiceclient(
                self.client,interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                "Can't disconnect from nothing.", ephemeral=eph)
            return
        if interaction.user.voice.channel.id != v_chan.channel.id:
            await interaction.response.send_message("You can't " \
              'disconnect from a channel without being in the channel.',
              ephemeral=eph)
            return
        channel_name = v_chan.channel.name
        await v_chan.disconnect()
        await interaction.response.send_message(
            'Disconnected from `{}`.'.format(channel_name),
            ephemeral=eph)
        print('{}Disconnected from {}{}{} ({}{}{}){}'
              .format(style.ff_text, style.ff_disc,
                      v_chan.channel.name,
                      style.ff_text, style.ff_disc,
                      v_chan.channel.guild.name,
                      style.ff_text, style.reset))

    @playb.command(name='play',description='Plays an audio file with ' \
    'the given name. Loaded from ./Assets/Music') 
    # The REAL meat of this mess. Wow.
    @discord.app_commands.describe(filepath='The file to play.')
    async def play_audio(self, interaction: discord.Interaction, 
                         filepath:str):
        if interaction.user.voice is None:
            await interaction.response.send_message(
                'You need to be in a voice channel to play audio.',
                ephemeral=eph)
            return
        try:
            v_chan = await get_voiceclient(
                self.client, interaction.guild)
        except MissingVoiceClientError:
            v_chan = await interaction.user.voice.channel.connect(
                cls=CosmicVoice)
        await interaction.response.defer()
        if filepath.startswith('fl!'):
            source = 'folder'
        elif filepath.startswith('pl!'):
            source = 'playlist'
        elif filepath.startswith('http'):
            source = 'online'
        else:
            if os.path.isdir(filepath):
                source = 'folder'
            elif (
                not filepath.endswith(
                ('mp3','mp4','wav','flac','ogg','ac3','aac',
                 'wma','wmv','mkv','opus','mp2','m4a','m4r')) and 
                os.path.isfile(filepath)):
                source = 'playlist'
            else:
                source = 'local'
        match source:
            case 'playlist':
                if filepath.endswith('.txt'):
                    filepath = filepath[:-4]
                if not os.path.exists(
                    '{}/Assets/Playlists/{}.txt'
                    .format(froot, filepath)):
                    await interaction.followup.send(
                        'Playlist {} not found.'.format(filepath),
                        ephemeral=eph)
                else:
                    if len(v_chan.queue) <= 0:
                        new_tracks = True
                    else:
                        new_tracks = False
                    audios = await read_playlist(
                        filepath, interaction.guild)
                    if len(audios) == 0:
                        await interaction.followup.send(
                            'Playlist `{}` is empty.'
                            .format(filepath),
                            ephemeral=eph)
                        return
                    if json.get_setting(interaction.Guild,
                                        'shuffle', 'vw'):
                        shuffle(audios)
                    for src in audios:
                        v_chan.add_track(src)
                    if new_tracks:
                        await interaction.followup.send(
                            'Now playing the contents of playlist `{}`.'
                            .format(filepath), ephemeral=eph)
                    else:
                        await interaction.followup.send(
                            'Added contents of playlist `{}` to queue.'
                            .format(filepath), ephemeral=eph)
                print('{}Now playing playlist {}./Assets/Playlists/{}.txt{}'
                      .format(style.ff_text, style.ff_file,
                              filepath, style.reset))
                return
        
            case 'folder':
                file_list = []
                temp_queue = []
                for (root, dirs, file) in os.walk(
                    '{}/Assets/Music/{}'.format(froot, filepath),
                    topdown=True):
                    dirs[:] = []
                    for f in file:
                        if not f.endswith(
                            ('mp3','mp4','wav','flac','ogg',
                             'opus','aac','wma','wmv','mkv',
                             'ac3','mp2','m4a','m4r')):
                            pass
                        else:
                            file_list.append(f)
                file_list.sort(key=natural_keys)
                for file in file_list:
                    thingpath = ('{}/Assets/Music/{}/{}'
                                .format(froot, filepath, file))
                    thingpath = await juggle_pathsep(thingpath)
                    temp_queue.append(
                        TrackWithMeta(thingpath, 
                                      json.get_setting(
                                          interaction.guild,
                                          'volume',
                                          'vw')))
                new_queue = temp_queue
                if json.get_setting(interaction.guild,'shuffle','vw'):
                    shuffle(new_queue)
                v_chan.add_track(new_queue[0])
                for track in new_queue[1:]:
                    v_chan.queue.append(track)
                print('{}Appended {}{}{} to queue{}'
                      .format(style.ff_text, style.ff_file,
                              filepath.split(os.sep)[-1],
                              style.ff_text, style.reset))
                await interaction.followup.send(
                    'The contents of `{}` have been added to the queue.'
                    .format(filepath.split(os.sep)[-1]),
                    ephemeral=eph)
                return

            case 'online':
                if '/playlist' in filepath:
                    await interaction.followup.send(
                        'Playlists are not currently implemented.',
                        ephemeral=eph)
                    return
                if any(link in filepath for link in yt_urls):
                    with YoutubeDL(dl_opts) as ydl:
                        file_info = ydl.extract_info(filepath,
                                                     download=False)
                    file_list = await get_folder_contents(
                        'YouTube', 'mp3')
                    if '{} - {}.mp3'.format(file_info['title'], 
                                            file_info['uploader']
                                            ) not in file_list:
                        await interaction.followup.send(
                            'Now downloading: `{} - {}`'
                            .format(file_info['title'], 
                                    file_info['uploader']),
                            ephemeral=eph)
                        with YoutubeDL(dl_opts) as ydl:
                            error_code = ydl.download(filepath)
                    filepath = '{} - {}.mp3'.format(
                        file_info['title'], file_info['uploader'])
                    audio_file = TrackWithMeta(
                        '{}/Assets/Music/YouTube/{}'.format(
                            froot, filepath),
                        json.get_setting(
                            interaction.guild, 'volume','vw'),
                            file_info['title'], file_info['uploader'])
                else:
                    await interaction.followup.send(
                        'Non-YouTube URLs are not implemented.',
                        ephemeral=eph)
                    return
                    
            case 'local':
                if not os.path.exists('{}/Assets/Music/{}'
                                      .format(froot, filepath)):
                    await interaction.followup.send(
                        'File at `./Assets/Music/{}` not found.'
                        .format(filepath), ephemeral=eph)
                    return
                filepath = await juggle_pathsep(filepath)
                audio_file = TrackWithMeta('{}/Assets/Music/{}'
                                           .format(froot, filepath),
                                           json.get_setting(
                                               interaction.guild,
                                               'volume','vw'))
        v_chan.add_track(audio_file)
        if len(v_chan.queue) >= 2:
            await interaction.followup.send('Added to queue: `{}`'
                                            .format(audio_file),
                                            ephemeral=eph)
        else:
            await interaction.followup.send('Now playing: `{}`'
                                            .format(audio_file),
                                            ephemeral=eph)

    @playb.command(name='stop',
                   description='Stops any currently playing audio.')
    @is_user_trusted()
    async def stop_audio(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message(
                'You need to be in a voice channel to stop its audio.',
                ephemeral=eph)
            return
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                "You can't stop nothing.",
                ephemeral=eph)
            return
        v_chan.stop_it = True
        temp_track = v_chan.source
        v_chan.queue = [temp_track]
        v_chan.stop()
        await interaction.response.send_message(
            'Stopped playing audio.', ephemeral=eph)
        print('{}Playback stopped.{}'.format(
            style.ff_text, style.reset
        ))
        v_chan.stop_it = False

    @playb.command(name='pause',
                   description='Pauses the currently playing ' \
                   'track, or resumes if paused.')
    @is_user_trusted()
    async def pause_track(self, interaction: discord.Interaction):
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                "Can't pause if nothing's playing.",
                ephemeral=eph)
            return
        trackref = v_chan.queue[0]
        if v_chan.is_playing() and not v_chan.is_paused():
            await interaction.response.defer()
            v_chan.pause()
            await interaction.followup.send(
                'Paused playback of `{}`.'.format(trackref),
                ephemeral=eph)
            print('{}Paused playback of {}{}{}'.format(
                style.ff_text, style.ff_file, trackref, style.reset))
        elif v_chan.is_paused():
            await interaction.response.defer()
            v_chan.resume()
            await interaction.followup.send(
                'Resumed playback of `{}`.'.format(trackref),
                ephemeral=eph)
            print('{}Resumed playback of {}{}{}'.format(
                style.ff_text, style.ff_file, trackref, style.reset))

    @playb.command(name='resume',
                   description='Resumes the paused track.')
    @is_user_trusted()
    async def resume_track(self, interaction: discord.Interaction):
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                'Nothing to resume.',
                ephemeral=eph)
            return
        name_thing = v_chan.queue[0]
        if v_chan.is_paused():
            await interaction.response.defer()
            v_chan.resume()
            await interaction.followup.send(
                'Resumed playback of `{}`.'.format(name_thing),
                ephemeral=eph)
            print('{}Resumed playback of {}{}{}'.format(
                style.ff_text, style.ff_file, name_thing, style.reset))
        else:
            await interaction.response.send_message(
                'The current track is not paused.',
                ephemeral=eph)

    @playb.command(name='skip',
                   description='Skips the currently playing track.')
    @is_user_trusted()
    async def skip_audio_track(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message(
                'You need to be in a voice channel to skip audio.',
                ephemeral=eph)
            return
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                "Can't skip if nothing's playing.", ephemeral=eph)
            return
        if v_chan.is_playing() or v_chan.is_paused():
            await interaction.response.defer()
            if not isinstance(v_chan.source, TrackWithMeta):
                raise IncorrectAudioSourceError(
                    'Given AudioSource is not a TrackWithMeta ' \
                    'AudioSource')
            skipped_track:TrackWithMeta = v_chan.source
            v_chan.stop_it_skip = True
            v_chan.skip_track()
            if v_chan.is_playing():
                await interaction.followup.send(
                    'Skipped playing `{}`.\nNow playing: `{}`'
                    .format(skipped_track,v_chan.source),
                    ephemeral=eph)
            else:
                await interaction.followup.send(
                    'Skipped playing `{}`.'.format(skipped_track),
                    ephemeral=eph)
        else:
            await interaction.followup.send(
                "You can't skip if nothing's playing.", ephemeral=eph)
            return

    @playb.command(
            name='playing',
            description='Show the status of the currently playing track.')
    async def now_playing(self, interaction: discord.Interaction):
        try:
            v_chan = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                'There is nothing playing.')
            return
        if not v_chan.is_playing():
            await interaction.response.send_message(
                'There is nothing playing.')
            return
        await interaction.response.defer()
        trackref = v_chan.source
        if not isinstance(trackref, TrackWithMeta):
            raise IncorrectAudioSourceError(
                'Now Playing expected TrackWithMeta')
        total = (trackref.get_track_length())
        elap = (trackref.get_time_elapsed())
        left = (trackref.get_time_to_end())
        await interaction.followup.send(f'Currently playing: {trackref}\n' \
        f'Time played: {elap[0]}:{elap[1]}:{elap[2]} of ' \
        f'{total[0]}:{total[1]}:{total[2]}\n' \
        f'Time left: {left[0]}:{left[1]}:{left[2]}',
        ephemeral=eph)

    @playb.command(
            name='list',
            description='Lists audio files available to be played.')
    @discord.app_commands.describe(
        subdir='The subdirectory to check. ' \
        'Defaults to the main folder.')
    async def file_list(self, interaction: discord.Interaction,
                        subdir:str|None = None):
        await interaction.response.defer(ephemeral=True)
        files = []
        if subdir != None:
            cont = '\'s subfolder {}{}'.format(style.ff_file, subdir)
            for (root, dirs, file) in os.walk(
                '{}/Assets/Music/{}'.format(froot, subdir)):
                for f in file:
                    if 'sources.txt' in f:
                        pass
                    else:
                        files.append(f)
        else:
            cont = ''
            for (root, dirs, file) in os.walk(
                '{}/Assets/Music'.format(froot),topdown=True):
                dirs[:] = []
                for f in file:
                    if 'sources.txt' in f:
                        pass
                    else:
                        files.append(f)
        filelist = '\n'.join(files)
        print('{}Listing contents of the music folder{}.{}'.format(
            style.ff_text, cont, style.reset))
        if len(filelist) > 1993:
            with open(
                '{}/file_list.txt'.format(froot),
                '+w', encoding='utf-8') as filefile:
                filefile.write(filelist)
            await interaction.followup.send(
                file=discord.File('{}/file_list.txt'.format(froot)),
                ephemeral=eph)
            await asyncio.sleep(5)
            os.remove('{}/file_list.txt'.format(froot))
        else:
            filelist = '```\n' + '\n'.join(files) + '```'
            await interaction.followup.send(filelist, ephemeral=eph)

    @playb.command(name='lyrics', description='Shows the lyrics for ' \
    'the currently playing file, if present.')
    async def show_lyrics(self, interaction: discord.Interaction):
        try:
            v_chan = await get_voiceclient(self.client, 
                                                  interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("There's nothing " \
            "playing right now.")
            return
        print('{}Grabbing lyrics for {}{}{}'
              .format(style.ff_text, style.ff_file,
                      v_chan.source, style.reset))
        path = '.'.join(str(v_chan.source.filepath)
                        .replace('Music', 'Lyrics')
                        .split('.')[:-1])
        if os.path.exists(path + '.txt'): 
            file = path + '.txt'
        # I specifically want to prioritize .txt for caching purposes
        # As in, you toss the .lrc through the converter, dump that
        # result back into the appropriate .txt file, and use that
        # file from then on
        elif os.path.exists(path + '.lrc'):
            file = path + '.lrc'
        else:
            await interaction.response.send_message(
                '`{}` has no lyrics.'.format(v_chan.source))
            print('{}No lyrics found for {}{}{}'.format(
                style.ff_err, style.ff_file, 
                v_chan.source, style.reset))
            return
        await interaction.response.defer()
        if file.endswith('.lrc'):
            with open(file, 'r', encoding='utf-8') as lyricfile:
                lyrics = lyricfile.read()
            lyrics = await lrc_format(lyrics)
            file = file[:-4] + '.txt'
            with open(file, '+w', encoding='utf-8') as lyricfile:
                lyricfile.write(lyrics)
        await interaction.followup.send(file=discord.File(file))
        
    @playb.command(name='help', 
                      description='Defines how to write a playlist file.')
    async def playlist_help(self, interaction: discord.Interaction,
                            topic: Literal[
                                'playlist writing',
                                'play a file',
                                'play a folder',
                                'requesting songs',
                                'shuffle',
                                'volume',
                                'searching'
                                ]):
        print('{}Help called: {}{}{}'
              .format(style.ff_text, style.ff_file,
                      topic, style.reset))
        match topic:
            case 'playlist writing':
                content = 'Playlist files are defined as raw `.txt` ' \
                'files, with each line of the file being a path to ' \
                'a local file to play. You can add comments with //' \
                ', but playlists must end with `<eof>` on a new line.'
            
            case 'play a file':
                content = 'To play a file, pass it (including ' \
                'subfolder path, if applicable) to the play command. ' \
                "It\'ll be added to the queue, or start playing " \
                'if the queue is empty.'
            
            case 'play a folder':
                content = 'To play the contents of a folder, run ' \
                'the play command with the name of the folder ' \
                'instead of a file. The contents of the folder ' \
                'will automatically be added to the queue.'
            
            case 'requesting songs':
                content = 'To request a song, if the server has it ' \
                'enabled, just use the play command like you ' \
                'normally would, and the track will be added ' \
                'to the end of the queue.'
            
            case 'shuffle':
                content = 'The shuffle setting takes effect when you ' \
                'play a playlist, or a folder. Otherwise, you can ' \
                'manually shuffle the queue.'

            case 'volume':
                content = 'Volume adjustment is on a scale of 0.0 to ' \
                '1.0, representing a scale of 0% to 100%. This is ' \
                "because I'm silly and haven't implemented the " \
                'percentage scale yet.'
            
            case 'searching':
                content = 'Searching checks the music folder, the ' \
                "playlist folder, or the active queue. Case doesn't " \
                'matter, as whatever you type is turned lowercase for ' \
                'the check itself. When searching the music or ' \
                'playlist folders, the folder structure given for ' \
                'any file is exactly what you would pass to the ' \
                'commands.'
        await interaction.response.send_message(
            content, silent = True, ephemeral = eph)


    # Queue commands
    que = discord.app_commands.Group(
        name='queue',
        description='Commands that act on the queue.',
        parent=playb, guild_only=True)

    @que.command(name='shuffle',
                 description='Shuffles the contents of the queue.')
    @is_user_trusted()
    async def queue_shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            await interaction.followup.send('Failed to shuffle queue; ' \
            'not connected to a channel.')
            return
        shuffled_queue = sample(
            v_chan.queue[1:], len(v_chan.queue) - 1)
        shuffled_queue.insert(0, v_chan.queue[0])
        v_chan.queue = shuffled_queue
        print('{}Queue shuffled.{}'.format(
            style.ff_text, style.reset))
        await interaction.followup.send('Queue has been shuffled.')

    @que.command(name='move',
                 description='Moves an item in the queue.')
    @is_user_trusted()
    async def queue_move(self, interaction: discord.Interaction,
                         source:int, target:int):
        if interaction.user.voice is None:
            await interaction.response.send_message(
                'You need to be in a voice channel to' \
                'manipulate its queue.')
            return
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                "You can't move in a non-existent queue.")
            return
        await interaction.response.defer()
        try:
            moved_track:TrackWithMeta = v_chan.queue.pop(source)
            v_chan.queue.insert(
                -1 if len(v_chan.queue) < target else target,
                moved_track)
        except IndexError:
            await interaction.followup.send(
                'No track at {} to move.'.format(source))
        else:
            if target == -1:
                exp = 'the end'
            else:
                exp = str(target)
            await interaction.followup.send(
                'Moved `{}` from index {} to {}.'
                .format(moved_track, source, exp))
        print('{}Moved {}{}{} from {}{}{} to {}{}{}.{}'.format(
            style.ff_text, style.ff_file, moved_track, style.ff_text,
            style.ff_file, source, style.ff_text, style.ff_file,
            exp, style.ff_text, style.reset))

    @que.command(name='remove',
                 description='Removes an item from the queue.')
    @discord.app_commands.describe(
        index='The index of the track in the queue to remove.')
    @is_user_trusted()
    async def queue_remove(self, interaction: discord.Interaction,
                           index:int):
        if index < 0:
            await interaction.response.send_message(
                "There won't be anything at a negative index.")
            return
        elif index == 0:
            await interaction.response.send_message(
                "I think you're looking for `/music skip`.")
            return
        await interaction.response.defer()
        v_chan = await get_voiceclient(self.client, interaction.guild)
        if v_chan == None:
            await interaction.followup.send(
                "Can't remove an item from a queue that isn't real.")
        try:
            removed_track:TrackWithMeta = v_chan.queue.pop(index)
        except IndexError:
            await interaction.followup.send(
                'There is nothing at index {}.'.format(index))
        else:
            await interaction.followup.send(
                'Removed `{}` from the queue.'.format(removed_track))
            print('{}Removed {}{}{} from the queue.{}'.format(
                style.ff_text, style.ff_file, removed_track, 
                style.ff_text, style.reset))

    @que.command(name='list',description='List the contents of the queue.')
    async def queue_list(self,interaction: discord.Interaction):
        try:
            v_chan = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("Can't list the contents of a queue that isn't real.")
            return
        if len(v_chan.queue) <= 1:
            await interaction.response.send_message('The queue is empty.\nDid you mean `/music playing`?')
        else:
            await interaction.response.defer()
            print_queue = []
            queue_count = 1
            while queue_count != len(v_chan.queue):
                trackref:TrackWithMeta = v_chan.queue[queue_count]
                print_queue.append('{}. {}'.format(queue_count, trackref))
                queue_count += 1
            filelist = '\n'.join(print_queue)
            if len(filelist) > 1993:
                with open('{}/track_queue.txt'.format(froot), '+w', encoding='utf-8') as filefile:
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
            v_chan = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message("Can't clear an empty queue.")
            return
        if len(v_chan.queue) <= 1 and not active:
            await interaction.response.send_message("Can't clear an empty queue.")
            return
        elif len(v_chan.queue) <= 0 and active:
            await interaction.response.send_message("Can't clear an empty queue.")
            return
        await interaction.response.defer()
        temp_queue = v_chan.queue
        v_chan.queue = []
        v_chan.queue.append(temp_queue[0])
        print('{}Queue cleared.{}'.format(style.ff_text, style.reset))
        if active:
            v_chan.stop()
            await interaction.followup.send('Playback has been stopped, and the queue has been cleared.')
        else:
            await interaction.followup.send('The queue has been cleared.')

    @que.command(name='save',description='Saves the current queue to a ' \
    'file. Will not save current playtime.')
    @is_user_trusted()
    async def create_queue_playlist(self, interaction: discord.Interaction):
        try:
            v_chan: CosmicVoice = await get_voiceclient(self.client,interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                "Can't disconnect from nothing.", ephemeral=eph)
            return
        await interaction.response.defer()
        final = []
        for track in v_chan.queue:
            final.append(track.filepath + '\n')
        final.append('<eof>')
        with open('{}/Assets/Playlists/filth pile.txt'.format(froot), 
                  mode = '+w', encoding = 'utf-8') as magic:
            magic.writelines(final)
        await interaction.followup.send('Queue has been saved to ' \
        'playlist `filth pile`.', ephemeral=eph)
        print('{}Queue saved.{}'.format(style.ff_text, style.reset))


    # Playlist commands
    playlist = discord.app_commands.Group(
        name='playlist', description='Playlist commands.',
        parent=playb, guild_only=True)
    
    @playlist.command(name='play',
                      description='Plays the given playlist.')
    async def playlist_loopback(self, 
                                interaction: discord.Interaction, 
                                playlist:str):
        # I can't figure out how to get it to just use play_audio
        # so we have redundancy instead
        if interaction.user.voice is None:
            await interaction.response.send_message(
                'You need to be in a voice channel to play audio.')
            return
        try:
            v_chan = await get_voiceclient(
                self.client, interaction.guild)
        except MissingVoiceClientError:
            v_chan = await interaction.user.voice.channel.connect(
                cls=CosmicVoice)
        await interaction.response.defer()
        print('{}Attempting to load playlist {}{}{}'
              .format(style.ff_text, style.ff_file, 
                      playlist, style.reset))
        if not os.path.exists('{}/Assets/Playlists/{}.txt'.format(froot, playlist)):
            await interaction.followup.send('Playlist {} not found.'.format(playlist))
            print('{}Playlist {}{} not found.{}'
                  .format(style.ff_err, style.ff_file, 
                          playlist, style.ff_err, style.reset))
        else:
            if len(v_chan.queue) <= 0:
                new_tracks = True
            else:
                new_tracks = False
            audios = await read_playlist(playlist, interaction.guild)
            for src in audios:
                v_chan.add_track(src)
            if new_tracks:
                await interaction.followup.send(
                    'Now playing the contents of playlist `{}`.'
                    .format(playlist), ephemeral=eph)
            else:
                await interaction.followup.send(
                    'Added contents of playlist `{}` to queue.'
                    .format(playlist), ephemeral=eph)
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
                        if f.lower() == 'readme.txt':
                            pass
                        elif f.endswith('.txt'):
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
            if len(files) >= 1965:
                with open('{}/track_queue.txt'.format(froot), '+w', encoding='utf-8') as filefile:
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
    @discord.app_commands.describe(
        name='The name of the playlist to create.',
        subfolder = 'The subfolder to place the file in.',
        overwrite = "Whether it's okay to overwrite an existing " \
        'playlist.')
    async def create_playlist(self, interaction: discord.Interaction, 
                              name: str, subfolder: str = '',
                              overwrite: bool = False):
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
            
    @playlist.command(
            name='upload',
            description='Upload a file to the playlist folder.')
    @discord.app_commands.describe(file='The file to be uploaded.',
                                   subfolder='The subfolder to put the'
                                   ' file in. Defaults to none.')
    async def upload_playlist(self, interaction: discord.Interaction, 
                              file: discord.Attachment, subfolder: str = '', 
                              overwrite: bool = False):
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

    @playlist.command(name='add', 
                      description='Adds a track to the playlist.')
    @discord.app_commands.describe(playlist='The playlist to add to.',
                                   index='The track to add to the queue. ' \
                                   'Defaults to the current track.' \
                                   'Specify -1 to use a file path.',
                                   path='The file path to add. Ignored '\
                                   "if index isn't -1.")
    async def playlist_append(self, interaction: discord.Interaction, 
                              playlist: str,
                              path: str,
                              index: int = 0):
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            v_chan = None
        if playlist == 'filth pile':
            await interaction.response.send_message("Can't use reserved" \
            "playlist name `filth pile`.")
        with open('{}/Assets/Playlists/{}.txt'.format(froot, playlist),
                  mode='r', encoding='utf-8') as magic:
            audio = magic.readlines()
        if index > len(v_chan.queue):
            await interaction.response.send_message(
                'Index {} out of range.'.format(index))
        elif index == -1:
            if path == '':
                await interaction.response.send_message(
                    "No file path given.")
            else:
                audio.insert(-1, path)
                await interaction.response.send_message(
                    "Added `{}` to `{}`.".format(path, playlist))
        else:
            audio.insert(-1, v_chan.queue[index].filepath + '\n')


    # Config commands
    cfg = discord.app_commands.Group(
        name='config', description='Commands that change settings.',
        parent=playb, guild_only=True)

    @cfg.command(name='establish',
                 description='Generates the base configuration ' \
                 'file for a new server. WILL overwrite an existing '
                 'file if present.')
    @is_user_trusted()
    async def establish(self, interaction: discord.Interaction):
        json.create(interaction.guild, 'vw')
        await interaction.response.send_message(
            'Config file for `{}` created at `./Config/Guilds/{}.json`.'
            .format(interaction.guild.name,interaction.guild.id),
            ephemeral=eph)

    @cfg.command(name='volume',
                 description='Change the volume music plays at.')
    @discord.app_commands.describe(amount='The volume to set, with a ' \
    'range of 0.0 to 1.0. Leave this empty to show the current volume.')
    @is_user_trusted()
    async def volume(
        self, interaction: discord.Interaction,
        amount: discord.app_commands.Range[float, 0.0, 1.0] = 10.0):
        v_chan:CosmicVoice|None = None
        if amount == 10.0:
            current_volume = int(json.get_setting(
                interaction.guild,'volume','vw') * 100)
            await interaction.response.send_message(
                'Current volume is {}%.'.format(str(current_volume)))
            return
        json.change_setting(interaction.guild,'volume',amount,'vw')
        volume_percent = int(amount * 100)
        volume = str(volume_percent) + '%'
        await interaction.response.defer()
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            pass
        else:
            if v_chan.is_playing():
                v_chan.source.volume = amount
            if len(v_chan.queue) >= 2:
                for audio in v_chan.queue:
                    audio.volume = amount
        await interaction.followup.send(
            'Volume changed to {}.'.format(volume))

    @cfg.command(name='repeat',description='Set the repeat mode.')
    @is_user_trusted()
    async def repeat(self, interaction: discord.Interaction,
                     new_value:Literal['none','single','all','show']):
        if new_value == 'show':
            await interaction.response.send_message(
                'Repeat is currently set to "{}".'.format(
                    json.get_setting(interaction.guild,'repeat','vw')),
                    ephemeral=eph)
            return
        json.change_setting(interaction.guild,'repeat',new_value,'vw')
        if len(self.client.voice_clients) >= 0:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
            v_chan.repeat = new_value
        if new_value == 'none':
            val = 'disabled'
        else:
            val = 'set to {}'.format(new_value)
        await interaction.response.send_message('Repeat has been {}.'
                                                .format(val), 
                                                ephemeral=eph)

    @cfg.command(name='clear_cache', 
                 description='Clears the YouTube file cache.')
    @is_user_trusted()
    async def clear_cache(self, interaction: discord.Interaction):
        await interaction.response.defer()
        file_list = await get_folder_contents('YouTube', 'mp3')
        for file in file_list:
            os.remove(file)
        await interaction.followup.send('Cache has been cleared.')
    
    @cfg.command(
            name='setdj',
            description='Sets which role is considered as the "DJ" role.')
    @discord.app_commands.describe(roleid='The ID of the new DJ role.')
    @is_user_trusted()
    async def dj(self, interaction: discord.Interaction, roleid:int):
        json.change_setting(interaction.guild,'dj',roleid,'vw')
        if roleid != 0:
            await interaction.response.send_message(
                'The role `{}` has been set as the DJ role.'
                .format(interaction.guild.get_role(roleid).name),
                ephemeral=eph)
        else:
            await interaction.response.send_message(
                'The DJ role has been cleared.', ephemeral=eph)

    @cfg.command(name='shuffle',
                 description='Toggle shuffle on or off.')
    @is_user_trusted()
    async def shuffle(self, interaction: discord.Interaction,
                      new_value:bool):
        json.change_setting(interaction.guild,'shuffle',new_value,'vw')
        if new_value:
            val = 'enabled'
        else:
            val = 'disabled'
        await interaction.response.send_message(
            'Shuffle has been {}.'.format(val))
        print('{}Shuffle has been {}.{}'
              .format(style.ff_text, val, style.reset))


    # Search commands
    srk = discord.app_commands.Group(
        name='search',
        description='Commands to search places.', 
        parent=playb, guild_only=True)
    
    @srk.command(name='music', 
                 description='Search for a file in the music folder.')
    async def folder_search(self, interaction: discord.Interaction, 
                            search: str):
        if search == '':
            print("{}Folder search called; {}empty.{}"
                  .format(style.ff_text, style.ff_err, style.reset))
            await interaction.response.send_message("No search " \
            "string specified.")
            return
        print("{}Folder search called: {}{}{}"
              .format(style.ff_text, style.ff_file, 
                      search, style.reset))
        await interaction.response.defer()
        files = await get_string_from_folder('Music', search)
        if len(files) == 0:
            numcol = style.ff_err
        else:
            numcol = style.ff_file
        print("{}{}{} hits.{}"
              .format(numcol, len(files),
                      style.ff_text, style.reset))
        if len(files) == 0:
            await interaction.followup.send(
                "Couldn't find {} in music.".format(search))
            return
        result = '\n'.join(files)
        if len(result) > 1993:
            with open('{}/filesearch.txt'.format(froot), '+w',
                      encoding='utf-8') as searchdrop:
                searchdrop.write(result)
            await interaction.followup.send(file=discord.File(
                '{}/filesearch.txt'.format(froot)))
            await asyncio.sleep(5)
            os.remove('{}/filesearch.txt')
            return
        await interaction.followup.send("```\n{}```".format(result))

    @srk.command(name='playlist', 
                 description='Search for a playlist.')
    async def playlist_search(self, interaction: discord.Interaction,
                              search: str):
        if search == '':
            print("{}Playlist search called; {}empty.{}"
                  .format(style.ff_text, style.ff_err, style.reset))
            await interaction.response.send_message("No search " \
            "string specified.")
            return
        print("{}Playlist search called: {}{}{}"
              .format(style.ff_text, style.ff_file,
                      search, style.reset))
        await interaction.response.defer()
        files = await get_string_from_folder('Playlists', search)
        for file in files:
            file.replace('.txt', '')
        if len(files) == 0:
            numcol = style.ff_err
        else:
            numcol = style.ff_file
        print("{}{}{} hits.{}"
              .format(numcol, len(files), style.ff_text, style.reset))
        if len(files) == 0:
            await interaction.followup.send(
                "Couldn't find {} in playlists.".format(search))
            return
        result = '\n'.join(files)
        if len(result) > 1993:
            with open('{}/playlistsearch.txt'.format(froot), '+w',
                      encoding='utf-8') as searchdrop:
                searchdrop.write(result)
            await interaction.followup.send(file=discord.File(
                '{}/playlistsearch.txt'.format(froot)))
            await asyncio.sleep(5)
            os.remove('{}/playlistsearch.txt')
            return
        await interaction.followup.send("```\n{}```".format(result))

    @srk.command(name='queue', 
                 description='Search for a track in the queue.')
    async def queue_search(self, interaction: discord.Interaction,
                           search: str):
        try:
            v_chan = await get_voiceclient(self.client,
                                           interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message(
                'No queue active.')
        else:
            if len(v_chan.queue) == 0:
                await interaction.response.send_message(
                    'No queue active.')
        if search == '':
            print("{}Queue search called; {}empty.{}"
                  .format(style.ff_text, style.ff_err, style.reset))
            await interaction.response.send_message("No search " \
            "string specified.")
            return
        print("{}Queue search called: {}{}{}"
              .format(style.ff_text, style.ff_file,
                      search, style.reset))
        await interaction.response.defer()
        files = []
        for track in v_chan.queue:
            if search.strip().lower() in track.lower():
                files.append("{}. {}".format(
                    v_chan.queue.index(track), track))
        if len(files) == 0:
            numcol = style.ff_err
        else:
            numcol = style.ff_file
        print("{}{}{} hits.{}"
              .format(numcol, len(files),
                      style.ff_text, style.reset))
        if len(files) == 0:
            await interaction.followup.send(
                "Couldn't find {} in the queue.".format(search))
            return
        result = '\n'.join(files)
        if len(result) > 1993:
            with open('{}/queuesearch.txt'.format(froot), '+w',
                      encoding='utf-8') as searchdrop:
                searchdrop.write(result)
            await interaction.followup.send(file=discord.File(
                '{}/queuesearch.txt'.format(froot)))
            await asyncio.sleep(5)
            os.remove('{}/queuesearch.txt')
            return
        await interaction.followup.send("```\n{}```".format(result))

async def setup(client:commands.Bot):
    load_opus_if_enabled(settings['voicework']['group_enabled'])
    await client.add_cog(VoiceWork(client))
    print('{}VoiceWork loaded.{}'.format(style.ff_text,style.reset))

async def teardown(client:commands.Bot):
    for voic in client.voice_clients:
        if not isinstance(voic, CosmicVoice):
            pass
        else:
            await voic.disconnect()
    print('{}VoiceWork unloaded.{}'.format(style.ff_text,style.reset))