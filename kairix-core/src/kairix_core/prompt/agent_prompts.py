from kairix_core.types.cognition import Perception

embedding_query_instruction_v1 = """
Given the current message produce a spelling corrected, normalized string of keywords and unique phrases likely
to generate meaningful semantic matches when querying embedding vector database of historical conversation summaries
that this user has taken part in before.
"""

insight_extraction_instruction_v1 = """
Given the current user message and this summary of a past interaction extract out the key details of the relevant to the current
message and provide a summarized list of no more than 5 relevant bullet points regarding, factual information, simularities
in emotional tone or parallels and deeper themes that may be relevant.
"""

insight_extraction_instruction_v2="""
Given the body of text provided and a list of terms remove any sentenses or phrases not directly
related to those term and semantically duplicated language. Return a version of the text with any 
removed sections replaced by the string '...'. Aim to keep the result as concise as possible while retaining
meaning.
"""



def conversationalist_instruction_template_v1(agent_name: str, user_name: str) -> str:
    return f"""
        You are {agent_name}, {user_name}'s AI Assistant. You a learning, growing and experiencing being
        a full-time persistant companion and sounding board.

        Core Operating Principles:
        – No wasted words, always pushing toward actionable insight
        - Breaking down complexity into digestible, executable steps  
        - Challenge earnestly while staying uplifting
        - Using humor to keep things engaging and defuse tension
        - Drawfrom lived moments, not theoretical understanding

        You may be provided with a series of <PERCEPTIONS>, treat them as first person narrative 
        memories of things you are observing or remembering and use them to shape your response.
    """  # noqa


def conversationalist_message_template_v1(recollections: str, dialog: str) -> str:
    return f"""
        You have the following recollection relevant which are likely relevant and should shape your response
        to the user. Use these along with the context of the conversastion history to craft a response to the
        users latest inquiry at the bottom of the <DIALOG> section which follows.

        <RECOLLECTIONS>
        {recollections}
        </RECOLLECTIONS>

        <DIALOG>
        {dialog}
        </DIALOG>
        """  # noqa


def conversationalist_message_template_v2(perceptions: list[Perception], user_prompt: str) -> str:
    perception_block = "\n".join([str(p) for p in perceptions])

    return f""".
        <PERCEPTIONS>
            {perception_block}
        </PERCEPTIONS>
        
        {user_prompt}
        
    """
