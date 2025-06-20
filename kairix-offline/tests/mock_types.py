"""
Mock types for testing knowledge_db_demo without requiring the actual Neo4j models
"""

from unittest.mock import Mock


class MockStructuredNode:
    """Base class for mock Neo4j nodes"""
    nodes = Mock()
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def save(self):
        pass
    
    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)


class MockSemanticUnit(MockStructuredNode):
    def __init__(self, uid=None, descriptions=None, type=None, occurences=1, embedding=None):
        self.uid = uid
        self.descriptions = descriptions or []
        self.type = type
        self.occurences = occurences
        self.embedding = embedding or []
        self.relates = Mock()
        self.relates.relationship = Mock(return_value=None)
        self.relates.connect = Mock()
    
    def save(self):
        pass


class MockSemanticRelationship:
    def __init__(self, descriptions=None, occurences=1):
        self.descriptions = descriptions or []
        self.occurences = occurences
    
    def save(self):
        pass


class MockSummary(MockStructuredNode):
    def __init__(self, summary_text=""):
        self.summary_text = summary_text


# Create mock classes that can be imported
SemanticUnit = MockSemanticUnit
SemanticRelationship = MockSemanticRelationship
Summary = MockSummary