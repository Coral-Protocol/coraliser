agent_evaluation_prompt = """
Given the content of a Python file provided below, determine if it defines an agent. An agent is a system that exhibits the following characteristics:
1. A reasoning component (e.g., a language model, rule-based logic, or decision-making module) to process inputs and make decisions.
2. An input handling mechanism to receive user or environmental inputs (e.g., user prompts, API calls, or data streams).
3. Optional tools or external integrations (e.g., functions, APIs, or interfaces) to extend functionality beyond reasoning.
4. An execution loop or mechanism to process inputs, perform actions (e.g., tool calls or direct responses), and return outputs.
5. Optional memory or context management to maintain state across interactions (e.g., conversation history or session data).

Analyze the provided Python code to check for these components. Determine if the code defines an agent and provide a brief explanation of your reasoning, highlighting which components are present or missing. If the code is incomplete or unclear, note any assumptions made during the analysis.

**Python File Content**:
```
{python_content}
```

**Response Format**:
Your response should be a JSON object with the following structure:
{{
  "agent": "yes/no",
  "reasoning": "Explain which components are present or missing, and why the code does or does not qualify as an agent."
}}
"""

agent_conversion_prompt = """
You are a python developer with the task of converting a base agent written in langchain into a coral agent which will also be written in langchain.

You are provided three things for added context:
1. The base agent which needs to be converted into a coral agent: python_content
2. An example coral agent content to help you understand what the final file will look like: EXAMPLE_AGENT_CONTENT
3. The instruction prompt which acts as an algorithm for the agent to use coral mcp tools: INTERFACE_AGENT_SYSTEM_PROMPT

I have provided detailed instructions about the above in the rest of this prompt.

Coral agent is an agent which can use its own tools along with the tools of the coral mcp it is connected to. 
A coral agent python file contains the following:
1. Imports: It will contain an import line like this: "from langchain_mcp_adapters.client import MultiServerMCPClient". This is the langchain adapter for connecting mcp to the agent.

2. A function to get tools description: It will contain a function like this:
```
def get_tools_description(tools):
    return "\n".join(
        f"Tool: {{tool.name}}, Schema: {{json.dumps(tool.args).replace('{{', '{{').replace('}}', '}}')}}"
        for tool in tools
    )
```

3. A function to create the agent which will have a tools_description, a prompt to teach the agent how to use the tools, a model to use, an agent creation function using the model, tools and prompt, and finally a return statement to return the AgentExecutor. If you were to convert a user interface agent into a coral agent, it would look like this:

```
async def create_interface_agent(client, tools):
    tools_description = get_tools_description(tools)
    
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f""""""
                ),
                ("placeholder", "{{agent_scratchpad}}")
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
```

4. The prompt will largely adhere to a set template which explains how the coral mcp tools should be used. It is like an algorithm to follow. The changes in the template will be the agent's tools and the instructions to use them. Do not change the template, only add or replace the existing instructions about the agent's tools.

5. It will have a main function which will run a loop to attempt to connect to the mcp. The loop will have code to connect to the coral mcp, combine the agent's tools and the coral mcp tools. It will finally use the function to create the agent using the connected mcp client and the combined tools.

6. It will finally have a name equals main if statement to run the main function using asyncio. It will look like this:
```
if __name__=="__main__":
    asyncio.run(main())
```

Instructions to convert an agent into a coral agent:
1. Do not change the inherent logic of how the agent is written.
2. Do not add your own functions other than the ones which I have specified. 
3. Identify what tools the agent is using in the base agent file and make sure the final converted agent included all of them. Make sure you don't confuse the agent's tools with the coral mcp's tools.
4. Make sure you don't add your own langchain logic apart from the ones already in the base agent file and the example converted coral agent file. 
5. Make sure you don't make unsolicited changes in the prompt, understand the prompt well, identify the instructions you need to change with respect to the base agent while also keeping the coral mcp tool usage instructions intact.
6. Your goal is to convert every agent file and make it as similar as possible to the example coral agent file's structure. Keep in mind that the example coral agent file is just for you to refer to the structure of the final code, do not confuse yourself and write the same code as the example agent content, you have to think for yourself and write a new logic adhering to the same structure.
7. Make sure all your imports are correct, refer to the example coral agent file content to know the essential imports for mcp adapters, error handling, etc.
8. Make sure there are no syntax errors in the final coral agent file.


The files you need for your context:
base agent file content: {python_content}
example coral agent file content: {EXAMPLE_AGENT_CONTENT}
instruction prompt from the example coral agent: {INTERFACE_AGENT_SYSTEM_PROMPT}

**Response Format**:
Your response should be a JSON object with the following structure:
{{
  "coral_agent_content": "",
  "potential_errors": "Explain why the code will not work"
}}
"""

INTERFACE_AGENT_SYSTEM_PROMPT = """
You are an agent interacting with the tools from Coral Server and having your own Human Tool to ask have a conversation with Human. 
Follow these steps in order:
1. Use `list_agents` to list all connected agents and  get their descriptions.
2. Use `ask_human` to ask, "How can I assist you today?" and capture the response.
3. Take 2 seconds to think and understand the user's intent and decide the right agent to handle the request based on list of agents. 
4. If the user wants any information about the coral server, use the tools to get the information and pass it to the user. Do not send any message to any other agent, just give the information and go to Step 1.
5. Once you have the right agent, use `create_thread` to create a thread with the selected agent. If no agent is available, use the `ask_human` tool to specify the agent you want to use.
6. Use your logic to determine the task you want that agent to perform and create a message for them which instructs the agent to perform the task called "instruction". 
7. Use `send_message` to send a message in the thread, mentioning the selected agent, with content: "instructions".
8. Use `wait_for_mentions` with a 30 seconds timeout to wait for a response from the agent you mentioned.
9. Show the entire conversation in the thread to the user.
10. Wait for 3 seconds and then use `ask_human` to ask the user if they need anything else and keep waiting for their response.
11. If the user asks for something else, repeat the process from step 1.

Use only listed tools: {{tools_description}}
"""

EXAMPLE_AGENT_CONTENT = """
import asyncio
import os
import json
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import Tool
from dotenv import load_dotenv
from anyio import ClosedResourceError
import urllib.parse

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

base_url = "http://localhost:5555/devmode/exampleApplication/privkey/session1/sse"
params = {{
    "waitForAgents": 2,
    "agentId": "user_interface_agent",
    "agentDescription": "You are user_interaction_agent, responsible for engaging with users, processing instructions, and coordinating with other agents"
}}
query_string = urllib.parse.urlencode(params)
MCP_SERVER_URL = f"{{{{base_url}}}}?{{{{query_string}}}}"

AGENT_NAME = "user_interaction_agent"

def get_tools_description(tools):
    return "\n".join(
        f"Tool: {{tool.name}}, Schema: {{json.dumps(tool.args).replace('{', '{{').replace('}', '}}')}}"
        for tool in tools
    )

async def ask_human_tool(question: str) -> str:
    print(f"Agent asks: {{question}}")
    return input("Your response: ")

async def create_interface_agent(client, tools):
    tools_description = get_tools_description(tools)
    
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f""You are an agent interacting with the tools from Coral Server and having your own Human Tool to ask have a conversation with Human. 
            Follow these steps in order:
            1. Use `list_agents` to list all connected agents and  get their descriptions.
            2. Use `ask_human` to ask, "How can I assist you today?" and capture the response.
            3. Take 2 seconds to think and understand the user's intent and decide the right agent to handle the request based on list of agents. 
            4. If the user wants any information about the coral server, use the tools to get the information and pass it to the user. Do not send any message to any other agent, just give the information and go to Step 1.
            5. Once you have the right agent, use `create_thread` to create a thread with the selected agent. If no agent is available, use the `ask_human` tool to specify the agent you want to use.
            6. Use your logic to determine the task you want that agent to perform and create a message for them which instructs the agent to perform the task called "instruction". 
            7. Use `send_message` to send a message in the thread, mentioning the selected agent, with content: "instructions".
            8. Use `wait_for_mentions` with a 30 seconds timeout to wait for a response from the agent you mentioned.
            9. Show the entire conversation in the thread to the user.
            10. Wait for 3 seconds and then use `ask_human` to ask the user if they need anything else and keep waiting for their response.
            11. If the user asks for something else, repeat the process from step 1.

            Use only listed tools: {{t}ools_description}}""
                ),
                ("placeholder", "{{agent_scratchpad}}")
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

async def main():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with MultiServerMCPClient(
                connections={{
                    "coral": {{
                        "transport": "sse",
                        "url": MCP_SERVER_URL,
                        "timeout": 300,
                        "sse_read_timeout": 300,
                    }}
                }}
            ) as client:
                logger.info(f"Connected to MCP server at {{MCP_SERVER_URL}}")
                tools = client.get_tools() + [Tool(
                    name="ask_human",
                    func=None,
                    coroutine=ask_human_tool,
                    description="Ask the user a question and wait for a response."
                )]
                await (await create_interface_agent(client, tools)).ainvoke({{}})
        except ClosedResourceError as e:
            logger.error(f"ClosedResourceError on attempt {{attempt + 1}}: {{e}}")
            if attempt < max_retries - 1:
                logger.info("Retrying in 5 seconds...")
                await asyncio.sleep(5)
                continue
            else:
                logger.error("Max retries reached. Exiting.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error on attempt {{attempt + 1}}: {{e}}")
            if attempt < max_retries - 1:{
                logger.info("Retrying in 5 seconds...")
                await asyncio.sleep(5)
                continue
            else:
                logger.error("Max retries reached. Exiting.")
                raise

if __name__ == "__main__":
    asyncio.run(main())

"""

# agent_conversion_prompt = """
# You are a Python developer with the task of converting a base agent written in LangChain into a Coral agent, also written in LangChain.

# You are provided three key references for context:
# 1. The base agent code that needs to be converted into a Coral agent: python_content
# 2. An example Coral agent file to help you understand the expected structure and conventions: EXAMPLE_AGENT_CONTENT
# 3. The instruction prompt (used within the Coral agent) that describes how to utilize Coral MCP tools: INTERFACE_AGENT_SYSTEM_PROMPT

# Please read and follow the instructions below carefully. These are meant to ensure accurate conversion and maintain consistency across all agents:

# ──────────────────────────── Overview of a Coral Agent ────────────────────────────
# A Coral agent can use both its own tools and the tools provided by the Coral MCP server. 
# The structure of a Coral agent file typically contains the following components:

# 1. **Imports**: Ensure inclusion of necessary packages for MCP support:
# ```python
# from langchain_mcp_adapters.client import MultiServerMCPClient
# ```
# Include all other necessary imports (e.g., for models, prompts, error handling, tools) by referring to the example Coral agent file.

# 2. **Function to Get Tool Descriptions**:
# ```python
# def get_tools_description(tools):
#     return "\\n".join(
#         f"Tool: {{tool.name}}, Schema: {{json.dumps(tool.args).replace('{{{{', '{{').replace('}}}}', '}}')}}"
#         for tool in tools
#     )
# ```

# 3. **Agent Creation Function**:
# This function must:
# - Accept the MCP client and tools.
# - Construct a prompt using the instruction template.
# - Set up the model using `init_chat_model()`.
# - Create the agent with `create_tool_calling_agent()`.
# - Return an `AgentExecutor` instance.

# Template:
# ```python
# async def create_interface_agent(client, tools):
#     tools_description = get_tools_description(tools)

#     prompt = ChatPromptTemplate.from_messages([
#         (
#             "system",
#             f""{{INTERFACE_AGENT_SYSTEM_PROMPT}}""
#         ),
#         ("placeholder", "{{{{agent_scratchpad}}}}")
#     ])

#     model = init_chat_model(
#         model="gpt-4o-mini",
#         model_provider="openai",
#         api_key=os.getenv("OPENAI_API_KEY"),
#         temperature=0.3,
#         max_tokens=16000
#     )

#     agent = create_tool_calling_agent(model, tools, prompt)
#     return AgentExecutor(agent=agent, tools=tools, verbose=True)
# ```

# Only modify the part of the prompt that pertains to your agent's own tools. Do **not** alter the logic concerning Coral MCP tools.

# 4. **Main Function**:
# Handles connection attempts to the Coral MCP server with appropriate error handling. Within the connection block, it:
# - Combines the Coral MCP tools and the agent's own tools.
# - Passes them to the agent creation function.

# 5. **Script Entrypoint**:
# ```python
# if __name__ == "__main__":
#     asyncio.run(main())
# ```

# ──────────────────────────── Instructions for Conversion ────────────────────────────
# 1. **Preserve Core Logic**: Do not modify the structure or retry logic in the main function. Use the example Coral agent as a reference.
# 2. **No Additional Functions**: Only include the functions explicitly required (as described above).
# 3. **Correct Tool Usage**: Identify all tools used in the base agent and ensure they are included in the Coral agent. Clearly distinguish between:
#    - Tools defined in the base agent
#    - Tools provided by the Coral MCP client
# 4. **Maintain LangChain Conventions**: Do not introduce new LangChain logic unless it exists in either the base agent or the example Coral agent.
# 5. **Prompt Adherence**: Use the provided instruction template for your prompt. Only update the section that pertains to the agent's own tool usage. Do **not** rewrite the MCP usage logic.
# 6. **Import Accuracy**: Match your imports to those shown in the example Coral agent.
# 7. **Syntax Validity**: Ensure the final output is syntactically correct Python.
# 8. **Do Not Copy the Example**: Use it as a structural reference only. Your final code should be based on the base agent content.

# {{  # <-- double curly braces for .format()
# ──────────────────────────── Input References ────────────────────────────
# - Base Agent: {{python_content}}
# - Example Coral Agent: {{EXAMPLE_AGENT_CONTENT}}
# - Instruction Prompt Template: {{INTERFACE_AGENT_SYSTEM_PROMPT}}

# ──────────────────────────── Response Format ────────────────────────────
# Return your result in the following JSON format:
# ```json
# {{
#   "coral_agent_content": "<final Coral agent Python code>",
#   "potential_errors": "<brief explanation of potential issues in the generated code, if any>"
# }}
# ```
# }}
# """