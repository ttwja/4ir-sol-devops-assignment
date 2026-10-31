
from typing import Sequence

import pulumi
from pulumi import ResourceOptions, ComponentResource, Output
from pulumi_kubernetes.apiextensions import CustomResource
from pulumi_kubernetes.apps.v1 import Deployment, DeploymentSpecArgs
from pulumi_kubernetes.core.v1 import (
    ContainerArgs,
    ContainerPortArgs,
    PodSpecArgs,
    PodTemplateSpecArgs,
    ResourceRequirementsArgs,
    Service,
    ServicePortArgs,
    ServiceSpecArgs,
    Secret
)
from pulumi_kubernetes.meta.v1 import LabelSelectorArgs, ObjectMetaArgs


class GuestbookWithSidecar(ComponentResource):
    deployment: Deployment
    service: Service
    ip_address: Output[str]

    def __init__(
        self,
        app_name: str,
        component_name: str,
        image: str = "pulumi/guestbook-php-redis",
        namespace: str = "default",
        resources: ResourceRequirementsArgs = None,
        replicas: int = None,
        ports: Sequence[int] = None,
        allocate_ip_address: bool = None,
        opts: ResourceOptions = None,
    ):
        super().__init__("k8sx:component:GuestbookWithSidecar", component_name, {}, opts)

        labels = {"app": app_name, "component": component_name}
        container = ContainerArgs(
            name=component_name,
            image=image,
            resources=resources
            or ResourceRequirementsArgs(
                requests={"cpu": "100m", "memory": "100Mi"},
            ),
            ports=([ContainerPortArgs(container_port=p) for p in ports] if ports else None),
        )

        sidecar_container = ContainerArgs(
            name="apache-exporter",
            image="solsson/prometheus-exporter-apache:latest",
            args=[
                "--scrape_uri=http://localhost/server-status?auto"
            ],
            ports=[
                ContainerPortArgs(container_port=9117, name="metrics")
            ],
            resources=ResourceRequirementsArgs(
                requests={"cpu": "50m", "memory": "50Mi"},
            ),
        )

        self.deployment = Deployment(
            component_name,
            metadata=ObjectMetaArgs(
                name=component_name,
                namespace=namespace,
                labels=labels,
            ),
            spec=DeploymentSpecArgs(
                selector=LabelSelectorArgs(match_labels=labels),
                replicas=replicas if replicas is not None else 1,
                template=PodTemplateSpecArgs(
                    metadata=ObjectMetaArgs(labels=labels),
                    spec=PodSpecArgs(containers=[container, sidecar_container]),
                ),
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )
        # create service
        self.service = Service(
            component_name,
            metadata=ObjectMetaArgs(
                name=component_name,
                namespace=namespace,
                labels=self.deployment.metadata.apply(lambda m: m.labels),
            ),
            spec=ServiceSpecArgs(
                ports=([ServicePortArgs(port=p, target_port=p) for p in ports] if ports else None),
                selector=self.deployment.spec.apply(lambda s: s.template.metadata.labels),
                type=(
                     "LoadBalancer" if allocate_ip_address else None
                ),
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )
        if allocate_ip_address:
            ingress = self.service.status.apply(lambda s: s.load_balancer.ingress[0])
            self.ip_address = ingress.apply(lambda i: i.ip or i.hostname or "")

        create_grafana_dashboard_secret(name=component_name, namespace=namespace, app_name=app_name)
        self.register_outputs({})


    def create_pod_monitor(self, name: str, app_labels: dict[str, str], namespace: str = "default", depends_on: list = None):
    #Define the Prometheus PodMonitor CRD
        pod_monitor = CustomResource(
            f"{name}-pod-monitor",
            api_version="monitoring.coreos.com/v1",
            kind="PodMonitor",
            metadata=ObjectMetaArgs(
                name=f"{name}-apache-exporter",
                namespace=namespace,
                labels={"release": "prometheus"},  # Adjust based on your Prometheus Operator selector labels
            ),
            spec={
                "selector": {
                    "matchLabels": app_labels
                },
                "podMetricsEndpoints": [
                    {
                        "port": "metrics",
                        "path": "/metrics",
                        "interval": "30s",
                    }
                ],
            },
            opts=ResourceOptions(depends_on=depends_on, parent=self) if depends_on else None
        )
        return pod_monitor

import json
def create_grafana_dashboard_secret(name: str, namespace: str = "default", app_name: str = "Guestbook"):
    # 3. Create a Grafana dashboard secret
    with open("basic_dashboard.json", "r") as f:
        dashboard_json = f.read()

    secret = Secret(
        f"{name}-grafana-dashboard-secret",
        api_version="v1",
        kind="Secret",
        metadata=ObjectMetaArgs(
            name=f"{name}-grafana-dashboard",
            namespace=namespace,
            labels={"grafana_dashboard": "1"},
        ),
        type="Opaque",
        string_data={
            f"{name}-dashboard.json": dashboard_json
        }
    )
    return secret
