from argparse import ArgumentParser, Namespace

from pydantic import BaseModel, Field

from kairix_core.commands.command import KairixCommand


class ExtractionOptions(BaseModel):
    is_process_all: bool = Field(...)
    offset: int | None = Field(is_required=False)
    n: int | None = Field(is_required=False)


class ExtractFactsFromSummaries(KairixCommand[ExtractionOptions]):
    def register(self, command: ArgumentParser):
        summary_selection = command.add_mutually_exclusive_group()
        summary_selection.add_argument(
            "--all",
            "-a",
            type=bool,
            help="If set extract from all unprocessed Summaries.",
        )

        fine_grained_selection = summary_selection.add_argument_group()
        fine_grained_selection.add_argument(
            "-n",
            "--n",
            type=int,
            help="Number of summaries to process.",
        )
        fine_grained_selection.add_argument(
            "-o",
            "--offset",
            type=int,
            help="Offset into db to start from, "
            "for reprocessing in case of partial failure only.",
        )

    def selected(self, options: Namespace) -> ExtractionOptions:
        if options.all:
            return ExtractionOptions(is_process_all=True)

        assert options.n
        n = options.n

        offset = options.offset if options.offset else 0
        return ExtractionOptions(is_process_all=False, n=n, offset=offset)
