import pulumi

# Import from the new component module:
from service_deployment import ServiceDeployment
from p8s_operator import PrometheusOperatorHelmChart
from guestbook_with_sidecar import GuestbookWithSidecar

# Read the configuration value:
config = pulumi.Config()
# isMinikube = config.get_bool("isMinikube")

ServiceDeployment("Guestbook", "redis-leader", image="redis", ports=[6379])
ServiceDeployment("Guestbook", "redis-replica", image="pulumi/guestbook-redis-replica", ports=[6379])
frontend = GuestbookWithSidecar(
    "Guestbook",
    "frontend",
    replicas=1,
    ports=[80],
    allocate_ip_address=True,
)

# p8s operator
p8s_chart = PrometheusOperatorHelmChart("prometheus-operator", allocate_ip_address=True)
p8s_chart.display_secret()

labels = {"app": "Guestbook", "component": "frontend"}
frontend.create_pod_monitor("frontend", labels, namespace="default", depends_on=[p8s_chart.chart])

# install Grafana dashboard secret


# prometheus_operator.prometheus_operator.apply(lambda p: print(p))
pulumi.export("frontend_ip", frontend.ip_address)
pulumi.export("grafana_ip", p8s_chart.grafana_ip)
pulumi.export("grafana_password", p8s_chart.grafana_password)

