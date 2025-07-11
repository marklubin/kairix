import dataclasses
from argparse import ArgumentParser, Namespace
from typing import Optional

from kairix_core.commands.command import KairixCommand


@dataclasses.dataclass
class ExtractionOptions:
    is_process_all: Optional[bool]
    n: Optional[int]
    offset: Optional[int]


class ExtractFactsFromSummaries(KairixCommand[ExtractionOptions]):
    def register(self, command: ArgumentParser):
        command.add_argument("--all", action="store_true")
        command.add_argument("-n", "--n", type=int, required=False)
        command.add_argument("-o", "--offset", type=int, required=False)

    def selected(self, options: Namespace) -> ExtractionOptions:
        if options.all:
            return ExtractionOptions(is_process_all=True, n=None, offset=None)

        if not options.n:
            raise Exception("n must be specified if not --all selected is.")

        n = options.n

        offset = options.offset if options.offset else 0
        return ExtractionOptions(is_process_all=False, n=n, offset=offset)
