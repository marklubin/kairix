import json
import logging
from typing import cast

from kairix_core.prompt import as_historical_convo, as_message
from kairix_core.types import SourceDocument

logger = logging.getLogger(__name__)


def clean_title(title):
    return title.replace(" ", "_")


allowed_roles = ["user", "assistant", "system"]


def parse_mapping(mapping: dict) -> dict[str, str] | None:  # noqa
    if type(mapping) is not dict:
        return None

    if "message" not in mapping:
        return None

    message = mapping["message"]
    if type(message) is not dict or "content" not in message:
        return None

    content = message["content"]
    if type(content) is not dict or "parts" not in content:
        return None

    parts = content["parts"]
    if type(parts) is not list:
        return None

    text = "\n".join(parts)

    if text.strip() == "":
        logger.info("Skipping empty message.")
        return None

    sender, timestamp = ("unknown", "unknown")

    if "author" in message:
        author = message["author"]

        if "role" in author:
            sender = author["role"]
    if sender not in allowed_roles:
        logger.info("Filtering out unsupported role: %s", sender)
        return None

    if "create_time" in message:
        timestamp = message["create_time"]  # noqa

    # return f"({timestamp})-{sender}: {text}\n"
    result: dict[str, str] = as_message(role=sender.upper(), content=text)
    return result


def _get_data(file: str) -> dict:
    try:
        with open(file, encoding="utf-8") as f:
            return cast(dict, json.load(f))
    except FileNotFoundError:
        logger.info("Received file content, loading from string.")
        return cast(dict, json.loads(file))


def load_sources_from_gpt_export(agent_name: str, file: str | list[str]):
    if isinstance(file, list):
        raise Exception("Multiple files unsupported.")

    logger.info("Loading file...")
    data = _get_data(file)
    logger.info(f"Loaded {len(data)} conversations.")
    documents = []
    for d in data:
        label = d["title"]
        title = clean_title(label)

        id_to_mapping = d["mapping"]
        if title is None or title == "":
            logger.info("Skipping conversation with no title.")
            yield "Skipping conversation with no title."
            continue
        if id_to_mapping is None:
            logger.info(f"Skipping convo {title} with no messages.")
            yield f"Skipping convo {title} with no messages."
            continue

        uid = f"{agent_name}-{title}"
        logger.info(f"Checking for existing source with id {uid}")

        if SourceDocument.nodes.first_or_none(uid=uid) is not None:
            logger.info(f"Skipping existing source with id {uid}")
            continue

        logger.info(f"Processing conversation: {uid}- Original:{title}")
        logger.info(f"# of mappings: {len(id_to_mapping)}")

        messages = []
        for _key, mapping in id_to_mapping.items():
            text = parse_mapping(mapping)
            if text is not None:
                messages.append(text)

        document_content = as_historical_convo(messages)

        logger.info(
            f"Writing graph db record for {title}, # of messages: {len(messages)}"
        )
        doc = SourceDocument(
            uid=uid,
            source_label=title,
            source_type="chatgpt",
            content=document_content,
            # content="\n".join(messages),
        )

        try:
            doc.save()
            documents.append(doc)
        except Exception as e:
            raise RuntimeError(f"Failed to save SourceDocument for {title}: {e}") from e
    if len(documents) == 0:
        logger.info("Done. Nothing to do.")
    else:
        msg = "Finished! Wrote Source Documents:" + "\n".join(
            [f"SourceDocument - UID={d.uid} LABEL={d.source_label}." for d in documents]
        )
        logger.info(msg)
        return msg
    return "done!"
