import subprocess
import shlex
import re
from langchain_core.tools import tool

@tool
def execute_shell_command_tool(command: str) -> str:
    """
    Execute a shell command and return its output.
    Args:
    command (str): The command to execute (supports pipes, redirections, and shell features)
    Returns:
        str: results as a string
    """
    # More comprehensive blocklist with regex patterns for dangerous operations
    dangerous_patterns = [
        r'\brm\s+-rf\b', r'\bdd\b', r'\bmkfs\b', 
        r'\bchmod\s+777\b', r'\bchown\b', r'\bmkswap\b',
        r'>\s*/dev/', r'>\s*/etc/', r'>\s*/sys/', 
        r'>\s*/proc/', r'>\s*/boot/'
    ]
    
    # Check for unsafe commands using regex for better pattern matching
    if any(re.search(pattern, command, re.IGNORECASE) for pattern in dangerous_patterns):
        return "Error: Command blocked for security reasons."
    
    try:
        # Use shell=True to support pipes, redirections, and other shell features
        result = subprocess.run(
            command, 
            shell=True,
            capture_output=True, 
            text=True, 
            timeout=60,
            executable='/bin/bash'
        )
        
        if result.returncode == 0:
            return result.stdout.strip() or "Command executed successfully with no output."
        else:
            return f"Command failed (Exit code {result.returncode}):\n{result.stderr.strip()}"
    
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except FileNotFoundError:
        return f"Error: Command not found or shell cannot execute - {command}"
    except PermissionError:
        return f"Error: Permission denied for command - {command}"
    except Exception as e:
        return f"Error executing command: {str(e)}"