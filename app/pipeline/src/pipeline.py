import json

import pandas as pd
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
from prometheus_api_client.utils import parse_datetime
from prophet import Prophet
from prophet.serialize import model_to_dict


def fetch_data(
    prometheus_url: str,
    workload_type: str,
    workload_name: str,
    workload_namespace: str,
    query_type: str,
):
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()

    workload_type = workload_type.lower()

    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    if workload_type == "deployment":
        dep = apps_v1.read_namespaced_deployment(workload_name, workload_namespace)
        selector = dep.spec.selector.match_labels
    elif workload_type == "statefulset":
        sts = apps_v1.read_namespaced_stateful_set(workload_name, workload_namespace)
        selector = sts.spec.selector.match_labels
    elif workload_type == "replicaset":
        rs = apps_v1.read_namespaced_replica_set(workload_name, workload_namespace)
        selector = rs.spec.selector.match_labels
    elif workload_type == "daemonset":
        ds = apps_v1.read_namespaced_daemon_set(workload_name, workload_namespace)
        selector = ds.spec.selector.match_labels

    label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])
    pod_list = v1.list_namespaced_pod(workload_namespace, label_selector=label_selector)
    pod_names = [pod.metadata.name for pod in pod_list.items]

    pod_regex = "|".join(pod_names)

    prom = PrometheusConnect(url=prometheus_url)
    start_time = parse_datetime("1h")
    end_time = parse_datetime("now")

    cpu_q = (
        "sum(rate(container_cpu_usage_seconds_total{{pod=~'{}', container!=''}}[5m]))"
    )
    mem_q = "sum(container_memory_usage_bytes{{pod=~'{}', container!=''}})"
    query = cpu_q if query_type == "cpu" else mem_q

    metrics = prom.get_metric_range_data(
        query.format(pod_regex),
        start_time=start_time,
        end_time=end_time,
    )

    df = pd.DataFrame(metrics[0]["values"], columns=["ds", "y"]).assign(
        ds=lambda d: pd.to_datetime(d["ds"], unit="s"),
        y=lambda d: pd.to_numeric(d["y"]),
    )

    df.to_csv("/tmp/data.csv", index=False)


def train_model():
    df = pd.read_csv("/tmp/data.csv")
    m = Prophet()
    m.fit(df)

    with open("/tmp/model.json", "w") as f:
        json.dump(model_to_dict(m), f)
