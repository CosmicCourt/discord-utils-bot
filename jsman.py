import json
import os
import discord

json_template = {'volume': 1.0, 'repeat': 'none', 'shuffle': False, 'dj': 0}
# repeat = one of: 'none', 'single', 'all'

class TempGuild:
    def __init__(self, name, id):
        self.name = name
        self.id = id

def load(guild:discord.Guild|TempGuild):
    if not os.path.exists('./Config/Guilds/{}.json'.format(guild.id)):
        raise FileNotFoundError('Guild {} has no config file'.format(guild.name))
    else:
        with open('./Config/Guilds/{}.json'.format(guild.id), 'r') as jsonfile:
            settings = json.load(jsonfile)
        return settings

def change_setting(guild:discord.Guild|None,setting:str,value):
    if guild == None:
        raise Exception('Go to hell.')
    settings = load(guild)
    settings[setting] = value
    save(guild,settings)

def get_setting(guild:discord.Guild|TempGuild|None,setting:str):
    if guild == None:
        raise Exception('Are you stupid or something?')
    settings = load(guild)
    return settings[setting]

def create(guild:discord.Guild|None = None):
    if guild == None:
        raise Exception('You should be shot')
    if not os.path.exists('./Config/Guilds'):
        os.mkdir('./Config/Guilds')
    with open('./Config/Guilds/{}.json'.format(guild.id), 'w+') as jsonfile:
        json.dump(json_template, jsonfile, indent=4)


def save(guild:discord.Guild,newjson:dict):
    if not os.path.exists('./Config/Guilds/{}.json'.format(guild.id)):
        raise FileNotFoundError('Guild {} has no config file'.format(guild.name))
    else:
        with open('./Config/Guilds/{}.json'.format(guild.id), 'r') as jsonfile:
            if jsonfile.read() == '':
                raise ValueError('Guild {} has no config data'.format(guild.name))
            else:
                with open('./Config/Guilds/{}.json'.format(guild.id), 'w+') as jsonfile:
                    json.dump(newjson, jsonfile, indent=4)

if __name__ == '__main__':
    print('What the hell is wrong with you?')
    quit(0)