import json
import logging
from typing import Any, cast

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

    text = " ".join(parts)

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

def clean_dialog(dialog: str) -> str:
    return dialog.replace('\n','_')

def record_failed_convos(failed):
    if len(failed) > 0:
        return
    with open("failed-conversations.json", "w", encoding="utf-8") as f:
        json.dump(failed, f)

def record_failed_mapping(uid, failed):
    if len(failed) == 0:
        return
    logger.warning(f"{uid}: Encountered {failed} failed mapping: {failed}")
    with open(f"{uid}-message-failures.json", "w", encoding="utf-8") as f:
        json.dump(failed, f)

def is_already_processed(uid: str) -> bool:
    logger.info(f"Checking for existing source with id {uid}")
    return SourceDocument.nodes.first_or_none(uid=uid) is not None

def has_valid_mapping(conversation: dict) -> bool:
    if "mapping" not in conversation:
        logger.info("Skipping convoo,Has no messages.")
        return False

    if not isinstance(conversation["mapping"], dict):
        logger.info("Mapping is not a dict. Can't process.")
        return False

    return True

def _process_conversation(
    agent_name: str, conversation: dict
) -> tuple[str, str, str] | None:
    if "title" not in conversation:
        logger.warning("Invalid conversation due to missing title. Skipping.")
        return None

    label = conversation["title"]
    title = clean_title(label)
    uid = f"{agent_name}_{title}"

    if is_already_processed(uid):
        logger.info(f"Skipping existing source with id {uid}")
        return None

    if not has_valid_mapping(conversation):
        logger.warning("Skipping not valid mapping.")
        return None

    mapping: dict = conversation["mapping"]
    logger.info(f"Processing conversation: {uid}- Original:{title}")
    logger.info(f"# of possible messages: {len(mapping)}")

    messages = []
    failed: list[tuple[Exception, Any]] = []
    for m in mapping.values():
        try:
            text = parse_mapping(mapping)
            if text is not None:
                messages.append(text)
        except Exception as e:
            logger.warning("Parsing mapping failed. Saving error.", exc_info=e)
            failed.append((m, e.with_traceback()))

    record_failed_mapping(uid, failed)
    logger.info(f"Processed conversation {uid} with {len(messages)} messages.")
    return uid, label, as_historical_convo(messages)


def load_sources_from_gpt_export(agent_name: str, file: str | list[str]):
    if isinstance(file, list):
        raise Exception("Multiple files unsupported.")

    logger.info("Loading file...")
    data = _get_data(file)
    logger.info(f"Loaded {len(data)} conversations.")
    documents = []
    failed = []
    for d in data:
        try:
            uid, label, dialog = _process_conversation(agent_name, d)

            logger.info(
                f"Writing graph db record for {uid}, Dialog Length in Chars: {len(dialog)}"
            )
            doc = SourceDocument(
                uid=uid,
                source_label=label,
                source_type="chatgpt",
                content=dialog
            )

            doc.save()
            documents.append(doc)
        except Exception as e:
            logger.warning("Encountered an error processing conversation.", exc_info=e)
            failed.append(d)

    if len(failed) > 0:
        logger.info(f"Failed to process {len(failed)} conversations. "
                    f"Writing failed convos to file for retry.")

    if len(documents) == 0:
        logger.info("Done. Wrote no documents.")
    else:
        msg = "Finished! Wrote Source Documents:" + "\n".join(
            [f"SourceDocument - UID={d.uid} LABEL={d.source_label}." for d in documents]
        )
        logger.info(msg)
        return msg
    return "done!"
