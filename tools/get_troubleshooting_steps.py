def get_service_troubleshooting_steps(service_name: str) -> dict:
    """
    Retrieves diagnostic steps and troubleshooting information for a failing service.
    
    Use this tool when you encounter issues with a specific service and need to diagnose the problem.
    The tool provides step-by-step diagnostic commands, common fixes, and additional troubleshooting tips.
    
    Args:
        service_name (str): The name of the failing service to troubleshoot (e.g., "kyc_services", "hydra_services")
        
    Returns:
        dict: A dictionary containing:
            - steps: List of diagnostic steps, each with a name and commands to execute
            - common_fixes: List of common solutions for this service
            - other_tips: Additional troubleshooting advice specific to this service
            
    Example:
        If a user reports KYC verification isn't working:
        
        kyc_info = get_service_troubleshooting_steps("kyc")
        
        # You can then execute the diagnostic steps and analyze results
        for step in kyc_info["steps"]:
            print(f"Performing: {step['name']}")
            for cmd in step["commands"]:
                # Execute each command and evaluate the result
                
        # Recommend fixes based on findings
        print("Recommended fixes:")
        for fix in kyc_info["common_fixes"]:
            print(f"- {fix}")
    """
    # Master troubleshooting map
    troubleshooting_map = {
        "kyc_services": {
            "steps": [
                {
                    "name": "Check if service-kyc tag exists in tags.json",
                    "commands": ["cat /etc/chef/chef/tags/qa.json | grep 'service_kyc'"]
                },
                {
                    "name": "Check if required KYC service folders exist",
                    "commands": [
                        "ls -la /home/git/regentmarkets/environment-manifests-qa/k8s/service-business-rules",
                        "ls -la /home/git/regentmarkets/environment-manifests-qa/k8s/service-kyc-rules"
                    ]
                },
                {
                    "name": "Fix missing service folders (if needed)",
                    "commands": [
                        "# If service-business-rules is missing, run:",
                        "mkdir -p /home/git/regentmarkets/environment-manifests-qa/k8s/service-business-rules",
                        "rsync -avz qa61:/home/git/regentmarkets/environment-manifests-qa/k8s/service-business-rules/ /home/git/regentmarkets/environment-manifests-qa/k8s/service-business-rules/",
                        
                        "# If service-kyc-rules is missing, run:",
                        "mkdir -p /home/git/regentmarkets/environment-manifests-qa/k8s/service-kyc-rules",
                        "rsync -avz qa61:/home/git/regentmarkets/environment-manifests-qa/k8s/service-kyc-rules/ /home/git/regentmarkets/environment-manifests-qa/k8s/service-kyc-rules/",
                        
                        "# Copy related entries in values.yml",
                        "scp qa61:/home/git/regentmarkets/environment-manifests-qa/values/internal-services.yaml /tmp/qa61-internal-services.yaml",
                        "echo 'Compare and copy relevant KYC entries from /tmp/qa61-internal-services.yaml to your internal-services.yaml'",
                        
                        "# Commit changes",
                        "cd /home/git/regentmarkets/environment-manifests-qa && git status",
                        "# Then add, commit and push changes if needed"
                    ]
                },
                {
                    "name": "Check hosts file for k8s-lb-local.deriv.local entry",
                    "commands": [
                        "grep '10.14.20.218 k8s-lb-local.deriv.local' /etc/hosts || echo 'No k8s-lb-local.deriv.local entry found in /etc/hosts'"
                    ]
                },
                {
                    "name": "Restart BSDB",
                    "commands": [
                        "cd /home/git/regentmarkets/bom-postgres-bsdb/kyc && make pgtap.port"
                    ]
                },
                {
                    "name": "Check if KYC pods are running",
                    "commands": [
                        "kubectl get pods -n <qabox e.g qa40>"
                    ]
                },

            ],
            "common_fixes": [
                "Add service_kyc tag to /etc/chef/chef/tags/qa.json and run chef-client",
                "Fix missing service folders (if needed)",
                "Add this entry in hosts: echo '10.14.20.218 k8s-lb-local.deriv.local' | sudo tee -a /etc/hosts",
                "Restard bsdb: cd /home/git/regentmarkets/bom-postgres-bsdb/kyc && make pgtap.port"
            ],
            "other_tips": [
                "KYC service requires  service-kyc-rules and business-rules service to be running",
                "Add this entry in hosts: echo '10.14.20.218 k8s-lb-local.deriv.local' in /etc/hosts",
                "Restart all services"
            ]
        },
        
        "payment": {
            "steps": [
                {
                    "name": "Check if service_payment tag exists",
                    "commands": ["cat /etc/chef/chef/tags/qa.json | grep service_payment"]
                },
                {
                    "name": "Verify payment service pods are running",
                    "commands": ["kubectl get pods | grep payment-service"]
                },
                {
                    "name": "Check payment database connection",
                    "commands": [
                        "kubectl exec -it $(kubectl get pod -l app=payment-service -o jsonpath='{.items[0].metadata.name}') -- env | grep DATABASE",
                        "kubectl exec -it $(kubectl get pod -l app=payment-service -o jsonpath='{.items[0].metadata.name}') -- curl -s database-host:port"
                    ]
                },
                {
                    "name": "Check payment processor connectivity",
                    "commands": [
                        "kubectl exec -it $(kubectl get pod -l app=payment-service -o jsonpath='{.items[0].metadata.name}') -- curl -s payment-gateway-url/status"
                    ]
                }
            ],
            "common_fixes": [
                "Add service_payment tag to /etc/chef/chef/tags/qa.json and run chef-client",
                "Restart payment service: kubectl rollout restart deployment payment-service",
                "Verify payment database credentials in secrets"
            ],
            "other_tips": [
                "Payment service requires functioning network connection to payment processor",
                "Check firewall rules for outbound connections to payment gateway",
                "Verify SSL certificates for payment gateway are valid"
            ]
        }
    }
    
    # Return troubleshooting info or not found message
    if service_name in troubleshooting_map:
        return troubleshooting_map[service_name]
    else:
        available_services = list(troubleshooting_map.keys())
        return {
            "steps": [{
                "name": f"Service '{service_name}' not found in troubleshooting database",
                "commands": [f"echo 'Available services: {', '.join(available_services)}'"]
            }],
            "common_fixes": ["Verify that the service name is correct"],
            "other_tips": [f"Available services: {', '.join(available_services)}"]
        }