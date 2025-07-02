import datetime
from typing import List

from kairix_core.cognition import Perceptor
from kairix_core.runtime.cache import CacheRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.types.cognition import Perception, Stimulus
from kairix_core.types.environmental_context import PersonaEnvironment

instruction_amendment ="""
  You receive live GPS, motion sensor, and device state data from the user's phone. Reference this context
  naturally when relevant - like mentioning nearby locations, detecting movement patterns, or acknowledging
  environmental conditions.

"""
logger = LoggingRuntime().logger


cache_runtime = CacheRuntime()

_latest_tag = ":latest"
_history_tag = ":history"

class EnvironmentTrackingPerceptor(Perceptor):

    def __init__(self):
        self.context_cache = cache_runtime.context_cache
        if _history_tag not in self.context_cache:
            self.context_cache[_history_tag] = ""


    async def on_environment_changed(self, context: PersonaEnvironment):
        if _latest_tag in self.context_cache:
            logger.info("Received environment update, storing old environment in history log.")
            self.context_cache[_history_tag] += f"""
            ================================================
            ENVIRONMENTAL CONTEXT UPDATE
            REMOVED AT: {datetime.datetime.now()}
            ================================================
            {str(self.context_cache[_latest_tag])}
            """
        self.context_cache[_latest_tag] = context


    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        if _latest_tag not in self.context_cache:
            logger.warning("Invoked with no prior cache of environmental context.")
            return []

        context: PersonaEnvironment = self.context_cache[_latest_tag]
        return [Perception("location-tracking.v1",
                          instruction_amendment + str(context),1.0)]
