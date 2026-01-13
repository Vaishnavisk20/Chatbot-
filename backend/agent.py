from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Import config
import config

# Import all tools
from tools import (
    get_purchase_links, track_shipment, get_application_details,
    faqdoc, errordscdoc, website_search, query_data_tool
)
from prompts import LIA_SYSTEM_PROMPT 

def get_agent_executor():
    # Use config for model name and temp
    llm = ChatOpenAI(
        model=config.OPENAI_MODEL_NAME, 
        temperature=config.OPENAI_TEMPERATURE,
        openai_api_key=config.OPENAI_API_KEY
    )
    
    # ✅ Add all RAG tools here
    tools = [
        get_purchase_links, track_shipment, get_application_details,
        faqdoc, errordscdoc, website_search, query_data_tool
    ]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", LIA_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return agent_executor