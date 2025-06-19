from typing import List, Tuple, Type, TypeVar, TYPE_CHECKING, Dict, Any, Optional

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
      vector_property: Optional[str] = None,
      k: int = 10
  ) -> List[Tuple['T', float]]:
      """
      Perform vector similarity search.

      Args:
          vector: Query vector
          vector_property: Name of the vector property (defaults to first in
VECTOR_INDEX_CONFIG)
          k: Number of results to return

      Returns:
          List of tuples (node, similarity_score)
      """
      if cls.__abstract_node__:
          raise TypeError(f"Cannot perform vector search on abstract node {cls.__name__}")

      if not cls.VECTOR_INDEX_CONFIG:
          raise ValueError(f"{cls.__name__} has no VECTOR_INDEX_CONFIG defined")

      if vector_property is None:
          vector_property = next(iter(cls.VECTOR_INDEX_CONFIG.keys()))

      index_name = f"{cls.__label__.lower()}_{vector_property}_index"

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
