#!/usr/bin/env python3
import subprocess
import json
import re
from typing import List, Dict, Any

# Color codes for terminal output
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"

# List of important services to check
DEFAULT_SERVICES = [
    "crypto_cashier_paymentapi",
    "kyc_identity_verification",
    "passkeys",
    "pgbouncer",
    "pgbouncer-chart",
    "dd_agent",
    "kyc_health_check",
    "binary_events_general_stream",
    "service-kyc-smile-identity",
    "service-kyc-rules",
    "service-business-rule",
    "deriv-redis-passkeys",
    "pgbouncer-chart-gray",
    "deriv-passkeys-gray"
]

# Get the hostname for kubernetes
hostname_process = subprocess.run("hostname", shell=True, capture_output=True, text=True)
hostname = hostname_process.stdout.strip().split('.')[0]

def check_service_status(service_name: str) -> Dict[str, Any]:
    """Check the status of a specific service"""
    result = {
        "name": service_name,
        "status": "unknown",
        "running": False,
        "message": "",
        "error": None
    }
    
    try:
        # First try systemctl (for system services)
        cmd = f"systemctl status {service_name}"
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if process.returncode == 0:
            # Service exists and systemctl returned info
            if "Loaded: loaded" in process.stdout:
                result["status"] = "ok"
            else:
                result["status"] = "Not loaded"
            active_match = re.search(r'Active:\s+(.*?)(?:\s+since|\s*$)', process.stdout)
            if active_match:
                result["running"] = True
                result["message"] = "System service: Loaded and running"
        else:
            # Try checking as a Docker container
            docker_cmd = f"docker ps --filter name={service_name} --format '{{{{.Status}}}}'"
            docker_process = subprocess.run(docker_cmd, shell=True, capture_output=True, text=True)
            
            if docker_process.stdout.strip():
                # Container exists and is listed in docker ps
                result["status"] = "ok"
                result["running"] = True
                result["message"] = f"Docker container: {docker_process.stdout.strip()}"
            else:
                # Check if container exists but is not running
                docker_all_cmd = f"docker ps -a --filter name={service_name} --format '{{{{.Status}}}}'"
                docker_all_process = subprocess.run(docker_all_cmd, shell=True, capture_output=True, text=True)
                
                if docker_all_process.stdout.strip():
                    result["status"] = "warning"
                    result["running"] = False
                    result["message"] = f"Docker container exists but is not running: {docker_all_process.stdout.strip()}"
                else:
                    # Try checking as a Kubernetes pod
                    k8s_cmd = f"kubectl get pods --all-namespaces | grep {service_name}"
                    k8s_process = subprocess.run(k8s_cmd, shell=True, capture_output=True, text=True)

                    
                    if k8s_process.stdout.strip():
                        # Extract pod status from kubectl output
                        # Format typically: NAMESPACE NAME READY STATUS RESTARTS AGE
                        pod_info = k8s_process.stdout.strip().split()
                        if len(pod_info) >= 4:  # Ensure we have enough columns
                            namespace = hostname
                            pod_status = pod_info[3]  # Status column
                            
                            if pod_status.lower() == "running":
                                result["status"] = "ok"
                                result["running"] = True
                                result["message"] = f"Kubernetes pod running in namespace {namespace}"
                            else:
                                result["status"] = "warning"
                                result["running"] = False
                                result["message"] = f"Kubernetes pod exists but status is: {pod_status}"
                        else:
                            result["status"] = "warning"
                            result["running"] = False
                            result["message"] = f"Kubernetes pod found but status unclear: {k8s_process.stdout.strip()}"
                    else:
                        result["status"] = "not found"
                        result["message"] = "Service not found in system services, Docker containers, or Kubernetes pods"

        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["message"] = f"Error checking service: {str(e)}"
    
    return result

def check_services(services: List[str] = None, for_agent: bool = False) -> str:
    """
    Check the status of multiple services
    
    Args:
        services: List of service names to check. If None, checks default services.
        for_agent: Whether this is being called by an agent
        
    Returns:
        String containing the service status results
    """
    # Use default services if none specified
    if services is None:
        services = DEFAULT_SERVICES
    
    # Check each service
    results = []
    for service in services:
        service_result = check_service_status(service)
        results.append(service_result)
    
    # Format output
    if for_agent:
        # Plain text format for agent consumption
        lines = []
        lines.append(f"Service Status Check Results ({len(results)} services):")
        
        for result in results:
            status_text = (
                "✅ RUNNING" if result["running"] else 
                "❌ STOPPED" if result["status"] == "ok" else
                "⚠️ WARNING" if result["status"] == "warning" else
                "❓ NOT FOUND" if result["status"] == "not found" else
                "❌ ERROR"
            )
            
            lines.append(f"{result['name']}: {status_text} - {result['message']}")
        
        return "\n".join(lines)
    else:
        # Rich text format with colors for human consumption
        lines = []
        lines.append(f"{BOLD}Service Status Check Results:{RESET}")
        
        for result in results:
            if result["running"]:
                status = f"{GREEN}{BOLD}✅ RUNNING{RESET}"
            elif result["status"] == "ok":
                status = f"{RED}{BOLD}❌ STOPPED{RESET}"
            elif result["status"] == "warning":
                status = f"{YELLOW}{BOLD}⚠️ WARNING{RESET}"
            elif result["status"] == "not found":
                status = f"{YELLOW}❓ NOT FOUND{RESET}"
            else:
                status = f"{RED}{BOLD}❌ ERROR{RESET}"
                
            lines.append(f"{BOLD}{result['name']}:{RESET} {status} - {result['message']}")
        
        return "\n".join(lines)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check health of system services')
    parser.add_argument('--services', nargs='*', help='Specific services to check')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    args = parser.parse_args()
    
    services_to_check = args.services if args.services else None
    
    if args.json:
        # JSON output
        services_results = []
        for service in (services_to_check or DEFAULT_SERVICES):
            services_results.append(check_service_status(service))
        print(json.dumps(services_results, indent=2))
    else:
        # Human-readable output
        print(check_services(services_to_check))