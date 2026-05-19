# Predictive Pod Autoscaler (PPA)

Predictive Pod Autoscaler (PPA) is an AI-driven horizontal pod autoscaling solution for Kubernetes. It leverages Facebook's **Prophet** for time-series forecasting to proactively scale your workloads based on historical CPU and memory usage patterns.

## Why PPA?

Standard Kubernetes HPA and KEDA scalers are reactive—they scale up when a threshold is breached. PPA is **proactive**—it anticipates traffic spikes and scales your application *before* the load hits, ensuring better performance and availability.

## Key Features

- 🧠 **Predictive Scaling**: Uses Prophet for accurate time-series forecasting.
- ⚡ **KEDA Integration**: Works as an External Scaler for KEDA, allowing you to use it alongside other KEDA scalers.
- 🔄 **Automated Training**: Hourly retraining of models using Argo Workflows ensures your scaling logic adapts to changing patterns.
- 🚀 **Cloud-Native Architecture**: Built on top of KServe, MLServer, and Argo Workflows.
- 🛠️ **Declarative Management**: Define your predictive scaling models using a simple Custom Resource (`Model`).

## How it Works

1. **Fetch**: PPA fetches historical metrics (CPU/Memory) from Prometheus.
2. **Train**: An Argo Workflow trains a Prophet model on the collected data.
3. **Serve**: The trained model is deployed as a KServe `InferenceService`.
4. **Scale**: The PPA Scaler queries the `InferenceService` and tells KEDA how many replicas are needed.
