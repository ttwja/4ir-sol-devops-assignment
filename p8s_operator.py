import pulumi
import pulumi_kubernetes as k8s


class PrometheusOperatorHelmChart(pulumi.ComponentResource):
    def __init__(self, name: str, allocate_ip_address=True, opts = None):
        super().__init__('quickstart:index:PrometheusOperatorHelmChart', name, {}, opts)

# 1. Create a dedicated namespace for monitoring
        monitoring_namespace = k8s.core.v1.Namespace("monitoring",
            metadata={
                "name": "monitoring"
            }
        )
# 2. Deploy the kube-prometheus-stack Helm chart (includes Prometheus Operator and CRDs)
        stack_name= "kube-prometheus-stack"
        namespace = monitoring_namespace.metadata["name"]
        prometheus_operator = k8s.helm.v3.Chart("kube-prometheus-stack",
            config=k8s.helm.v3.ChartOpts(
                chart=stack_name,
                version="92.14.1", # Adjust to your desired chart version
                fetch_opts=k8s.helm.v3.FetchOpts(
                    repo="https://prometheus-community.github.io/helm-charts"
                ),
                namespace=namespace,
                values={
                    "prometheus": {
                        "prometheusSpec": {
                            # Automatically discover ServiceMonitors with matching labels (or match all)
                            "serviceMonitorSelectorNilUsesHelmValues": False,
                            "podMonitorSelectorNilUsesHelmValues": False,
                        }
                    },
                    "grafana": {
                        "service": {
                            "type": "LoadBalancer" if allocate_ip_address else "ClusterIP",
                            "port": 3000
                        },
                    }
                }
            ),
            opts=pulumi.ResourceOptions(depends_on=[monitoring_namespace], parent=self)
        )

        self.grafana_ip = prometheus_operator.get_resource("v1/Service", f"{stack_name}-grafana", namespace) \
            .apply(lambda s: s.status.load_balancer.ingress[0].ip if s.status.load_balancer.ingress else None)

        self.grafana_ip  = pulumi.Output.concat(self.grafana_ip, ":3000")
        self.chart = prometheus_operator
        self.register_outputs({ 'prometheus_operator': prometheus_operator })

    def display_secret(self):
        secret = self.chart.get_resource("v1/Secret", "kube-prometheus-stack-grafana", "monitoring")
        self.grafana_password = secret.data.apply(lambda data: pulumi.Output.secret(decode_password(data)))
        


import base64

def decode_password(data):
    if not data or "admin-password" not in data:
        return ""
    decoded_bytes = base64.b64decode(data["admin-password"])
    return decoded_bytes.decode("utf-8")