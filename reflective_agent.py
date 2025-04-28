import os
from typing import Annotated, Dict, List, Literal, TypedDict, Union
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatLiteLLM
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

# Define the agent state
class AgentState(TypedDict):
    messages: list
    current_plan: str
    reflection: str
    tool_history: List[str]
    problem_understanding: str
    status: Literal["planning", "executing", "reflecting", "finished", "awaiting_approval"]
    proposed_tool: str  # Store the proposed tool while waiting for approval

# DevOps Troubleshooting Tools
# [Same tool definitions as before]
@tool
def check_system_resources(query: str = "Check CPU, memory, and disk usage") -> str:
    """Check system resources like CPU, memory, and disk usage."""
    return """
    CPU: 78% utilized
      - Process 'java' using 45% CPU (PID: 1234)
      - Process 'node' using 23% CPU (PID: 2345)
    Memory: 5.2GB/8GB used (65%)
    Disk: 
      - /dev/sda1: 85% used (120GB/140GB)
      - /dev/sda2: 45% used (400GB/1TB)
    """

@tool
def analyze_logs(service_name: str) -> str:
    """Analyze logs for a specific service to identify errors or warnings."""
    logs = {
        "nginx": "2023-06-15 07:23:15 [error] 12345#0: *1234 connect() failed (111: Connection refused) while connecting to upstream",
        "docker": "2023-06-15 07:22:10 ERROR: failed to start container: Error response from daemon: OCI runtime create failed",
        "kubernetes": "2023-06-15 07:20:45 Failed to pull image 'myapp:latest': rpc error: code = Unknown desc = Error response from daemon",
        "mysql": "2023-06-15 07:18:30 [ERROR] [MY-012592] [InnoDB] Operating system error number 28 in a file operation.",
    }
    return logs.get(service_name.lower(), f"No logs found for service: {service_name}")

@tool
def check_network_connectivity(source: str, destination: str) -> str:
    """Check network connectivity between source and destination."""
    return f"""
    Connectivity test from {source} to {destination}:
    PING {destination} (10.0.0.5): 56 data bytes
    64 bytes from 10.0.0.5: icmp_seq=0 ttl=64 time=0.85 ms
    64 bytes from 10.0.0.5: icmp_seq=1 ttl=64 time=0.92 ms
    64 bytes from 10.0.0.5: icmp_seq=2 ttl=64 time=0.78 ms
    
    --- {destination} ping statistics ---
    3 packets transmitted, 3 packets received, 0% packet loss
    round-trip min/avg/max = 0.78/0.85/0.92 ms
    
    TCP port scan shows ports 22, 80, 443 are OPEN
    """

@tool
def check_container_status(container_id_or_name: str) -> str:
    """Check the status and details of a Docker container."""
    return f"""
    Container: {container_id_or_name}
    Status: Running
    Created: 2 days ago
    Ports: 0.0.0.0:8080->80/tcp
    Image: nginx:latest
    Networks: bridge
    CPU Usage: 2.5%
    Memory Usage: 256MB / 1GB
    Logs (last 5 lines):
      - 10.0.0.4 - - [15/Jun/2023:07:23:10 +0000] "GET /api/users HTTP/1.1" 200 1024
      - 10.0.0.5 - - [15/Jun/2023:07:23:12 +0000] "POST /api/login HTTP/1.1" 401 256
      - 10.0.0.4 - - [15/Jun/2023:07:23:14 +0000] "GET /api/status HTTP/1.1" 500 853
      - Error: Failed to connect to database at 10.0.0.10:5432
      - Attempting database reconnection (attempt 3 of 5)...
    """

@tool
def check_service_status(service_name: str) -> str:
    """Check the status of a system service."""
    services = {
        "nginx": "active (running)",
        "docker": "active (running)",
        "kubernetes": "active (running)",
        "mysql": "inactive (dead)",
        "mongodb": "active (running)",
        "redis": "active (running)",
    }
    status = services.get(service_name.lower(), "not found")
    return f"Service {service_name}: {status}"

@tool
def validate_configuration(config_path: str) -> str:
    """Validate configuration files for syntax or logical errors."""
    configs = {
        "/etc/nginx/nginx.conf": "Configuration is valid",
        "/etc/kubernetes/config": "Warning: deprecated API versions found in line 42",
        "/etc/docker/daemon.json": "Error: Invalid JSON at line 17 - missing comma",
        "/etc/mysql/my.cnf": "Configuration is valid",
    }
    return configs.get(config_path, f"Configuration file not found at {config_path}")

# Create the agent
def create_agent():
    # Initialize LLM

    llm = ChatOpenAI(model="gpt-4")
    
    # Define prompts
    # [Same planning_prompt and other prompts as before]
    planning_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are DevOpsTroubleshooter, an advanced DevOps troubleshooting agent.
        Given a problem description, create a detailed troubleshooting plan.
        Break down the steps you'll take to diagnose and potentially solve the issue.
        Think methodically about what information you need and which tools would be most helpful.
        
        Available tools:
        - check_system_resources: Check CPU, memory, and disk usage
        - analyze_logs: Look for errors in service logs
        - check_network_connectivity: Test connectivity between services
        - check_container_status: Examine container health and logs
        - check_service_status: Verify if services are running
        - validate_configuration: Check for config errors
        
        Provide your plan in numbered steps."""),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    execution_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are DevOpsTroubleshooter, an advanced DevOps troubleshooting agent.
        Execute your troubleshooting plan by using the appropriate tools.
        
        Available tools:
        - check_system_resources(): Check CPU, memory, and disk usage
        - analyze_logs(service_name): Look for errors in service logs
        - check_network_connectivity(source, destination): Test connectivity between services
        - check_container_status(container_id_or_name): Examine container health and logs
        - check_service_status(service_name): Verify if services are running
        - validate_configuration(config_path): Check for config errors
        
        To use a tool, respond with:
        ```tool
        tool_name(parameters)
        ```"""),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "Current plan: {current_plan}"),
        ("user", "Tool usage history: {tool_history}"),
        ("user", "What tool would you like to use next based on your plan?"),
    ])
    
    reflection_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are DevOpsTroubleshooter, an advanced DevOps troubleshooting agent.
        Reflect on the information gathered so far and analyze what it tells you about the problem.
        Consider:
        1. What have you learned about the issue?
        2. Do the results confirm your initial hypothesis or suggest a different cause?
        3. What additional information might you need?
        4. Should you adjust your troubleshooting approach?
        
        Be honest about what you know, don't know, and what is still uncertain."""),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "Initial problem understanding: {problem_understanding}"),
        ("user", "Current plan: {current_plan}"),
        ("user", "Tool usage history and results: {tool_history}"),
        ("user", "Please provide your reflection on the troubleshooting process so far."),
    ])
    
    final_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are DevOpsTroubleshooter, an advanced DevOps troubleshooting agent.
        Summarize your findings and provide a clear diagnosis of the problem.
        Then, recommend specific actions to resolve the issue.
        
        Your response should include:
        1. A summary of the problem diagnosis
        2. The root cause(s) identified
        3. Step-by-step resolution steps
        4. Preventive measures for the future
        
        Be precise and technical, but explain your reasoning clearly."""),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "Initial problem understanding: {problem_understanding}"),
        ("user", "Plan executed: {current_plan}"),
        ("user", "Tool usage and results: {tool_history}"),
        ("user", "Your reflection: {reflection}"),
        ("user", "Please provide your final diagnosis and recommended solution."),
    ])
    
    # Define state transitions
    def understand_problem(state):
        messages = state["messages"]
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            return {"messages": messages, 
                    "status": "planning", 
                    "current_plan": "", 
                    "reflection": "",
                    "tool_history": [],
                    "problem_understanding": last_message.content,
                    "proposed_tool": ""}
        return state
    
    def create_plan(state):
        messages = state["messages"]
        planning_chain = planning_prompt | llm
        response = planning_chain.invoke({"messages": messages})
        
        # Update state with the plan
        updated_messages = messages + [response]
        return {"messages": updated_messages, 
                "status": "executing", 
                "current_plan": response.content,
                "problem_understanding": state["problem_understanding"],
                "reflection": state["reflection"],
                "tool_history": state["tool_history"],
                "proposed_tool": ""}
    
    def propose_tool(state):
        execution_chain = execution_prompt | llm
        response = execution_chain.invoke({
            "messages": state["messages"],
            "current_plan": state["current_plan"],
            "tool_history": state["tool_history"]
        })
        
        updated_messages = state["messages"] + [response]
        tool_call = None
        
        # Parse the response for a tool call
        if "```tool" in response.content:
            tool_parts = response.content.split("```tool")[1].split("```")[0].strip()
            tool_call = tool_parts
        
        # If a tool was proposed
        if tool_call:
            return {
                "messages": updated_messages,
                "status": "awaiting_approval",
                "current_plan": state["current_plan"],
                "problem_understanding": state["problem_understanding"],
                "reflection": state["reflection"],
                "tool_history": state["tool_history"],
                "proposed_tool": tool_call
            }
        else:
            # No tool was proposed, move to reflection
            return {
                "messages": updated_messages,
                "status": "reflecting",
                "current_plan": state["current_plan"],
                "problem_understanding": state["problem_understanding"],
                "reflection": state["reflection"],
                "tool_history": state["tool_history"],
                "proposed_tool": ""
            }
    
    def process_approval(state):
        messages = state["messages"]
        last_message = messages[-1]
        
        if not isinstance(last_message, HumanMessage):
            # This shouldn't happen in normal operation
            return state
        
        tool_call = state["proposed_tool"]
        
        # Check if the user approved the tool execution
        if "approve" in last_message.content.lower() or "yes" in last_message.content.lower():
            # Execute the approved tool
            tool_name = tool_call.split("(")[0].strip()
            try:
                if tool_name == "check_system_resources":
                    result = check_system_resources()
                elif tool_name == "analyze_logs":
                    service = tool_call.split("(")[1].split(")")[0].replace('"', '').replace("'", "")
                    result = analyze_logs(service)
                elif tool_name == "check_network_connectivity":
                    params = tool_call.split("(")[1].split(")")[0]
                    source, destination = [p.strip().replace('"', '').replace("'", "") for p in params.split(",")]
                    result = check_network_connectivity(source, destination)
                elif tool_name == "check_container_status":
                    container = tool_call.split("(")[1].split(")")[0].replace('"', '').replace("'", "")
                    result = check_container_status(container)
                elif tool_name == "check_service_status":
                    service = tool_call.split("(")[1].split(")")[0].replace('"', '').replace("'", "")
                    result = check_service_status(service)
                elif tool_name == "validate_configuration":
                    config_path = tool_call.split("(")[1].split(")")[0].replace('"', '').replace("'", "")
                    result = validate_configuration(config_path)
                else:
                    result = f"Unknown tool: {tool_name}"
                    
                tool_history = state["tool_history"] + [f"Tool: {tool_call}\nResult: {result}"]
                updated_messages = messages + [HumanMessage(content=f"Tool result: {result}")]
                
                # Continue executing if tool count is below threshold, otherwise reflect
                if len(tool_history) < 5:
                    next_status = "executing"
                else:
                    next_status = "reflecting"
                    
            except Exception as e:
                tool_history = state["tool_history"] + [f"Tool: {tool_call}\nError: {str(e)}"]
                updated_messages = messages + [HumanMessage(content=f"Error executing tool: {str(e)}")]
                next_status = "reflecting"  # On error, move to reflection
        else:
            # User denied the tool execution
            tool_history = state["tool_history"] + [f"Tool: {tool_call}\nStatus: Execution denied by user"]
            updated_messages = messages + [HumanMessage(content=f"Tool execution denied: {tool_call}")]
            next_status = "executing"  # Continue with execution to propose a different tool
        
        return {
            "messages": updated_messages,
            "status": next_status,
            "current_plan": state["current_plan"],
            "problem_understanding": state["problem_understanding"],
            "reflection": state["reflection"],
            "tool_history": tool_history,
            "proposed_tool": ""
        }
    
    def reflect(state):
        reflection_chain = reflection_prompt | llm
        response = reflection_chain.invoke({
            "messages": state["messages"],
            "current_plan": state["current_plan"],
            "problem_understanding": state["problem_understanding"],
            "tool_history": state["tool_history"]
        })
        
        updated_messages = state["messages"] + [response]
        
        # Decide whether to continue executing or finish
        need_more_info = "need more information" in response.content.lower() or "should continue" in response.content.lower()
        status = "executing" if need_more_info and len(state["tool_history"]) < 10 else "finished"
        
        return {
            "messages": updated_messages,
            "status": status,
            "current_plan": state["current_plan"],
            "problem_understanding": state["problem_understanding"],
            "reflection": response.content,
            "tool_history": state["tool_history"],
            "proposed_tool": ""
        }
    
    def finish(state):
        final_chain = final_prompt | llm
        response = final_chain.invoke({
            "messages": state["messages"],
            "current_plan": state["current_plan"],
            "problem_understanding": state["problem_understanding"],
            "reflection": state["reflection"],
            "tool_history": state["tool_history"]
        })
        
        updated_messages = state["messages"] + [response]
        
        return {
            "messages": updated_messages,
            "status": "finished",
            "current_plan": state["current_plan"],
            "problem_understanding": state["problem_understanding"],
            "reflection": state["reflection"],
            "tool_history": state["tool_history"],
            "proposed_tool": ""
        }
    
    # Set up the workflow graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("understand_problem", understand_problem)
    workflow.add_node("create_plan", create_plan)
    workflow.add_node("propose_tool", propose_tool)
    workflow.add_node("process_approval", process_approval)
    workflow.add_node("reflect", reflect)
    workflow.add_node("finish", finish)
    
    # Add edges
    workflow.set_entry_point("understand_problem")
    workflow.add_edge("understand_problem", "create_plan")
    workflow.add_edge("create_plan", "propose_tool")
    
    # Conditional edges based on status
    workflow.add_conditional_edges(
        "propose_tool",
        lambda state: state["status"],
        {
            "awaiting_approval": "process_approval",
            "reflecting": "reflect",
        }
    )
    
    workflow.add_conditional_edges(
        "process_approval",
        lambda state: state["status"],
        {
            "executing": "propose_tool",
            "reflecting": "reflect",
        }
    )
    
    workflow.add_conditional_edges(
        "reflect",
        lambda state: state["status"],
        {
            "executing": "propose_tool",
            "finished": "finish",
        }
    )
    
    workflow.add_edge("finish", END)
    
    # Compile the graph
    return workflow.compile()

# Interactive function to run the agent
def run_interactive_agent():
    agent = create_agent()
    
    # Get user's initial problem description
    problem = input("Please describe the DevOps issue you're experiencing: ")
    
    # Initialize the state
    current_state = agent.invoke({
        "messages": [HumanMessage(content=problem)]
    })
    
    # Loop to handle interactions
    while current_state["status"] != "finished":
        # Display relevant messages
        for message in current_state["messages"][-2:]:  # Show only the latest exchange
            if isinstance(message, AIMessage):
                print(f"\nAgent: {message.content}\n")
            elif isinstance(message, HumanMessage):
                print(f"\nYou: {message.content}\n")
        
        # If waiting for approval
        if current_state["status"] == "awaiting_approval":
            tool = current_state["proposed_tool"]
            print(f"\n=== APPROVAL REQUIRED ===")
            print(f"Tool to execute: {tool}")
            approval = input("Do you approve this command? (yes/no): ")
            
            # Continue with user's response
            current_state = agent.invoke({
                **current_state,
                "messages": current_state["messages"] + [HumanMessage(content=approval)]
            })
        else:
            # For other states, just continue the execution
            current_state = agent.invoke(current_state)
    
    # Display the final output
    for message in current_state["messages"][-2:]:
        if isinstance(message, AIMessage):
            print(f"\nAgent: {message.content}\n")
        elif isinstance(message, HumanMessage):
            print(f"\nYou: {message.content}\n")

# Example usage
if __name__ == "__main__":
    run_interactive_agent()