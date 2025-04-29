import os
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum
import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain_community.chat_models import ChatLiteLLM
from langgraph.graph import StateGraph, END

from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the state for our graph
class AgentState(BaseModel):
    problem: str = Field(description="The problem description from the user")
    plan: List[str] = Field(default_factory=list, description="Step-by-step troubleshooting plan")
    current_step_index: int = Field(default=0, description="Index of the current step in the plan")
    execution_results: List[Dict[str, str]] = Field(default_factory=list, description="Results of executed commands")
    analysis: List[str] = Field(default_factory=list, description="Analysis of executed steps")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested remediation actions")
    user_input: str = Field(default="", description="Latest input from the user")
    history: List[str] = Field(default_factory=list, description="History of previous troubleshooting sessions")
    current_state: str = Field(default="initial", description="Current state of the agent workflow")

llm = ChatLiteLLM(
    model_name="gpt-4.1-mini",
    api_base=os.getenv("API_BASE"),
    api_key=os.getenv("API_KEY")
)

# Define action nodes for our graph
def create_plan(state: AgentState) -> AgentState:
    """Generate a troubleshooting plan based on the problem description"""
    
    plan_prompt = ChatPromptTemplate.from_template(
        """You are a DevOps assistant agent trying to troubleshoot a server issue.
        
        Problem: {problem}
        
        Generate a detailed step-by-step troubleshooting plan. Focus on diagnostic commands 
        that would help identify the root cause. Include commands like checking service status,
        viewing logs, checking resource usage, etc.
        
        Return ONLY a numbered list of steps, with each step being a specific command or action.
        """
    )
    
    plan_chain = plan_prompt | llm | StrOutputParser()
    
    result = plan_chain.invoke({"problem": state.problem})
    
    # Convert the result into a list of steps
    steps = []
    for line in result.split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-")):
            # Remove numbering/bullets and clean up
            cleaned_step = line.split(".", 1)[-1].strip() if "." in line else line[1:].strip()
            steps.append(cleaned_step)
    
    # Update the state
    state.plan = steps
    state.current_state = "plan_created"
    return state

def present_plan(state: AgentState) -> AgentState:
    """Present the plan to the user and get feedback"""
    
    print("\n🧠 PROPOSED TROUBLESHOOTING PLAN")
    for i, step in enumerate(state.plan, 1):
        print(f"{i}. {step}")
    
    print("\n👀 PLAN FEEDBACK")
    print("Do you approve this plan? You can:")
    print("- Type 'yes' to approve the plan")
    print("- Type 'no' to reject and create a new plan")
    print("- Provide specific feedback to modify the plan")
    print("- Add additional commands you want included")
    
    user_input = input("> ")
    state.user_input = user_input
    state.current_state = "plan_feedback_received"
    
    return state

def process_plan_feedback(state: AgentState) -> AgentState:
    """Process user feedback on the plan"""
    
    user_input = state.user_input.lower()
    
    # Simple approval case
    if user_input in ["yes", "y", "approve", "ok"]:
        print("\n✅ Plan approved! Let's start executing the steps.")
        state.current_state = "plan_approved"
        return state
    
    # Rejection case
    if user_input in ["no", "n", "reject"]:
        print("\n🔄 Let's create a new plan. Please provide more details about what you're looking for:")
        new_details = input("> ")
        state.problem += f" Additional context: {new_details}"
        state.current_state = "plan_rejected"
        return state
    
    # Modification case - use LLM to interpret the feedback and modify the plan
    modification_prompt = ChatPromptTemplate.from_template(
        """You are a DevOps assistant agent.
        
        Original problem: {problem}
        Current plan: {current_plan}
        User feedback on the plan: {feedback}
        
        Based on the user's feedback, modify the troubleshooting plan.
        Return a complete, numbered list of steps that incorporates the user's feedback.
        Each step should be a specific command or action.
        """
    )
    
    modification_chain = modification_prompt | llm | StrOutputParser()
    
    modified_plan_text = modification_chain.invoke({
        "problem": state.problem,
        "current_plan": "\n".join(f"{i+1}. {step}" for i, step in enumerate(state.plan)),
        "feedback": state.user_input
    })
    
    # Parse the modified plan
    modified_steps = []
    for line in modified_plan_text.split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-")):
            # Remove numbering/bullets and clean up
            cleaned_step = line.split(".", 1)[-1].strip() if "." in line else line[1:].strip()
            modified_steps.append(cleaned_step)
    
    state.plan = modified_steps
    
    print("\n🔄 UPDATED PLAN")
    for i, step in enumerate(state.plan, 1):
        print(f"{i}. {step}")
    
    print("\nDo you approve this updated plan? [yes/no]")
    approval = input("> ")
    
    if approval.lower() in ["yes", "y", "approve", "ok"]:
        state.current_state = "plan_approved"
    else:
        state.current_state = "plan_rejected"
    
    return state

def prepare_next_step(state: AgentState) -> AgentState:
    """Prepare the next step for execution"""
    
    if state.current_step_index >= len(state.plan):
        state.current_state = "all_steps_completed"
        return state
    
    current_step = state.plan[state.current_step_index]
    
    print(f"\n⏭️ NEXT STEP ({state.current_step_index + 1}/{len(state.plan)})")
    print(f"Command: {current_step}")
    print("\nDo you want to execute this command? [yes/no/modify]")
    
    user_input = input("> ")
    state.user_input = user_input
    state.current_state = "step_decision_received"
    
    return state

def process_step_decision(state: AgentState) -> AgentState:
    """Process the user's decision about the next step"""
    
    user_input = state.user_input.lower()
    
    if user_input in ["yes", "y", "execute", "run"]:
        state.current_state = "execute_step"
        return state
    
    if user_input in ["no", "n", "skip"]:
        print(f"\n⏩ Skipping step {state.current_step_index + 1}")
        state.current_step_index += 1
        state.current_state = "prepare_next_step"
        return state
    
    if user_input.startswith("modify"):
        print("\nPlease enter the modified command:")
        modified_command = input("> ")
        state.plan[state.current_step_index] = modified_command
        print(f"\n✏️ Command modified to: {modified_command}")
        state.current_state = "execute_step"
        return state
    
    # Default fallback
    print("\n❓ I didn't understand that response. Please answer yes, no, or modify.")
    state.current_state = "prepare_next_step"
    return state

def execute_step(state: AgentState) -> AgentState:
    """Execute the current step of the plan"""
    
    current_step = state.plan[state.current_step_index]
    
    print(f"\n⚙️ EXECUTION (Step {state.current_step_index + 1}/{len(state.plan)})")
    print(f"Executing: {current_step}")
    
    # In a real implementation, this would execute actual system commands
    # Here we'll simulate command execution with an LLM
    execution_prompt = ChatPromptTemplate.from_template(
        """You are a DevOps assistant agent simulating the execution of a system command.
        
        Problem: {problem}
        Command to execute: {command}
        
        Generate a realistic output for this command as it would appear on a Linux system.
        The output should be relevant to the problem described.
        """
    )
    
    execution_chain = execution_prompt | llm | StrOutputParser()
    
    # Simulate command execution
    print("Executing command...")
    time.sleep(1)  # Simulate execution time
    
    output = execution_chain.invoke({
        "problem": state.problem,
        "command": current_step
    })
    
    print("\nOutput:")
    print(output)
    
    # Store the results
    state.execution_results.append({
        "step": current_step,
        "output": output
    })
    
    state.current_state = "analyze_results"
    return state

def analyze_results(state: AgentState) -> AgentState:
    """Analyze the results of the executed step"""
    
    latest_result = state.execution_results[-1]
    
    analysis_prompt = ChatPromptTemplate.from_template(
        """You are a DevOps assistant agent analyzing the results of a command execution.
        
        Problem: {problem}
        Command executed: {command}
        Command output: {output}
        
        Analyze the output and provide insights. What does this tell us about the problem?
        Is there evidence of the root cause? What have we learned from this step?
        
        Provide a concise analysis in 2-3 sentences.
        """
    )
    
    analysis_chain = analysis_prompt | llm | StrOutputParser()
    
    analysis = analysis_chain.invoke({
        "problem": state.problem,
        "command": latest_result["step"],
        "output": latest_result["output"]
    })
    
    print("\n📊 ANALYSIS")
    print(analysis)
    
    state.analysis.append(analysis)
    
    # Generate suggested next actions based on this result
    suggestion_prompt = ChatPromptTemplate.from_template(
        """You are a DevOps assistant agent suggesting next actions based on command results.
        
        Problem: {problem}
        Command executed: {command}
        Command output: {output}
        Analysis: {analysis}
        Remaining steps in plan: {remaining_steps}
        
        Based on this result, suggest 1-3 possible next actions. These could be:
        1. Continue with the next step in the plan
        2. A specific remediation action based on what you've found
        3. A different diagnostic command that would be more helpful now
        
        Format your response as a numbered list of specific actions.
        """
    )
    
    remaining_steps = state.plan[state.current_step_index + 1:] if state.current_step_index < len(state.plan) - 1 else []
    
    suggestion_chain = suggestion_prompt | llm | StrOutputParser()
    
    suggestions = suggestion_chain.invoke({
        "problem": state.problem,
        "command": latest_result["step"],
        "output": latest_result["output"],
        "analysis": analysis,
        "remaining_steps": "\n".join(remaining_steps)
    })
    
    print("\n🔄 SUGGESTED ACTIONS")
    print(suggestions)
    
    # Ask for user direction
    print("\nWhat would you like to do next?")
    print("- Type 'next' to continue with the next step in the plan")
    print("- Type 'remediate X' to take a specific remediation action")
    print("- Type a custom command to execute instead")
    print("- Type 'end' to finish troubleshooting")
    
    user_input = input("> ")
    state.user_input = user_input
    state.current_state = "post_execution_decision"
    
    return state

def process_post_execution_decision(state: AgentState) -> AgentState:
    """Process the user's decision after executing a step"""
    
    user_input = state.user_input.lower()
    
    if user_input in ["next", "continue"]:
        state.current_step_index += 1
        if state.current_step_index < len(state.plan):
            state.current_state = "prepare_next_step"
        else:
            state.current_state = "all_steps_completed"
        return state
    
    if user_input == "end":
        state.current_state = "end_session"
        return state
    
    if user_input.startswith("remediate"):
        # Extract the remediation action
        remediation = user_input[len("remediate"):].strip()
        
        print(f"\n🔧 REMEDIATION: {remediation}")
        print("Simulating remediation action...")
        time.sleep(1)  # Simulate action
        
        # Simulate the remediation result
        remediation_prompt = ChatPromptTemplate.from_template(
            """You are a DevOps assistant agent simulating a remediation action.
            
            Problem: {problem}
            Remediation action: {action}
            
            Generate a realistic output for this remediation action as it would appear on a Linux system.
            """
        )
        
        remediation_chain = remediation_prompt | llm | StrOutputParser()
        
        result = remediation_chain.invoke({
            "problem": state.problem,
            "action": remediation
        })
        
        print("\nResult:")
        print(result)
        
        # Ask what to do next
        print("\nWhat would you like to do next?")
        print("- Type 'next' to continue with the next step in the plan")
        print("- Type a custom command to execute")
        print("- Type 'end' to finish troubleshooting")
        
        next_step = input("> ")
        state.user_input = next_step
        # Stay in the same state to process the new input
        return state
    
    # If the input is a custom command, execute it
    print(f"\n🔧 CUSTOM COMMAND: {user_input}")
    print("Executing custom command...")
    
    execution_prompt = ChatPromptTemplate.from_template(
        """You are a DevOps assistant agent simulating the execution of a system command.
        
        Problem: {problem}
        Command to execute: {command}
        
        Generate a realistic output for this command as it would appear on a Linux system.
        """
    )
    
    execution_chain = execution_prompt | llm | StrOutputParser()
    
    output = execution_chain.invoke({
        "problem": state.problem,
        "command": user_input
    })
    
    print("\nOutput:")
    print(output)
    
    # Store the results
    state.execution_results.append({
        "step": user_input,
        "output": output
    })
    
    # Analyze this custom command
    state.current_state = "analyze_results"
    return state

def summarize_session(state: AgentState) -> AgentState:
    """Summarize the troubleshooting session"""
    
    if not state.execution_results:
        print("\n❗ No commands were executed during this session.")
        state.current_state = "end_session"
        return state
    
    summary_prompt = ChatPromptTemplate.from_template(
        """You are a DevOps assistant agent summarizing a troubleshooting session.
        
        Original problem: {problem}
        Commands executed and their outputs: {executed_commands}
        Analysis provided: {analysis}
        
        Provide a concise summary of:
        1. What we discovered about the problem
        2. What actions were taken
        3. What the current status is
        4. What further steps might be needed
        
        Format your response as a structured summary with clear sections.
        """
    )
    
    executed_commands = "\n\n".join([
        f"Command: {result['step']}\nOutput: {result['output']}" 
        for result in state.execution_results
    ])
    
    analysis_text = "\n".join(state.analysis)
    
    summary_chain = summary_prompt | llm | StrOutputParser()
    
    summary = summary_chain.invoke({
        "problem": state.problem,
        "executed_commands": executed_commands,
        "analysis": analysis_text
    })
    
    print("\n📋 SESSION SUMMARY")
    print(summary)
    
    state.current_state = "end_session"
    return state

def determine_next(state: AgentState) -> str:
    """Determine the next node in the workflow based on the current state"""
    
    current_state = state.current_state
    
    if current_state == "initial":
        return "create_plan"
    
    elif current_state == "plan_created":
        return "present_plan"
    
    elif current_state == "plan_feedback_received":
        return "process_plan_feedback"
    
    elif current_state == "plan_approved":
        return "prepare_next_step"
    
    elif current_state == "plan_rejected":
        return "create_plan"
    
    elif current_state == "step_decision_received":
        return "process_step_decision"
    
    elif current_state == "execute_step":
        return "execute_step"
    
    elif current_state == "analyze_results":
        return "analyze_results"
    
    elif current_state == "post_execution_decision":
        return "process_post_execution_decision"
    
    elif current_state == "all_steps_completed":
        return "summarize_session"
    
    elif current_state == "end_session":
        return END
    
    # Fallback to prevent hanging
    return END

# Create and run the graph
def create_agent_graph():
    # Define the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("create_plan", create_plan)
    workflow.add_node("present_plan", present_plan)
    workflow.add_node("process_plan_feedback", process_plan_feedback)
    workflow.add_node("prepare_next_step", prepare_next_step)
    workflow.add_node("process_step_decision", process_step_decision)
    workflow.add_node("execute_step", execute_step)
    workflow.add_node("analyze_results", analyze_results)
    workflow.add_node("process_post_execution_decision", process_post_execution_decision)
    workflow.add_node("summarize_session", summarize_session)
    
    # Add conditional edges using the determine_next function
    workflow.add_conditional_edges(
        "create_plan",
        determine_next,
    )
    workflow.add_conditional_edges(
        "present_plan",
        determine_next,
    )
    workflow.add_conditional_edges(
        "process_plan_feedback",
        determine_next,
    )
    workflow.add_conditional_edges(
        "prepare_next_step",
        determine_next,
    )
    workflow.add_conditional_edges(
        "process_step_decision",
        determine_next,
    )
    workflow.add_conditional_edges(
        "execute_step",
        determine_next,
    )
    workflow.add_conditional_edges(
        "analyze_results",
        determine_next,
    )
    workflow.add_conditional_edges(
        "process_post_execution_decision",
        determine_next,
    )
    workflow.add_conditional_edges(
        "summarize_session",
        determine_next,
    )
    
    # Set the entry point
    workflow.set_entry_point("create_plan")
    
    # Compile the graph
    return workflow.compile()

def main():
    # Create the agent graph
    agent = create_agent_graph()
    
    # Run the agent
    print("🤖 DevOps Assistant Agent")
    print("------------------------")
    print("What problem are you experiencing?")
    problem = input("> ")
    
    # Create initial state
    state = AgentState(problem=problem)

    # Run the graph
    agent.invoke(state)
    
    print("\n✅ Troubleshooting session complete.")

if __name__ == "__main__":
    main()