import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from llm import llm, REGULAR_MODELS, STRUCTURED_MODELS

load_dotenv(os.path.expanduser('~/.env'))
load_dotenv()

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
user_models = {}

@bot.event
async def on_ready():
    print("Bot ready!", flush=True)
    await bot.tree.sync()

@bot.tree.command(name="llm", description="Ask the LLM")
async def llm_cmd(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    model = user_models.get(interaction.user.id, {}).get('llm')
    response = llm(prompt, model=model)
    await interaction.followup.send(response)

@bot.tree.command(name="properties-gen", description="Generate properties as strings")
async def properties_gen_cmd(interaction: discord.Interaction, prompt: str, properties: str):
    await interaction.response.defer()
    model = user_models.get(interaction.user.id, {}).get('structured')
    prop_names = [p.strip() for p in properties.split(',')]
    schema = {
        "type": "object",
        "properties": {name: {"type": "string"} for name in prop_names},
        "required": prop_names,
        "additionalProperties": False
    }
    response = llm(prompt, schema=schema, model=model)
    response_text = f"```json\n{json.dumps(response, indent=2)}\n```"
    for i in range(0, len(response_text), 2000):
        await interaction.followup.send(response_text[i:i+2000])

@bot.tree.command(name="setmodel-llm", description="Set your LLM model")
@discord.app_commands.choices(model=[discord.app_commands.Choice(name=m, value=m) for m in REGULAR_MODELS])
async def setmodelllm_cmd(interaction: discord.Interaction, model: str):
    if 'llm' not in user_models.get(interaction.user.id, {}):
        user_models[interaction.user.id] = {}
    user_models[interaction.user.id]['llm'] = model
    await interaction.response.send_message(f"LLM model: {model}")

@bot.tree.command(name="setmodel-structured", description="Set your structured model")
@discord.app_commands.choices(model=[discord.app_commands.Choice(name=m, value=m) for m in STRUCTURED_MODELS])
async def setmodelstructured_cmd(interaction: discord.Interaction, model: str):
    if 'structured' not in user_models.get(interaction.user.id, {}):
        user_models[interaction.user.id] = {}
    user_models[interaction.user.id]['structured'] = model
    await interaction.response.send_message(f"Structured model: {model}")

@bot.tree.command(name="models", description="List available models")
async def models_cmd(interaction: discord.Interaction):
    regular = ", ".join(REGULAR_MODELS)
    structured = ", ".join(STRUCTURED_MODELS)
    await interaction.response.send_message(f"**Regular:** {regular}\n**Structured:** {structured}")

bot.run(os.getenv('DISCORD_BOT_TOKEN'))
