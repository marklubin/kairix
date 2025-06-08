import json
import logging
import uuid

from kairix_core.types import SourceDocument

logger = logging.getLogger(__name__)


def parse_mapping(mapping: dict) -> str | None:
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

    sender, timestamp = ("unknown", "unknown")

    if "author" in message:
        author = message["author"]

        if "role" in author:
            sender = author["role"]
    if "create_time" in message:
        timestamp = message["create_time"]

    return f"({timestamp})-{sender}: {text}\n"


def load_sources_from_gpt_export(file_name: str | list[str]):
    documents = []
    if isinstance(file_name, list):
        if not file_name:
            yield "No file selected"
            logger.info("No file selected")
            return
        file_name = file_name[0]
    yield (f"Loading {file_name}")
    with open(file_name) as f:
        data = json.load(f)
        logger.info(f"Loaded {len(data)} conversations.")
        yield f"Loaded {len(data)} conversations."
        for d in data:
            title = d["title"]
            id_to_mapping = d["mapping"]
            if title is None or title == "":
                logger.info("Skipping conversation with no title.")
                yield "Skipping conversation with no title."
                continue
            if id_to_mapping is None:
                logger.info(f"Skipping convo {title} with no messages.")
                yield f"Skipping convo {title} with no messages."
                continue

            logger.info(f"Processing conversation: {title}")
            yield f"Processing conversation: {title}"
            logger.info(f"# of mappings: {len(id_to_mapping)}")
            yield f"# of mappings: {len(id_to_mapping)}"

            messages = []
            for _key, mapping in id_to_mapping.items():
                text = parse_mapping(mapping)
                if text is not None:
                    messages.append(text)

            logger.info(
                f"Writing graph db record for {title}, # of messages: {len(messages)}"
            )
            yield f"Writing graph db record for {title}, # of messages: {len(messages)}"

            doc = SourceDocument(
                uid=uuid.uuid4().urn,
                source_label=title,
                source_type="chatgpt",
                content="\n".join(messages),
            )

            try:
                doc.save()
                documents.append(doc)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to save SourceDocument for {title}: {e}"
                ) from e

        msg = "finished! Wrote Source Documents:" + "\n".join(
            [d.source_label for d in documents]
        )
        logger.info(msg)
        yield msg
