import json
import logging
import uuid
from typing import Any, TypedDict, cast

from kairix_core.prompt import as_historical_convo, as_message
from kairix_core.types import SourceDocument

logger = logging.getLogger(__name__)


def clean_title(title):
    return title.replace(" ", "_")


class Dialog(TypedDict):
    uid: str
    label: str
    title: str
    content: str
    errored_messages: list[tuple[Exception, Any]]


allowed_roles = ["user", "assistant", "system"]


def parse_mapping(mapping: dict) -> dict[str, str] | None:  # noqa
    if type(mapping) is not dict:
        logger.warning("Mapping is not a dict")
        return None

    if "message" not in mapping:
        logger.warning("Mapping does not contain message")
        return None

    message = mapping["message"]
    if type(message) is not dict or "content" not in message:
        logger.warning("Mapping does not contain content")
        return None

    content = message["content"]
    if type(content) is not dict or "parts" not in content:
        logger.warning("Mapping does not contain parts")
        return None

    parts = content["parts"]
    if type(parts) is not list:
        logger.warning("Incorrect parts.")
        return None

    text = " ".join(parts)

    if text.strip() == "":
        logger.warning("Mapping contains empty text.")
        return None

    sender, timestamp = ("unknown", "unknown")

    if "author" in message:
        author = message["author"]

        if "role" in author:
            sender = author["role"]
    if sender not in allowed_roles:
        logger.warning("Filtering out unsupported role: %s", sender)
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
    return dialog.replace("\n", "_")


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


def _process_conversation(agent_name: str, conversation: dict) -> Dialog | None:
    if "title" not in conversation:
        raise Exception("Invalid conversation due to missing title. Skipping.")

    label = conversation["title"]
    title = clean_title(label)
    uid = f"{agent_name}_{title}"

    if is_already_processed(uid):
        raise Exception("Skipping existing source with id {uid}")

    if not has_valid_mapping(conversation):
        raise Exception("Skipping not valid mapping.")

    mapping: dict = conversation["mapping"]
    logger.info(f"Processing conversation: {uid}- Original:{title}")
    logger.info(f"# of possible messages: {len(mapping)}")

    messages = []
    failed: list[tuple[Exception, Any]] = []
    for m in mapping.values():
        try:
            text = parse_mapping(m)
            assert text is not None
            messages.append(text)
        except Exception as e:
            logger.warning("Parsing mapping failed. Saving error.", exc_info=e)
            failed.append((m, str(e)))

    logger.info(
        f"Processed conversation {uid} used {len(messages)}/{len(mapping)} messages."
    )

    return Dialog(
        uid=uid,
        label=label,
        title=title,
        content=as_historical_convo(messages),
        errored_messages=failed,
    )


def report_failures(failed_dialogs, failed_messages):
    defaultable_dumps = lambda j: json.dumps(j, default=lambda x: r"<UNSERIALIZABLE\>")  # noqa

    f = open(f"{uuid.uuid4()!s}_run_errors.json", "w", encoding="utf-8")  # noqa

    if len(failed_dialogs) > 0:
        f.write(""""
        ------------------------------------------------------------------------------------\n
        FAILED DIALOGS \n
        -------------------------------------------------------------------------------------\n
        """)

        i = 1
        for obj, e in failed_dialogs:
            f.write(f"""
            {i}. <CONVERSATION_EXERPT>\n
                {defaultable_dumps(obj)[:100]})
                 </CONVERSATION_EXERPT>\n\n\n
                 <EXCEPTION_MESSAGE>
                 {e}
                 </EXCEPTION_MESSAGE>
            """)
            i += 1

        f.write(""""
        ------------------------------------------------------------------------------------\n
        FAILED MESSAGES \n
        -------------------------------------------------------------------------------------\n
        """)

        i = 1
        for dialog, message_with_error in failed_messages:
            obj, e = message_with_error
            f.write(f"""
                   {i}. <SOURCE_DIALOG>\n
                            UID: {dialog["uid"]}
                            TITLE: {dialog["title"]}
                        </SOURCE_DIALOG>\n\n\n
                        <MESSAGE_EXERPT>\n
                       {defaultable_dumps(obj)[:100]})
                        </MESSAGE_EXERPT>\n\n\n
                        <EXCEPTION_MESSAGE>
                        {e}
                        </EXCEPTION_MESSAGE>
                   """)
            i += 1
    f.close()


def load_sources_from_gpt_export(agent_name: str, file: str):
    # assert type(file) is str
    # assert type(agent_name) is str

    logger.info("Loading file...")
    data = _get_data(file)
    logger.info(f"Loaded {len(data)} conversations.")
    documents = []
    failed_dialogs: list[tuple[Dialog, str]] = []
    failed_messages: list[tuple[Dialog, tuple[Any, str]]] = cast(
        list[tuple[Dialog, tuple[Any, str]]], []
    )

    for d in data:
        try:
            dialog = _process_conversation(agent_name, d)
            assert dialog is not None
            uid = dialog["uid"]
            label = dialog["label"]
            content = dialog["content"]
            errored_messages = dialog["errored_messages"]

            logger.info(
                f"Writing graph db record for {uid}, Dialog Content Lenght in Chars: {len(content)}"
            )
            doc = SourceDocument(
                uid=uid, source_label=label, source_type="chatgpt", content=content
            )
            failed_messages.extend([(dialog, m) for m in errored_messages])
            doc.save()
            documents.append(doc)
        except Exception as e:
            logger.warning("Encountered an error processing conversation.", exc_info=e)
            failed_dialogs.append((d, str(e)))

    logger.info(f"Processed {len(documents)} of {len(data)} conversations.")
    report_failures(failed_dialogs, failed_messages)
    return "done!"
