# Usage Guide

Once PPA is installed, you can enable proactive scaling for your applications by defining a `Model` resource and configuring KEDA to utilize it.

## 1. Define a Predictive Model

The `Model` Custom Resource triggers the automated pipeline that fetches historical metrics and trains a Prophet model for your workload.

```yaml
apiVersion: ppa.io/v1alpha1
kind: Model
metadata:
  name: my-app-cpu-prediction
  namespace: my-apps
spec:
  prometheusUrl: "http://prometheus-operated.monitoring:9090"
  queryType: "cpu"
  horizon: "5m"
  retrainSchedule: "0 * * * *"
  targetRef:
    name: "my-app"
```

### Full Model Spec Reference

| Field | Type | Default | Required | Description |
|---|---|---|---|---|
| `spec.prometheusUrl` | `string` | — | ✅ | Full URL of the Prometheus instance containing container metrics |
| `spec.queryType` | `string` | — | ✅ | Metric to forecast: `cpu`, `memory`, `network`, `filesystem`, `requests`, or `custom` |
| `spec.customQuery` | `string` | `""` | ❌ | PromQL custom query (required if `queryType` is `custom`). Supported pod regex placeholders: `{{pod_regex}}`, `{{namespace}}` |
| `spec.horizon` | `string` | `"5m"` | ❌ | Forecast horizon (e.g., `5m`, `10m`, `1h`). Determines how far ahead to predict |
| `spec.lookBackInterval` | `string` | `"1y"` | ❌ | How far back to query Prometheus for training data (e.g., `1y`, `6m`, `30d`, `1h`) |
| `spec.windowInterval` | `string` | `"5m"` | ❌ | Prometheus rate query window (e.g., `5m`) |
| `spec.retrainSchedule` | `string` | `"0 * * * *"` | ❌ | Cron expression for the retraining schedule (defaults to hourly) |
| `spec.targetRef.apiVersion` | `string` | `"apps/v1"` | ❌ | API version of the target workload |
| `spec.targetRef.kind` | `string` | `"Deployment"` | ❌ | Kind of the target workload (`Deployment`, `StatefulSet`, `DaemonSet`) |
| `spec.targetRef.name` | `string` | — | ✅ | Name of the target Kubernetes workload |

### Query Types

| Query Type | Description | PromQL Used |
|---|---|---|
| `cpu` | CPU usage rate | `sum(rate(container_cpu_usage_seconds_total[...]))` |
| `memory` | Memory working set | `sum(container_memory_working_set_bytes)` |
| `network` | Network receive rate | `sum(rate(container_network_receive_bytes_total[...]))` |
| `filesystem` | Filesystem write rate | `sum(rate(container_fs_writes_bytes_total[...]))` |
| `requests` | HTTP request rate | `sum(rate(http_requests_total[...]))` |
| `custom` | Custom PromQL query | Use `spec.customQuery` with `{{pod_regex}}` and `{{namespace}}` placeholders |

### Automation Workflow

When you apply this resource, the following sequence occurs automatically:

1. **Orchestration**: Kro detects the new `Model`.
2. **Initial Training**: An Argo Workflow trains the baseline model using data from `lookBackInterval` with `windowInterval` granularity.
3. **Scheduled Training**: A `CronWorkflow` retrains the model on the `retrainSchedule` (default: hourly).
4. **Inference Service**: A KServe `InferenceService` is deployed to serve the latest model.

## 2. Configure KEDA ScaledObject

Link your workload to the PPA External Scaler by configuring KEDA to trigger based on the model's predictions.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-app-scaler
  namespace: my-apps
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: external-push
      metadata:
        scalerAddress: ppa-scaler.ppa:9090
        modelName: my-app-cpu-prediction
        horizon: "5"       # Minutes to look ahead
        targetValue: "0.8" # Target utilization (e.g., 80%)
```

### ScaledObject Trigger Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `scalerAddress` | `string` | ✅ | gRPC address of the PPA Scaler. Default: `ppa-scaler.ppa:9090` |
| `modelName` | `string` | ✅ | Must match `metadata.name` of the `Model` CRD in the same namespace |
| `horizon` | `integer` | ✅ | How many minutes into the future to forecast. Smaller = tighter; larger = more lead time |
| `targetValue` | `float` | ✅ | Target utilization ratio (e.g. `0.8` = 80%). Used to compute required replica count |

## 3. Monitoring

Verify the lifecycle of your predictive models through the command line:

```bash
# Check training workflow status
argo list -n my-apps

# Check model availability and inference URL
kubectl get models my-app-cpu-prediction -o yaml

# Check the KServe InferenceService
kubectl get inferenceservice -n my-apps

# Check the KEDA ScaledObject status
kubectl get scaledobject my-app-scaler -n my-apps
```

## 4. Multi-Metric Scaling

Create multiple `Model` resources and combine multiple triggers in a single `ScaledObject`. KEDA will use the highest predicted replica count across all triggers:

```yaml
triggers:
  - type: external-push
    metadata:
      scalerAddress: ppa-scaler.ppa:9090
      modelName: my-app-cpu-prediction
      horizon: "5"
      targetValue: "0.8"
  - type: external-push
    metadata:
      scalerAddress: ppa-scaler.ppa:9090
      modelName: my-app-memory-prediction
      horizon: "5"
      targetValue: "0.75"
```
