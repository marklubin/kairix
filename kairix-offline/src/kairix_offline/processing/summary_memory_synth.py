import hashlib
import logging
from typing import Any

from kairix_core.inference_provider import InferenceParams, InferenceProvider
from kairix_core.types import Agent, Embedding, MemoryShard, SourceDocument, Summary
from semchunk import Chunker
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class Chunk:
    def __init__(self, *, idempotency_key: str, text: str, source: SourceDocument):
        self.idempotency_key = idempotency_key
        self.text = text
        self.source = source


class SummaryMemorySynth:
    def __init__(
        self,
        *,
        chunker,
        embedder,
        inference_provider: InferenceProvider,
        **kwargs,
    ):
        self.chunker: Chunker = chunker
        self.embedder: SentenceTransformer = embedder
        self.inference_provider: InferenceProvider = inference_provider
        self.inference_parameters: InferenceParams = InferenceParams(kwargs)

    def _get_summary(self, chunk):
        summary = Summary.get_or_none(chunk.idempotency_key)
        if summary is not None:
            logger.info("\nFound existing summary reusing.")
            return summary

        logger.info("\nStartig to call provider for summary..")

        summary_text = self.inference_provider.predict(
            chunk.text, self.inference_parameters
        )
        logger.info(f"Summary received got {len(summary_text)} characters back.")

        # Create and save Summary object
        summary = Summary(uid=chunk.idempotency_key, summary_text=summary_text)
        summary.save()
        return summary

    def _get_embedding(self, chunk: Chunk, summary):
        logger.info("\nBegining Emedding generation.")

        embedding = Embedding.get_or_none(chunk.idempotency_key)

        if embedding is not None:
            logger.info("\nFound existing embedding reusing.")
            return embedding

        logger.info("\nCalling Model to generate embedding.")
        numpy_array = self.embedder.encode(summary.summary_text)
        vector = numpy_array.tolist()
        embedding = Embedding(
            uid=chunk.idempotency_key,
            embedding_model=self.embedder.model_card_data.base_model,
            vector=vector,
        )
        embedding.save()
        return embedding

    def _get_chunks(self, key_prefix: str) -> list[Chunk]:
        all_documents = SourceDocument.nodes.all()
        chunks: list[Chunk] = []

        for document in all_documents:
            # Call chunker with just the text
            doc_chunks: list[str] = self.chunker(document.content)  # type: ignore[assignment]
            for doc_chunk in doc_chunks:
                key = self.__get_idempotency_key(key_prefix, doc_chunk)
                chunk = Chunk(idempotency_key=key, text=doc_chunk, source=document)
                chunks.append(chunk)
                logger.info(f"Chunk: {chunk}")
        return chunks

    def _process(self, chunk) -> MemoryShard:
        summary = self._get_summary(chunk)
        embedding = self._get_embedding(chunk, summary)

        logger.info("\nPersisting runtime MemoryShard")
        shard_uid = chunk.idempotency_key

        existing_shard: Any = MemoryShard.get_or_none(shard_uid)
        if existing_shard is not None:
            logger.info("\nFound existing shard, nothing to do.")
            return existing_shard

        shard = MemoryShard(
            uid=shard_uid,
            shard_contents=summary.summary_text,
            vector_address=embedding.vector,
        )
        shard.save()

        # Connect relationships
        shard.embedding.connect(embedding)
        shard.summary.connect(summary)
        shard.source_document.connect(chunk.source)

        return shard

    def __get_idempotency_key(self, prefix: str, text: str) -> str:
        chunk_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"{prefix}-{chunk_hash}"

    def synthesize_memories(
        self,
        agent_name: str,
        key_prefix: str,
    ) -> tuple[list[MemoryShard], list[tuple[Chunk, Exception]]]:
        # Get or create agent
        agent = Agent.nodes.first_or_none(name=agent_name)
        if agent is None:
            agent = Agent(name=agent_name)
            agent.save()

        all_chunks: list[Chunk] = self._get_chunks(key_prefix)
        logger.info(f"Split input into {len(all_chunks)} chunks.")

        # Get existing memory shards
        all_shards: list[MemoryShard] = MemoryShard.nodes.all()

        shard_idempotency_keys: set[str] = {s.uid for s in all_shards}

        chunks_to_process: list[Chunk] = [
            c for c in all_chunks if c.idempotency_key not in shard_idempotency_keys
        ]

        logger.info(
            f"Processing {len(chunks_to_process)} chunks for {agent.name} as new memory shards."
        )

        shards: list[MemoryShard] = []
        failed: list[tuple[Chunk, Exception]] = []

        for chunk in chunks_to_process:
            try:
                shards.append(self._process(chunk))
            except Exception as e:
                logger.error(
                    f"Failed to process chunk {chunk.idempotency_key}: {e}", exc_info=e
                )
                failed.append((chunk, e))

        logger.info(
            f"Chunk processing completed. Processed {len(shards)} chunks succesfully.Failed Chunks: {len(failed)}"
        )

        return shards, failed
