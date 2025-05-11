from rich import print

def auto_troubleshoot_services_if_needed(structured_output, graph, config, display_typing_effect):
    """
    Check for failing services and automatically get troubleshooting guidance through the agent
    """
    
    # Step 1: Check for failing services across all service categories
    failing_services = []
    service_categories = ["kyc_services", "passkeys_services", "hydra_services", "general_services"]
    
    for category in service_categories:
        services = getattr(structured_output.services, category, []) or []
        category_failing = [
            {"name": svc.name, "category": category.replace("_services", "")} 
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
    
    # Step 3: Craft a human-like troubleshooting request for the agent
    troubleshoot_message = f"""
        I need your help with troubleshooting some failing services on our system. The following services are currently not running or showing errors:

        {failing_service_list}

        Please provide your response and all your future responses in well-formatted markdown:
        1. Use ## headings for service names
        2. Use numbered lists for steps
        3. Put commands in `code blocks`
        4. Use **bold** for important information
        5. Use > blockquotes for warnings or special notes
        6. Use ```bash for command examples (the syntax highlighting will make them stand out)

        For each failing service:
        1. Use the get_service_troubleshooting_steps_tool for each failing service to get diagnostic information.
        2. For services falling under same category, call the tool once.
        3. Provide me with a clear set of steps, custom fixes and commands needed to troubleshoot and fix each service.
        4. Finish by asking the user if you can go ahead and start executing one by one.
    """
    
    # Step 4: Invoke the agent with the troubleshooting message
    response = graph.invoke({"messages": troubleshoot_message}, config)
    agent_response = response["messages"][-1].content
    
    # Step 5: Display the agent's response
    display_typing_effect(agent_response)