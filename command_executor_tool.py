import subprocess
import shlex
from langchain_core.tools import tool

@tool
def execute_shell_command(command: str) -> str:
    """Execute a shell command and return its output."""
    # List of potentially dangerous commands to block
    unsafe_commands = [
        'sudo', 'rm -rf', 'dd', 'mkfs', 
        'chmod', 'chown', 'mkswap'
    ]
    
    # Check for unsafe commands
    if any(unsafe_cmd in command.lower() for unsafe_cmd in unsafe_commands):
        return "Error: Command blocked for security reasons."
    
    try:
        # Split the command safely
        split_command = shlex.split(command)
        
        # Run the command
        result = subprocess.run(
            split_command, 
            capture_output=True, 
            text=True, 
            timeout=30  # 30-second timeout
        )
        
        # Combine stdout and stderr
        if result.returncode == 0:
            return result.stdout.strip() or "Command executed successfully with no output."
        else:
            return f"Command failed (Exit code {result.returncode}):\n{result.stderr.strip()}"
    
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except FileNotFoundError:
        return f"Error: Command not found - {command}"
    except PermissionError:
        return f"Error: Permission denied for command - {command}"
    except Exception as e:
        return f"Error executing command: {str(e)}"