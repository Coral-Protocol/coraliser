import os
from dotenv import load_dotenv
from openai import OpenAI
import prompts
import json

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

class AgentCoraliser:
    def __init__(self, filename):
        self.filename = filename
    
    def read_file(self):
        try:
            with open(self.filename, 'r') as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"The file {self.filename} does not exist.")
        except Exception as e:
            raise Exception(f"An error occurred while reading the file: {e}")
    
    def agent_evaluation(self):
        try:
            python_content = self.read_file()
            # Use OpenAI's ChatCompletion API
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "user", "content": prompts.agent_evaluation_prompt.format(python_content=python_content)}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"An error occurred during agent evaluation: {e}")
        
    def agent_conversion(self):
        try:
            python_content = self.read_file()
            response = client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                temperature=0.3,
                response_format = {"type": "json_object"},
                messages=[{"role":"user","content": prompts.agent_conversion_prompt.format(
                    python_content=python_content,
                    EXAMPLE_AGENT_CONTENT=prompts.EXAMPLE_AGENT_CONTENT,
                    INTERFACE_AGENT_SYSTEM_PROMPT = prompts.INTERFACE_AGENT_SYSTEM_PROMPT
                    )}]
            )
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"An error occurred during agent conversion: {e}")
        
    def save_file(self, content: str, filename: str = "converted_agent.py"):
        try:
             converted_path = "converted_agents"

             if not os.path.exists(converted_path):
                 os.makedirs(converted_path, exist_ok=True)
                
             file_path = os.path.join(converted_path, filename)
             
             with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
             print(f"File saved successfully as '{filename}'")
        except Exception as e:
            print(f"Failed to save file: {e}")
    
    def run(self):
        try:
            # evaluation_result = self.agent_evaluation()
            # evaluation_result = json.loads(evaluation_result)
            # print("Agent Evaluation Result:")
            # print(json.dumps(evaluation_result, indent=2))
            
            # if evaluation_result["agent"].lower() == "yes":
            conversion_result = self.agent_conversion()
            conversion_result = json.loads(conversion_result)
            print("Converted Agent Code:", conversion_result["coral_agent_content"])  

            self.save_file(conversion_result['coral_agent_content'])
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    coraliser = AgentCoraliser("1_langchain_math.py")
    coraliser.run()