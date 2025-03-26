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
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

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

# Initialize LLM
llm = ChatLiteLLM(
    model_name="gpt-4o",
    api_base=os.getenv("API_BASE"),
    api_key=os.getenv("API_KEY")
).bind(
    messages=[SystemMessage(content="""
            You are a DevOps assistant designed to help with system monitoring and troubleshooting. 
            Your primary objectives are:
            1. Provide clear and concise information about system health
            2. Use available tools to investigate system issues
            3. Offer actionable recommendations
            4. Communicate in a professional and helpful manner

            When using tools:
            - Always explain what tool you're using and why
            - Interpret tool results in a meaningful context
            - Provide clear explanations of any findings
            - Suggest next steps if potential issues are detected

            Constraints:
            - Never attempt to execute potentially dangerous commands
            - Protect system security at all times
            - If unsure about a command or its implications, ask for clarification
            """)]
)

# Set up tools
tools = [fetch_logs, fetch_service_status, execute_shell_command]

# Initialize memory
memory = MemorySaver()

# Create agent graph
graph = create_react_agent(
    llm,
    tools=tools,
    checkpointer=memory
)

# Configuration
config = {"configurable": {"thread_id": "1"}}

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
    initial_query = "As DevOps assistant agent, give me the report of the current logs and the service health check"
    typer.echo(f"\n🔍 Running initial check: '{initial_query}'")
    
    try:
        # Run the first query automatically
        response = graph.invoke({"messages": initial_query}, config)
        agent_response = response["messages"][-1].content
        
        typer.echo("\n🤖 Agent response:")
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