import chatformat


def as_message(role: str, content: str, **kwargs) -> dict:
    if kwargs is not None:
        content = content.format(**kwargs)
    return {"role": role, "content": content}


def as_prompt(template: str, messages: list[dict]):
    prompt, stop = chatformat.format_chat_prompt(template=template, messages=messages)
    return prompt
