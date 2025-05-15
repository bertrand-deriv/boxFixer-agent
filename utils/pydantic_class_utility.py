from pydantic import BaseModel, Field
from typing import List, Optional, Dict
class ServiceStatus(BaseModel):
    name: str = Field(description="Name of the service")
    status: str = Field(description="General status indicator, e.g., 'ok', 'not found', 'error'")
    running: bool = Field(description="Indicates whether the service is running")
    message: str = Field(description="Descriptive message about the service state")
    error: Optional[str] = Field(default=None, description="Error message if the service failed")

class ResourceStatus(BaseModel):
    cpu_usage: str = Field(description="CPU usage")
    memory_usage: str = Field(description="Memory usage")
    disk_usage: str = Field(description="Disk usage")

class ServicesOutput(BaseModel):
    kyc_services: Optional[List[ServiceStatus]] = Field(description="All services that has word 'kyc' in their name for example: kyc_receiver, kyc_identity_verification, onfido webhook service and 'service-business-rule'. Include any service related to document authentication. If there's none, return null")
    passkeys_services: Optional[List[ServiceStatus]] = Field(description="All services that has word 'passkeys' in their name. If there's none, return null")
    mt5_services: Optional[List[ServiceStatus]] = Field(description="All services that has 'mt5webapi' prefix in their name. If there's none, return null")
    hydra_services: Optional[List[ServiceStatus]] = Field(description="This includes All service that has word 'hydra' in their name as well as pgbouncer services. If there's none, return null")
    cli_http_service: Optional[List[ServiceStatus]] = Field(description="A service called 'cli_http_service'. If there's none, return null")
    crypto_services: Optional[List[ServiceStatus]] = Field(description="All services that has word 'crypto' in their name. If there's none, return null")
    other_services: List[ServiceStatus] = Field(description="Other miscellaneous services")

class MonitoringReport(BaseModel):
    services: ServicesOutput = Field(description="Categorized service statuses")
    resources: ResourceStatus = Field(description="Brief interpretation of system resource usage")
    summary: str = Field(description="Brief summary of system health.")
    recommendations: List[str] = Field(description="Recommended actions based on findings. You Should excplicity state whether to rebuild QAbox or not depending on how long services has been running and CPU and/or memory is at bottleneck")