
# Coral Agents

## Introduction

### AI Agents

An AI agent within any given framework ([LangChain](https://github.com/langchain-ai/langchain), [Camel](https://github.com/camel-ai/camel), [CrewAi](https://github.com/crewAIInc/crewAI)) can be conceptualised as comprising three core components: model, prompts, and tools. Together, these components enable the AI agent to perceive, reason, and act within a framework, with the model processing data, prompts directing its focus, and tools facilitating real-world interactions.

- **Model:** The model serves as the computational core, typically a machine learning system like a large language model or reinforcement learning algorithm, processing inputs to generate decisions or outputs. 

-**Prompts:** Prompts act as the guiding interface, providing structured instructions or queries that shape the model’s behavior to align with specific goals, such as answering questions or executing tasks.

- **Tools:** Tools extend the agent’s capabilities by enabling interaction with the external environment, such as fetching data via APIs, controlling hardware, or performing specialized computations.

### MCP & AI Agent Frameworks

After the launch of [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol), most AI frameworks have adopted a client-based approach, enabling AI agents, acting as clients, to easily connect to a suite of powerful tools provided by the MCP server. These tools include standardised APIs that allow agents to interface with external systems, such as databases or web services, for seamless data retrieval and task execution specific to AI operations. Data exchange modules enable real-time data transfer, connecting agents to AI-relevant data sources, such as training datasets or live inference inputs. Task orchestration tools further enhance the system by coordinating synchronised actions, allowing AI agents to execute collaborative tasks efficiently within the multi-agent framework. 

An AI agent determines which tools it can use through a discovery mechanism provided by the MCP server, typically involving a tool registry or metadata service that lists available tools, their functionalities, and access protocols, enabling the agent to select appropriate tools based on its task requirements and compatibility.

### Coralised Agent

A Coralised Agent is an AI agent developed within any given framework and configured to connect as a client to the [Coral Server](https://github.com/Coral-Protocol/coral-server), which is a MCP server. This connection enables the agent to access a robust set of tools provided by the Coral Server, enhancing its capabilities beyond those of its original framework. In addition to these server-provided tools, the Coralised Agent retains its native tools from its original framework, allowing it to combine the Coral Server’s advanced capabilities with its inherent functionalities. 

## What is Coraliser?

Coraliser streamlines the adoption of Coral by automating the conversion of both MCP servers and standalone agents into Coral-compatible agents. Once integrated, these agents can seamlessly receive inputs from the Coral Server and invoke their tools as needed. This makes your multi-agent system more efficient, scalable, and ready for production use without additional configuration.

Coraliser is a powerful tool that streamlines the integration of both MCP servers and standalone agents with the Coral Server. It automates the generation of Coral-compatible agents, eliminating the need for manual wiring or complex configurations.

Coraliser currently includes the following components:

- **mcp-coraliser**: By simply providing a `coraliser_settings.json` file containing connection details for multiple MCP servers and executing `coraliser.py`, Coraliser automates the entire setup. It generates Coral-compatible agents that are immediately ready to operate within the Coral Server.

- **agent-coraliser**: By providing an input agent in `.py` format and executing `coraliser.py`, Coraliser first validates whether the file contains a valid agent. If it does, it generates a Coral-compatible version of that agent, ready to run within the Coral Server.

## Get Started

### 1. Clone & Install Dependencies
<details>

```bash
# Clone the Repository
git clone https://github.com/Coral-Protocol/Coraliser.git

# Navigate to the Project Directory
cd Coraliser

# Install uv
pip install uv

# Sync dependencies from pyproject.toml
uv sync
```
</details>

### 2. Configure Environment Variables
<details>

```bash
# Create .env file in project root
cp -r .env_sample .env
```
</details> 

### 3. Setting Up and Running the MCP-Coraliser
<details>

1. **Update `coraliser_settings.json`**:  
   Provide the connection details for your MCP server(s).

2. **Run the MCP Coraliser**:

```bash
   uv run utils/langchain/mcp-coraliser/coraliser.py
```

This script validates connections and generates Coral-compatible agent scripts.

4. **Review the Generated Agents**:  
   Check files like `firecrawl_coral_agent.py`, `github_coral_agent.py` to confirm they are configured correctly.

5. **Run the Agents** (assuming your Coral Server is running):

```bash
   uv run firecrawl_coral_agent.py
```

```bash
   uv run github_coral_agent.py
```
</details> 

### 4. Setting Up and Running the Agent-Coraliser
<details>

1. **Prepare the Input Agent**:  
   Ensure you have a valid agent Python file (e.g., `agent_coraliser_sample_input.py`).

2. **Run the Agent Coraliser**:

```bash
   uv run utils/langchain/agent-coraliser/coraliser.py
```

   (You’ll be prompted to enter the agent file name (including `.py` extension).)

3. **Review the Generated Agent File**:  
   Confirm the generated script matches your expectations.

4. **Run the Agent**:

```bash
uv run <generated_filename>.py
```
</details>

## Contribution Guidelines

We welcome contributions! Email us at [hello@coralprotocol.org](mailto:hello@coralprotocol.org) or join our Discord [here](https://discord.gg/rMQc2uWXhj) to connect with the developer team. Feel free to open issues or submit pull requests.

Thanks for checking out the project, we hope you like it!

## License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2025 Coral Protocol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

For more information, visit:  
https://www.coralprotocol.org/