import discord
from discord.ext import commands
import os
import json
import asyncio
import shlex
import logging
from dotenv import load_dotenv
from llm import llm, REGULAR_MODELS, STRUCTURED_MODELS
from google import genai
from PIL import Image
from io import BytesIO

load_dotenv(os.path.expanduser('~/.env'))
load_dotenv()

genai_client = genai.Client()
logger = logging.getLogger('discord')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
user_models = {}

@bot.event
async def on_ready():
    print("Bot ready!", flush=True)
    await bot.tree.sync()

@bot.command(name='llm')
async def llm_prefix_cmd(ctx, *, prompt: str):
    async with ctx.typing():
        model = user_models.get(ctx.author.id, {}).get('llm')
        full_prompt = prompt

        if ctx.message.reference:
            replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            full_prompt = f"Context: {replied_msg.content}\n\n{prompt}"

        response = llm(full_prompt, model=model)
        await ctx.reply(f"> {prompt}\n\n{response}")

@bot.command(name='i2i')
async def i2i_cmd(ctx, *, prompt: str):
    async with ctx.typing():
        image_url = None
        if ctx.message.reference:
            replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_msg.attachments:
                image_url = replied_msg.attachments[0].url
        elif ctx.message.attachments:
            image_url = ctx.message.attachments[0].url

        if not image_url:
            await ctx.reply("Reply to a message with an image or attach one")
            return

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                image_data = await resp.read()

        input_image = Image.open(BytesIO(image_data))
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt, input_image]
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image_bytes = BytesIO()
                image.save(image_bytes, format='PNG')
                image_bytes.seek(0)
                await ctx.reply(f"> {prompt}", file=discord.File(image_bytes, filename='i2i.png'))
                return

@bot.command(name='nukki')
async def nukki_cmd(ctx):
    async with ctx.typing():
        image_url = None
        if ctx.message.reference:
            replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if replied_msg.attachments:
                image_url = replied_msg.attachments[0].url
        elif ctx.message.attachments:
            image_url = ctx.message.attachments[0].url

        if not image_url:
            await ctx.reply("Reply to a message with an image or attach one")
            return

        import aiohttp
        from rembg import remove
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                image_data = await resp.read()

        input_image = Image.open(BytesIO(image_data))
        output_image = remove(input_image)

        image_bytes = BytesIO()
        output_image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        await ctx.reply(file=discord.File(image_bytes, filename='nukki.png'))

@bot.command(name='enhance')
async def enhance_cmd(ctx, *, prompt: str):
    async with ctx.typing():
        import subprocess
        script_dir = os.path.join(os.path.dirname(__file__), 'scripts')
        llm_script = os.path.join(script_dir, 'llm.sh')

        enhance_prompt = f"Convert this prompt into a detailed English image generation prompt. Prefix it with 'digital anime illustration of'. Be concise and focused on visual details only. Do not include any explanations, just output the enhanced prompt:\n\n{prompt}"

        proc = await asyncio.create_subprocess_exec(
            'bash', llm_script, enhance_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0 and stdout:
            enhanced = stdout.decode().strip()
            await ctx.reply(f"> {prompt}\n\n**Enhanced:**\n{enhanced}")
        else:
            await ctx.reply("Enhancement failed")

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

@bot.tree.command(name="qwen-wan", description="LoRA 이미지 생성")
@discord.app_commands.choices(aspect=[
    discord.app_commands.Choice(name="Portrait", value="portrait"),
    discord.app_commands.Choice(name="Landscape", value="landscape"),
    discord.app_commands.Choice(name="Square", value="square")
])
async def qwen_wan_cmd(interaction: discord.Interaction, prompt: str, aspect: str = None, lora_strength: float = None):
    await interaction.response.defer()

    import subprocess
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'qwen_wan.sh')
    output_path = os.path.join(os.path.dirname(__file__), 'scripts', 'QWEN_WAN.png')

    # Build command with flags (no enhancement by default)
    args = [script_path]
    if aspect:
        args.extend(['-a', aspect])
    if lora_strength is not None:
        args.extend(['-s', str(lora_strength)])
    args.append(prompt)

    # Run the shell script
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=os.path.dirname(script_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    # Log script output
    if stdout:
        print(f"[qwen-wan] stdout: {stdout.decode()}", flush=True)
    if stderr:
        print(f"[qwen-wan] stderr: {stderr.decode()}", flush=True)

    # Read the generated image
    with open(output_path, 'rb') as f:
        image_bytes = BytesIO(f.read())

    await interaction.followup.send(
        f"> {prompt}",
        file=discord.File(image_bytes, filename='generated.png')
    )

@bot.tree.command(name="enhanced-qwen-wan", description="LoRA 이미지 생성 (prompt enhance)")
@discord.app_commands.choices(aspect=[
    discord.app_commands.Choice(name="Portrait", value="portrait"),
    discord.app_commands.Choice(name="Landscape", value="landscape"),
    discord.app_commands.Choice(name="Square", value="square")
])
async def enhanced_qwen_wan_cmd(interaction: discord.Interaction, prompt: str, aspect: str = None, lora_strength: float = None):
    await interaction.response.defer()

    import subprocess
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'qwen_wan.sh')
    output_path = os.path.join(os.path.dirname(__file__), 'scripts', 'QWEN_WAN.png')

    # Build command with flags (enable enhancement with -e)
    args = [script_path]
    if aspect:
        args.extend(['-a', aspect])
    if lora_strength is not None:
        args.extend(['-s', str(lora_strength)])
    args.append('-e')  # Enable enhancement
    args.append(prompt)

    # Run the shell script
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=os.path.dirname(script_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    # Log script output
    if stdout:
        print(f"[enhanced-qwen-wan] stdout: {stdout.decode()}", flush=True)
    if stderr:
        print(f"[enhanced-qwen-wan] stderr: {stderr.decode()}", flush=True)

    # Extract enhanced prompt from stdout
    enhanced_prompt = prompt
    stdout_text = stdout.decode() if stdout else ""
    for line in stdout_text.split('\n'):
        if line.startswith('Enhanced: '):
            enhanced_prompt = line[10:]  # Remove "Enhanced: " prefix
            break

    # Read the generated image
    with open(output_path, 'rb') as f:
        image_bytes = BytesIO(f.read())

    await interaction.followup.send(
        f"> {prompt}\n\n**Enhanced:** {enhanced_prompt}",
        file=discord.File(image_bytes, filename='generated.png')
    )

@bot.tree.command(name="nukki-enhanced-qwen-wan", description="LoRA 이미지 생성 (prompt enhance + background removal)")
@discord.app_commands.choices(aspect=[
    discord.app_commands.Choice(name="Portrait", value="portrait"),
    discord.app_commands.Choice(name="Landscape", value="landscape"),
    discord.app_commands.Choice(name="Square", value="square")
])
async def nukki_enhanced_qwen_wan_cmd(interaction: discord.Interaction, prompt: str, aspect: str = None, lora_strength: float = None):
    await interaction.response.defer()

    import subprocess
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'qwen_wan.sh')
    output_path = os.path.join(os.path.dirname(__file__), 'scripts', 'QWEN_WAN.png')
    nukki_script = os.path.join(os.path.dirname(__file__), 'scripts', 'nukki.py')
    nukki_output = os.path.join(os.path.dirname(__file__), 'scripts', 'QWEN_WAN_nukki.png')

    # Append "no background" to prompt for enhancement
    enhanced_prompt_input = f"{prompt}, no background"

    # Build command with flags (enable enhancement with -e)
    args = [script_path]
    if aspect:
        args.extend(['-a', aspect])
    if lora_strength is not None:
        args.extend(['-s', str(lora_strength)])
    args.append('-e')  # Enable enhancement
    args.append(enhanced_prompt_input)

    # Run the image generation script
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=os.path.dirname(script_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    # Log script output
    if stdout:
        print(f"[nukki-enhanced-qwen-wan] qwen_wan stdout: {stdout.decode()}", flush=True)
    if stderr:
        print(f"[nukki-enhanced-qwen-wan] qwen_wan stderr: {stderr.decode()}", flush=True)

    # Extract enhanced prompt from stdout
    enhanced_prompt = enhanced_prompt_input
    stdout_text = stdout.decode() if stdout else ""
    for line in stdout_text.split('\n'):
        if line.startswith('Enhanced: '):
            enhanced_prompt = line[10:]  # Remove "Enhanced: " prefix
            break

    # Run nukki background removal
    python_path = os.path.join(os.path.dirname(__file__), '.venv', 'bin', 'python')
    nukki_proc = await asyncio.create_subprocess_exec(
        python_path, nukki_script, output_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    nukki_stdout, nukki_stderr = await nukki_proc.communicate()

    # Log nukki output
    if nukki_stdout:
        print(f"[nukki-enhanced-qwen-wan] nukki stdout: {nukki_stdout.decode()}", flush=True)
    if nukki_stderr:
        print(f"[nukki-enhanced-qwen-wan] nukki stderr: {nukki_stderr.decode()}", flush=True)

    # Read the nukki'd image
    with open(nukki_output, 'rb') as f:
        image_bytes = BytesIO(f.read())

    await interaction.followup.send(
        f"> {prompt}\n\n**Enhanced:** {enhanced_prompt}",
        file=discord.File(image_bytes, filename='generated_nukki.png')
    )

@bot.tree.command(name="cathy-gen", description="Cathy workflow 이미지 생성")
@discord.app_commands.choices(aspect=[
    discord.app_commands.Choice(name="Portrait", value="portrait"),
    discord.app_commands.Choice(name="Landscape", value="landscape"),
    discord.app_commands.Choice(name="Square", value="square")
])
async def cathy_gen_cmd(interaction: discord.Interaction, prompt: str, aspect: str = None, number: int = 1):
    await interaction.response.defer()

    import subprocess
    import glob
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'qwen_wan.sh')
    output_path = os.path.join(os.path.dirname(__file__), 'scripts', 'cathy.png')

    # Build command with flags
    args = [script_path, '-w', 'cathy.json', '-o', output_path]
    if aspect:
        args.extend(['-a', aspect])
    if number > 1:
        args.extend(['-n', str(number)])
    args.append(prompt)

    # Run the shell script
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=os.path.dirname(script_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    # Log script output
    if stdout:
        print(f"[cathy-gen] stdout: {stdout.decode()}", flush=True)
    if stderr:
        print(f"[cathy-gen] stderr: {stderr.decode()}", flush=True)

    # Collect all generated images
    script_dir = os.path.dirname(script_path)
    files = []

    if number == 1:
        files.append(output_path)
    else:
        # Multiple images: cathy_001.png, cathy_002.png, etc.
        pattern = os.path.join(script_dir, 'cathy_*.png')
        files = sorted(glob.glob(pattern))

    # Send all images
    discord_files = []
    for i, fpath in enumerate(files):
        with open(fpath, 'rb') as f:
            discord_files.append(discord.File(BytesIO(f.read()), filename=f'cathy_{i+1:03d}.png'))

    await interaction.followup.send(
        f"> {prompt}",
        files=discord_files
    )

@bot.tree.command(name="chouloky-gen", description="Chouloky workflow 이미지 생성")
@discord.app_commands.choices(aspect=[
    discord.app_commands.Choice(name="Portrait", value="portrait"),
    discord.app_commands.Choice(name="Landscape", value="landscape"),
    discord.app_commands.Choice(name="Square", value="square")
])
async def chouloky_gen_cmd(interaction: discord.Interaction, prompt: str, aspect: str = None, number: int = 1):
    logger.info(f"chouloky-gen: {interaction.user.name} started generation (n={number})")
    await interaction.response.defer()

    import subprocess
    import glob
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'qwen_wan.sh')
    output_path = os.path.join(os.path.dirname(__file__), 'scripts', 'chouloky.png')

    # Build command with flags
    args = [script_path, '-w', 'chouloky.json', '-o', output_path]
    if aspect:
        args.extend(['-a', aspect])
        logger.info(f"chouloky-gen: aspect={aspect}")
    if number > 1:
        args.extend(['-n', str(number)])
    args.append(prompt)

    # Run the shell script
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=os.path.dirname(script_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    # Log script output
    if stdout:
        logger.info(f"chouloky-gen: {stdout.decode().strip()}")
    if stderr:
        logger.warning(f"chouloky-gen: {stderr.decode().strip()}")

    # Collect all generated images
    script_dir = os.path.dirname(script_path)
    files = []

    if number == 1:
        files.append(output_path)
    else:
        # Multiple images: chouloky_001.png, chouloky_002.png, etc.
        pattern = os.path.join(script_dir, 'chouloky_*.png')
        files = sorted(glob.glob(pattern))

    # Send all images
    discord_files = []
    for i, fpath in enumerate(files):
        with open(fpath, 'rb') as f:
            discord_files.append(discord.File(BytesIO(f.read()), filename=f'chouloky_{i+1:03d}.png'))

    await interaction.followup.send(
        f"> {prompt}",
        files=discord_files
    )

    logger.info(f"chouloky-gen: completed for {interaction.user.name}")

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

@bot.tree.command(name="list-commands", description="List all prefix commands")
async def list_commands_cmd(interaction: discord.Interaction):
    commands_list = """**Prefix Commands (!):**
• `!llm <prompt>` - Ask LLM (supports reply context)
• `!i2i <prompt>` - Transform image (reply to or attach image)
• `!nukki` - Remove background (reply to or attach image)
• `!enhance <prompt>` - Enhance prompt for image generation"""
    await interaction.response.send_message(commands_list)

bot.run(os.getenv('DISCORD_BOT_TOKEN'))
