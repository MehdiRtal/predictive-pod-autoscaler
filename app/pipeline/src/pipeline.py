import json
from pathlib import Path
from typing import Annotated

import pandas as pd
from hera.workflows import (
    Artifact,
    Parameter,
    S3Artifact,
)
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
from prometheus_api_client.utils import parse_datetime
from prophet import Prophet
from prophet.serialize import model_to_dict


def fetch_data(
    prometheus_url: Annotated[str, Parameter(name="prometheus_url")],
    target_ref_api_version: Annotated[str, Parameter(name="target_ref_api_version")],
    target_ref_kind: Annotated[str, Parameter(name="target_ref_kind")],
    target_ref_name: Annotated[str, Parameter(name="target_ref_name")],
    namespace: Annotated[str, Parameter(name="namespace")],
    query_type: Annotated[str, Parameter(name="query_type")],
    lookBackInterval: Annotated[str, Parameter(name="lookBackInterval")],
    windowInterval: Annotated[str, Parameter(name="windowInterval")],
    custom_query: Annotated[str, Parameter(name="custom_query")],
) -> Annotated[str, Artifact(name="data")]:
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()

    parts = target_ref_api_version.split("/")
    group = parts[0] if len(parts) > 1 else ""
    version = parts[1] if len(parts) > 1 else parts[0]

    plural = target_ref_kind.lower() + "s"
    if target_ref_kind.lower().endswith("y"):
        plural = target_ref_kind.lower()[:-1] + "ies"

    custom_api = client.CustomObjectsApi()
    scale = custom_api.get_namespaced_custom_object_scale(
        group=group,
        version=version,
        namespace=namespace,
        plural=plural,
        name=target_ref_name,
    )
    label_selector = scale["status"]["selector"]

    v1 = client.CoreV1Api()
    pod_list = v1.list_namespaced_pod(namespace, label_selector=label_selector)
    pod_names = [pod.metadata.name for pod in pod_list.items]

    pod_regex = "|".join(pod_names)

    if query_type == "cpu":
        query = "sum(rate(container_cpu_usage_seconds_total{{namespace='{}', pod=~'{}', container!=''}}[{window}]))".format(
            namespace, pod_regex, window=windowInterval
        )
    elif query_type == "memory":
        query = "sum(container_memory_working_set_bytes{{namespace='{}', pod=~'{}', container!=''}})".format(
            namespace, pod_regex
        )
    elif query_type == "network":
        query = "sum(rate(container_network_receive_bytes_total{{namespace='{}', pod=~'{}'}}[{window}]))".format(
            namespace, pod_regex, window=windowInterval
        )
    elif query_type == "filesystem":
        query = "sum(rate(container_fs_writes_bytes_total{{namespace='{}', pod=~'{}', container!=''}}[{window}]))".format(
            namespace, pod_regex, window=windowInterval
        )
    elif query_type == "requests":
        query = "sum(rate(http_requests_total{{namespace='{}', pod=~'{}'}}[{window}]))".format(
            namespace, pod_regex, window=windowInterval
        )
    elif query_type == "custom":
        if not custom_query:
            raise ValueError(
                "custom_query must be provided when query_type is 'custom'"
            )
        query = custom_query.replace("{{pod_regex}}", pod_regex).replace(
            "{{namespace}}", namespace
        )
    else:
        raise ValueError(f"Unknown query_type: {query_type}")

    prom = PrometheusConnect(url=prometheus_url)
    metrics = prom.get_metric_range_data(
        query,
        start_time=parse_datetime(lookBackInterval),
        end_time=parse_datetime("now"),
    )

    df = pd.DataFrame(metrics[0]["values"], columns=["ds", "y"]).assign(
        ds=lambda d: pd.to_datetime(d["ds"], unit="s"),
        y=lambda d: pd.to_numeric(d["y"]),
    )

    return df.to_csv(index=False)


def train_model(
    data: Annotated[Path, Artifact(name="data")],
) -> Annotated[
    str,
    S3Artifact(name="model"),
]:
    df = pd.read_csv(data)
    m = Prophet()
    m.fit(df)

    return json.dumps(model_to_dict(m))
