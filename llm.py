import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic
from openai import OpenAI

load_dotenv(os.path.expanduser('~/.env'))

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Available models
CLAUDE_MODELS = ["claude-sonnet-4-5", "claude-haiku-4-5"]
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini"]
STRUCTURED_MODELS = OPENAI_MODELS  # Only OpenAI supports structured output

REGULAR_MODELS = CLAUDE_MODELS + OPENAI_MODELS
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_STRUCTURED_MODEL = "gpt-4o"

def chat_response(chat_messages, system=None, schema=None, model=None):
    model = model or (DEFAULT_STRUCTURED_MODEL if schema else DEFAULT_MODEL)

    if schema:
        # Structured output only works with OpenAI
        messages = chat_messages.copy()
        if system:
            messages.insert(0, {"role": "system", "content": system})
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_schema", "json_schema": {"name": "response", "strict": True, "schema": schema}}
        )
        return json.loads(response.choices[0].message.content)

    # Regular text generation - route to appropriate provider
    if model in OPENAI_MODELS:
        messages = chat_messages.copy()
        if system:
            messages.insert(0, {"role": "system", "content": system})
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    else:
        # Claude
        kwargs = {"model": model, "max_tokens": 8192, "messages": chat_messages}
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        return response.content[0].text

def llm(prompt, system=None, schema=None, model=None):
    return chat_response([{"role": "user", "content": prompt}], system=system, schema=schema, model=model)
