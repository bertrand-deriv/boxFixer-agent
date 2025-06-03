#!/usr/bin/env python3

import os
import subprocess
import sys
import yaml

YAML_CRED_PATH = '/etc/rmg/qa_credentials.yml'  # Change path as needed
REQUIREMENTS_FILE = "requirements.txt"

def install_requirements():
    if os.path.exists(REQUIREMENTS_FILE):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE])
    else:
        print(f"[WARNING] No {REQUIREMENTS_FILE} found. Skipping dependency installation.")

def load_env_from_yaml(yaml_path):
    if not os.path.exists(yaml_path):
        print(f"[ERROR] YAML credentials file not found at: {yaml_path}")
        sys.exit(1)

    with open(yaml_path, 'r') as file:
        secrets = yaml.safe_load(file)

    if secrets:
        for k, v in secrets.items():
            if v is not None:
                os.environ[str(k)] = str(v)

def run_app():
    cmd = [sys.executable, "agent.py", "run-agent"]
    os.execvp(cmd[0], cmd)

def main():
    install_requirements()
    load_env_from_yaml(YAML_CRED_PATH)
    run_app()

if __name__ == "__main__":
    main()
