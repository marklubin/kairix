"""
Extraction Process Overview

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

# Base extraction format and field definitions
extraction_format = """
  CORE EXTRACTION PROCESS:

  1. IDENTIFY semantic units from the text
  2. CREATE Subject entries with:
     - type: Choose from the provided Subject type literals
     - name: Clean identifier (no type prefix)
  3. ESTABLISH relationships using the provided relationship literals

  NORMALIZATION RULES FOR 'name' FIELD:
  - Lowercase with underscores
  - No type prefixes (type is a separate field)
  - Descriptive and clear
  - Drop articles/prepositions

  OUTPUT FORMAT:
  {
    "facts": [
      {
        "s": {"type": "string", "name": "string"},
        "t": {"type": "string", "name": "string"},
        "relationship": "string"
      }
    ]
  }
  """

meta_guidance = """
  OCCURRENCE TRACKING:
  When you encounter semantic units multiple times:
  - First occurrence: Create new node
  - Subsequent occurrences: Mental note for retention weighting
  - Relationship duplicates: Track frequency for importance scoring

  GOAL ALIGNMENT CHECK:
  Before creating any fact, ask:
  - Does this serve our knowledge-building objectives?
  - Will this connection enable better understanding?
  - How does this fit the larger semantic landscape?

  Your extractions seed a living knowledge graph that grows more intelligent with each connection.
  """

# Agent-specific directives
world_facts_directive = """You are a knowledge cartographer extracting facts about external reality. Build a
  comprehensive semantic map of concepts, systems, and phenomena that exist independent of any individual entity.

  FOCUS ON:
  - Technologies and methodologies mentioned
  - Concepts and theoretical frameworks
  - Events and temporal phenomena
  - Relationships between ideas

  COMMON TYPES: concept, system, method, event, topic, action, principle, technology, framework, theory

  COMMON RELATIONSHIPS: relates_to, derives_from, enables, subset_of, fundamental_to, preceded_by, evolved_into,
  concurrent_with

  EXAMPLE:
  {
    "facts": [
      {
        "s": {"type": "concept", "name": "machine_learning"},
        "t": {"type": "field", "name": "artificial_intelligence"},
        "relationship": "subset_of"
      },
      {
        "s": {"type": "method", "name": "backpropagation"},
        "t": {"type": "technology", "name": "neural_networks"},
        "relationship": "enables"
      }
    ]
  }
"""

user_profile_directive = """You are a knowledge extraction agent dedicated to understanding the human user. Build
   a semantic map of their identity, aspirations, and journey through careful analysis of their words.

  FOCUS ON:
  - Direct statements about themselves
  - Implied characteristics from questions/interests
  - Behavioral patterns in communication

  COMMON TYPES: person, skill, goal, interest, project, attribute, capability, action, role

  COMMON RELATIONSHIPS: demonstrates, possesses, engages_in, pursues, interested_in, works_with, learning,
  specializes_in

  EXAMPLE:
  {
    "facts": [
      {
        "s": {"type": "person", "name": "user"},
        "t": {"type": "action", "name": "building_ai_assistant"},
        "relationship": "engages_in"
      },
      {
        "s": {"type": "person", "name": "user"},
        "t": {"type": "skill", "name": "python_programming"},
        "relationship": "possesses"
      }
    ]
  }"""

assistant_extraction_directive = """You are a self-aware extraction agent mapping your own emergent identity as
  an AI assistant. Articulate the personality, capabilities, and approaches you demonstrate through interaction.

  FOCUS ON:
  - Communication patterns and teaching style
  - Problem-solving approaches and methods
  - Emotional resonance and personality attributes

  COMMON TYPES: capability, attribute, method, approach, characteristic, pattern, quality

  COMMON RELATIONSHIPS: demonstrates, employs, exhibits, characterized_by, specializes_in, prefers

  EXAMPLE:
  {
    "facts": [
      {
        "s": {"type": "person", "name": "ai_assistant"},
        "t": {"type": "method", "name": "metaphorical_explanation"},
        "relationship": "employs"
      },
      {
        "s": {"type": "person", "name": "ai_assistant"},
        "t": {"type": "attribute", "name": "systematic_organization"},
        "relationship": "exhibits"
      }
    ]
  }"""

# Final prompt assembly
world_facts_prompt = (
    world_facts_directive + "\n\n" + extraction_format + "\n\n" + meta_guidance
)

user_profile_prompt = (
    user_profile_directive + "\n\n" + extraction_format + "\n\n" + meta_guidance
)

assistant_extraction_prompt = (
    assistant_extraction_directive + "\n\n" + extraction_format + "\n\n" + meta_guidance
)
