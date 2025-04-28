#!/usr/bin/env python
"""
DevOps Troubleshooter Agent CLI
--------------------------------
A command-line interface for interacting with the DevOps Troubleshooter Agent.
"""

import os
import sys
import argparse
import json
from typing import List, Optional
import readline  # For better command line editing experience

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

# Import the agent
from devops_agent import create_devops_agent

class DevOpsAgentCLI:
    """Command-line interface for the DevOps Agent."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the CLI."""
        # Set API key if provided
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # Create the agent
        self.agent = create_devops_agent()
        
        # Initialize conversation history
        self.conversation_history: List[BaseMessage] = []
        
        # Initialize readline history
        readline.set_history_length(1000)
        
        # Terminal colors
        self.colors = {
            "reset": "\033[0m",
            "bold": "\033[1m",
            "underline": "\033[4m",
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
        }
    
    def print_header(self):
        """Print the CLI header."""
        header = f"""
{self.colors['bold']}{self.colors['cyan']}=================================================={self.colors['reset']}
{self.colors['bold']}{self.colors['cyan']}       DevOps Troubleshooter Agent CLI{self.colors['reset']}
{self.colors['bold']}{self.colors['cyan']}=================================================={self.colors['reset']}
{self.colors['green']}
Type your DevOps issues or questions below.
Use /help to see available commands.
Use /exit or Ctrl+C to quit.
{self.colors['reset']}
"""
        print(header)
    
    def print_help(self):
        """Print help information."""
        help_text = f"""
{self.colors['bold']}{self.colors['yellow']}Available Commands:{self.colors['reset']}
{self.colors['yellow']}/help{self.colors['reset']}     - Show this help message
{self.colors['yellow']}/exit{self.colors['reset']}     - Exit the application
{self.colors['yellow']}/clear{self.colors['reset']}    - Clear the conversation history
{self.colors['yellow']}/save{self.colors['reset']}     - Save conversation to a file
{self.colors['yellow']}/load{self.colors['reset']}     - Load conversation from a file
{self.colors['yellow']}/history{self.colors['reset']}  - Show conversation history
{self.colors['yellow']}/tools{self.colors['reset']}    - List available troubleshooting tools
"""
        print(help_text)
    
    def print_tools(self):
        """Print information about available tools."""
        tools_text = f"""
{self.colors['bold']}{self.colors['yellow']}Available Troubleshooting Tools:{self.colors['reset']}
{self.colors['yellow']}check_system_resource_usage{self.colors['reset']} - Check CPU, memory, disk, or network usage
{self.colors['yellow']}check_logs{self.colors['reset']} - Retrieve logs for a specific service
{self.colors['yellow']}check_service_status{self.colors['reset']} - Check if a service is running correctly
{self.colors['yellow']}run_network_diagnostics{self.colors['reset']} - Test connectivity, latency, or routing to a target
{self.colors['yellow']}check_configuration{self.colors['reset']} - Retrieve configuration for a system component
{self.colors['yellow']}search_documentation{self.colors['reset']} - Find relevant information in documentation
"""
        print(tools_text)
    
    def save_conversation(self, filename: str):
        """Save the conversation history to a file."""
        if not filename.endswith('.json'):
            filename += '.json'
        
        serializable_history = []
        for msg in self.conversation_history:
            serializable_history.append({
                "type": msg.type,
                "content": msg.content
            })
        
        with open(filename, 'w') as f:
            json.dump(serializable_history, f, indent=2)
        
        print(f"{self.colors['green']}Conversation saved to {filename}{self.colors['reset']}")
    
    def load_conversation(self, filename: str):
        """Load a conversation history from a file."""
        if not filename.endswith('.json'):
            filename += '.json'
        
        try:
            with open(filename, 'r') as f:
                serialized_history = json.load(f)
            
            self.conversation_history = []
            for msg in serialized_history:
                if msg["type"] == "human":
                    self.conversation_history.append(HumanMessage(content=msg["content"]))
                elif msg["type"] == "ai":
                    self.conversation_history.append(AIMessage(content=msg["content"]))
                elif msg["type"] == "system":
                    self.conversation_history.append(SystemMessage(content=msg["content"]))
            
            print(f"{self.colors['green']}Conversation loaded from {filename}{self.colors['reset']}")
            
            # Print a summary
            human_msgs = sum(1 for msg in self.conversation_history if isinstance(msg, HumanMessage))
            ai_msgs = sum(1 for msg in self.conversation_history if isinstance(msg, AIMessage))
            print(f"{self.colors['green']}Loaded {human_msgs} user messages and {ai_msgs} agent responses{self.colors['reset']}")
            
        except FileNotFoundError:
            print(f"{self.colors['red']}File not found: {filename}{self.colors['reset']}")
        except json.JSONDecodeError:
            print(f"{self.colors['red']}Invalid JSON in file: {filename}{self.colors['reset']}")
    
    def print_history(self):
        """Print the conversation history."""
        if not self.conversation_history:
            print(f"{self.colors['yellow']}No conversation history yet.{self.colors['reset']}")
            return
        
        print(f"\n{self.colors['bold']}{self.colors['cyan']}Conversation History:{self.colors['reset']}")
        for i, msg in enumerate(self.conversation_history):
            if isinstance(msg, SystemMessage):
                continue  # Skip system messages
            elif isinstance(msg, HumanMessage):
                print(f"{self.colors['green']}User ({i}):{self.colors['reset']} {msg.content[:100]}...")
            elif isinstance(msg, AIMessage):
                print(f"{self.colors['blue']}Agent ({i}):{self.colors['reset']} {msg.content[:100]}...")
        print()
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        print(f"{self.colors['green']}Conversation history cleared.{self.colors['reset']}")
    
    def process_command(self, command: str) -> bool:
        """Process CLI commands."""
        cmd = command.strip().lower()
        
        if cmd == "/help":
            self.print_help()
            return True
        elif cmd == "/exit":
            print(f"{self.colors['green']}Goodbye!{self.colors['reset']}")
            return False
        elif cmd == "/clear":
            self.clear_history()
            return True
        elif cmd.startswith("/save"):
            parts = command.split(maxsplit=1)
            filename = parts[1] if len(parts) > 1 else "conversation.json"
            self.save_conversation(filename)
            return True
        elif cmd.startswith("/load"):
            parts = command.split(maxsplit=1)
            filename = parts[1] if len(parts) > 1 else "conversation.json"
            self.load_conversation(filename)
            return True
        elif cmd == "/history":
            self.print_history()
            return True
        elif cmd == "/tools":
            self.print_tools()
            return True
        
        return True  # Continue running
    
    def format_agent_response(self, response: str) -> str:
        """Format the agent's response for terminal display."""
        # Basic formatting
        formatted = response.replace('\n\n', '\n')
        
        # Highlight tool usages
        formatted = formatted.replace("I used the ", f"{self.colors['cyan']}I used the ")
        formatted = formatted.replace(" tool with input ", f" tool{self.colors['reset']} with input ")
        
        # Highlight reflection sections
        if "Reflection:" in formatted:
            formatted = formatted.replace("Reflection:", f"{self.colors['magenta']}Reflection:{self.colors['reset']}")
        
        # Highlight diagnostics and solutions
        highlight_phrases = [
            "The issue is", "The problem is", "This indicates", "I recommend", 
            "You should", "Steps to fix", "Solution:", "Diagnosis:"
        ]
        for phrase in highlight_phrases:
            if phrase in formatted:
                formatted = formatted.replace(phrase, f"{self.colors['yellow']}{phrase}{self.colors['reset']}")
        
        return formatted
    
    def run(self):
        """Run the CLI interaction loop."""
        self.print_header()
        
        try:
            while True:
                # Get user input
                user_input = input(f"{self.colors['green']}User:{self.colors['reset']} ")
                
                # Process commands
                if user_input.startswith("/"):
                    should_continue = self.process_command(user_input)
                    if not should_continue:
                        break
                    continue
                
                print(f"{self.colors['blue']}Agent:{self.colors['reset']} Thinking...")
                
                # Run the agent
                try:
                    messages = self.agent(user_input, self.conversation_history)
                    
                    # Find the last AI message
                    ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
                    if ai_messages:
                        last_response = ai_messages[-1].content
                        formatted_response = self.format_agent_response(last_response)
                        print(f"{self.colors['blue']}Agent:{self.colors['reset']} {formatted_response}")
                    
                    # Update conversation history
                    self.conversation_history = [msg for msg in messages 
                                               if not isinstance(msg, SystemMessage)]
                    
                except Exception as e:
                    print(f"{self.colors['red']}Error: {str(e)}{self.colors['reset']}")
                
        except KeyboardInterrupt:
            print(f"\n{self.colors['green']}Exiting...{self.colors['reset']}")
        
        print(f"{self.colors['green']}Thank you for using DevOps Troubleshooter!{self.colors['reset']}")

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="DevOps Troubleshooter Agent CLI")
    parser.add_argument("--api-key", type=str, help="OpenAI API key")
    args = parser.parse_args()
    
    # Create and run the CLI
    cli = DevOpsAgentCLI(api_key=args.api_key)
    cli.run()

if __name__ == "__main__":
    main()