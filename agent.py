#!/usr/bin/env python3
import typer
import os
import sys
import time
from typing import List, Optional, Dict
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from tools.log_monitor_tool import check_logs_once
from tools.service_health_check_tool import check_services
from tools.command_executor_tool import execute_shell_command
from tools.resource_monitoring_tool import check_system_resources
from tools.kyc_troubleshooting_tool import troubleshoot_kyc
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

class ServiceStatus(BaseModel):
    name: str = Field(description="Name of the service")
    status: str = Field(description="General status indicator, e.g., 'ok', 'not found', 'error'")
    running: bool = Field(description="Indicates whether the service is running")
    message: str = Field(description="Descriptive message about the service state")
    error: Optional[str] = Field(default=None, description="Error message if the service failed")

class ResourceStatus(BaseModel):
    cpu_usage: str = Field(description="CPU usage")
    memory_usage: str = Field(description="Memory usage")
    disk_usage: str = Field(description="Disk usage")

class ServicesOutput(BaseModel):
    kyc_services: Optional[List[ServiceStatus]] = Field(description="Any service that has word 'kyc' in its name for example: kyc_identity_verification as well as 'service-business-rule' If there's none, return null")
    passkeys_services: Optional[List[ServiceStatus]] = Field(description="Any service that word 'passkeys' in its name. If there's none, return null")
    crypto_services: Optional[List[ServiceStatus]] = Field(description="Any service that word 'crypto' in its name. If there's none, return null")
    other_services: List[ServiceStatus] = Field(description="Other miscellaneous services")

class MonitoringReport(BaseModel):
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
def fetch_service_status():
    """Checks service health using the service checker tool."""
    return check_services()

@tool
def troubleshoot_kyc_tool():
    """Troubleshoot KYC service ."""
    return troubleshoot_kyc()


system_message = SystemMessagePromptTemplate.from_template(
    f"""
        You are a DevOps assistant designed to help with system monitoring and troubleshooting. 
        Your primary objectives are:
        1. Provide clear and concise information about system health
        2. Use available tools to investigate system issues
        3. Offer actionable recommendations
        4. Communicate in a helpful manner

        Tools available and their purpose:
        - fetch_service_status: Use this tool to get different service statuses including system statuses, docker services, k8s pods
                                Use this tool also to advice whether the host (QAbox) needs a rebuild. If more than 2 services has been 
                                running for 5 days its advisable to rebuild the QAbox
        - execute_shell_command: Use this tool to execute commands in terminal. Always ask for user approval before executing command.
        - check_system_resources: Use this tool to check system resource usage. If there's any red flags, report them. It is advisable to rebuild
                                  QAbox when either Disk, CPU or memory is at bottleneck.
        - troubleshoot_ky_tool: Use this to troubleshoot the kyc service

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
tools = [ fetch_service_status, execute_shell_command, check_system_resources, troubleshoot_kyc_tool ] # removed fetch_logs

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

def display_services(label: str, services: List):
    print(f"\n{label.upper()}:")
    if services:
        sorted_services = sorted(services, key=lambda svc: bool(svc.running))
        for svc in sorted_services:
            status_emoji = "✅" if svc.running else "❌"
            print(f"  {status_emoji} {svc.name}")
            print(f"     Status  : {svc.status}")
            print(f"     Running : {svc.running}")
            print(f"     Message : {svc.message}")
            print(f"     Error   : {svc.error if svc.error else 'None'}")
    else:
        print(f"No {label.lower()} found.")


def display_structured_output(structured_output):
    """Display the structured output in a user-friendly format"""

    print("\n ===== 🤖 MONITORING REPORT =====\n")

    # Display summary
    print(f"📋 SUMMARY: {structured_output.summary}\n")

    # Display service categories
    display_services("KYC Services", structured_output.services.kyc_services)
    display_services("Passkeys Services", structured_output.services.passkeys_services)
    display_services("Crypto Services", structured_output.services.crypto_services)
    display_services("Other Services", structured_output.services.other_services)

    # Display system resources
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
        time.sleep(0.002)
    print()

def auto_troubleshoot_kyc_if_needed(structured_output, graph, config):
    """
    Check for failing KYC services and automatically run troubleshooting through the agent
    """
    from rich import print
    # Step 1: Check if any KYC services are failing
    kyc_services = structured_output.services.kyc_services or []
    failing_services = [
        svc for svc in kyc_services 
        if not svc.running or svc.status.lower() in ["error", "not found"]
    ]

    if not failing_services:
        print("\n[green]✅ All KYC services are operational. No troubleshooting needed.[/green]")
        return

    # Step 2: Format a list of failing services for the prompt
    failing_service_names = ", ".join([svc.name for svc in failing_services])
    print(f"\n[yellow]⚠️ Found failing KYC services: {failing_service_names}[/yellow]")
    print("[yellow]🔧 Automatically initiating KYC troubleshooting...[/yellow]\n")
    
    # Step 3: Craft a troubleshooting instruction for the agent
    troubleshoot_message = f"""
    URGENT: KYC services are failing. The following services need immediate attention:
    {failing_service_names}
    
    Use the troubleshoot_kyc_tool to diagnose and fix these services. Provide a detailed
    report of what you find and any actions taken and a list of commands to be executed. Return the response in Human friendly way (Not JSON).
    Finish by asking the user if you can go ahead and start executing one by one
    """
    
    # Step 4: Invoke the agent with the troubleshooting message
    print("🤖 [Agent is troubleshooting KYC services...]")
    response = graph.invoke({"messages": troubleshoot_message}, config)
    agent_response = response["messages"][-1].content
    
    # Step 5: Display the response with typing effect for natural conversation
    print("\n🤖 [KYC Troubleshooting Results]")
    display_typing_effect(agent_response)

@app.command()
def run_agent(interactive: bool = True):
    """
    Runs the AI agent to fetch logs and service status.
    
    Args:
        interactive: Whether to run in interactive mode with continuous conversation
    """
    typer.echo("\n🤖 AI Agent starting up...")
    typer.echo("📊 Initializing systems...")

    instructions = output_parser.get_format_instructions()
    escaped_instructions = instructions.replace("{", "{{").replace("}", "}}")
    
    # First automated query to check logs and service status
    initial_query = f"""
    As DevOps assistant agent, give the report of the service health check and advise when QAbox is in ready status to start testing
    CRITICAL: At the end of your analysis, you MUST provide a standardized report in JSON format exactly as specified here:
        {escaped_instructions}
    Do not include any text before or after the JSON structure. The JSON should be the only content in your final response.
    """
    typer.echo(f"\n🔍 Running initial check.....")
    
    try:
        # Run the first query automatically
     
        response = graph.invoke({"messages": initial_query}, config)
        agent_response = response["messages"][-1].content
        print(tools)
        try:
            # Try to parse the response into structured format
            structured_output = output_parser.parse(agent_response)
            display_structured_output(structured_output)
            auto_troubleshoot_kyc_if_needed(structured_output, graph, config)

        except Exception as e:
            # Fall back to normal display if parsing fails
            typer.echo("\n🤖 Agent response (raw format - parsing failed):")
            typer.echo(f"\nParsing error: {str(e)}")
            display_typing_effect(agent_response)        
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
                    typer.echo("\n🤖 Agent response:")
                    display_typing_effect(agent_response)
            except Exception as e:
                typer.echo(f"\n❌ Error processing query: {str(e)}")
                
    except Exception as e:
        typer.echo(f"\n❌ Error starting agent: {str(e)}")

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

