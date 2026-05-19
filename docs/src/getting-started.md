# Getting Started

Predictive Pod Autoscaler (PPA) is an AI-driven horizontal pod autoscaling solution for Kubernetes that proactively scales workloads based on historical usage.

## Prerequisites

Before deploying PPA, ensure your cluster meets the following requirements:

- **Kubernetes**: v1.25 or newer
- **Helm**: v3.x
- **KEDA**: Enabled for horizontal pod autoscaling
- **Argo Workflows**: Required for model training orchestration
- **KServe**: Required for serving predictive models
- **Kro**: Required to manage the `Model` Custom Resource
- **Prometheus**: Source for historical metrics
- **S3-Compatible Storage**: (e.g., SeaweedFS, Minio) for storing model artifacts

---

## Next Steps

Follow the guides below to get PPA up and running:

*   [**Installation Guide**](installation.md)
*   [**Usage Guide**](usage.md)
