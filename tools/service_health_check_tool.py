#!/usr/bin/env python3
import subprocess
import json
import re
from typing import List, Dict, Any, Optional
from config.services_config import DEFAULT_SERVICES

# Get the hostname for kubernetes
hostname_process = subprocess.run("hostname", shell=True, capture_output=True, text=True)
namespace = hostname_process.stdout.strip().split('.')[0]

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
                    # Check if the pod exists in the given namespace
                    k8s_cmd = f"kubectl get pods -n {namespace} | grep {service_name}"
                    k8s_process = subprocess.run(k8s_cmd, shell=True, capture_output=True, text=True)

                    
                    if k8s_process.stdout.strip():
                        # Extract pod status from kubectl output
                        # Format typically: NAME READY STATUS RESTARTS AGE
                        pod_info = k8s_process.stdout.strip().split()
                        if len(pod_info) >= 4:
                            
                            pod_status = pod_info[2]
                            pod_restarts = pod_info[3]
                            pod_age = pod_info[4]
                            
                            if pod_status.lower() == "running":
                                result["status"] = "ok"
                                result["running"] = True
                                result["message"] = f"Kubernetes pod running in namespace {namespace}.It's been up for {pod_age}. Number of restarts: {pod_restarts}"
                            else:
                                result["status"] = "warning"
                                result["running"] = False
                                result["message"] = f"Kubernetes pod exists in namespace {namespace} but status is: {pod_status}.It's been up for {pod_age}. Number of restarts: {pod_restarts}"
                        else:
                            result["status"] = "warning"
                            result["running"] = False
                            result["message"] = f"Kubernetes pod found in namespace {namespace} but status unclear: {pod_status}. It's been up for {pod_age}. Number of restarts: {pod_restarts}"
                    else:
                        result["status"] = "not found"
                        result["message"] = f"Service not found in system services, Docker containers, or Kubernetes pods"

        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["message"] = f"Error checking service: {str(e)}"
    
    return result

def check_services(services: Optional[List[str]] = None) -> List[dict]:
    """
    Check the status of multiple services.

    Args:
        services: List of service names to check. If None, uses default list.

    Returns:
        List of service status dictionaries (JSON-serializable).
    """
    if services is None:
        services = DEFAULT_SERVICES

    return [check_service_status(service) for service in services]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Check health of system services')
    parser.add_argument('--services', nargs='*', help='Specific services to check')
    args = parser.parse_args()

    services_to_check = args.services if args.services else None
    results = check_services(services_to_check)

    print(json.dumps(results, indent=2))