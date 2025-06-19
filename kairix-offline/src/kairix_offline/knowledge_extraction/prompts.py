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
