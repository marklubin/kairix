from rich import print
from diskcache import  Index, FanoutCache
class CacheRuntime:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self):
        self._c = FanoutCache(".cache")

    def indices(self):
        return [i for  i in self._c._indexes]


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._c.close()

    def __getattr__(self, item: str) -> Index:

        return self._c.index(item)


    def _index_stats(self, index: Index) -> None:
        print("[green]------------------------------")
        print(f"[green][INDEX]{index.directory}[/]")
        print("[green]------------------------------")

        print(f"# of items: [aqua]{len(index)}")

        if len(index) < 1:
            return

        sample = index.peekitem()

        print("\n---------Sample Item------------")
        print(sample)
        print("-----------------------------------\n")

        choice = input("Print keys?(y)")

        if choice == "y":
            for key in index:
                print(f"\t* {key}")




    def stats(self) -> None:
        print("[green]-----------Indices----------[/]")
        mapping: dict[int, Index] = dict()
        for i, index in enumerate(self.indices()):
            print(f"[purple]- {i}. {str(index)}, Entries: {len(index)}")
            mapping[i] = index

        while True:
            choice_str = input("Select Index to view or 'exit' to exit this screen.")

            try:
                choice = int(choice_str)
            except Exception:
                break

            if choice not in mapping:
                break

            self._index_stats(mapping[choice])
