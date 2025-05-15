import subprocess
hostname_process = subprocess.run("hostname", shell=True, capture_output=True, text=True)
hostname = hostname_process.stdout.strip().split('.')[0]
DEFAULT_SERVICES = [
    "crypto_cashier_paymentapi",
    "crypto_cashier_api",
    "binary_events_document_authentication_stream.service",
    "binary_starman_bom-backoffice.service",
    "binary_starman_paymentapi.service",
    "cli_http_service",
    "kyc_identity_verification",
    "kyc_phone_number_verification",
    "kyc_receiver",
    "kyc_identity_verification_scheduler",
    "kyc_transmitter",
    "service-kyc-rules",
    "service-business-rule",
    "passkeys",
    "deriv-redis-passkeys",
    "deriv-passkeys-gray",
    "hydra",
    "pgbouncer",
    "pgbouncer-chart",
    "pgbouncer-chart-gray",
    "mt5webapi_nginx",
    "mt5webapi_real_p03_ts01"
    "mt5webapi_real_p01_ts02",
    "mt5webapi_real_p01_ts04",
    "mt5webapi_demo_p01_ts01",
    "mt5webapi_demo_p01_ts02",
]
    
TROUBLESHOOTING_STEPS_MAP = {
    "kyc_services": {
        "steps": [
            {
                "name": "Check if service_kyc tag exists in tags.json, If not, then it needs to be added",
                "commands": [
                    "grep 'service_kyc' /etc/chef/chef/tags/qa.json",
                    "jq '.tags += [\"service_kyc\"]' /etc/chef/chef/tags/qa.json > temp.json && mv temp.json /etc/chef/chef/tags/qa.json"
                    ]
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
                "name": "Check hosts file for k8s-lb-local.deriv.local entry, if not then add it",
                "commands": [
                    "grep '10.14.20.218 k8s-lb-local.deriv.local' /etc/hosts",
                    "echo '10.14.20.218 k8s-lb-local.deriv.local' >> /etc/hosts"
                ]
            },
            {
                "name": "Restart BSDB",
                "commands": [
                    "sh -c \"cd /home/git/regentmarkets/bom-postgres-bsdb/kyc && make pgtap.port\""
                ]
            },
            {
                "name": "Check if KYC pods are running",
                "commands": [
                    f"kubectl get pods -n {hostname}"
                ]
            },

        ],
        "common_fixes": [
            "Sometimes you need to update image tag in the service-kyc-rules/values.yaml to the latest",
            "Add service_kyc tag to /etc/chef/chef/tags/qa.json and run chef-client",
            "Fix missing service folders (if needed) in /home/git/regentmarkets/environment-manifests-qa/k8s",
            "Add this entry in hosts: echo '10.14.20.218 k8s-lb-local.deriv.local' | sudo tee -a /etc/hosts",
            "Restart bsdb: cd /home/git/regentmarkets/bom-postgres-bsdb/kyc && make pgtap.port",

        ],
        "other_tips": [
            "KYC service requires  service-kyc-rules and business-rules service to be running",
            "Add this entry in hosts: echo '10.14.20.218 k8s-lb-local.deriv.local' in /etc/hosts",
            "Restart all services",
            "If all troubleshooting is not helping, You need to ask qa-kyc team"
        ]
    },
    "cli_http_services": {
        "steps": [
            {
                "name": "Check if the 'qa_script_runner' is in qa.json, and if not, you need to add it then run chef-client",
                "commands": [
                    "grep 'qa_script_runner' /etc/chef/chef/tags/qa.json",
                    "jq '.tags += [\"qa_script_runner\"]' /etc/chef/chef/tags/qa.json > temp.json && mv temp.json /etc/chef/chef/tags/qa.json"
                    ]
            }
        ],
        "common_fixes": [
            "Adding qa_script_runner and running chef client"
        ],
        "other_tips": []
    }
}