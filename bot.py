import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from llm import llm, REGULAR_MODELS, STRUCTURED_MODELS
from google import genai
from PIL import Image
from io import BytesIO

load_dotenv(os.path.expanduser('~/.env'))
load_dotenv()

genai_client = genai.Client()

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
    await interaction.followup.send(f"> {prompt}\n\n{response}")

@bot.tree.command(name="json-gen", description="Generate properties as strings")
async def properties_gen_cmd(interaction: discord.Interaction, prompt: str, properties: str):
    await interaction.response.defer()
    model = user_models.get(interaction.user.id, {}).get('llm', 'claude-sonnet-4-5')
    prop_names = [p.strip() for p in properties.split(',')]
    full_prompt = f"{prompt}\n\n다음 속성들을 포함해서 생성해줘:\n" + "\n".join(f"**{name}**:" for name in prop_names)
    response = llm(full_prompt, model=model)
    full_text = f"> {prompt}\n\n{response}"
    for i in range(0, len(full_text), 2000):
        await interaction.followup.send(full_text[i:i+2000])

@bot.tree.command(name="character-text-gen", description="Generate a character")
async def character_text_gen_cmd(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    model = user_models.get(interaction.user.id, {}).get('llm', 'claude-sonnet-4-5')
    prop_names = ["이름", "나이", "배경", "출신", "직업", "꿈", "무기", "스킬1", "스킬2", "스킬3"]
    full_prompt = f"{prompt}\n\n다음 속성들을 포함해서 캐릭터를 생성해줘:\n" + "\n".join(f"**{name}**:" for name in prop_names)
    response = llm(full_prompt, model=model)
    full_text = f"> {prompt}\n\n{response}"
    for i in range(0, len(full_text), 2000):
        await interaction.followup.send(full_text[i:i+2000])

@bot.tree.command(name="character-gen", description="Generate a character and its image")
async def character_and_image_gen_cmd(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    model = user_models.get(interaction.user.id, {}).get('llm', 'claude-sonnet-4-5')
    prop_names = ["이름", "나이", "배경", "출신", "직업", "꿈", "무기", "스킬1", "스킬2", "스킬3"]
    full_prompt = f"{prompt}\n\n다음 속성들을 포함해서 캐릭터를 생성해줘:\n" + "\n".join(f"**{name}**:" for name in prop_names)
    character_response = llm(full_prompt, model=model)

    # Send character description first
    char_text = f"> {prompt}\n\n{character_response}"
    for i in range(0, len(char_text), 2000):
        await interaction.followup.send(char_text[i:i+2000])

    # Show typing while generating image
    async with interaction.channel.typing():
        # Convert character to image description
        image_desc_prompt = f"Convert this character description into a detailed visual portrait description for image generation. Focus on physical appearance, clothing, pose, and mood:\n\n{character_response}"
        image_description = llm(image_desc_prompt, model=model)

        # Generate image based on description
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[image_description]
        )

        # Send image
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image_bytes = BytesIO()
                image.save(image_bytes, format='PNG')
                image_bytes.seek(0)
                await interaction.followup.send(file=discord.File(image_bytes, filename='character.png'))
                return

@bot.tree.command(name="image-gen", description="Generate an image")
async def image_gen_cmd(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    response = genai_client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt]
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image_bytes = BytesIO()
            image.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            await interaction.followup.send(
                f"> {prompt}",
                file=discord.File(image_bytes, filename='generated.png')
            )
            return

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
