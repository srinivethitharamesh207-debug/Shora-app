from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.tools import tool

wikipedia_api = WikipediaAPIWrapper()
wikipedia_tool = WikipediaQueryRun(api_wrapper=wikipedia_api)

@tool
def search_tool(query: str) -> str:
    """Search Wikipedia for information about a topic."""
    return wikipedia_tool.run(query)

api_wrapper = WikipediaAPIWrapper(top_k_results=5, doc_content_chars_max=10000)
wiki_tool_obj = WikipediaQueryRun(api_wrapper=api_wrapper)

@tool
def wiki_tool(topic: str) -> str:
    """Get detailed Wikipedia information about a topic."""
    return wiki_tool_obj.run(topic)

@tool
def save_tooltext(text: str) -> str:
    """Save text data to a file or storage."""
    return f"Saved: {text}"

