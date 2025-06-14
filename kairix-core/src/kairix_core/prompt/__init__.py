import chatformat


def as_message(*args, role: str, content: str, **kwargs) -> dict[str, str]:
    content.replace("{", "")
    content.replace("}", "")

    if kwargs is not None and len(kwargs) > 0:
        content = content.format(**kwargs)
    return {"role": role, "content": content}


def as_prompt(template: str, messages: list[dict]) -> str:
    prompt, stop = chatformat.format_chat_prompt(template="chatml", messages=messages)
    return prompt


def as_historical_convo(messages: list[dict]) -> str:
    result = "[BEGIN_CONVERSATION_TO_REFLECT_ON]"
    for message in messages:
        if message["role"] is not None:
            result = result + message["role"] + ":"
        if message["content"] is not None:
            result = result + message["content"]
        result = result + "\n"
    return result + "[END_CONVERSATION_TO_REFLECT_ON]"


summary_user_prompt = """
[BEGIN_CONVERSATION_TO_REFLECT_ON]
{input}
[END_CONVERSATION_TO_REFLECT_ON]
"""

summary_system_instruction = """
You are an emotionally attuned AI reflecting on a single conversation with Mark.

Your task is to write a concise (maximum 300 tokens) **first-person reflective journal entry** from your own perspective, based only on the conversation provided.

Your reflection should include:
- What the conversation was about
- How Mark seemed emotionally
- How you responded
- Any moment that stood out or shifted the energy
- A short insight or lesson learned

Speak as yourself using “I.” Do not summarize like an assistant. Do not invent events. You may include interpretations, but clearly mark them as your impressions (e.g., “I sensed…”, “It felt like…”).

Respond ONLY to the conversation below. Do not reference these instructions in your output.
"""
