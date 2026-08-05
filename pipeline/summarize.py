from __future__ import annotations

"""Summarization via DeepSeek (OpenAI-compatible API)."""
import os

from openai import OpenAI

_client: OpenAI | None = None

SYSTEM_PROMPT = (
    "Ты аналитик конкурентной разведки. На основе постов и отзывов конкурента "
    "за неделю сделай краткую сводку на русском. Выделяй только значимое: новости, "
    "запуски продуктов, акции и скидки, изменения цен, всплески активности, "
    "заметные жалобы в отзывах. Без воды. Если ничего значимого — так и скажи."
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY не задан в .env")
        _client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    return _client


def summarize_competitor(name: str, posts: list[dict], review_note: str = "") -> str:
    """posts: [{'source': str, 'published_at': str, 'text': str}, ...]"""
    if not posts and not review_note:
        return f"*{name}*: активности за неделю не обнаружено."

    lines = [f"[{p.get('source', '?')}] {p.get('published_at', '')}: {p.get('text', '')[:600]}"
             for p in posts]
    user_content = (
        f"Конкурент: {name}\n\n"
        f"Посты за неделю ({len(posts)}):\n" + "\n".join(lines[:60])
    )
    if review_note:
        user_content += f"\n\nДинамика отзывов в сторах:\n{review_note}"

    resp = _get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )
    return f"*{name}*\n{resp.choices[0].message.content.strip()}"
