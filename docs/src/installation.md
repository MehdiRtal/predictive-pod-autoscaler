# Installation

This guide covers how to deploy the Predictive Pod Autoscaler (PPA) using the Helm chart from our OCI registry.

## 1. Configure Storage
PPA requires S3-compatible storage for model artifacts. Create a `values.yaml` file with your storage credentials:

```yaml
s3:
  endpoint: s3.your-domain.com
  bucket: ppa-models
  accessKey: YOUR_ACCESS_KEY
  secretKey: YOUR_SECRET_KEY
  insecure: false
```

## 2. Deploy PPA
Install PPA in your cluster using the OCI Helm chart:

```bash
kubectl create namespace ppa
helm install ppa oci://ghcr.io/mehdirtal/predictive-pod-autoscaler/ppa --version 0.1.9 -n ppa -f values.yaml
```

??? note "Quick Install (Optional Dependencies)"
    If you don't have the prerequisites installed, the PPA chart can install them for you:
    ```bash
    helm install ppa oci://ghcr.io/mehdirtal/predictive-pod-autoscaler/ppa --version 0.1.9 \
      --set keda.enabled=true \
      --set argo-workflows.enabled=true \
      --set seaweedfs.enabled=true
    ```

## 3. Verify Deployment
Confirm that the components are running:

```bash
kubectl get pods -l app.kubernetes.io/name=ppa-scaler -n ppa
kubectl get resourcegraphdefinitions
```

---

## Lifecycle Management

### Upgrading
To upgrade to a newer version:
```bash
helm upgrade ppa oci://ghcr.io/mehdirtal/predictive-pod-autoscaler/ppa --version 0.1.9 -n ppa -f values.yaml
```

### Uninstallation
To remove PPA from your cluster:
```bash
helm uninstall ppa -n ppa
```
