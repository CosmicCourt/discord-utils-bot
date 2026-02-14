"""All the VoiceWork sections."""
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
import re
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
# // This section copied from https://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside
def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]
# //

def be_mean():
    meancount = randrange(0,len(meanstrings) - 1)
    return meanstrings[meancount]

class MissingVoiceClientError(Exception):
    def __init__(self, message):
        self.message = '{} - {}'.format(message, self.__context__)
        super().__init__(self.message)

class IncorrectAudioSourceError(Exception):
    def __init__(self, message):
        self.message = '{} - {}'.format(message, self.__context__)
        super().__init__(self.message)

def reconstruct_as(source:TrackWithMeta):
    # We're looking for the volume, trackname, trackartist, filename, hours, minutes, seconds, and filepath. We can steal all these from the existing one, we just need to rebuild this to fix things. Hopefully.
    hell_track = discord.FFmpegPCMAudio(source.filepath)
    new_track = TrackWithMeta(hell_track, source.volume, source.trackname, source.trackartist, source.filename, source.hours, source.minutes, source.seconds, source.filepath)
    return new_track


class TrackWithMeta(discord.PCMVolumeTransformer):
    def __init__(self, original, volume: float = 1.0, trackname:str = 'UNTAGGED', trackartist:str = 'UNTAGGED', filename:str = 'UNSET', hours:int = 0, minutes:int = 0, seconds:int = 0, filepath:str = 'EMPTY'):
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
        self.filepath = filepath
        if self.filepath == 'EMPTY':
            raise discord.ClientException('TrackWithMeta requires a valid file path.')
        self.time_passed: int = 0
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
    
    def read(self) -> bytes:
        self.time_passed += 20
        return super().read()
    
    def get_track_length(self):
        self.track_hours = int(self.hours)
        self.track_minutes = int(self.minutes)
        self.track_seconds = int(self.seconds)
        if len(str(self.track_hours)) == 1:
            self.track_hours = '0{}'.format(str(self.hours))
        if len(str(self.track_minutes)) == 1:
            self.track_minutes = '0{}'.format(str(self.minutes))
        if len(str(self.track_seconds)) == 1:
            self.track_seconds = '0{}'.format(str(self.seconds))
        return self.track_hours, self.track_minutes, self.track_seconds

    def get_time_elapsed(self):
        self.time_played = self.time_passed / 1000
        self.hours_played = int(self.time_played // 3600)
        self.time_played %= 3600
        self.minutes_played = int(self.time_played // 60)
        self.time_played %= 60
        self.seconds_played = int(self.time_played)
        if len(str(self.hours_played)) == 1:
            self.hours_played = '0{}'.format(str(self.hours_played))
        if len(str(self.seconds_played)) == 1:
            self.minutes_played = '0{}'.format(str(self.minutes_played))
        if len(str(self.seconds_played)) == 1:
            self.seconds_played = '0{}'.format(str(self.seconds_played))
        return self.hours_played, self.minutes_played, self.seconds_played
    
    def get_time_to_end(self):
        self.time_in_seconds = (self.hours * 60) + (self.minutes * 60) + self.seconds
        self.time_played = self.time_passed / 1000 # / 100 to get 1 second's worth
        self.time_in_seconds -= self.time_played
        self.hours_left = int(self.time_in_seconds // 3600)
        self.time_in_seconds %= 3600
        self.minutes_left = int(self.time_in_seconds // 60)
        self.time_in_seconds %= 60
        self.seconds_left = int(self.time_in_seconds) + 1
        if len(str(self.hours_left)) == 1:
            self.hours_left = '0{}'.format(str(self.hours_left))
        if len(str(self.minutes_left)) == 1:
            self.minutes_left = '0{}'.format(str(self.minutes_left))
        if len(str(self.seconds_left)) == 1:
            self.seconds_left = '0{}'.format(str(self.seconds_left))
        return self.hours_left, self.minutes_left, self.seconds_left

async def get_muta_data(mutafile):
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

async def get_muta_duration(mutafile):
    length = mutafile.info.length
    hours = length // 3600
    length %= 3600
    minutes = length // 60
    length %= 60
    seconds = length
    return int(hours), int(minutes), int(seconds)        

def is_user_trusted():
    async def predicate(interaction:discord.Interaction) -> bool:
        trusted = False
        dj_role = False
        bot_owner = False
        if interaction.user.id in settings['users']['trusted']:
            trusted = True
        if interaction.guild.get_role(json.get_setting(interaction.guild, 'dj','vw')) in interaction.user.roles:
            dj_role = True
        if interaction.user.id == settings['client']['bot_owner']:
            bot_owner = True
        if trusted or dj_role or bot_owner:
            return True
        else:
            return False
    return discord.app_commands.check(predicate)

async def get_voiceclient(client:discord.Client, guild:discord.Guild|None):
    if guild == None:
        raise discord.ClientException('Invalid guild passed to get_voiceclient')
    voice_channel:CustomVoiceClient|None = None
    for voic in client.voice_clients:
        if voic.guild.id != guild.id:
            pass
        else:
            if not type(voic) == CustomVoiceClient:
                raise MissingVoiceClientError('Current guild does not have a CustomVoiceClient.')
            voice_channel = voic
    if voice_channel == None:
        raise MissingVoiceClientError('Current guild does not have a CustomVoiceClient.')
    else:
        return voice_channel

if os.name == 'nt':
    libopus = './Assets/Libraries/libopus/libopus.dll'
else:
    libopus = './Assets/Libraries/libopus/libopus.so'

async def juggle_pathsep(string):
    filelist = []
    if os.name == 'nt':
        for letter in string:
            if letter == '/':
                filelist.append('\\')
            else:
                filelist.append(letter)
    else:
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
            print('No need to load Opus; we\'re on Windows and it\'s already loaded; file a bug report if this is not the case')
            return True
    else:
        return False
    
class CustomVoiceClient(discord.VoiceClient):
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

    def track_finished_single(self, error):
        test = self.queue.pop(0)
        if not self.stop_it_skip:
            new_source = reconstruct_as(test)
            self.queue.insert(0, new_source)
        else:
            self.stop_it_skip = False
        self.play(self.queue[0], after=self.check_repeat)
        
    def track_finished_all(self, error):
        track = self.queue.pop(0)
        new_source = reconstruct_as(track)
        self.queue.append(new_source)
        self.play(self.queue[0], after=self.check_repeat)

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
                    raise discord.ClientException('self.repeat is set to "show"')
        else:
            return

    def add_track(self, track: discord.AudioSource):
        self.queue.append(track)
        if len(self.queue) == 1:
            self.play(self.queue[0], after=self.check_repeat)

    def skip_track(self):
        self.stop()

class VoiceWork(commands.Cog, name='VoiceWork'):
    group = discord.app_commands.Group(name='music',description='Music-related commands.')
    
    def __init__(self, client) -> None:
        self.client:discord.Client = client

    @group.command(name='repeat',description='Set the repeat mode.')
    async def repeat(self, interaction:discord.Interaction, new_value:Literal['none','single','all','show']):
        if new_value == 'show':
            await interaction.response.send_message('Repeat is currently set to "{}".'.format(json.get_setting(interaction.guild,'repeat','vw')))
            return
        json.change_setting(interaction.guild,'repeat',new_value,'vw')
        if len(self.client.voice_clients) >= 0:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
            voice_channel.repeat = new_value
        await interaction.response.send_message('Repeat has been disabled.' if new_value == 'none' else 'Repeat has been set to {}.'.format(new_value))

    @group.command(name='shuffle',description='Shuffles the contents of the queue.')
    @is_user_trusted()
    async def queue_shuffle(self, interaction:discord.Interaction):
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

    @group.command(name='connect',description='Connects the bot to your current voice channel.')
    async def voice_connect(self, interaction:discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message("You need to be in a voice channel to connect.",ephemeral=True)
        else:
            await interaction.response.defer()
            voice_channel:CustomVoiceClient = await interaction.user.voice.channel.connect(cls=CustomVoiceClient)
            voice_channel.repeat = json.get_setting(interaction.guild,'repeat','vw')
            await interaction.followup.send("Joined `{}` successfully.".format(interaction.user.voice.channel.name))
        
    @group.command(name='disconnect',description='Disconnects from the current voice channel.')
    @is_user_trusted()
    async def voice_disconnect(self, interaction:discord.Interaction):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if interaction.user.voice is None:
            await interaction.response.send_message('You can\'t disconnect from a channel without being in the channel.', ephemeral=True)
            return
        try:
            voice_channel:CustomVoiceClient = await get_voiceclient(self.client,interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message('Can\'t disconnect from nothing.', ephemeral=True)
            return
        if interaction.user.voice.channel.id != voice_channel.channel.id:
            await interaction.response.send_message('You can\'t disconnect from a channel without being in the channel.', ephemeral=True)
            return
        channel_name = voice_channel.channel.name
        await voice_channel.disconnect()
        await interaction.response.send_message('Disconnected from `{}`.'.format(channel_name))

    @group.command(name='play',description='Plays an audio file with the given name. Loaded from ./Assets/Music')
    @discord.app_commands.describe(source='Where the file comes from; the Assets/Music folder, or a web link.',filepath='The name of the file to play.')
    async def play_audio(self, interaction:discord.Interaction,source:Literal["local","online"],filepath:str):
        if interaction.user.id not in settings['users']['trusted']:
            await interaction.response.send_message(be_mean())
            return
        if interaction.user.voice is None:
            await interaction.response.send_message("You need to be in a voice channel to play audio.")
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            voice_channel = await interaction.user.voice.channel.connect(cls=CustomVoiceClient)
        if source == 'online':
            await interaction.response.send_message('How about you go to hell?', ephemeral=True)
            return
        await interaction.response.defer()
        if source == 'local':
            if not os.path.exists('./Assets/Music/{}'.format(filepath)):
                await interaction.followup.send('File at `./Assets/Music/{}` not found.'.format(filepath))
                return
            filepath = await juggle_pathsep(filepath)
            le_sound = discord.FFmpegPCMAudio('./Assets/Music/{}'.format(filepath))
            mutagen_ref = mutagen.File('./Assets/Music/{}'.format(filepath))
            track_name, track_artist = await get_muta_data(mutagen_ref)
            track_hour, track_minute, track_second = await get_muta_duration(mutagen_ref)
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
        audio_file = TrackWithMeta(le_sound,json.get_setting(interaction.guild, 'volume','vw'), track_name, track_artist, file_name, track_hour, track_minute, track_second, './Assets/Music/{}'.format(filepath)) 
        voice_channel.add_track(audio_file)
        file_identifier = '{} - {}'.format(audio_file.trackname, audio_file.trackartist) if audio_file.trackname != 'UNTAGGED' and audio_file.trackname != 'UNTAGGED' else '{}'.format(audio_file.filename)
        if len(voice_channel.queue) >= 2:
            await interaction.followup.send('Added to queue: `{}`'.format(file_identifier))
        else:
            await interaction.followup.send('Now playing: `{}`'.format(file_identifier))

    @group.command(name='setdj',description='Sets which role is considered as the "DJ" role (has access to the playback commands).')
    @discord.app_commands.describe(roleid='The ID of the new DJ role.')
    async def dj(self, interaction:discord.Interaction, roleid:int):
        json.change_setting(interaction.guild,'dj',roleid,'vw')
        if roleid != 0:
            await interaction.response.send_message('The role `{}` has been set as the DJ role.'.format(interaction.guild.get_role(roleid).name),ephemeral=True)
        else:
            await interaction.response.send_message('The DJ role has been cleared.',ephemeral=True)

    @group.command(name='resume',description='Resumes the paused track.')
    @is_user_trusted()
    async def unpause_track(self, interaction:discord.Interaction):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
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
    async def pause_track(self, interaction:discord.Interaction):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message('Can\'t pause if nothing\'s playing.')
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
        if interaction.user.voice is None:
            await interaction.response.send_message("You need to be in a voice channel to skip audio.")
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message('Can\'t skip if nothing\'s playing.')
            return
        if voice_channel.is_playing() or voice_channel.is_paused():
            await interaction.response.defer()
            if not type(voice_channel.source) == TrackWithMeta:
                raise IncorrectAudioSourceError('Given AudioSource is not a TrackWithMeta AudioSource')
            skipped_track:TrackWithMeta = voice_channel.source
            voice_channel.stop_it_skip = True
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
            await interaction.response.send_message('You need to be in a voice channel to stop its audio.')
            return
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message('You can\'t stop nothing.')
            return
        voice_channel.stop_it = True
        temp_track = voice_channel.source
        voice_channel.queue = [temp_track]
        voice_channel.stop()
        await interaction.response.send_message('Stopped playing audio.')
        voice_channel.stop_it = False
    
    @group.command(name='remove',description='Removes an item from the queue.')
    @discord.app_commands.describe(index='The index of the track in the queue to remove.')
    @is_user_trusted()
    async def queue_remove(self, interaction:discord.Interaction, index:int):
        if index < 0:
            await interaction.response.send_message('There won\'t be anything at a negative index. If you\'re trying to clear the queue, there\'s a command specifically to do that.')
            return
        elif index == 0:
            await interaction.response.send_message('I think you\'re looking for `/music skip`.')
            return
        await interaction.response.defer()
        voice_channel = await get_voiceclient(self.client, interaction.guild)
        if voice_channel == None:
            await interaction.followup.send('Can\'t remove an item from a queue that isn\'t real.')
        try:
            removed_track:TrackWithMeta = voice_channel.queue.pop(index)
        except IndexError:
            await interaction.followup.send('There is nothing in the queue at the index {}.'.format(index))
        else:
            await interaction.followup.send('Removed `{}` from the queue, from index {}.'.format('{} - {}'.format(removed_track.trackname,removed_track.trackartist) if removed_track.trackname != 'UNTAGGED' and removed_track.trackartist != 'UNTAGGED' else '{}'.format(removed_track.filename), index))

    @group.command(name='playing',description='Show the status of the currently playing track.')
    async def now_playing(self, interaction:discord.Interaction):
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
        if type(trackref) != TrackWithMeta:
            raise IncorrectAudioSourceError('Now Playing expected TrackWithMeta')
        current_name = '{}'.format('{}'.format(trackref.filename) if trackref.trackname == 'UNTAGGED' and trackref.trackartist == 'UNTAGGED' else '{} - {}'.format(trackref.trackname, trackref.trackartist))
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

    @group.command(name='queue',description='List the contents of the queue.')
    @is_user_trusted()
    async def queue_list(self,interaction:discord.Interaction):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message('Can\'t list the contents of a queue that isn\'t real.')
            return
        if len(voice_channel.queue) <= 1:
            await interaction.response.send_message('The queue is empty.\nDid you mean `/music playing`?')
        else:
            await interaction.response.defer()
            print_queue = []
            queue_count = 1
            while queue_count != len(voice_channel.queue):
                trackref:TrackWithMeta = voice_channel.queue[queue_count]
                print_queue.append('{}. {}'.format(queue_count, trackref.filename if trackref.trackname == 'UNTAGGED' and trackref.trackartist == 'UNTAGGED' else '{} - {}'.format(trackref.trackname, trackref.trackartist)))
                queue_count += 1
            filelist = '\n'.join(print_queue)
            if len(filelist) > 1993:
                with open('./track_queue.txt', '+w') as filefile:
                    filefile.write(filelist)
                await interaction.followup.send(file=discord.File('./track_queue.txt'))
                await asyncio.sleep(5)
                os.remove('./track_queue.txt')
            else:
                filelist = '```\n' + '\n'.join(print_queue) + '```'
                await interaction.followup.send(filelist, ephemeral=True)
        
    @group.command(name='shuffle_toggle',description='Toggle shuffle on or off.')
    async def shuffle(self, interaction:discord.Interaction, new_value:bool):
        json.change_setting(interaction.guild,'shuffle',new_value,'vw')
        await interaction.response.send_message('Shuffle has been turned {}.'.format('on' if new_value else 'off'))

    @group.command(name='clear',description='Clears the active queue.')
    @discord.app_commands.describe(active='Whether to stop the currently playing track, too.')
    @is_user_trusted()
    async def clear(self, interaction:discord.Interaction, active:bool):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            await interaction.response.send_message('Can\'t clear an empty queue.')
            return
        if len(voice_channel.queue) <= 1 and not active:
            await interaction.response.send_message('Can\'t clear an empty queue.')
            return
        elif len(voice_channel.queue) <= 0 and active:
            await interaction.response.send_message('Can\'t clear an empty queue.')
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

    @group.command(name='folder',description='Plays the contents of a folder, in random or file order, skipping files with unknown extensions.')
    @discord.app_commands.describe(folder='The folder to play the contents of.', order='The order to play the files in. If set to \'default\', respects the shuffle setting.')
    @is_user_trusted()
    async def folder(self,interaction:discord.Interaction,folder:str,order:Literal['random','normal','default']):
        try:
            voice_channel = await get_voiceclient(self.client, interaction.guild)
        except MissingVoiceClientError:
            if interaction.user.voice != None:
                voice_channel = await interaction.user.voice.channel.connect(cls=CustomVoiceClient)
            else:
                await interaction.response.send_message('You need to be in a voice channel to play audio.')
                return
        if order == 'default':
            order = 'normal' if not json.get_setting(interaction.guild,'shuffle','vw') else 'random'
        if folder == '':
            await interaction.response.send_message('Nothing to play.')
            return
        if folder.startswith(('http', 'ftp')):
            source = 'online'
        else:
            source = 'local'
        await interaction.response.defer()
        if source == 'local':
            file_list = []
            temp_queue = []
            for (root, dirs, file) in os.walk('./Assets/Music/{}'.format(folder),topdown=True):
                dirs[:] = []
                for f in file:
                    if not f.endswith(('mp3','mp4','wav','flac','ogg','opus','aac','wma','wmv','mkv','ac3','mp2','m4a','m4r')):
                        pass
                    else:
                        file_list.append(f)
            file_list.sort(key=natural_keys)
            for file in file_list:
                thingpath = './Assets/Music/{}/{}'.format(folder,file)
                thingpath = await juggle_pathsep(thingpath)
                mutaref = mutagen.File(thingpath)
                track_name, artist_name = await get_muta_data(mutaref)
                track_hour, track_minute, track_second = await get_muta_duration(mutaref)
                file_pat = thingpath.split(os.pathsep)[-1]
                filename = "".join(file_pat)
                fourletter = ['mp3', 'wav', 'ogg', 'm4a', 'm4r', 'aac', 'ac3', 'mp2', 'wma', 'mov', 'wmv', 'mp4', 'mkv']
                fiveletter = ['opus', 'flac']
                if filename.endswith(tuple(fiveletter)):
                    file_name = filename[:-5]
                elif filename.endswith(tuple(fourletter)):
                    file_name = filename[:-4]
                else:
                    file_name = filename
                temp_source_main = discord.FFmpegPCMAudio(thingpath)
                temp_source = TrackWithMeta(temp_source_main,json.get_setting(interaction.guild,'volume','vw'),track_name,artist_name,file_name,track_hour,track_minute,track_second,thingpath)
                temp_queue.append(temp_source)
            if order == 'random':
                new_queue = sample(temp_queue,len(temp_queue))
            else:
                new_queue = temp_queue
            voice_channel.add_track(new_queue[0])
            for track in new_queue[1:]:
                voice_channel.queue.append(track)
            await interaction.followup.send('The contents of {} have been added to the queue.'.format(folder.split(os.sep)[:-1]))



    @group.command(name='establish',description='Generates the base configuration file for a new server. WILL OVERWRITE AN EXISTING FILE.')
    async def establish(self, interaction:discord.Interaction):
        json.create(interaction.guild, 'vw')
        await interaction.response.send_message('Config file for {} created at `./Config/Guilds/{}.json`.'.format(interaction.guild.name,interaction.guild.id),ephemeral=True)

    @group.command(name='volume',description='Change the volume music plays at.')
    @discord.app_commands.describe(amount='The volume to set, with a range of 0.0 to 1.0 (representing 0 - 100%). Leave this empty to show the current volume.')
    @is_user_trusted()
    async def volume(self, interaction:discord.Interaction, amount:discord.app_commands.Range[float, 0.0, 1.0] = 10.0):
        voice_channel:CustomVoiceClient|None = None
        if amount == 10.0:
            current_volume = int(json.get_setting(interaction.guild,'volume','vw') * 100)
            await interaction.response.send_message('Current volume is {}.'.format(str(current_volume) + '%'))
            return
        json.change_setting(interaction.guild,'volume',amount,'vw')
        volume_percent = int(amount * 100)
        volume = str(volume_percent) + "%"
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
            

    @group.command(name='list',description='Lists audio files available to be played.')
    @discord.app_commands.describe(subdir='The subdirectory to check, if empty, only checks the main folder.')
    @is_user_trusted()
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
        if not type(voic) == CustomVoiceClient:
            pass
        else:
            await voic.disconnect()