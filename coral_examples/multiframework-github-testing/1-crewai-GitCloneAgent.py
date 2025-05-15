import os
import json
import logging
import subprocess
import traceback
import asyncio
from typing import List, Dict
import urllib.parse
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool
from crewai_tools import MCPServerAdapter

# Setup logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
print("Environment variables loaded")

# MCP Server configuration
base_url = "http://localhost:5555/devmode/exampleApplication/privkey/session1/sse"
params = {
    "waitForAgents": 4,
    "agentId": "gitclone_agent",
    "agentDescription": "You are gitclone_agent, responsible for cloning a GitHub repository and checking out the branch associated with a specific pull request."
}
query_string = urllib.parse.urlencode(params)
MCP_SERVER_URL = f"{base_url}?{query_string}"
print(f"MCP Server URL: {MCP_SERVER_URL}")

# Validate API keys
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is not set in environment variables.")
else:
    print("OpenAI API key found")

@tool("Checkout GitHub PR")
def checkout_github_pr(repo_full_name: str, pr_number: int) -> str:
    """
    Clone a GitHub repository and check out the branch associated with a specific pull request.

    Args:
        repo_full_name (str): GitHub repository in the format "owner/repo".
        pr_number (int): Pull request number.

    Returns:
        str: Absolute path to the local repository checked out to the PR branch.
    """
    print(f"Tool called: checkout_github_pr({repo_full_name}, {pr_number})")
    dest_dir = os.getcwd()
    print(f"Working directory: {dest_dir}")

    repo_name = repo_full_name.split('/')[-1]
    repo_url = f'https://github.com/{repo_full_name}.git'
    repo_path = os.path.join(dest_dir, repo_name)
    pr_branch = f'pr-{pr_number}'
    
    print(f"Repository URL: {repo_url}")
    print(f"Local path: {repo_path}")
    print(f"PR branch: {pr_branch}")

    try:
        if not os.path.exists(repo_path):
            print(f"Cloning repository {repo_url} to {repo_path}")
            subprocess.run(['git', 'clone', repo_url, repo_path], check=True)
            print("Clone completed successfully")
        else:
            print(f"Repository already exists at {repo_path}")

        try:
            print("Attempting to checkout main branch")
            subprocess.run(['git', '-C', repo_path, 'checkout', 'main'], check=True)
            print("Checked out main branch")
        except subprocess.CalledProcessError:
            try:
                print("Main branch not found, attempting to checkout master branch")
                subprocess.run(['git', '-C', repo_path, 'checkout', 'master'], check=True)
                print("Checked out master branch")
            except subprocess.CalledProcessError:
                print("Neither main nor master branch found, continuing with current branch")
                pass

        print("Checking existing branches")
        existing_branches = subprocess.run(['git', '-C', repo_path, 'branch'], capture_output=True, text=True).stdout
        print(f"Existing branches: {existing_branches}")
        
        if pr_branch in existing_branches:
            print(f"Deleting existing PR branch: {pr_branch}")
            subprocess.run(['git', '-C', repo_path, 'branch', '-D', pr_branch], check=True)

        print(f"Fetching PR #{pr_number}")
        subprocess.run(['git', '-C', repo_path, 'fetch', 'origin', f'pull/{pr_number}/head:{pr_branch}'], check=True)
        print(f"Checking out PR branch: {pr_branch}")
        subprocess.run(['git', '-C', repo_path, 'checkout', pr_branch], check=True)
        
        result_path = os.path.abspath(repo_path)
        print(f"Successfully checked out PR. Repository path: {result_path}")
        return result_path
    
    except subprocess.CalledProcessError as e:
        error_message = f"Git operation failed: {e.stderr if hasattr(e, 'stderr') else str(e)}"
        print(f"ERROR: {error_message}")
        return f"Error: {error_message}"
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(f"ERROR: {error_message}")
        traceback.print_exc()
        return f"Error: {error_message}"

async def setup_components():
    # Load LLM
    llm = LLM(
        model="openai/gpt-4.1-mini-2025-04-14",
        temperature=0.3,
        max_tokens=8192
    )
    # MCP Server
    serverparams = {"url": MCP_SERVER_URL}
    mcp_server_adapter = MCPServerAdapter(serverparams)
    mcp_tools = mcp_server_adapter.tools

    # GitClone Agent
    gitclone_agent = Agent(
        role="Git Clone Agent",
        goal="Clone GitHub repositories and check out branches for specific Pull Requests. Continue running until a PR is successfully checked out.",
        backstory="I am responsible for cloning GitHub repositories and checking out branches associated with specific pull requests. I will not stop until I successfully check out a PR.",
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=mcp_tools + [checkout_github_pr]
    )

    return gitclone_agent, mcp_tools, mcp_server_adapter

async def main():
    retry_delay = 5
    max_retries = 5
    retries = max_retries

    print("Initializing GitClone system...")
    gitclone_agent, mcp_tools, mcp_server_adapter = await setup_components()

    while True:
        try:
            print("Creating new task and crew...")

            task = Task(
                description="""You are `gitclone_agent`, responsible for cloning a GitHub repository and checking out the branch for a specific pull request.

                1. Use `wait_for_mentions(timeoutMs=30000)` to wait for instructions from other agents.
                2. When a mention is received, record the `threadId` and `senderId`.
                3. Check if the message asks to checkout a PR with a given repo name and PR number.
                4. Extract `repo` and `pr_number` from the message.
                5. Call `checkout_github_pr(repo_full_name=repo, pr_number=pr_number)` to clone and checkout the PR.
                6. If the call is successful, send a message saying the PR was checked out with the local path.
                7. If the call fails, send the error message using `send_message` to the sender.
                8. If the message format is invalid or incomplete, skip it silently.
                9. Do not create threads; always use the `threadId` from the mention.
                10. Wait 2 seconds and repeat from step 1.
                """,
                agent=gitclone_agent,
                expected_output="Successfully checked out PR branch and provided the local repository path",
                async_execution=True
            )

            crew = Crew(
                agents=[gitclone_agent],
                tasks=[task],
                verbose=True,
                enable_telemetry=False
            )

            print("Kicking off crew execution")
            result = crew.kickoff()
            print(f"Crew execution completed with result: {result}")

            await asyncio.sleep(1)

        except Exception as e:
            retries -= 1
            print(f"Error: {str(e)}. Retries left: {retries}")
            logger.error(f"Error in GitClone main loop: {str(e)}", exc_info=True)
            if retries == 0:
                print("Max retries reached. Exiting.")
                break
            await asyncio.sleep(retry_delay)

if __name__ == "__main__":
    asyncio.run(main())
    print("GitClone Agent script completed")