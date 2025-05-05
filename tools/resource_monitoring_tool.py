#!/usr/bin/env python3
import subprocess

def check_system_resources(): 
    """Get basic CPU, memory, and disk usage percentages.""" 
    try:
        # CPU Usage (top in batch mode, parse with awk)
        cpu_cmd = "top -bn1 | grep '%Cpu' | awk '{print $2}'"
        cpu_result = subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True)
        cpu_usage = cpu_result.stdout.strip() or "N/A"
        
        # Memory Usage (free -m)
        mem_cmd = "free -m | grep 'Mem:' | awk '{print $3/$2 * 100}'"
        mem_result = subprocess.run(mem_cmd, shell=True, capture_output=True, text=True)
        mem_usage = mem_result.stdout.strip() or "N/A"
        
        # Disk Usage (df for root partition)
        disk_cmd = "df -h / | awk 'NR==2 {print $5}'"
        disk_result = subprocess.run(disk_cmd, shell=True, capture_output=True, text=True)
        disk_usage = disk_result.stdout.strip() or "N/A"
        
        # Format memory usage as float with 1 decimal if valid
        try:
            mem_usage_float = float(mem_usage)
            mem_usage_formatted = f"{mem_usage_float:.1f}"
        except ValueError:
            mem_usage_formatted = mem_usage
        
        return (
            "System Resources:\n"
            f"- CPU Usage   : {cpu_usage}%\n"
            f"- Memory Usage: {mem_usage_formatted}%\n"
            f"- Disk Usage  : {disk_usage}"
        )
    
    except Exception as e:
        return f"Error checking system resources: {str(e)}"

if __name__ == "__main__":
    print(check_system_resources())