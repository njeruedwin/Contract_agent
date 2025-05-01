🧠📄 Contract Assistant AI
Overview
Contract Assistant AI is an intelligent, automated system designed to streamline and enhance contract processing workflows. It leverages multiple specialized AI agents to perform risk analysis, generate comprehensive legal reports, recommend contract edits, track obligations, and seamlessly coordinate signing and calendar events — all from a single command.

This project significantly reduces manual overhead, increases legal accuracy, and ensures contract obligations are tracked and met.

🔧 Features
✅ Risk Analysis Agent
Automatically evaluates the contract for potential legal and business risks.

Flags high-risk clauses, missing terms, ambiguous language, and non-standard obligations.

Outputs a detailed risk report with severity scoring and rationale.

✅ Agreement Assistance Agent
Consumes the risk report and:

Generates a structured legal review report.

Shares the report with the Legal Team (via email or shared workspace).

Updates the original agreement file with recommended edits.

Highlights obligations and key dates in the contract.

Sets reminders and events in Outlook (e.g., renewal dates, payment milestones).

Prepares the final agreement for digital signing.

🚀 Getting Started
Prerequisites
Python 3.8+

Microsoft Outlook (installed and configured)

A .docx contract file to analyze

Running the Project
Open your terminal or command prompt.

Navigate to the python directory of the project.

Activate the virtual environment:


venv\Scripts\activate  
#
Run the main contract assistant script: python contract_assistant.py

This will trigger:

The risk analysis agent

The legal report generation

Calendar event setup

Document update and e-sign dispatch
