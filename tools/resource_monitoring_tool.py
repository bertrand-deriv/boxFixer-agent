#!/usr/bin/env python3
import subprocess
from langchain_core.tools import tool

# @tool
def check_system_resources(): 
    """Get basic CPU and memory usage percentages.""" 
    try:
        # Get CPU usage with top (batch mode, run once)
        cpu_cmd = "top -bn1 | grep '%Cpu' | awk '{print $2}'"
        cpu_result = subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True)
        cpu_usage = cpu_result.stdout.strip() or "N/A"
        
        # Get memory usage with free
        mem_cmd = "free -m | grep 'Mem:' | awk '{print $3/$2 * 100}'"
        mem_result = subprocess.run(mem_cmd, shell=True, capture_output=True, text=True)
        mem_usage = mem_result.stdout.strip() or "N/A"
        
        # Convert memory usage to float if possible
        try:
            mem_usage_float = float(mem_usage)
            mem_usage_formatted = f"{mem_usage_float:.1f}"
        except ValueError:
            mem_usage_formatted = mem_usage
        
        # Format output
        return f"System Resources:\n- CPU Usage: {cpu_usage}%\n- Memory Usage: {mem_usage_formatted}%"
    except Exception as e:
        return f"Error checking system resources: {str(e)}"
