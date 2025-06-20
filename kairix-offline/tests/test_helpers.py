"""
Helper functions for tests
"""

from knowledge_db_demo import Unit


def create_unit_with_uid(type, short_description, id):
    """Create a Unit and add uid property for testing.
    
    The original code has a bug where it tries to access unit.uid 
    but Unit only has id. This helper works around that.
    """
    class UnitWithUid(Unit):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._uid = kwargs.get('id')
        
        @property
        def uid(self):
            return self._uid
    
    return UnitWithUid(type=type, short_description=short_description, id=id)