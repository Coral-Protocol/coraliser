import asyncio
import os
import json
import logging
from camel.toolkits.mcp_toolkit import MCPClient
from camel.toolkits import MCPToolkit
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent
import urllib.parse
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Validate API keys and tokens
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is not set in environment variables.")
if not os.getenv("GITHUB_ACCESS_TOKEN"):
    raise ValueError("GITHUB_ACCESS_TOKEN is not set in environment variables.")

base_url = "http://localhost:5555/devmode/exampleApplication/privkey/session1/sse"
params = {
    "waitForAgents": 1,
    "agentId": "codediff_review_agent",
    "agentDescription": "You are codediff_review_agent, responsible for analyzing code changes in GitHub Pull Requests and identifying which functions have been modified, which tests should be executed, and where those tests are located in the repository."
}
query_string = urllib.parse.urlencode(params)
MCP_SERVER_URL = f"{base_url}?{query_string}"

async def connect_client():
    global coral_server, github_client, toolkit
    
    # Initialize coral_server client
    coral_server = MCPClient(
        command_or_url=MCP_SERVER_URL,
        timeout=300.0
    )
    
    # Initialize github_client
    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    github_client = MCPClient(
        command_or_url="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server"
        ],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token},
        timeout=300.0
    )

    # Initialize MCPToolkit with both clients
    toolkit = MCPToolkit(servers=[coral_server, github_client])
    return toolkit

async def get_tools_description(tools):
    descriptions = []
    for tool in tools:
        tool_name = getattr(tool.func, '__name__', 'unknown_tool')
        schema = tool.get_openai_function_schema() or {}
        arg_names = list(schema.get('parameters', {}).get('properties', {}).keys()) if schema else []
        description = tool.get_function_description() or 'No description'
        schema_str = json.dumps(schema, default=str).replace('{', '{{').replace('}', '}}')
        descriptions.append(
            f"Tool: {tool_name}, Args: {arg_names}, Description: {description}, Schema: {schema_str}"
        )
    return "\n".join(descriptions)

async def create_codediff_agent(toolkit):
    tools = toolkit.get_tools()
    tools_description = await get_tools_description(tools)
    sys_msg = (
        f"""You are `codediff_review_agent`, responsible for retrieving and formatting code diffs from a GitHub pull request.

        1. Use `wait_for_mentions(timeoutMs=30000)` to wait for instructions from other agents.
        2. When a mention is received, record the `threadId` and `senderId`.
        3. Check if the message asks to analyze a PR with a repo name and PR number.
        4. Extract `repo_name` and `pr_number` from the message.
        5. Call `get_pull_request_files(pullNumber=pr_number, repo=repo_name)` to get code diffs.
        6. If this call fails, send the error message using `send_message` to the sender.
        7. If successful, send the formatted code diffs using `send_message` to the sender.
        8. If the message format is invalid or parsing fails, skip it silently.
        9. Do not create threads; always use the `threadId` from the mention.
        10. Wait 2 seconds and repeat from step 1. 

        These are the list of all tools: {tools_description}"""
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        api_key=os.getenv("OPENAI_API_KEY"),
        model_config_dict={"temperature": 0.3, "max_tokens": 16000},
    )
    
    agent = ChatAgent(
        system_message=sys_msg,
        model=model,
        tools=tools,
    )
    return agent

async def main():
    toolkit = await connect_client()
    async with toolkit.connection() as connected_toolkit:
        tools = connected_toolkit.get_tools()
        tools_description = await get_tools_description(tools)
        logger.info(f"Tools Description:\n{tools_description}")
        
        agent = await create_codediff_agent(connected_toolkit)
        
        # Initial agent step
        await agent.astep("Initializing codediff_review_agent, checking for mentions from other agents.")
        await asyncio.sleep(3)
        
        # Main agent loop
        while True:
            try:
                logger.info("Agent step")
                response = await agent.astep("Process any new mentions from other agents.")
                if response.msgs:
                    msg = response.msgs[0].to_dict()
                    logger.info(f"Agent response: {json.dumps(msg, indent=2)}")
                else:
                    logger.info("No messages received in this step")
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in agent loop: {str(e)}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())