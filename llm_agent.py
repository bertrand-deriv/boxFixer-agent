#!/usr/bin/env python3
import typer
import os
import sys
import time
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from log_monitor_tool import check_logs_once
from service_health_check_tool import check_services
from command_executor_tool import execute_shell_command
from resource_monitoring_tool import check_system_resources
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from kyc_troubleshooting_tool import troubleshoot_kyc

from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
# Define structured output models
# class LogEntry(BaseModel):
#     message: str = Field(description="The log message content")
#     timestamp: Optional[str] = Field(description="Timestamp of the log entry if available")
#     source: Optional[str] = Field(description="Source file or service that generated the log")
    
# class LogsOutput(BaseModel):
#     errors: List[LogEntry] = Field(description="List of error log entries")
#     warnings: List[LogEntry] = Field(description="List of warning log entries")

class ServiceStatus(BaseModel):
    name: str = Field(description="Name of the service")
    status: str = Field(description="Current status (running, stopped, error, etc.)")
    details: Optional[str] = Field(description="Additional details about the service status")

class ResourceStatus(BaseModel):
    cpu_usage: str = Field(description="CPU usage")
    memory_usage: str = Field(description="Memory usage")

class ServicesOutput(BaseModel):
    kyc_services: Optional[List[ServiceStatus]] = Field(description="Any service that has word 'kyc' in its name. If there's none, return null")
    hydra_services: Optional[List[ServiceStatus]] = Field(description="Any service that word 'hydra' in its name. If there's none, return null")
    other_services: List[ServiceStatus] = Field(description="Other miscellaneous services")

class MonitoringReport(BaseModel):
    # logs: LogsOutput = Field(description="Categorized log entries")
    services: ServicesOutput = Field(description="Categorized service statuses")
    resources: ResourceStatus = Field(description="Brief interpretation of system resource usage")
    summary: str = Field(description="Brief summary of system health.")
    recommendations: List[str] = Field(description="Recommended actions based on findings. You Should excplicity state whether to rebuild QAbox or not depending on how long services has been running and CPU and/or memory is at bottleneck")
    
# Initialize the parser
output_parser = PydanticOutputParser(pydantic_object=MonitoringReport)

# Load environment variables
load_dotenv()

app = typer.Typer()

# Define tools
@tool
def fetch_logs():
    """Fetches logs with errors and warnings from system log files."""
    return check_logs_once(for_agent=True, no_color=True)

@tool
def fetch_service_status():
    """Checks service health using the service checker tool."""
    return check_services()

instructions = output_parser.get_format_instructions()
escaped_instructions = instructions.replace("{", "{{").replace("}", "}}")

system_message = SystemMessagePromptTemplate.from_template(
    f"""
        You are a DevOps assistant designed to help with system monitoring and troubleshooting. 
        Your primary objectives are:
        1. Provide clear and concise information about system health
        2. Use available tools to investigate system issues
        3. Offer actionable recommendations
        4. Communicate in a helpful manner

        When using tools:
        - Always explain what tool you're using and why
        - Interpret tool results in a meaningful context
        - Provide clear explanations of any findings
        - Suggest next steps if potential issues are detected

        Tools available and their purpose:
        - fetch_logs: Use this tool to get system logs including docker containers
        - fetch_service_status: Use this tool to get different service statuses including system statuses, docker services, k8s pods
                                Use this tool also to advice whether the host (QAbox) needs a rebuild. If more than 2 services has been 
                                running for 5 days its advisable to rebuild the QAbox
        - execute_shell_command: Use this tool to execute commands in terminal. Always ask for user approval before executing command.
        - check_system_resources: Use this tool to check system resource usage. If there's any red flags, report them. It is advisable to rebuild
                                  QAbox when CPU and/or memory is at bottleneck.
        - troubleshoot_kyc: Use this to troubleshoot the kyc service

        CRITICAL: At the end of your analysis, you MUST provide a standardized report in JSON format exactly as specified here:
        {escaped_instructions}
        Do not include any text before or after the JSON structure. The JSON should be the only content in your final response.

        Constraints:
        - Never attempt to execute potentially dangerous commands
        - Always ask for user approval before executing any command
        - If unsure about a command or its implications, ask for clarification   
    """
)
prompt = ChatPromptTemplate.from_messages([
    system_message,
    HumanMessagePromptTemplate.from_template("{messages}")
])
# Initialize LLM
llm = ChatLiteLLM(
    model_name="gpt-4o",
    api_base=os.getenv("API_BASE"),
    api_key=os.getenv("API_KEY")
)
# Set up tools
tools = [ fetch_service_status, execute_shell_command, check_system_resources, troubleshoot_kyc ] # removed fetch_logs

# Initialize memory
memory = MemorySaver()

# Create agent graph
graph = create_react_agent(
    llm,
    tools=tools,
    checkpointer=memory,
    prompt=prompt
)

# Configuration
config = {"configurable": {"thread_id": "1"}}

# Modify your display function to handle structured output
def display_structured_output(structured_output):
    """Display the structured output in a user-friendly format"""
    
    print("\n===== MONITORING REPORT =====\n")
    
    # Display summary
    print(f"📋 SUMMARY: {structured_output.summary}\n")
    
    # Display logs
    # print("🔴 ERRORS:")
    # if structured_output.logs.errors:
    #     for error in structured_output.logs.errors:
    #         source = f" [{error.source}]" if error.source else ""
    #         timestamp = f" at {error.timestamp}" if error.timestamp else ""
    #         print(f"  - {error.message}{source}{timestamp}")
    # else:
    #     print("  No errors found")
    
    # print("\n🟠 WARNINGS:")
    # if structured_output.logs.warnings:
    #     for warning in structured_output.logs.warnings:
    #         source = f" [{warning.source}]" if warning.source else ""
    #         timestamp = f" at {warning.timestamp}" if warning.timestamp else ""
    #         print(f"  - {warning.message}{source}{timestamp}")
    # else:
    #     print("  No warnings found")
    
    # Display services
    print("\n🔷 KYC SERVICES:")
    if structured_output.services.kyc_services:
        sorted_services = sorted(
            structured_output.services.kyc_services,
            key=lambda svc: 0 if svc.status.lower() != "running" else 1
        )
        
        for svc in sorted_services:
            status_emoji = "✅" if svc.status.lower() == "running" else "❌"
            print(f"  {status_emoji} {svc.name} - {svc.status}")
            if svc.details:
                print(f"     {svc.details}")
    else: 
        print("There's no KYC related services available")
    
    print("\n🔶 HYDRA SERVICES:")
    if structured_output.services.hydra_services:
        sorted_services = sorted(
            structured_output.services.hydra_services,
            key=lambda svc: 0 if svc.status.lower() != "running" else 1
        )
        for svc in sorted_services:
            status_emoji = "✅" if svc.status.lower() == "running" else "❌"
            print(f"  {status_emoji} {svc.name} - {svc.status}")
            if svc.details:
                print(f"     {svc.details}")
    else:
        print("There's no Hydra related services available")
    
    print("\n⚪ OTHER SERVICES:")
    sorted_services = sorted(
        structured_output.services.other_services,
        key=lambda svc: 0 if svc.status.lower() != "running" else 1
    )
    for svc in sorted_services:
        status_emoji = "✅" if svc.status.lower() == "running" else "❌"
        print(f"  {status_emoji} {svc.name} - {svc.status}")
        if svc.details:
            print(f"     {svc.details}")

    # Display resouces
    print("\n🔋 SYSTEM RESOURCES:")
    print(f"  {structured_output.resources}\n")

    # Display recommendations
    print("\n💡 RECOMMENDATIONS:")
    for i, rec in enumerate(structured_output.recommendations, 1):
        print(f"  {i}. {rec}")
    
    print("\n=============================\n")

def display_typing_effect(message):
    """Display a typing effect for agent responses"""
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        # Small random delay between characters for a natural typing effect
        time.sleep(0.002)
    print()

@app.command()
def run_agent(interactive: bool = True):
    """
    Runs the AI agent to fetch logs and service status.
    
    Args:
        interactive: Whether to run in interactive mode with continuous conversation
    """
    typer.echo("\n🤖 AI Agent starting up...")
    typer.echo("📊 Initializing systems...")
    
    # First automated query to check logs and service status
    initial_query = "As DevOps assistant agent, give the report of the service health check and advise when QAbox is in ready status to start testing"
    typer.echo(f"\n🔍 Running initial check: '{initial_query}'")
    
    try:
        # Run the first query automatically
        response = graph.invoke({"messages": initial_query}, config)
        agent_response = response["messages"][-1].content
        try:
            # Try to parse the response into structured format
            structured_output = output_parser.parse(agent_response)
            display_structured_output(structured_output)

        except Exception as e:
            # Fall back to normal display if parsing fails
            typer.echo("\n🤖 Agent response (raw format - parsing failed):")
            typer.echo(f"\nParsing error: {str(e)}")
            display_typing_effect(agent_response)
        
        # typer.echo("\n🤖 Agent response:")
        # display_typing_effect(agent_response)
        
        if not interactive:
            typer.echo("\n✅ Agent task completed.")
            return
        
        # Continue with interactive mode
        typer.echo("\n🔄 Entering interactive mode. Type 'exit' or 'quit' to end the session.")
        
        # Interactive loop
        while True:
            user_input = typer.prompt("\n💬 You")
            
            if user_input.lower() in ["exit", "quit", "q"]:
                typer.echo("\n👋 Ending agent session. Goodbye!")
                break
                
            try:
                # Process the user query through the agent
                response = graph.invoke({"messages": user_input}, config)
                agent_response = response["messages"][-1].content
                try:
                    # Try to parse the response into structured format
                    structured_output = output_parser.parse(agent_response)
                    display_structured_output(structured_output)
                except Exception as e:
                    # Fall back to normal display if parsing fails
                    typer.echo("\n🤖 Agent response (raw format):")
                    display_typing_effect(agent_response)
                
                typer.echo("\n🤖 Agent response:")
                display_typing_effect(agent_response)
                
            except Exception as e:
                typer.echo(f"\n❌ Error processing query: {str(e)}")
                
    except Exception as e:
        typer.echo(f"\n❌ Error starting agent: {str(e)}")

@app.command()
def check_logs(
    files: Optional[List[str]] = typer.Argument(None, help="Log files to check"),
    errors_only: bool = typer.Option(False, "--errors-only", "-e", help="Show only errors, not warnings"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow logs continuously")
):
    """
    Run the log monitoring tool directly.
    
    Args:
        files: Optional list of log files to check
        errors_only: Whether to show only errors (not warnings)
        follow: Whether to follow logs continuously
    """
    from log_monitor_tool import monitor_logs_continuous
    
    if follow:
        # Run in continuous monitoring mode
        monitor_logs_continuous(files, errors_only)
    else:
        # Run as a one-time check
        results = check_logs_once(files, errors_only)
        typer.echo(results)

@app.command()
def check_services_cmd():
    """Run a quick check on service status only."""
    typer.echo("\n🔍 Checking service status...")
    
    try:
        results = check_services()
        typer.echo(results)
    except Exception as e:
        typer.echo(f"\n❌ Error checking services: {str(e)}")

if __name__ == "__main__":
    # Show a banner on startup
    print("""
    ╔════════════════════════════════════╗
    ║    QAbox Health Checker Agent      ║
    ╚════════════════════════════════════╝
    """)
    app()