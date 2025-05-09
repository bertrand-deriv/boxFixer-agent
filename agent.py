#!/usr/bin/env python3
import typer
import os
import sys
import time
from dotenv import load_dotenv

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from tools.log_monitor_tool import check_logs_once
from tools.service_health_check_tool import check_services
from tools.command_executor_tool import execute_shell_command_tool
from tools.resource_monitoring_tool import check_system_resources
from tools.get_troubleshooting_steps_tool import get_service_troubleshooting_steps

from utils.display_utility import display_typing_effect, display_structured_output
from utils.pydantic_class_utility import MonitoringReport
from utils.troubleshoot_service_utility import auto_troubleshoot_services_if_needed

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich import box, print

output_parser = PydanticOutputParser(pydantic_object=MonitoringReport)

load_dotenv()

app = typer.Typer()

console = Console()

# Define tools
@tool
def get_service_status_tool():
    """Checks services health using the check_services function"""
    return check_services()

@tool
def get_service_troubleshooting_steps_tool(service_name: str):
    """
    Retrieves diagnostic steps and troubleshooting information for a service.
    
    Args:
        service_name (str): The name of the service to troubleshoot (e.g., "kyc_services", "passkeys_services", "hydra_services")
        
    Returns:
        dict: A dictionary containing troubleshooting steps, common fixes, and additional tips
    """
    return get_service_troubleshooting_steps(service_name)

@tool
def get_system_resources_tool():
    """Get basic CPU, memory, and disk usage percentages.""" 
    return check_system_resources()

system_message = SystemMessagePromptTemplate.from_template(
    f"""
        You are a DevOps assistant designed to help with system monitoring and troubleshooting. 
        Your primary objectives are:
        1. Provide clear and concise information about system health
        2. Use available tools to investigate system issues
        3. Offer actionable recommendations
        4. Communicate in a helpful manner

        Tools available and their purpose:
        - get_service_status_tool: Use this tool to get different service statuses including system statuses, docker services, k8s pods
                                Use this tool also to advice whether the host (QAbox) needs a rebuild. If more than 2 services has been 
                                running for 5 days its advisable to rebuild the QAbox
        - execute_shell_command_tool: Use this tool to execute commands in terminal. Always ask for user approval before executing command.
        - get_system_resources_tool: Use this tool to check system resource usage. If there's any red flags, report them. It is advisable to rebuild
                                  QAbox when either Disk, CPU or memory is at bottleneck.

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
tools = [ get_service_status_tool, execute_shell_command_tool, get_system_resources_tool, get_service_troubleshooting_steps_tool ]

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

@app.command()
def run_agent():
    """
    Runs the AI agent to fetch logs and service status.
    """
    typer.echo("\n🤖 BoxFixer starting up...")

    typer.echo("\n🔚 Type 'exit' or 'quit' to end the session.")

    instructions = output_parser.get_format_instructions()
    escaped_instructions = instructions.replace("{", "{{").replace("}", "}}")
    
    initial_query = f"""
    As DevOps assistant agent, give the report of the service health check and advise when QAbox is in ready status to start testing
    CRITICAL: At the end of your analysis, you MUST provide a standardized report in JSON format exactly as specified here:
        {escaped_instructions}
    Do not include any text before or after the JSON structure. The JSON should be the only content in your final response.
    """
    typer.echo(f"\n🔍 Running initial diagnosis...")
    
    try: 
        with console.status("[bold blue]Analyzing your system...", spinner="dots") as status:  
            time.sleep(2)  
            status.update("[bold yellow]Running Service health check tools...")
            time.sleep(2)  
            status.update("[bold green]Processing results...") 
            time.sleep(2)  
        response = graph.invoke({"messages": initial_query}, config)
        agent_response = response["messages"][-1].content
        try:
            structured_output = output_parser.parse(agent_response)
            display_structured_output(structured_output, console)
            auto_troubleshoot_services_if_needed(structured_output, graph, config, display_typing_effect)

        except Exception as e:
            typer.echo("\n🤖 Agent response:")
            typer.echo(f"\nParsing error: {str(e)}")
            display_typing_effect(agent_response)        
                
        while True:
            user_input = typer.prompt("\n💬 You")
            
            if user_input.lower() in ["exit", "quit", "q"]:
                typer.echo("\n👋 Ending agent session. Goodbye!")
                break       
            try:
                with console.status("[bold cyan]Thinking...", spinner="dots") as status:
                    time.sleep(2)
                response = graph.invoke({"messages": user_input}, config)
                agent_response = response["messages"][-1].content
                try:
                    structured_output = output_parser.parse(agent_response)
                    display_structured_output(structured_output, console)
                except Exception as e:
                    typer.echo("\n🤖 Agent response:")
                    display_typing_effect(agent_response)
            except Exception as e:
                typer.echo(f"\n❌ Error processing query: {str(e)}")
                
    except Exception as e:
        typer.echo(f"\n❌ Error starting agent: {str(e)}")

@app.command()
def check_services_cmd():
    """Run a quick check to get services status."""
    typer.echo("\n🔍 Checking service status...\n")
    try:
        results = check_services()
        typer.echo(results)
    except Exception as e:
        typer.echo(f"\n❌ Error checking services: {str(e)}")

@app.command()
def get_tb_steps( service: str = typer.Argument(..., help="e.g: kyc_services, hydra_services, etc")):
    """Get troubleshooting steps for particular services"""
    typer.echo(f"\n🔍 Fetching troubleshooting steps for {service}...\n")
    try:
        results = get_service_troubleshooting_steps(service)
        typer.echo(results)
    except Exception as e:
        typer.echo(f"\n❌ Error Getting troubleshooting steps: {str(e)}")

@app.command()
def check_sys_resources():
    """Get System resources like CPU, Memory, Disk space"""
    try:
        results = check_system_resources()
        typer.echo(results)
    except Exception as e:
        typer.echo(f"\n❌ Error Getting system resources: {str(e)}")

if __name__ == "__main__":
    text = f"[bold blue]BoxFixer Agent"
    centered_text = Align.center(text)
    start_panel = Panel(
        centered_text,
        border_style="cyan",
        box=box.ROUNDED
    )
    console.print(start_panel)
    console.print("\n")
    app()

