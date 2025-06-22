from typing import List, Tuple, Type, TypeVar, TYPE_CHECKING, Dict, Any

from neomodel import StructuredNode, db

if TYPE_CHECKING:
  T = TypeVar('T', bound='VectorIndexedNode')


class VectorIndexedNode(StructuredNode):
  """
  Abstract base class for nodes with vector search capabilities.

  Subclasses should define VECTOR_INDEX_CONFIG to specify vector indexes:

  VECTOR_INDEX_CONFIG = {
      'embedding': {  # property name
          'dimensions': 384,
          'similarity_function': 'cosine'  # or 'euclidean'
      }
  }
  """

  __abstract_node__ = True  # Tell neomodel this is abstract

  VECTOR_INDEX_CONFIG: Dict[str, Dict[str, Any]] = {}

  @classmethod
  def install_labels(cls, quiet=True, stdout=None):
      """Override to create vector indexes during install_all_labels()"""
      super().install_labels(quiet=quiet, stdout=stdout)

      # Skip if abstract or no vector config
      if cls.__abstract_node__ or not cls.VECTOR_INDEX_CONFIG:
          return

      for prop_name, config in cls.VECTOR_INDEX_CONFIG.items():
          index_name = f"{cls.__label__.lower()}_{prop_name}_index"

          try:
              db.cypher_query(f"""
                  CREATE VECTOR INDEX {index_name} IF NOT EXISTS
                  FOR (n:{cls.__label__})
                  ON (n.{prop_name})
                  OPTIONS {{
                      indexConfig: {{
                          `vector.dimensions`: {config['dimensions']},
                          `vector.similarity_function`: '{config.get('similarity_function',
'cosine')}'
                      }}
                  }}
              """)
              if not quiet:
                  print(f"Created vector index: {index_name}")
          except Exception as e:
              if not quiet:
                  print(f"Vector index {index_name} may already exist: {e}")

  @classmethod
  def vector_search(
      cls: Type['T'],
      vector: List[float],
      k: int = 10,
      index_name: str = "vector_index_Concept_embedding"
  ) -> List[Tuple['T', float]]:


      results, _ = db.cypher_query(
          f"""
          CALL db.index.vector.queryNodes('{index_name}', $k, $vector)
          YIELD node, score
          RETURN node, score
          ORDER BY score DESC
          """,
          {"k": k, "vector": vector}
      )

      return [(cls.inflate(node), score) for node, score in results]
