#!/usr/bin/env python3

import os
import subprocess
import sys
import yaml

YAML_CRED_PATH = '/etc/rmg/qa_credentials.yml'
REQUIREMENTS_FILE = "requirements.txt"

def install_requirements():
    if os.path.exists(REQUIREMENTS_FILE):
        print("[INFO] Installing Python requirements (no output unless there is an error)...")
        try:
            # Capture stdout and stderr
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE, "--quiet"],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            print("[ERROR] Requirements installation failed!")
            print("stdout:\n", e.stdout)
            print("stderr:\n", e.stderr)
            sys.exit(e.returncode)
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
