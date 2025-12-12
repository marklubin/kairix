from main import MetricsRecord


class MetricsServer:

    def ingest(self, record: MetricsRecord):
        # store in sqlite
