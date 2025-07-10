from datetime import datetime

class MetricsRecord:
    annotations: dict[str, str]
    timings: dict[str, float]
    counts: dict[str, int]
    service: str
    operation: str
    segement: str
    treatment: str
    start: datetime
    end: datetime


class WritableMetrics:



    def __init__(self):
        self.start = datetime.now()

        etc.


    def __end__(self):
        end = datetime.now()


    def annotate(self, symbol: str, annotation: str):
        pass

    def add_timing(self, name: str, timing: float):
        pass
    #etc
