# BoxFixer Agent

BoxFixer Agent is a DevOps assistant designed to monitor logs, check service health, gather system resource metrics, and provide troubleshooting guidance for services running in the QABOX (test environment). It leverages a lightweight LLM (via LangGraph/LangChain) to automate diagnostic workflows and present structured reports. It also integrates with LangSmith for agent activity monitoring.

## Features

- Comphrensive initial qabox diagnosis
- Health checks for multiple services
- CPU, memory, and disk usage reporting
- Service troubleshooting 
- Interactive CLI powered by [Typer](https://typer.tiangolo.com/)  
- Extensible toolset architecture

## Prerequisites

- Python 3.9+  
- Docker CLI (for docker-related checks)  
- A QABOX test environment with accessible services 

## How to use the app:

1. Clone the repo and go to its directory
2. Install required packages. `pip install -r requirements.txt`
3. Make sure you have all the env variables in `.env` file. You just need 2 secrets as mentioned below
4. Run `python3 agent.py run-agent`

## How to contribute:

> You need to do this while connected to a qabox. Same as using this agent.

1. Clone the Repo and change directory to boxFixer-agent

    ```
    cd boxFixer-agent
    ```
2. Create a feature branch:

   ```bash
   git checkout -b username/your-feature
   ```
3. Run the interactive agent session:

    ```bash
    python3 agent.py run-agent
    ```
Available commands:
- `run-agent` : Starts the interactive LLM-driven diagnostic session.  
- `check-services-cmd` : Performs a one-off health check of configured services.  
- `get-tb-steps SERVICE_NAME` : Prints troubleshooting steps for a specific service, e.g.:  
  ```bash
  python3 agent.py get-tb-steps kyc_services
  ```
- `check-sys-resources`  
  Reports current CPU, memory, and disk usage.

**Credentials are set in QABOX by default (in `/etc/rmg/qa_credentials.yml`). Incase you want to modify these secrets, especially the BOX_API_KEY that expires,  you can test and exercise with it using `.env` file. Then later ask the DevOps team via `#need_help_qabox_issues` to update the secret.
Here's the list off all secrets required.**

   ```text
   BOX_API_KEY=<your-openai-key>
   LANGSMITH_API_KEY=<langsmith-api-key>
   ```

## Configuration

- **config/prompts_config.py** — Manages system, initial, and human prompt templates.  
- **config/services_config.py** — Defines services to monitor and troubleshooting steps for available services.

## Directory Structure

```
boxFixer-agent/
├── agent.py                 # Main Typer CLI entrypoint
├── requirements.txt         # Python dependencies
├── .gitignore
├── .env                     # Environment variables
├── config/
│   ├── prompts_config.py    # Prompt templates
│   └── services_config.py   # Service definitions and troubleshooting  steps
├── tools/
│   ├── command_executor_tool.py
│   ├── get_troubleshooting_steps_tool.py
│   ├── log_monitor_tool.py
│   ├── resource_monitoring_tool.py
│   └── service_health_check_tool.py
├── utils/
│   ├── display_utility.py
|   |── fetch_env_utility.py
│   ├── pydantic_class_utility.py
│   └── troubleshoot_service_utility.py
└── README.md                
```

## Upcomming Features

- Intelligently monitoring logs(errors, warning, PII leaked) and giving insights from them
- Adding steps to troubleshoot other service features (e.g hydra, passkeys, pnv)
- Integrate with wikijs