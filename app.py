import gradio as gr
import json
import os
import subprocess
import asyncio

async def update_settings(json_input):
    with open("coraliser_settings.json", "w") as f:
        json.dump(json.loads(json_input), f)
    return "Coral Agent Ready!"

async def create_agent():
    try:
        process = await asyncio.create_subprocess_exec(
            "uv", "run", os.path.join("utils", "langchain", "mcp-coraliser", "coraliser.py"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(f"Error running coraliser.py: {stderr.decode()}")

        current_dir = os.getcwd()
        agent_files = [f for f in os.listdir(current_dir) if f.endswith("_coral_agent.py")]
        if not agent_files:
            return "No agent file generated."
        latest_file = max(agent_files, key=lambda x: os.path.getctime(os.path.join(current_dir, x)))
        with open(os.path.join(current_dir, latest_file), "r") as f:
            code_content = f.read()
        return code_content
    except Exception as e:
        return f"Error: {str(e)}"

async def coralise_all(json_input):
    status = await update_settings(json_input)
    code = await create_agent()
    return status, code

with gr.Blocks() as demo:
    gr.Markdown("## 🪸 Coraliser Tool")

    with gr.Row():
        with gr.Column(scale=1):
            json_input = gr.Code(label="MCP Server JSON", language="json", value="", lines=10)
            coralise_btn = gr.Button("Coralise Agent!")
            output_msg = gr.Textbox(label="Status", value="")
        
        with gr.Column(scale=2):
            code_output = gr.Code(label="Python Code Canvas", language="python", value="")

    coralise_btn.click(fn=coralise_all, inputs=json_input, outputs=[output_msg, code_output])

demo.launch()
