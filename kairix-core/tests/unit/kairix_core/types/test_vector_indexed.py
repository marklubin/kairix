import pytest
from unittest.mock import patch, Mock

from kairix_core.types.vector_indexed import VectorIndexedNode


class TestVectorIndexedNode:
    """Test suite for VectorIndexedNode functionality.
    
    Note: Due to neomodel's metaclass system, some tests work around
    the framework's internals by testing the logic directly.
    """
    
    def test_vector_index_config_default(self):
        """Test that default VECTOR_INDEX_CONFIG is empty"""
        assert VectorIndexedNode.VECTOR_INDEX_CONFIG == {}

    def test_class_has_abstract_marker(self):
        """Test that VectorIndexedNode is marked as abstract in its definition"""
        # Check the class definition includes the abstract marker
        import inspect
        source = inspect.getsource(VectorIndexedNode)
        assert "__abstract_node__ = True" in source

    @patch('kairix_core.types.vector_indexed.db')
    def test_vector_search_functionality(self, mock_db):
        """Test the core vector search functionality without metaclass issues"""
        # Create a mock that mimics a concrete node class
        mock_cls = Mock()
        mock_cls.__name__ = 'TestNode'
        mock_cls.__label__ = 'TestNode'
        mock_cls.__abstract_node__ = False
        mock_cls.VECTOR_INDEX_CONFIG = {
            'embedding': {'dimensions': 3}
        }
        
        # Mock database response
        raw_node = {'id': 1}
        mock_db.cypher_query.return_value = ([(raw_node, 0.95)], None)
        
        # Mock inflate to return a simple object
        inflated = Mock()
        mock_cls.inflate = Mock(return_value=inflated)
        
        # Call the unbound method directly
        result = VectorIndexedNode.vector_search.__func__(
            mock_cls, [1.0, 2.0, 3.0], k=5
        )
        
        # Verify results
        assert len(result) == 1
        assert result[0] == (inflated, 0.95)
        
        # Verify the query structure
        query, params = mock_db.cypher_query.call_args[0]
        assert "CALL db.index.vector.queryNodes" in query
        assert "'testnode_embedding_index'" in query
        assert params == {"k": 5, "vector": [1.0, 2.0, 3.0]}

    def test_vector_search_validation(self):
        """Test vector search validation logic"""
        # Test abstract node check
        mock_cls = Mock()
        mock_cls.__name__ = 'AbstractNode'
        mock_cls.__abstract_node__ = True
        
        with pytest.raises(TypeError, match="Cannot perform vector search on abstract node"):
            VectorIndexedNode.vector_search.__func__(mock_cls, [1.0])
        
        # Test missing config check
        mock_cls.__abstract_node__ = False
        mock_cls.VECTOR_INDEX_CONFIG = {}
        
        with pytest.raises(ValueError, match="has no VECTOR_INDEX_CONFIG defined"):
            VectorIndexedNode.vector_search.__func__(mock_cls, [1.0])

    @patch('kairix_core.types.vector_indexed.db')
    def test_vector_property_selection(self, mock_db):
        """Test vector property selection logic"""
        mock_cls = Mock()
        mock_cls.__label__ = 'TestNode'
        mock_cls.__abstract_node__ = False
        mock_cls.VECTOR_INDEX_CONFIG = {
            'first': {'dimensions': 3},
            'second': {'dimensions': 3}
        }
        mock_db.cypher_query.return_value = ([], None)
        
        # Test default property (should use first)
        VectorIndexedNode.vector_search.__func__(mock_cls, [1, 2, 3])
        query = mock_db.cypher_query.call_args[0][0]
        assert "'testnode_first_index'" in query
        
        # Test specific property
        VectorIndexedNode.vector_search.__func__(
            mock_cls, [1, 2, 3], vector_property='second'
        )
        query = mock_db.cypher_query.call_args[0][0]
        assert "'testnode_second_index'" in query

    @patch('kairix_core.types.vector_indexed.db')
    def test_install_labels_vector_index_creation(self, mock_db):
        """Test the vector index creation logic"""
        # Create a mock class that simulates a concrete node
        mock_cls = Mock()
        mock_cls.__label__ = 'TestNode'
        mock_cls.__abstract_node__ = False
        mock_cls.VECTOR_INDEX_CONFIG = {
            'embedding': {
                'dimensions': 384,
                'similarity_function': 'cosine'
            }
        }
        
        # Mock the super() call to avoid issues
        with patch('kairix_core.types.vector_indexed.super') as mock_super:
            mock_super.return_value.install_labels = Mock()
            
            # Call install_labels
            VectorIndexedNode.install_labels.__func__(mock_cls, quiet=False)
            
            # Verify parent was called
            mock_super.return_value.install_labels.assert_called_once_with(
                quiet=False, stdout=None
            )
            
            # Verify index creation query
            mock_db.cypher_query.assert_called_once()
            query = mock_db.cypher_query.call_args[0][0]
            
            assert "CREATE VECTOR INDEX testnode_embedding_index IF NOT EXISTS" in query
            assert "FOR (n:TestNode)" in query
            assert "ON (n.embedding)" in query
            assert "`vector.dimensions`: 384" in query
            assert "`vector.similarity_function`: 'cosine'" in query

    @patch('kairix_core.types.vector_indexed.db')
    def test_install_labels_default_similarity(self, mock_db):
        """Test that default similarity function is cosine"""
        mock_cls = Mock()
        mock_cls.__label__ = 'TestNode'
        mock_cls.__abstract_node__ = False
        mock_cls.VECTOR_INDEX_CONFIG = {
            'embedding': {'dimensions': 128}  # No similarity_function
        }
        
        with patch('kairix_core.types.vector_indexed.super'):
            VectorIndexedNode.install_labels.__func__(mock_cls)
            
            query = mock_db.cypher_query.call_args[0][0]
            assert "`vector.similarity_function`: 'cosine'" in query

    @patch('kairix_core.types.vector_indexed.db')
    def test_install_labels_skip_conditions(self, mock_db):
        """Test conditions where install_labels should skip index creation"""
        with patch('kairix_core.types.vector_indexed.super') as mock_super:
            mock_super.return_value.install_labels = Mock()
            
            # Test 1: Skip abstract nodes
            mock_cls = Mock()
            mock_cls.__abstract_node__ = True
            mock_cls.VECTOR_INDEX_CONFIG = {'embedding': {'dimensions': 128}}
            
            VectorIndexedNode.install_labels.__func__(mock_cls)
            mock_db.cypher_query.assert_not_called()
            
            # Test 2: Skip nodes without config
            mock_cls.__abstract_node__ = False
            mock_cls.VECTOR_INDEX_CONFIG = {}
            
            VectorIndexedNode.install_labels.__func__(mock_cls)
            mock_db.cypher_query.assert_not_called()

    @patch('kairix_core.types.vector_indexed.db')
    def test_install_labels_error_handling(self, mock_db):
        """Test error handling during index creation"""
        mock_db.cypher_query.side_effect = Exception("Index already exists")
        
        mock_cls = Mock()
        mock_cls.__label__ = 'TestNode'
        mock_cls.__abstract_node__ = False
        mock_cls.VECTOR_INDEX_CONFIG = {
            'embedding': {'dimensions': 128}
        }
        
        with patch('kairix_core.types.vector_indexed.super'):
            # Should not raise exception
            VectorIndexedNode.install_labels.__func__(mock_cls, quiet=False)

    @patch('kairix_core.types.vector_indexed.db')
    def test_multiple_vector_indexes(self, mock_db):
        """Test creating multiple vector indexes"""
        mock_cls = Mock()
        mock_cls.__label__ = 'TestNode'
        mock_cls.__abstract_node__ = False
        mock_cls.VECTOR_INDEX_CONFIG = {
            'embedding1': {'dimensions': 384},
            'embedding2': {'dimensions': 768, 'similarity_function': 'euclidean'}
        }
        
        with patch('kairix_core.types.vector_indexed.super'):
            VectorIndexedNode.install_labels.__func__(mock_cls)
            
            # Should create two indexes
            assert mock_db.cypher_query.call_count == 2
            
            # Get both queries
            calls = [call[0][0] for call in mock_db.cypher_query.call_args_list]
            
            # Verify both indexes
            assert any("testnode_embedding1_index" in q for q in calls)
            assert any("testnode_embedding2_index" in q for q in calls)
            assert any("'euclidean'" in q for q in calls)