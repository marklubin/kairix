from argparse import ArgumentParser, Namespace

from kairix_core.commands.command import KairixCommand


class UpdateSemanticGraphFromUnprocessedFacts(KairixCommand):
    def register(self, command: ArgumentParser):
        pass

    def selected(self, options: Namespace):
        pass
