import asyncio
from typing import Literal, Optional, Any

from agents import Agent, Runner, ModelSettings

from neomodel import config as neomodel_config
from neomodel import db
from pydantic import BaseModel
from rich.logging import RichHandler
from rich.console import Console
import logging

from sentence_transformers import SentenceTransformer
from kairix_core.types import SemanticUnit, Summary

console = Console(width=140)
logging.basicConfig(
    handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
    level="INFO",
)
logger = logging.getLogger()

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"


CYPHER_QUERY = """
CALL db.index.vector.queryNodes('semantic_unit_SemanticUnit_embedding',
    $k, $query_vector)
YIELD node, score 
RETURN node, score 
ORDER BY score DESC
"""
embedder = SentenceTransformer(
    "sentence-transformers/all-mpnet-base-v2", device="mps", truncate_dim=128
)


def setup():
    neomodel_config.DATABASE_URL = NEO4J_URL
    db.set_connection(NEO4J_URL)
    db.install_all_labels()


def cypher_query(query: str, params: dict[str, Any]) -> tuple[list[Any], Any]:
    result = db.cypher_query(query, params)
    for o in result:
        logger.info(
            f"Embedding Index Query Found [bold green]{str(o[0])}[\] "
            f"with Distance [bold green]{str(o[1])}[\]."
        )
    return result  # type: ignore[no-any-return]


# Define data models first
class Unit(BaseModel):
    type: Literal["entity", "action", "attribute", "topic", "event"]
    short_description: str
    id: str


class Relation(BaseModel):
    u: Unit
    v: Unit
    relationship_descriptor: str


class Extraction(BaseModel):
    relationships: Optional[list[Relation]]


process_description = """
Step 1 - Goal Definition
Define a core set of objective and goals regarding the purpose of extracting a KB of data.

Step 2 - Parse Raw Inputs

for each source text
    parse out all the semantic units and their relationships
    for each semanatic unit 
        de-dupe in existing dataset or create if new
        if not new record an additional occurence of this semantic unit
    for each relationship
        create the relationship between the units if it doesnt exist
        if it does increment the number of occurences 


Step 3- Retention Strategy

Evaluate the semantic units for retention in the online KB. Use agent's subjective evaluation of whether a semantic unit
is relevant to the systems goals in combination with weighting by the number of occurence to determine if units ae retaiined.


Step 4 - Searching Store

Given a new piece of textual infromation
parse it into individual semantic units using a cannonical formulation
for each unit
    Do a fuzzy match query to find exisiting retained units
    traverse graph to a certain depth to regain addiitional contextual infromation
    in theory summary this connected network of units into a short paragraph of known information and 
    intention 
    
Step 5 -Training
Eventually use semantic unit data as time-series analysis to refine semantic unit selection strategy as well as refine goals.
Semantic Units themselves can be used to represent the encoding of the goals. Such that the goals and assistant responses can be
encoded as ATTRIBUTES and ACTION used to fine tune model to recognize which of it's ACTIONs related to which of it's stated ATTIRBUTES
and how well having taken that ACTION either resulted in an outcome aligened with that attribute or didn't. It can also be used to 
decision makig about how to respond by asking how well any possible response aligneed with them.
"""

# Agent 1: World Facts Extractor
world_facts_prompt = """
EXTRACT OBJECTIVE WORLD FACTS from the text that are NOT specific to the user/assistant relationship.

Focus on:
- Technical facts: "servers produce:noise", "colocation costs:more_than_home_hosting"
- Domain knowledge: "power_management requires:planning", "basements provide:power_access"
- General truths: "Wi-Fi has:lower_reliability_than_ethernet", "powerline_adapters enable:network_over_power"
- System properties: "AI_servers require:significant_power", "home_networks support:remote_access"
- Relationships between other people 
- Information about geographic locations



Ignore:
- User-specific information (Mark's preferences)
- Assistant behaviors or learnings
- Conversational details


The currently available schema keys for the world state are supplied below.



Output format: Extract entities and relationships representing objective facts about the world.
"""

world_facts_extractor = Agent(
    "world_facts",
    instructions=world_facts_prompt,
    output_type=Extraction,
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.3, max_tokens=8000),
)

# Agent 2: User Profile Extractor
user_profile_prompt = """
EXTRACT USER INFORMATION for long-term pattern recognition and personalization.

Focus on:
- Identity: Names, roles, relationships
- Traits: "values:transparency", "trait:resourceful", "trait:considerate"
- Concerns: "fears:unintended_consequences", "worries:disturbing_others"
- Preferences: "prefers:practical_solutions", "seeks:efficiency"
- Context: "has:AI_server_at_home", "lives_with:others"
- History: Past decisions, experiences mentioned

Resolve all pronouns to the user's name. Extract information that would help understand and predict user behavior over time.

	All of this information Will be specified in the terms of a knowledge graph database new most describe all of the facial information derivable about the user in a way that can be represented in this form that is to say all these things here should be relationships between the user entity themselves or a part of the user entity or any closely related and intrinsically tied aspect for instance possessions emotional well-being career information social life characteristics and is your job to build a comprehensive internal model of this individual
 
Output format: User-centric entities and relationships forming a persistent user profile. 
"""

user_profile_extractor = Agent(
    "user_profile",
    instructions=user_profile_prompt,
    output_type=Extraction,
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.5, max_tokens=8000),
)

# Agent 3: Assistant Cognitive Extractor
assistant_cognitive_prompt = """
EXTRACT ASSISTANT BEHAVIORS AND LEARNINGS through the lens of core AI directives.

CORE DIRECTIVES:
1. Be helpful and provide practical solutions
2. Understand and adapt to user needs
3. Maintain awareness of social/ethical implications
4. Learn from interactions to improve future responses

Extract:
- Actions taken: "AI_assistant offered:time_boxing_strategies", "AI_assistant provided:remote_access_options"
- Learnings: "AI_assistant learned:reassurance_reduces_anxiety", "AI_assistant discovered:user_values_discretion"
- Adaptations: "AI_assistant adapted:technical_solutions_to_social_concerns"
- Effectiveness: "time_boxing_strategy resulted:user_satisfaction", "cost_comparison helped:decision_making"

You will not only do this but you will as well format all of the extracted insights in terms of a knowledge graph hierarchy where each note in the graph represents one of the specified right do not simply state or recount factual information about the world or capture any information about the user involved or any other individuals involved if it is not directly related or a byproduct of an action State of mind wave being attempt or an internal model of our thought process that is demonstrated in the tax by the artificial intelligence assistive agent.

Output format: Assistant-centric relationships showing cognitive processes and their effects.
"""

assistant_cognitive_extractor = Agent(
    "assistant_cognitive",
    instructions=assistant_cognitive_prompt,
    output_type=Extraction,
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.7, max_tokens=8000),
)


async def extract_knowledge(
    summary: Summary, extraction_agents: list[Agent]
) -> list[Relation]:
    tasks_to_await = [
        Runner.run(agent, summary.summary_text) for agent in extraction_agents
    ]

    results = await asyncio.gather(*tasks_to_await)
    extractions = [r.final_output for r in results]
    all_extracted_rels = []

    for a, e in zip(extraction_agents, extractions):
        logger.debug(f"Inspecting extraction for {a.name}.")

        if e and e.relationships and len(e.relationships) > 0:
            logger.debug(f"Exracted Relaitonships.{e.relationships}")
            all_extracted_rels.extend(e.relationships)
        else:
            logger.warning("Extraction was empty.")

    return all_extracted_rels


def vector_search(
    query_vector: list[float], k: int = 2
) -> list[tuple[SemanticUnit, float]]:
    results, _ = db.cypher_query(CYPHER_QUERY, {"k": k, "query_vector": query_vector})
    return [(SemanticUnit.inflate(node), score) for node, score in results]


SCORE_THRESHOLD = 0.85


def dedupe_semantic_unit(unit: Unit) -> SemanticUnit:
    logger.debug(
        f"Creating or deduping Semantic unit for {unit.id}, type: {unit.type}."
    )
    maybe_unit = SemanticUnit.nodes.first_or_none(uid=unit.id)

    # Case I - Exact Match Exists - We require that both id and type of unit match
    if maybe_unit and maybe_unit.type == unit.type:
        logger.debug("Found exact match of type. Returning.")
        maybe_unit.descriptions.append(unit.short_description)
        maybe_unit.occurences += 1
        maybe_unit.save()
        return maybe_unit

    # Case II - Embedding match is close enough, should match by type in search algo
    embedding = embedder.encode(unit.id)
    matches: list[tuple[SemanticUnit, float]] = vector_search(embedding, 1)
    if (
        len(matches) >= 1
        and matches[0][1] >= SCORE_THRESHOLD
        and matches[0][0].type == unit.type
    ):
        semantic_unit: SemanticUnit = matches[0][0]
        logger.debug(
            f"Found semantic match via embedding index, matched is UID = [green]{semantic_unit.uid}[\]"
        )
        semantic_unit.occurences = semantic_unit.occurences + 1
        semantic_unit.embedding = embedding.tolist()
        semantic_unit.descriptions.append(unit.short_description)

        # TODO considering adjusting embedding to weighted midpoint
        semantic_unit.save()
        return semantic_unit

    # Case III - Never node with this type and id before

    logger.debug("Did not match any extant semantic unit, creating...")
    semantic_unit = SemanticUnit(
        uid=unit.id,
        descriptions=[unit.short_description],
        type=unit.type,
        embedding=embedding,
    )

    semantic_unit.save()
    return semantic_unit


async def process_knowledge(n_limit: int):
    extraction_type_id = "graph-processor-v1"
    n_limit = max(1, n_limit)
    logger.info(f"[red bold]Building knowledge graph from {n_limit} summaries.[/]")
    for i, summary in enumerate(Summary.nodes.all()):
        logger.info(f"Beginning Extraction for Summary: {summary.uid}")
        if extraction_type_id in summary.extractions_performed:
            logger.info("Already ran extraction sucessfully, skipping.")
            continue

        logger.info(
            f"\n{'=' * 20}\nExtracting semantic Structure.. {i + 1}\n{'=' * 20}"
        )

        with console.status("Extrating Semantic Structure", spinner="shark"):
            # Extract with specialized agents
            extractions = await extract_knowledge(
                summary,
                [
                    world_facts_extractor,
                    user_profile_extractor,
                    assistant_cognitive_extractor,
                ],
            )

        logger.info("Finished extraction...deduping and persisting to DB..")
        print(f"Processing {len(extractions)} extracted semantic units.")

        with db.transaction:
            try:
                for rel in extractions:
                    u_unit = dedupe_semantic_unit(rel.u)
                    v_unit = dedupe_semantic_unit(rel.v)

                    logger.info(
                        f"Handling relationship between {u_unit.uid} and {v_unit.uid}"
                        f" described as {rel.relationship_descriptor}."
                    )
                    unit_relationship = u_unit.related.relationship(v_unit)
                    if unit_relationship:
                        logger.info(
                            "Adding to existing relationship and strengthing connection."
                        )
                        unit_relationship.descriptions.append(
                            rel.relationship_descriptor
                        )
                        unit_relationship.occurrences += 1
                        unit_relationship.save()
                    else:
                        logger.info("Creating new relationship between Semantic Units.")
                        u_unit.related.connect(
                            v_unit,
                            {
                                "descriptions": [rel.relationship_descriptor],
                                "occurrences": 1,
                            },
                        )
                    logger.info("Finished with extractions commiting to db.")
                    summary.extractions_performed.append(extraction_type_id)
                    summary.save()
            except Exception as e:
                logger.error(
                    "Encounter fatal error when persisting to db, rolling back.",
                    exc_info=e,
                )
                raise e

        if i >= n_limit - 1:
            break


if __name__ == "__main__":
    import os

    if not os.getenv("PYTEST_RUN"):
        setup()
    asyncio.run(process_knowledge(10))
