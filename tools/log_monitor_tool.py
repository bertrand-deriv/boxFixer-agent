#!/usr/bin/env python3
import subprocess
import re
import json
import argparse
import sys
from typing import List, Dict, Any, Optional

ERROR_PATTERN = re.compile(r"\bE\b|error", re.IGNORECASE)
WARNING_PATTERN = re.compile(r"\bW\b|warn", re.IGNORECASE)

# Color codes
RESET = "\033[0m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"

def extract_message_from_json(line: str) -> str:
    """Extract just the message field from JSON log entries"""
    try:
        data = json.loads(line)

        if "message" in data:
            return data['message']
        else:
            for field in ["msg", "text", "log", "error"]:
                if field in data:
                    return data[field]  
            return f"[JSON log with no message field: {data.get('severity', 'unknown')} level]"
    except:
        return line

def colorize_log(line: str, errors_only: bool = False, no_color: bool = False) -> Optional[str]:
    """Apply color to error and warning logs for better visibility."""
    display_message = extract_message_from_json(line)
    
    if no_color:
        if ERROR_PATTERN.search(line):
            return f"[ERROR] {display_message}"
        elif not errors_only and WARNING_PATTERN.search(line):
            return f"[WARNING] {display_message}"
        return None
    else:
        if ERROR_PATTERN.search(line):
            return f"{RED}{BOLD}[ERROR]{RESET} {RED}{display_message}{RESET}"
        elif not errors_only and WARNING_PATTERN.search(line):
            return f"{YELLOW}{BOLD}[WARNING]{RESET} {YELLOW}{display_message}{RESET}"
        return None

def get_recent_logs(log_files: List[str]) -> List[str]:
    """Retrieve the most recent logs."""
    try:
        files_str = " ".join(log_files)
        
        cmd = f"""
        for f in {files_str}; do 
            echo -e "\\n--- $f ---"; 
            if [[ $f == *.gz ]]; then 
                zcat \"$f\" | tail -n 5; 
            else 
                tail -n 5 \"$f\"; 
            fi; 
        done
        """
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        # Filter out duplicate logs
        seen = set()
        unique_logs = []
        for line in result.stdout.split("\n"):
            stripped_line = line.strip()
            if stripped_line and stripped_line not in seen:
                seen.add(stripped_line)
                unique_logs.append(stripped_line)
        
        return unique_logs
        
    except Exception as e:
        print(f"\n❌ Error while retrieving logs: {str(e)}")
        return []

def check_logs_once(
    log_files: List[str] = None,
    errors_only: bool = False,
    no_color: bool = False,
    for_agent: bool = False
) -> str:
    """
    Check logs once for errors and warnings.
    
    Args:
        log_files: List of log file paths to check
        errors_only: Whether to show only errors (not warnings)
        no_color: Whether to disable colored output
        for_agent: Whether this is being called by an agent
        
    Returns:
        String containing the log analysis results
    """
    if log_files is None:
        log_files = [
            "/var/log/deriv/*",
            "/var/log/httpd/*"
        ]
    
    log_lines = get_recent_logs(log_files)
    
    results = []
    for line in log_lines:
        if not line.strip():
            continue
            
        colorized_line = colorize_log(line, errors_only, no_color)
        if colorized_line:
            results.append(colorized_line)
    
    if not results:
        return "No errors or warnings found in the recent logs."
    
    if for_agent:
        return f"Found {len(results)} issues in logs:\n" + "\n".join(results)
    else:
        return "\n".join(results)

def monitor_logs_continuous(
    log_files: List[str] = None,
    errors_only: bool = False,
    no_color: bool = False
) -> None:
    """
    Monitor logs continuously using tail -f
    
    Args:
        log_files: List of log file paths to monitor
        errors_only: Whether to show only errors (not warnings)
        no_color: Whether to disable colored output
    """
    if log_files is None:
        log_files = [
            "/var/log/httpd/*",          
        ]
        
    try:
        files_str = " ".join(log_files)
        cmd = f"tail -F {files_str}"
        
        if errors_only:
            print(f"\n🔍 Monitoring logs for ERRORS only (Ctrl+C to exit)...")
        else:
            print(f"\n🔍 Monitoring logs for ERRORS and WARNINGS (Ctrl+C to exit)...")
            
        # Use subprocess.Popen to stream output line by line
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                  stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        
        seen = set()
        unique_logs = []
        for line in process.stdout:
            stripped_line = line.strip()

            if not stripped_line:
                continue
            if stripped_line and stripped_line not in seen:
                seen.add(stripped_line)
            colorized_line = colorize_log(line, errors_only, no_color)
            if colorized_line:
                print(colorized_line, flush=True)            
                unique_logs.append(stripped_line)
        
        return unique_logs

        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
                
            colorized_line = colorize_log(line, errors_only, no_color)
            if colorized_line:
                print(colorized_line, flush=True)
              
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error executing tail command: {e}")
    except KeyboardInterrupt:
        print("\nExiting log monitor...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        # Cleanup
        if 'process' in locals() and process:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monitor logs for errors and warnings')
    parser.add_argument('--files', nargs='*', help='Override default log files to monitor')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--errors-only', action='store_true', help='Show only errors, not warnings')
    parser.add_argument('--follow', '-f', action='store_true', help='Follow logs continuously (like tail -f)')
    args = parser.parse_args()
    
    log_files = args.files if args.files else None
    
    if args.follow:
        monitor_logs_continuous(log_files, args.errors_only, args.no_color)
    else:
        results = check_logs_once(log_files, args.errors_only, args.no_color)
        print(results)