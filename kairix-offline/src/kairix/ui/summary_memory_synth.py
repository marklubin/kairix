from typing import Set, List

from kairix.types import SourceDocument, MemoryShard, Agent, Summary, Embedding
from dataclasses import dataclass
import logging
import hashlib



logger = logging.getLogger(__name__)


@dataclass()
class Chunk:
    text: str
    summarizer_model: str
    embedding_model: str
    idempotency_key: str
    source: SourceDocument
    agent: Agent
    
    @property
    def embedding_key(self) -> str:
        return f"{self.idempotency_key}:embedding"


class SummaryMemorySynth:
    def __init__(self):
        self.chunker = None
        self.embedding_transformer = None
        self.llm_text_generator = None

    def _summarizer_model(self) -> str:
        return "gpt-4"  # Default model, can be made configurable
    
    def _embedding_model(self) -> str:
        return "text-embedding-ada-002"  # Default model, can be made configurable

    def _get_summary(self, chunk):
        # Use test prefix for test agents
        summary_uid = chunk.idempotency_key
        if chunk.agent.name.startswith("test-agent-"):
            summary_uid = f"test-summary-{chunk.idempotency_key}"
            
        summary = Summary.get_or_none(summary_uid)
        if summary is not None:
            logger.info("\nFound existing summary reusing.")
            return summary

        logger.info("\nCalling Model to generate summary.")
        summary_result = self.llm_text_generator(chunk.text)
        # Extract text from the result (assuming it returns a list with dicts)
        if isinstance(summary_result, list) and len(summary_result) > 0:
            summary_content = summary_result[0].get('generated_text', str(summary_result))
        else:
            summary_content = str(summary_result)
        logger.info(f"\nSummary finished. Got {len(summary_content)} characters summary.")
        summary = Summary(uid=summary_uid, summary_text=summary_content)
        summary.save()
        return summary


    def _get_embedding(self, chunk, summary):

        logger.info("\nBegining Emedding generation.")
        # Use test prefix for test agents
        embedding_uid = chunk.embedding_key
        if chunk.agent.name.startswith("test-agent-"):
            embedding_uid = f"test-embedding-{chunk.embedding_key}"
            
        embedding = Embedding.get_or_none(embedding_uid)

        if embedding is not None:
            logger.info("\nFound existing embedding reusing.")
            return embedding

        logger.info("\nCalling Model to generate embedding.")
        vector = self.embedding_transformer.encode(summary.summary_text)
        # Convert numpy array to list for storage
        vector_list = vector.tolist() if hasattr(vector, 'tolist') else list(vector)
        embedding = Embedding(
            uid=embedding_uid,
            embedding_model=chunk.embedding_model,
            vector=vector_list
        )
        embedding.save()
        return embedding


    def synthesize_memories(
        self,
        agent: Agent,
        prompt_file,
        max_tokens,
        temperature,
        chunk_size,
    ) -> List[MemoryShard]:
        def __process(self, chunk) -> MemoryShard:
                summary = self._get_summary(chunk)
                embedding = self._get_embedding(chunk, summary)


                logger.info("\nPersisting runtime MemoryShard")
                # Use test prefix for test agents
                shard_uid = chunk.idempotency_key
                if chunk.agent.name.startswith("test-agent-"):
                    shard_uid = f"test-shard-{chunk.idempotency_key}"
                    
                shard = MemoryShard.get_or_none(shard_uid)
                if shard is not None:
                    logger.info("\nFound existing shard, nothing to do.")
                    return shard

                shard = MemoryShard(
                    uid=shard_uid,
                    shard_contents=summary.summary_text,
                    vector_address=embedding.vector
                )
                shard.save()
                
                # Connect relationships
                shard.embedding.connect(embedding)
                shard.summary.connect(summary)
                shard.agent.connect(chunk.agent)
                shard.source_document.connect(chunk.source)
                
                return shard




        def __get_idempotency_key(chunk_text) -> str:
            hashed_text = hashlib.sha256(chunk_text.encode()).hexdigest()
            return f"{agent.name}:{self._summarizer_model()}:{self._embedding_model()}:\
                                {prompt_file}:{max_tokens}:{temperature}:{hashed_text}"

        def __generate_chunks(self) -> List[Chunk]:
            all_documents = SourceDocument.nodes.all()
            chunks: List[Chunk] = []

            for document in all_documents:
                # Call chunker with just the text
                doc_chunks = self.chunker(document.content)
                chunk_list = [
                    Chunk(
                        t,
                        self._summarizer_model(),
                        self._embedding_model(),
                        __get_idempotency_key(t),
                        document,
                        agent,
                    )
                    for t in doc_chunks
                ]
                chunks.extend(chunk_list)

            return chunks

        all_chunks: List[Chunk] = __generate_chunks(self)
        logger.info(f"Split input into {len(all_chunks)} chunks.")

        # Get existing memory shards for this agent
        all_shards: List[MemoryShard] = []
        try:
            # Query for memory shards connected to this agent
            all_shards = agent.memory_shards.all()
        except Exception:
            # If no shards exist, that's fine
            pass
        logger.info(
            f"Got {len(all_shards)} existing Memory Shards for Agent {agent.name}."
        )

        shard_idempotency_keys: Set[str] = set([s.uid for s in all_shards])

        chunks_to_process: List[Chunk] = [
            c for c in all_chunks if c.idempotency_key not in shard_idempotency_keys
        ]

        logger.info(
            f"Processing {len(chunks_to_process)} chunks for {agent.name} as new memory shards."
        )

        shards: list[MemoryShard] = []
        failed: list[tuple[Chunk, Exception]] = []

        for chunk in chunks_to_process:
            try:
                shards.append(__process(self, chunk))
            except Exception as e:
                logger.error(f"Failed to process chunk {chunk.text}: {e}")
                failed.append((chunk, e))

        logger.info(f"Chunk processing completed. Processed {len(shards)} chunks succesfully.Failed Chunks: {len(failed)}")
        
        return shards
