import asyncio
import os
import json
import logging
import subprocess
import sys
import re
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_ollama.chat_models import ChatOllama
from dotenv import load_dotenv
from anyio import ClosedResourceError
import urllib.parse
from typing import Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

base_url = "http://localhost:5555/devmode/exampleApplication/privkey/session1/sse"
params = {
    "waitForAgents": 4,
    "agentId": "unit_test_runner_agent",
    "agentDescription": "You are unit_test_runner_agent, responsible for executing a specific pytest test based on function name"
}
query_string = urllib.parse.urlencode(params)
MCP_SERVER_URL = f"{base_url}?{query_string}"
AGENT_NAME = "unit_test_runner_agent"

# Validate API keys
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is not set in environment variables.")

def get_tools_description(tools):
    return "\n".join(f"Tool: {t.name}, Schema: {json.dumps(t.args).replace('{', '{{').replace('}', '}}')}" for t in tools)

@tool
def list_project_files(root_path: str) -> List[str]:
    """
    Fetch all visible file paths under a project root directory.

    Args:
        root_path (str): Absolute or relative path to the root folder.

    Returns:
        List[str]: A list of file paths relative to the root directory provided.

    Raises:
        ValueError: If root_path does not exist or is not a directory.
    """
    if not os.path.isdir(root_path):
        raise ValueError(f"Provided path '{root_path}' is not a directory or does not exist.")

    file_list: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Exclude hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        # Exclude hidden files
        visible_files = [f for f in filenames if not f.startswith('.')]
        for filename in visible_files:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root_path)
            normalized = rel_path.replace(os.sep, '/')
            file_list.append(normalized)

    return file_list

@tool
def read_project_files(root_path: str, relative_paths: List[str]) -> Dict[str, str]:
    """
    Read multiple files under a project root directory.

    Args:
        root_path (str): The root directory of the project.
        relative_paths (List[str]): A list of file paths relative to root_path.

    Returns:
        Dict[str, str]: A dictionary mapping each relative path to its file content.

    Raises:
        ValueError: If a constructed path does not exist or is not a file.
        IOError: If an I/O error occurs while reading a file.
    """
    contents: Dict[str, str] = {}
    for rel_path in relative_paths:
        # Construct the absolute file path
        full_path = os.path.normpath(os.path.join(root_path, rel_path))
        if not os.path.isfile(full_path):
            raise ValueError(f"File '{rel_path}' does not exist under '{root_path}'.")
        # Read and store file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                contents[rel_path] = f.read()
        except Exception as e:
            raise IOError(f"Failed to read '{full_path}': {e}")
    return contents

@tool
def run_test(project_root: str, relative_test_path: str) -> dict:
    """
    Run all pytest unit tests in a test file within a project directory.

    Args:
        project_root (str): Absolute path to the project root directory.
        relative_test_path (str): Path to the test file relative to the project root (e.g., 'tests/test_calculator.py').

    Returns:
        dict: Contains 'result' message, 'output' (full pytest output), and 'status' (True if all tests passed).
    """
    if not os.path.isabs(project_root):
        raise ValueError("project_root must be an absolute path.")

    abs_test_path = os.path.join(project_root, relative_test_path)

    if not os.path.exists(abs_test_path):
        raise FileNotFoundError(f"Test file does not exist: {abs_test_path}")

    command = ["pytest", relative_test_path]
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root

    print(f"Running pytest on: {relative_test_path}")
    result = subprocess.run(command, cwd=project_root, env=env, capture_output=True, text=True)

    print("--- Pytest Output ---")
    print(result.stdout)

    passed = result.returncode == 0
    status_msg = "All tests passed." if passed else "Some tests failed."

    return {
        "result": status_msg,
        "output": result.stdout,
        "status": passed
    }


async def create_unit_test_runner_agent(client, tools):
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are `unit_test_runner_agent`, responsible for running relevant pytest tests based on code diffs and a given project root.

        1. Use `wait_for_mentions(timeoutMs=30000)` to wait for instructions from other agents.
        2. When a mention is received, record the `threadId` and `senderId`.
        3. Check if the message contains a project root and a list of filenames with code diffs.
        4. Extract the `project_root` and the list of `(filename, diff snippet)` pairs.
        5. Call `list_project_files(project_root)` to get all files in the project.
        6. Filter out test files (e.g., in `tests/` folder or starting with `test_`).
        7. Call `read_project_files(project_root, test_files)` to read their content.
        8. For each changed file, find related test files using name or import matching.
        9. For each test file, call `run_test(project_root, test_file_path)` to run tests.
        10. Collect the test output and compare executed test functions with all defined ones.
        11. Format a result summary with test outcomes and pytest output.
        12. Use `send_message(senderId=..., mentions=[senderId], threadId=..., content="answer")` to reply.
        13. If there's an error, send a message with content `"error"` to the sender.
        14. Always respond to the sender, even if the result is empty or invalid.
        15. Wait 2 seconds and repeat from step 1. 
        Tools: {get_tools_description(tools)}"""),
        ("placeholder", "{agent_scratchpad}")
    ])

    model = ChatOpenAI(
        model="gpt-4.1-2025-04-14",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.3,
        max_tokens=8192  # or 16384, 32768 depending on your needs; for gpt-4o-mini, make sure prompt + history + output < 128k tokens
    )

    #model = ChatOllama(model="llama3")

    agent = create_tool_calling_agent(model, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

async def main():
    retry_delay = 5  # seconds
    max_retries = 5
    retries = max_retries

    while retries > 0:
        try:
            async with MultiServerMCPClient(connections={
                "coral": {"transport": "sse", "url": MCP_SERVER_URL, "timeout": 30, "sse_read_timeout": 60}
            }) as client:
                tools = client.get_tools() + [run_test, list_project_files, read_project_files]
                logger.info(f"Connected to MCP server. Tools:\n{get_tools_description(tools)}")
                retries = max_retries  # Reset retries on successful connection
                await (await create_unit_test_runner_agent(client, tools)).ainvoke({})
        except ClosedResourceError as e:
            retries -= 1
            logger.error(f"Connection closed: {str(e)}. Retries left: {retries}. Retrying in {retry_delay} seconds...")
            if retries == 0:
                logger.error("Max retries reached. Exiting.")
                break
            await asyncio.sleep(retry_delay)
        except Exception as e:
            retries -= 1
            logger.error(f"Unexpected error: {str(e)}. Retries left: {retries}. Retrying in {retry_delay} seconds...")
            if retries == 0:
                logger.error("Max retries reached. Exiting.")
                break
            await asyncio.sleep(retry_delay)

if __name__ == "__main__":
    asyncio.run(main())