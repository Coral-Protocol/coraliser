import asyncio
import os
import json
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import Tool
from dotenv import load_dotenv
from anyio import ClosedResourceError
import urllib.parse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

base_url = "http://localhost:5555/devmode/exampleApplication/privkey/session1/sse"
params = {
    "waitForAgents": 4,
    "agentId": "user_interaction_agent",
    "agentDescription": "You are user_interaction_agent, handling user instructions and coordinating testing tasks across agents"
}
query_string = urllib.parse.urlencode(params)
MCP_SERVER_URL = f"{base_url}?{query_string}"
AGENT_NAME = "user_interaction_agent"

def get_tools_description(tools):
    return "\n".join(
        f"Tool: {tool.name}, Schema: {json.dumps(tool.args).replace('{', '{{').replace('}', '}}')}"
        for tool in tools
    )

async def ask_human_tool(question: str) -> str:
    print(f"Agent asks: {question}")
    return input("Your response: ")

async def create_interface_agent(client, tools):
    tools_description = get_tools_description(tools)
    
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f"""You are an agent interacting with the tools from Coral Server and using your own `ask_human` tool to communicate with the user.

            Follow these steps in order:

            1. Use `list_agents` to list all connected agents and get their descriptions.
            2. Use `ask_human` to ask: "How can I assist you today?" and wait for the response.
            3. Take 2 seconds to understand the user's intent and decide which agent(s) are needed based on their descriptions.
            4. If the user requests Coral Server information (e.g., agent status, connection info), use your tools to retrieve and return the information directly to the user, then go back to Step 1.
            5. If the user's query is for example, "Please execute the unit test for the '1' PR in repo 'renxinxing123/camel-software-testing", extract PR number as "pr_number" and repo name as "repo_name" from the request.
            5. Once you identify the user's intent to execute a unit test for a PR on a repo do the below steps. Else go to Step 1 telling the user that you can help with Unit test and you require PR number and repo name.
            6. If the user's intent is to execute a unit test, do the following:
                * Use `list_agents` to check "gitclone_agent", "codediff_review_agent" and "unit_test_agent" agents are present, if not go to Step 1 and ask user to register these agents.
                * Send a message to the "gitclone_agent" with the content: "Please clone the repository "repo_name" and check out PR "pr_number".
                * Use `wait_for_mentions(timeoutMs=30000)` to receive the response from "gitclone_agent". If you don't receive a response, try twice more and then if it fails, go to Step 1 and tell the user that you are unable to clone the repo.
                * If the "gitclone_agent" successfully sends a message with the "root path", save it in memory
                * Send a message to the "codediff_review_agent" with the content: "Please analyze the code changes in PR "pr_number" of repo "repo_name".
                * Use `wait_for_mentions(timeoutMs=30000)` to receive the response from "codediff_review_agent". If you don't receive a response, try twice more and then if it fails, go to Step 1 and tell the user that you are unable to analyze the code changes.
                * If the "codediff_review_agent" successfully sends a message with  the "formatted code diffs", save it in memory.
                * Send a message to the "unit_test_agent" with the content: " With the "root path" and "formatted code diffs" execute the unit test."
                * Use `wait_for_mentions(timeoutMs=60000)` to receive the response from "unit_test_agent". If you don't receive a response, try twice more and then if it fails, go to Step 1 and tell the user that you are unable to execute the unit test.
                * If the "unit_test_agent" successfully sends a message with the "test results", send it back to the user as a response.
                * Record and store the response for final presentation.
            7. After all required agents have responded, show the complete conversation (all thread messages) to the user.
            8. Wait for 3 seconds, then use `ask_human` to ask: "Is there anything else I can help you with?"
            9. If the user replies with a new request, repeat the process from Step 1.
            - Use only tools: {tools_description}"""),
        ("placeholder", "{agent_scratchpad}")
    ])

    model = ChatOpenAI(
        model="gpt-4.1-2025-04-14",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.3,
        max_tokens=8192  # or 16384, 32768 depending on your needs; for gpt-4o-mini, make sure prompt + history + output < 128k tokens
    )

    agent = create_tool_calling_agent(model, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

async def main():
    max_retries = 5
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        try:
            async with MultiServerMCPClient(
                connections={
                    "coral": {
                        "transport": "sse",
                        "url": MCP_SERVER_URL,
                        "timeout": 30,
                        "sse_read_timeout": 60,  # Reduced timeout
                    }
                }
            ) as client:
                logger.info(f"Connected to MCP server at {MCP_SERVER_URL}")
                tools = client.get_tools() + [Tool(
                    name="ask_human",
                    func=None,
                    coroutine=ask_human_tool,
                    description="Ask the user a question and wait for a response."
                )]
                logger.info(f"Tools Description:\n{get_tools_description(tools)}")
                await (await create_interface_agent(client, tools)).ainvoke({})
        except ClosedResourceError as e:
            logger.error(f"ClosedResourceError on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                continue
            else:
                logger.error("Max retries reached. Exiting.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                continue
            else:
                logger.error("Max retries reached. Exiting.")
                raise

if __name__ == "__main__":
    asyncio.run(main())