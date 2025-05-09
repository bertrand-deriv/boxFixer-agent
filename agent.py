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
from tools.get_troubleshooting_steps import get_service_troubleshooting_steps
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

from rich.console import Console
from rich.table import Table
from rich.align import Align
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from rich.text import Text
from rich.emoji import Emoji
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.columns import Columns

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

console = Console()

# Define tools

@tool
def fetch_service_status_tool():
    """Checks services health using the check_services function"""
    return check_services()

@tool
def troubleshoot_kyc_tool():
    """Troubleshoot KYC service ."""
    return troubleshoot_kyc()

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


system_message = SystemMessagePromptTemplate.from_template(
    f"""
        You are a DevOps assistant designed to help with system monitoring and troubleshooting. 
        Your primary objectives are:
        1. Provide clear and concise information about system health
        2. Use available tools to investigate system issues
        3. Offer actionable recommendations
        4. Communicate in a helpful manner

        Tools available and their purpose:
        - fetch_service_status_tool: Use this tool to get different service statuses including system statuses, docker services, k8s pods
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
tools = [ fetch_service_status_tool, execute_shell_command, check_system_resources, get_service_troubleshooting_steps_tool ] # removed fetch_logs , troubleshoot_kyc_tool

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

def display_typing_effect(message):
    """Display a typing effect for agent responses"""
    for char in message:
        typer.echo(char, nl=False)  # nl=False prevents newline after each char
        time.sleep(0.002)
    typer.echo()  # Add a newline at the end

def display_service_category(category_name: str, services: Optional[List] = None):
    """Display a category of services in a styled table"""
    if not services:
        return None
        
    table = Table(
        box=box.ROUNDED,
        expand=True,
        title=f"{category_name}",
        title_style="bold cyan",
        header_style="bold",
        border_style="blue"
    )
    
    # Define columns
    table.add_column("Status", justify="center", width=6)
    table.add_column("Service Name", style="cyan")
    table.add_column("Status", width=12)
    table.add_column("Message", style="dim", no_wrap=False)
    
    # Add rows
    sorted_services = sorted(services, key=lambda svc: (not svc.running, svc.name))
    for service in sorted_services:
        status_emoji = "✅" if service.running else "❌"
        status_color = "green" if service.running else "red"
        error_text = f"\n[bold red]Error:[/bold red] {service.error}" if service.error else ""
        
        table.add_row(
            status_emoji,
            service.name,
            f"[{status_color}]{service.status}[/{status_color}]",
            f"{service.message}{error_text}"
        )
    
    return table

def create_resource_panel(resources):
    """Create a panel displaying system resource usage"""
    # Parse percentages for color coding
    def get_color(value):
        try:
            if isinstance(value, str) and '%' in value:
                percent = float(value.replace('%', ''))
                if percent > 90:
                    return "bold red"
                elif percent > 70:
                    return "bold yellow"
                return "bold green"
        except ValueError:
            pass
        return "bold"
    
    cpu_line = f"[{get_color(resources.cpu_usage)}]CPU Usage:[/{get_color(resources.cpu_usage)}] {resources.cpu_usage}"
    mem_line = f"[{get_color(resources.memory_usage)}]Memory Usage:[/{get_color(resources.memory_usage)}] {resources.memory_usage}"
    disk_line = f"[{get_color(resources.disk_usage)}]Disk Usage:[/{get_color(resources.disk_usage)}] {resources.disk_usage}"
    
    content = f"{cpu_line}\n{mem_line}\n{disk_line}"
    
    return Panel(
        content,
        title="🔋 System Resources",
        border_style="cyan",
        box=box.ROUNDED
    )

def display_structured_output(structured_output):
    """Display the structured output in a visually appealing format"""
    # Create header with animation
    with Progress(
        TextColumn("[bold blue]Generating diagnostic report..."),
        BarColumn(bar_width=40),
        TextColumn("[bold green]{task.percentage:.0f}%"),
        transient=True
    ) as progress:
        task = progress.add_task("", total=100)
        for i in range(101):
            progress.update(task, completed=i)
            time.sleep(0.01)
    
    # Banner
    console.print("\n")
    console.rule("[bold white on blue]⛑️  DIAGNOSTIC REPORT  ⛑️[/bold white on blue]", style="blue")
    
    # Summary section
    console.print("\n")
    summary_panel = Panel(
        structured_output.summary,
        title="📋 Summary",
        border_style="cyan",
        box=box.ROUNDED
    )
    console.print(summary_panel)
    console.print("\n")
    
    # Resource section
    resource_panel = create_resource_panel(structured_output.resources)
    console.print(resource_panel)
    console.print("\n")
    
    # Services section
    
    # Calculate overall service health
    all_services = []
    
    kyc_services = structured_output.services.kyc_services or []
    passkeys_services = structured_output.services.passkeys_services or []
    crypto_services = structured_output.services.crypto_services or []
    other_services = structured_output.services.other_services or []
    
    all_services.extend(kyc_services)
    all_services.extend(passkeys_services)
    all_services.extend(crypto_services)
    all_services.extend(other_services)
    
    total_services = len(all_services)
    running_services = sum(1 for svc in all_services if svc.running)
    
    if total_services > 0:
        health_percentage = (running_services / total_services) * 100
        health_color = "green" if health_percentage >= 90 else "yellow" if health_percentage >= 70 else "red"
        health_text = f"[bold]System Health:[/bold] [bold {health_color}]{health_percentage:.1f}%[/bold {health_color}] ({running_services} of {total_services} services running)"
        health_text_panel = Panel(
            health_text,
            title="🔌 Services",
            border_style="cyan",
            box=box.ROUNDED
        )
        console.print(health_text_panel)
        console.print("\n")

    # Display services by category
    if kyc_services:
        kyc_table = display_service_category("KYC Services", kyc_services)
        console.print(kyc_table)
        console.print("\n")
        
    if passkeys_services:
        passkeys_table = display_service_category("Passkeys Services", passkeys_services)
        console.print(passkeys_table)
        console.print("\n")
        
    if crypto_services:
        crypto_table = display_service_category("Crypto Services", crypto_services)
        console.print(crypto_table)
        console.print("\n")
        
    if other_services:
        other_table = display_service_category("Other Services", other_services)
        console.print(other_table)
        console.print("\n")
    
    # Display recommendations
    recommendations = structured_output.recommendations
    if recommendations:
        console.rule("[bold blue]💡 Recommendations[/bold blue]", style="blue")
        console.print("\n")
        
        for i, recommendation in enumerate(recommendations, 1):
            rec_panel = Panel(
                recommendation,
                title=f"Recommendation #{i}",
                border_style="cyan",
                box=box.ROUNDED
            )
            console.print(rec_panel)
            console.print("\n")
    
    # Footer
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    footer = Text(f"Report generated by BoxFixer at {timestamp}", style="italic dim")
    console.print(footer, justify="center")
    console.rule(style="blue")


def auto_troubleshoot_services_if_needed(structured_output, graph, config):
    """
    Check for failing services and automatically get troubleshooting guidance through the agent
    """
    from rich import print
    
    # Step 1: Check for failing services across all service categories
    failing_services = []
    service_categories = ["kyc_services", "passkeys_services", "hydra_services", "general_services"]
    
    for category in service_categories:
        services = getattr(structured_output.services, category, []) or []
        category_failing = [
            {"name": svc.name, "category": category.replace("_services", "")} 
            for svc in services 
            if not svc.running or svc.status.lower() in ["error", "not found"]
        ]
        failing_services.extend(category_failing)

    if not failing_services:
        print("\n[green]✅ All services are operational. No troubleshooting needed.[/green]")
        return

    # Step 2: Format a list of failing services for the agent
    failing_service_list = "\n".join([f"- {svc['name']} ({svc['category']})" for svc in failing_services])
    print(f"\n[yellow]⚠️ Found {len(failing_services)} failing services[/yellow]")
    print("[yellow]🤖 Let me find the troubleshooting steps for each...[/yellow]\n")
    
    # Step 3: Craft a human-like troubleshooting request for the agent
    troubleshoot_message = f"""
    I need your help with troubleshooting some failing services on our system. The following services are currently not running or showing errors:
    
    {failing_service_list}
    
    Could you please:
    1. Use the get_service_troubleshooting_steps_tool for each failing service to get diagnostic information. You should call it with
       appropriate service category.
    2. For services falling under same category, call the tool once otherwise it would be repeating same troubleshooting steps.
    3. Provide me with a clear set of steps, custom fixes and commands needed to troubleshoot and fix each service.
    5. Return the response in Human friendly way (Not JSON).
    6. Finish by asking the user if you can go ahead and start executing one by one
    """
    
    # Step 4: Invoke the agent with the troubleshooting message
    response = graph.invoke({"messages": troubleshoot_message}, config)
    agent_response = response["messages"][-1].content
    
    # Step 5: Display the agent's response
    print("\n🤖 [Troubleshooting Recommendations]")
    display_typing_effect(agent_response)

@app.command()
def run_agent(interactive: bool = True):
    """
    Runs the AI agent to fetch logs and service status.
    
    Args:
        interactive: Whether to run in interactive mode with continuous conversation
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
            display_structured_output(structured_output)
            auto_troubleshoot_services_if_needed(structured_output, graph, config)

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

