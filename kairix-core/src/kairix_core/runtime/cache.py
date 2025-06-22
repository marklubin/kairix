from diskcache import  Index, FanoutCache
class CacheRuntime:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self):
        self._c = FanoutCache(".cache")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._c.close()

    def __getattr__(self, item) -> Index:

        return self._c.index(item)
