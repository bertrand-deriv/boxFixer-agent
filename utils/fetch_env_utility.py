import os
import sys
import yaml

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