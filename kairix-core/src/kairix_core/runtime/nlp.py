from sentence_transformers import SentenceTransformer
from torch.distributed.elastic.utils import get_env_variable_or_raise


class NLPRuntime:
    _instance = None
    _embedding_model = get_env_variable_or_raise("KAIRIX_SEMANTIC_EMBEDDING_MODEL")
    _emedding_dims = int(get_env_variable_or_raise("KAIRIX_SEMANTIC_EMBEDDING_DIMS"))

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.semantic_embedder = SentenceTransformer(
            NLPRuntime._embedding_model,
            truncate_dim=NLPRuntime._emedding_dims)
