import os
import subprocess
import sys
import yaml

def install_requirements():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    req_path = os.path.join(project_root, "requirements.txt")

    if os.path.exists(req_path):
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", req_path , "--quiet"]
        )
    else:
        print("CWD:", os.getcwd())
        print(f"[WARNING] No 'requirements.txt' found at {req_path}. Skipping dependency installation.")

def load_env_from_yaml():
    if not os.path.exists('/etc/rmg/qa_credentials.yml'):
        print(f"[ERROR] YAML credentials file not found at: '/etc/rmg/qa_credentials.yml'")
        sys.exit(1)

    with open('/etc/rmg/qa_credentials.yml', 'r') as file:
        secrets = yaml.safe_load(file)

    if secrets:
        for k, v in secrets.items():
            if v is not None:
                os.environ[str(k)] = str(v)