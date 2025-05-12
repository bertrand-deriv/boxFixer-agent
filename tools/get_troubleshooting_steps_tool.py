from config.services_config import TROUBLESHOOTING_STEPS_MAP

def get_service_troubleshooting_steps(service_name: str) -> dict:
    """
    Retrieves diagnostic steps and troubleshooting information for a failing service.
    
    Use this tool when you encounter issues with a specific service and need to diagnose the problem.
    The tool provides step-by-step diagnostic commands, common fixes, and additional troubleshooting tips.
    
    Args:
        service_name (str): The name of the failing service to troubleshoot (e.g., "kyc_services", "hydra_services")
        
    Returns:
        dict: A dictionary containing:
            - steps: List of diagnostic steps, each with a name and commands to execute
            - common_fixes: List of common solutions for this service
            - other_tips: Additional troubleshooting advice specific to this service
    """
    if service_name in TROUBLESHOOTING_STEPS_MAP:
        return TROUBLESHOOTING_STEPS_MAP[service_name]
    else:
        available_services = list(TROUBLESHOOTING_STEPS_MAP.keys())
        return {
            "steps": [{
                "name": f"Service '{service_name}' not found in troubleshooting database",
                "commands": [f"echo 'Available services: {', '.join(available_services)}'"]
            }],
            "common_fixes": ["Verify that the service name is correct"],
            "other_tips": []
        }