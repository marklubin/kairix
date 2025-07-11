from src.kairix_metrics.types import WritableMetrics, MetricsRecord


class MetricContext:

    def __init(self,*,  reporter, service):
        self.reporter = reporter
        self.service = service

    def __aenter__(self)->WritableMetrics:
        metrics = WritableMetrics(service)
        pass


    def _aexit__(self)-> None:
        pass # clean up metrics no more writes or die()
        #Turns rwitable into a Metrics instance and esends to reporter


class MetricReporter:

    def report(self, metrics: MetricsRecord):
        pass


class AsyncHttpMetricsReporter(MetricReporter):

    def report(self, metrics: MetricsRecord):
        http ost to endpoint
