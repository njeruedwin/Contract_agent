import os
from dotenv import load_dotenv
from typing import Tuple, List
from pathlib import Path

import smtplib, ssl
from email.message import EmailMessage


from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FilePurpose, CodeInterpreterTool
from semantic_kernel.functions.kernel_function_decorator import kernel_function

from azure.ai.projects.models import FunctionTool, ToolSet



def agreement_update(user_prompt: str):
    """
    Calls an Azure AI agent with the user_prompt and returns the assistant's response
    and a list of any generated file names.
    """
    load_dotenv()
    PROJECT_CONNECTION_STRING = os.getenv("AZURE_AI_AGENT_PROJECT_CONNECTION_STRING")
    MODEL_DEPLOYMENT = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")

    script_dir = Path(__file__).parent
    file_path = script_dir / 'data.txt'

    with file_path.open('r') as file:
        data = file.read()

    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ),
        conn_str=PROJECT_CONNECTION_STRING
    )

    generated_files = []
    assistant_response = ""

    with project_client:
        file = project_client.agents.upload_file_and_poll(
            file_path=file_path, purpose=FilePurpose.AGENTS
        )

        code_interpreter = CodeInterpreterTool()
        
        

        agent = project_client.agents.create_agent(
            model=MODEL_DEPLOYMENT,
            name="report-agent",
            instructions="You are an AI agent that generates an updated agreement based on the reccommedations. Create the updated agreement and save as a .txt file",
            tools=code_interpreter.definitions,
            tool_resources=code_interpreter.resources,
        )

        thread = project_client.agents.create_thread()

        project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=user_prompt,
        )

        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            agent_id=agent.id
        )

        if run.status == "failed":
            raise RuntimeError(f"Run failed: {run.last_error}")

        messages = project_client.agents.list_messages(thread_id=thread.id)
        last_msg = messages.get_last_text_message_by_role("assistant")
        if last_msg:
            assistant_response = last_msg.text.value

        # Save generated files
        for annotation in messages.file_path_annotations:
            file_name = Path(annotation.text).name
            project_client.agents.save_file(
                file_id=annotation.file_path.file_id,
                file_name=file_name
            )
            
            generated_files.append(file_name)

        project_client.agents.delete_agent(agent.id)
        project_client.agents.delete_thread(thread.id)

    return assistant_response, generated_files


