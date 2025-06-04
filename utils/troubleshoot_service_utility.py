from rich import print
from dotenv import load_dotenv
from config.prompts_config import PromptManager
from utils.fetch_env_utility import load_env_from_yaml

load_env_from_yaml()

load_dotenv()

prompts = PromptManager()

def auto_troubleshoot_services_if_needed(structured_output, graph, config, display_typing_effect):
    """
    Check for failing services and automatically get troubleshooting guidance through the agent
    """
    # Step 1: Check for failing services across all service categories
    failing_services = []
    service_categories = ["kyc_services", "passkeys_services", "hydra_services", "mt5_services", "cli_http_service", "crypto_services"]
    
    for category in service_categories:
        services = getattr(structured_output.services, category, []) or []
        category_failing = [
            {"name": svc.name, "category": category.replace("_services", "").replace("_service", "")} 
            for svc in services 
            if not svc.running or svc.status.lower() in ["error", "not found"]
        ]
        failing_services.extend(category_failing)

    if not failing_services:
        print("\n[green]✅ All services are operational. No troubleshooting needed.[/green]")
        return

    # Step 2: Format a list of failing services for the agent
    failing_service_list = "\n".join([f"- {svc['name']} ({svc['category']})" for svc in failing_services])
    print(f"\n[yellow]⚠️ Found {len(failing_services)} failing services[/yellow]\n")
    print("[yellow]🤖 Let me find the troubleshooting steps for each...[/yellow]\n")

    troubleshoot_prompt = prompts.get_prompt("troubleshoot", failing_service_list=failing_service_list)
   
    # Step 3: Invoke the agent with the troubleshooting message
    response = graph.invoke({"messages": troubleshoot_prompt}, config)
    agent_response = response["messages"][-1].content
    
    # Step 4: Display the agent's response
    display_typing_effect(agent_response)