import config
from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def generate_community_post(caption_text: str) -> str:
    """Send caption text to ChatGPT and return the generated community post."""
    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": config.OPENAI_PROMPT},
            {"role": "user", "content": caption_text},
        ],
    )
    return response.choices[0].message.content
