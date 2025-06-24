
from agents import Agent
from pydantic import BaseModel


class CognitiveState(BaseModel):
    enrichment_candidates = dict[str, list[str]]









class ContextEnrichmentLifecycle:

    def on_update(self):
        pass

    def on_inquire(self):
        pass

    def on_expire(self):
        pass
