import config
from openai import OpenAI

_PROMPT = (
    "Create a captivating and engaging community post that teases our upcoming video without "
    "giving away too much detail. The post should generate excitement and anticipation among "
    "our audience of Ableton Live electronic music producers, 30 - 50 years old males. "
    "Use the context from the video script provided below."
)

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
            {"role": "system", "content": _PROMPT},
            {"role": "user", "content": caption_text},
        ],
    )
    return response.choices[0].message.content
