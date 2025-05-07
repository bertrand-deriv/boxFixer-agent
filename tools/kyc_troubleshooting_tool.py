#!/usr/bin/env python3
import os
import json
import subprocess
import re
from pathlib import Path
import sys

def troubleshoot_kyc(run_commands: bool = False):
    """Troubleshoot KYC service issues by checking configuration, services, and infrastructure."""
    results = []
    commands_to_execute = []
    
    # Step 1: Check if service-kyc tag exists in tags.json
    results.append("🔍 Step 1: Checking if service_kyc tag exists in tags.json...")
    tags_file = "/etc/chef/chef/tags/qa.json"
    
    if os.path.exists(tags_file):
        try:
            with open(tags_file, 'r') as f:
                tags_data = json.load(f)
                
            if 'service_kyc' in tags_data:
                results.append("✅ service_kyc tag found in tags.json")
            else:
                results.append("❌ service_kyc tag NOT found in tags.json")
                commands_to_execute.append(
                    "Add service_kyc tag to /etc/chef/chef/tags/qa.json and run chef-client"
                )
        except Exception as e:
            results.append(f"❌ Error reading tags.json: {str(e)}")
    else:
        results.append(f"❌ tags.json file not found at {tags_file}")
    
    # Step 2: Check if service folders exist
    results.append("\n🔍 Step 2: Checking if service folders exist...")
    k8s_dir = "/home/git/regentmarkets/environment-manifests-qa/k8s"
    required_services = ["service-business-rules", "service-kyc-rules"]
    
    missing_services = []
    for service in required_services:
        service_path = os.path.join(k8s_dir, service)
        if os.path.exists(service_path) and os.path.isdir(service_path):
            results.append(f"✅ {service} folder found")
        else:
            results.append(f"❌ {service} folder NOT found")
            missing_services.append(service)
    
    if missing_services:
        copy_commands = [
            f"mkdir -p {k8s_dir}/{service} && "
            f"rsync -avz qa61:{k8s_dir}/{service}/ {k8s_dir}/{service}/"
            for service in missing_services
        ]
        commands_to_execute.extend(copy_commands)
        commands_to_execute.append(
            "copy the related entry in internal-service values.yml from qa61 into your qabox; "
            "cd /home/git/regentmarkets/environment-manifest-qa && git add . && "
            "git commit -m 'Add missing service folders for KYC' && git push origin <current qabox>"
        )
    
    # Step 3: Check hosts file
    results.append("\n🔍 Step 3: Checking hosts file for k8s-lb-local.deriv.local entry...")
    try:
        with open('/etc/hosts', 'r') as f:
            hosts_content = f.read()
            
        if re.search(r'\b10\.14\.20\.218\s+k8s-lb-local\.deriv\.local\b', hosts_content):
            results.append("✅ k8s-lb-local.deriv.local found in /etc/hosts")
        else:
            results.append("❌ k8s-lb-local.deriv.local entry NOT found in /etc/hosts")
            commands_to_execute.append(
                "echo '10.14.20.218 k8s-lb-local.deriv.local' | sudo tee -a /etc/hosts"
            )
    except Exception as e:
        results.append(f"❌ Error checking hosts file: {str(e)}")
    
    # Step 4: Check if BSDB is running
    results.append("\n🔍 Step 4: Checking if BSDB needs to be restarted...")
    commands_to_execute.append(
        "cd /home/git/regentmarkets/bom-postgres-bsdb/kyc && make pgtap.port"
    )
    
    # Step 5: Check if pods are running
    results.append("\n🔍 Step 5: Checking if KYC pods are running...")
    try:
        kubectl_cmd = "kubectl get pods -n <qabox number e.g qa40> | grep -E 'service-kyc|business-rules'"
        kubectl_result = subprocess.run(kubectl_cmd, shell=True, capture_output=True, text=True)
        
        if kubectl_result.returncode == 0 and kubectl_result.stdout.strip():
            results.append("Pod status:")
            for line in kubectl_result.stdout.strip().split('\n'):
                results.append(f"  {line}")
                
            if "Running" in kubectl_result.stdout:
                results.append("✅ KYC pods appear to be running")
            else:
                results.append("❌ KYC pods might not be running correctly")
        else:
            results.append("❌ Failed to retrieve pod status or no KYC pods found")
    except Exception as e:
        results.append(f"❌ Error checking pod status: {str(e)}")
    
    # Final return — now returning a dictionary
    return {
        "log": "\n".join(results),
        "commands": commands_to_execute
    }

# Main block to make the script self-executable
if __name__ == "__main__":
    print(troubleshoot_kyc())
