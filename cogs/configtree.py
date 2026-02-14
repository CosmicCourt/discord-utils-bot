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

    async def interaction_check(self, interaction:discord.Interaction) -> bool: # pyright: ignore[reportIncompatibleMethodOverride]
        return interaction.user.id in settings['users']['trusted']

    @group.command(name='establish',description='Generates the base configuration file for a new server. WILL OVERWRITE AN EXISTING FILE.')
    async def establish(self, interaction:discord.Interaction):
        json.create(interaction.guild)
        await interaction.response.send_message('Config file for {} created at `./Config/Guilds/{}.json`.'.format(interaction.guild.name,interaction.guild.id),ephemeral=True)

    @group.command(name='setdj',description='Sets which role is considered as the "DJ" role (has access to the playback commands).')
    @discord.app_commands.describe(roleid='The ID of the new DJ role.')
    async def dj(self, interaction:discord.Interaction, roleid:int):
        json.change_setting(interaction.guild,'dj',roleid)
        if roleid != 0:
            await interaction.response.send_message('The role `{}` has been set as the DJ role.'.format(interaction.guild.get_role(roleid).name),ephemeral=True)
        else:
            await interaction.response.send_message('The DJ role has been cleared.',ephemeral=True)

async def setup(client:commands.Bot):
    await client.add_cog(Configuration(client))