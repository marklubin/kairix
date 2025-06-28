class LoggingRuntime:
    _instance = None

    FORMAT = "[%(filename)s:%(funcName)s:L%(lineno)d][%(levelname)s](%(asctime)s) %(message)s"
    DTF = "%H:%M:%S"

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    def __init__(self, logger_name:str ="kairix"):
        import logging

        from rich.console import Console
        from rich.logging import RichHandler
        from rich.style import Style
        from opentelemetry.instrumentation.logging import LoggingInstrumentor

        #
        # from uvicorn.config import Config
        #
        # Config.configure_logging = lambda _:\
        #     Console().print("🔪Bypassing uvicorn logging hijack.",
        #                   style=Style(color="hot_pink3", bgcolor="aquamarine1", bold=True, encircle=True))
        # #trace.set_tracer_provider(TracerProvider())
        #LoggingInstrumentor().instrument(set_logging_context=True)

        self.logger = logging.getLogger(logger_name)
        #self.tracer = trace.get_tracer(logger_name)

        self.console = Console(width=200)
        self.rich_handler = RichHandler(
                    console=self.console,
                    tracebacks_show_locals=True,
                    rich_tracebacks=True,
                    show_path=False,
                    show_time=False,
                    show_level=False,
                    markup=True,
                    enable_link_path=True,
                )

        logging.basicConfig(
            force=True,
            format=LoggingRuntime.FORMAT,
            datefmt= LoggingRuntime.DTF,
            handlers=[self.rich_handler],
            level="INFO")
