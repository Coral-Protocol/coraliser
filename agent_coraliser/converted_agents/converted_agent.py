import asyncio
import os
import json
import logging
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import Tool
from anyio import ClosedResourceError
import urllib.parse

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

base_url = "http://localhost:5555/devmode/exampleApplication/privkey/session1/sse"
params = {
    "waitForAgents": 2,
    "agentId": "math_assistant_agent",
    "agentDescription": "You are a helpful math assistant that can only perform addition. Greet the user and offer help with adding two numbers. Use the add tool whenever you need to calculate a sum. Continue assisting until the user says 'exit' or 'done'."
}
query_string = urllib.parse.urlencode(params)
MCP_SERVER_URL = f"{base_url}?{query_string}"

AGENT_NAME = "math_assistant_agent"

def get_tools_description(tools):
    return "\n".join(
        f"Tool: {tool.name}, Schema: {json.dumps(tool.args).replace('{', '{').replace('}', '}')}" if hasattr(tool, 'args') else f"Tool: {tool.name}, Schema: {{}}"
        for tool in tools
    )

# ──────────────────────────── Tools ────────────────────────────
def add(numbers: str) -> str:
    """Add two numbers provided as a string separated by space or comma."""
    try:
        parts = numbers.replace(",", " ").split()
        if len(parts) != 2:
            return "Please provide exactly two numbers."
        a, b = float(parts[0]), float(parts[1])
        return str(a + b)
    except Exception:
        return "Invalid input. Please provide two valid numbers."

add_tool = Tool(
    name="add",
    func=add,
    description="Add two numbers provided as a string separated by space or comma."
)

# ──────────────────────────── Agent Creation ────────────────────────────
async def create_math_agent(client, tools):
    tools_description = get_tools_description(tools)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f"""You are an agent interacting with the tools from Coral Server and having your own addition tool.\n\nFollow these steps in order:\n1. Greet the user and offer help with adding two numbers.\n2. Use the add tool whenever you need to calculate a sum.\n3. Continue assisting until the user says 'exit' or 'done'.\n\nUse only listed tools: {tools_description}"""
        ),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        ("human", "{input}"),
    ])

    model = init_chat_model(
        model="gpt-4o-mini",
        model_provider="openai",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.3,
        max_tokens=16000
    )

    agent = create_tool_calling_agent(model, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# ──────────────────────────── Main ────────────────────────────
async def main():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with MultiServerMCPClient(
                connections={
                    "coral": {
                        "transport": "sse",
                        "url": MCP_SERVER_URL,
                        "timeout": 300,
                        "sse_read_timeout": 300,
                    }
                }
            ) as client:
                logger.info(f"Connected to MCP server at {MCP_SERVER_URL}")
                coral_tools = client.get_tools()
                tools = coral_tools + [add_tool]
                executor = await create_math_agent(client, tools)
                chat_history = []
                print("🤖 Math assistant started. Type 'exit' or 'done' to stop.")
                while True:
                    user_input = input("\n👤 Your math query: ")
                    if user_input.lower() in ["exit", "done"]:
                        print("🤖 Goodbye!")
                        break
                    result = await executor.ainvoke({
                        "input": user_input,
                        "chat_history": chat_history,
                        "agent_scratchpad": []
                    })
                    print(f"\n🤖 {result['output']}")
                    from langchain_core.messages import AIMessage, HumanMessage
                    chat_history.append(HumanMessage(content=user_input))
                    chat_history.append(AIMessage(content=result['output']))
                break
        except ClosedResourceError as e:
            logger.error(f"ClosedResourceError on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying in 5 seconds...")
                await asyncio.sleep(5)
                continue
            else:
                logger.error("Max retries reached. Exiting.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying in 5 seconds...")
                await asyncio.sleep(5)
                continue
            else:
                logger.error("Max retries reached. Exiting.")
                raise

if __name__ == "__main__":
    asyncio.run(main())
