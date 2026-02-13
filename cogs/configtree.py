import jsman as json
import discord
import enum
import tomllib
from discord.ext import commands
from typing import Literal

def load_toml() -> dict:
    with open('./Config/config.toml', 'rb') as configfile:
        settings:dict = tomllib.load(configfile)
    return settings
    # ['users']['trusted']: List, user IDs in the whitelist
    
settings = load_toml()

class Configuration(commands.Cog):
    group = discord.app_commands.Group(name='config',description='The server-side config options.')

    def __init__(self, client) -> None:
        self.client:discord.Client = client

    async def interaction_check(self, interaction:discord.Interaction) -> bool:
        return interaction.user.id in settings['users']['trusted']

    @group.command(name='establish',description='Generates the base configuration file for a new server. WILL OVERWRITE AN EXISTING FILE.')
    async def establish(self, interaction:discord.Interaction):
        json.create(interaction.guild)
        await interaction.response.send_message('Config file for {} created at `./Config/Guilds/{}.json`.'.format(interaction.guild.name,interaction.guild.id),ephemeral=True)

    @group.command(name='volume',description='Change the volume music plays at.')
    async def volume(self, interaction:discord.Interaction, amount:discord.app_commands.Range[float, 0.0, 1.0]):
        json.change_setting(interaction.guild,'volume',amount)
        volume_percent = int(amount * 100)
        volume = str(volume_percent) + "%"
        await interaction.response.send_message('Volume changed to {}.'.format(volume))

    @group.command(name='setdj',description='Sets which role is considered as the "DJ" role (has access to the playback commands).')
    @discord.app_commands.describe(roleid='The ID of the new DJ role.')
    async def dj(self, interaction:discord.Interaction, roleid:int):
        json.change_setting(interaction.guild,'dj',roleid)
        if roleid != 0:
            await interaction.response.send_message('The role `{}` has been set as the DJ role.'.format(interaction.guild.get_role(roleid).name),ephemeral=True)
        else:
            await interaction.response.send_message('The DJ role has been cleared.',ephemeral=True)

    @group.command(name='repeat',description='Set the repeat mode.')
    async def repeat(self, interaction:discord.Interaction, new_value:Literal['none','single','all']):
        json.change_setting(interaction.guild,'repeat',new_value)
        await interaction.response.send_message('Repeat has been disabled.' if new_value == 'none' else 'Repeat has been set to {}.'.format(new_value))

    @group.command(name='shuffle',description='Toggle shuffle on or off.')
    async def shuffle(self, interaction:discord.Interaction, new_value:bool):
        json.change_setting(interaction.guild,'shuffle',new_value)
        if new_value == True:
            shufflemessage = 'on'
        else:
            shufflemessage = 'off'
        await interaction.response.send_message('Shuffle has been turned {}.'.format('on' if new_value else 'off'))

async def setup(client:commands.Bot):
    await client.add_cog(Configuration(client))