import asyncio
import os
import textwrap
from datetime import datetime
from pathlib import Path
import shutil

from risk_report_agent import risk_reporter
from user_functions import send_risk_assessment_email
from agreement_update_agent import agreement_update

from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings
from semantic_kernel.agents.strategies import TerminationStrategy, SequentialSelectionStrategy
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_function_decorator import kernel_function

RISK_MANAGER = "RISK_MANAGER"
RISK_MANAGER_INSTRUCTIONS = """
Analyze the given agreement file for risks.
Recommend the following actions based on the analysis:
- If agreement risks are detected,share the risks identifed as {risk_analysis} and send the risk analysis report.
- If obligation timelines are detected, set up reminders in Outlook.
- If the risk analysis report has been sent and timelines created, send agreement for signing.
- if agreement has been sent for signing, respond with "no action needed".
- If no action is needed, respond with "no action needed".
- If the log file is not found, respond with "log file not found".

RULES:
- Do not perform any corrective actions yourself.
- Read the agreement file on every turn.
- Prepend your response with this text: "RISK_MANAGER > {logfilepath} | "
- Only respond with the corrective action instructions.

"""

AGREEMENT_ASSISTANT = "AGREEMENT_ASSISTANT"
AGREEMENT_ASSISTANT_INSTRUCTIONS = """
Read the instructions from the RISK_MANAGER and apply the appropriate resolution function. 
Return the response as "{function_response}"



RULES:
- Use the instructions provided.
- Do not read any agreement files yourself.
- Prepend your response with this text: "AGREEMENT_ASSISTANT > "
"""

async def main():
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    # Get the log files
    print("Getting agreement files...\n")
    script_dir = Path(__file__).parent  # Get the directory of the script
    src_path = script_dir / "sample_contracts"
    
    file_path = script_dir / "logs"
    shutil.copytree(src_path, file_path, dirs_exist_ok=True)

    # Get the Azure AI Agent settings
    ai_agent_settings = AzureAIAgentSettings()

    async with (
        DefaultAzureCredential(exclude_environment_credential=True, 
            exclude_managed_identity_credential=True) as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):
    
        # Create the incident manager agent on the Azure AI agent service
        incident_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name=RISK_MANAGER,
            instructions=RISK_MANAGER_INSTRUCTIONS
        )


        # Create a Semantic Kernel agent for the Azure AI incident manager agent
        agent_incident = AzureAIAgent(
            client=client,
            definition=incident_agent_definition,
            plugins=[LogFilePlugin()]
        )


        # Create the AGREEMENT agent on the Azure AI agent service
        AGREEMENT_agent_definition = await client.agents.create_agent(
            model=ai_agent_settings.model_deployment_name,
            name=AGREEMENT_ASSISTANT,
            instructions=AGREEMENT_ASSISTANT_INSTRUCTIONS,
        )


        # Create a Semantic Kernel agent for the AGREEMENT Azure AI agent
        agent_AGREEMENT = AzureAIAgent(
            client=client,
            definition=AGREEMENT_agent_definition,
            plugins=[AgreementPlugin()]
        )


        # Add the agents to a group chat with a custom termination and selection strategy
        chat = AgentGroupChat(
            agents=[agent_incident, agent_AGREEMENT],
            termination_strategy=ApprovalTerminationStrategy(
                agents=[agent_incident], 
                maximum_iterations=20, 
                automatic_reset=True
            ),
            selection_strategy=SelectionStrategy(agents=[agent_incident,agent_AGREEMENT]),      
        )
        

         # Process log files
        for filename in os.listdir(file_path):
            logfile_msg = ChatMessageContent(role=AuthorRole.USER, content=f"USER > {file_path}/{filename}")
            await asyncio.sleep(30) # Wait to reduce TPM
            print(f"\nReady to process agreement file: {filename}\n")


            # Append the current log file to the chat
            await chat.add_chat_message(logfile_msg)
            print()


            try:
                print()

                ## Invoke a response from the agents
                async for response in chat.invoke():
                    if response is None or not response.name:
                        continue
                    print(f"{response.content}")

                
            except Exception as e:
                print(f"Error during chat invocation: {e}")
                # If TPM rate exceeded, wait 60 secs
                if "Rate limit is exceeded" in str(e):
                    print ("Waiting...")
                    await asyncio.sleep(60)
                    continue
                else:
                    break



# class for selection strategy
class SelectionStrategy(SequentialSelectionStrategy):
    """A strategy for determining which agent should take the next turn in the chat."""
    
    # Select the next agent that should take the next turn in the chat
    async def select_agent(self, agents, history):
        """"Check which agent should take the next turn in the chat."""

         # The Incident Manager should go after the User or the AGREEMENT Assistant
        if (history[-1].name == AGREEMENT_ASSISTANT or history[-1].role == AuthorRole.USER):
            agent_name = RISK_MANAGER
            return next((agent for agent in agents if agent.name == agent_name), None)
        
        # Otherwise it is the AGREEMENT Assistant's turn
        return next((agent for agent in agents if agent.name == AGREEMENT_ASSISTANT), None)



# class for temination strategy
class ApprovalTerminationStrategy(TerminationStrategy):
    """A strategy for determining when an agent should terminate."""

    # End the chat if the agent has indicated there is no action needed
    async def should_agent_terminate(self, agent, history):
        """Check if the agent should terminate."""
        return "no action needed" in history[-1].content.lower()




# class for AGREEMENT functions
class AgreementPlugin:
    """A plugin that performs developer operation tasks."""
    
    def append_to_log_file(self, filepath: str, content: str) -> None:
        with open(filepath, 'a', encoding='utf-8') as file:
            file.write('\n' + textwrap.dedent(content).strip())

    @kernel_function(description="A function that sends the risk analysis report and updates the agreement file")
    def send_report(self, risk_analysis: str = "", logfile: str = "") -> str:
        
        response , files = risk_reporter(f"{risk_analysis}")
        email_response = send_risk_assessment_email(files[0])
        update_response = agreement_update(f"Update the agreement file with {risk_analysis} reccommendations")
        
        
        log_entries = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT AGREEMENTAssistant: Multiple failures detected in {risk_analysis}. Sending Risk analysis Report.",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO  REPORTER_AGENT: {response}",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO  REPORTER_AGENT: {files}",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO  Email_Service: {email_response}",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO  Agreement_Update_AGENT: {update_response}",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO  REPORTER_AGENT: Report sent successfully.",
        ]

        log_message = "\n".join(log_entries)
        self.append_to_log_file(logfile, log_message)  
        
        return f"Service {risk_analysis} Report sent successfully."


    @kernel_function(description="A function that sets up reminders in Outlook")
    def increase_quota(self, logfile: str = "") -> str:
        """ A Simulation of setting up reminders in Outlook """
        log_entries = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT  AGREEMENTAssistant: Obligation Timelines Detected. Creating calendar tasks.",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO   CalendarManager: Calendar tasks submitted",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO   CalendarManager: Calendar tasks created successfully.",
        ]

        log_message = "\n".join(log_entries)
        self.append_to_log_file(logfile, log_message)

        return "Successfully created calendar tasks."

    @kernel_function(description="A function sends the agreement for signing")
    def escalate_issue(self, logfile: str = "") -> str:

        log_entries = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT  AGREEMENTAssistant: Agreement is ready for signing.",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT  EsignManager: Sending Agreement for signing.",
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT  EsignManager: Agreement successfully sent for signing.",
        ]
        
        log_message = "\n".join(log_entries)
        self.append_to_log_file(logfile, log_message)
        
        return "Submitted agreement for signing"


# class for Log File functions
class LogFilePlugin:
    """A plugin that reads and writes log files."""

    @kernel_function(description="Accesses the given file path string and returns the file contents as a string")
    def read_log_file(self, filepath: str = "") -> str:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()


# Start the app
if __name__ == "__main__":
    asyncio.run(main())