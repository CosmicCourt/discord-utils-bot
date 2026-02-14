import json
import os
import discord

json_template_vw = {'volume': 1.0, 'repeat': 'none', 'shuffle': False, 'dj': 0}
# repeat = one of: 'none', 'single', 'all'

def load(guild:discord.Guild,destination:str):
    match destination:
        case 'vw':
            if not os.path.exists('./Config/Guilds/VoiceWork/{}.json'.format(guild.id)):
                raise FileNotFoundError('Guild {} has no config file'.format(guild.name))
            else:
                with open('./Config/Guilds/VoiceWork/{}.json'.format(guild.id), 'r') as jsonfile:
                    settings = json.load(jsonfile)
                return settings
        case _:
            if not os.path.exists('./Config/Guilds/{}.json'.format(guild.id)):
                raise FileNotFoundError('Guild {} calling improperly; please specify destination')
            else:
                with open('./Config/Guilds/{}.json'.format(guild.id), 'r') as jsonfile:
                    settings = json.load(jsonfile)
                return settings

def change_setting(guild:discord.Guild|None,setting:str,value, destination:str):
    if guild == None:
        raise Exception('Go to hell.')
    settings = load(guild,destination)
    settings[setting] = value
    save(guild,settings,destination)

def get_setting(guild:discord.Guild|None,setting:str, destination:str):
    if guild == None:
        raise Exception('Are you stupid or something?')
    settings = load(guild, destination)
    return settings[setting]

def create(guild:discord.Guild|None, template:str):
    if guild == None:
        raise Exception('You should be shot')
    if not os.path.exists('./Config/Guilds'):
        os.mkdir('./Config/Guilds')
    match template:
        case 'vw':
            if not os.path.exists('./Config/Guilds/VoiceWork'):
                os.mkdir('./Config/Guilds/VoiceWork')
            with open('./Config/Guilds/VoiceWork/{}.json'.format(guild.id), 'w+') as jsonfile:
                json.dump(json_template_vw, jsonfile, indent=4)
        case _:
            raise Exception("Nah, no, hell no, not in here.")


def save(guild:discord.Guild,newjson:dict,destination:str):
    match destination:
        case 'vw':
            if not os.path.exists('./Config/Guilds/VoiceWork/{}.json'.format(guild.id)):
                raise FileNotFoundError('Guild {} has no config file'.format(guild.name))
            else:
                with open('./Config/Guilds/VoiceWork/{}.json'.format(guild.id), 'r') as jsonfile:
                    if jsonfile.read() == '':
                        raise ValueError('Guild {} has no config data'.format(guild.name))
                    else:
                        with open('./Config/Guilds/VoiceWork/{}.json'.format(guild.id), 'w+') as jsonfile:
                            json.dump(newjson, jsonfile, indent=4)
        case _:
            raise Exception("Absolutely not, go fuck yourself.")

if __name__ == '__main__':
    print('What the hell is wrong with you?')
    quit(0)