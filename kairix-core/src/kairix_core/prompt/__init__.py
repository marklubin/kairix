import chatformat


def as_message(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def as_prompt(template: str, messages: list[dict]):
    chatformat.format_chat_prompt(template=template, messages=messages)
