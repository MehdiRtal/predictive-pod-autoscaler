import asyncio
import logging
import os
import signal

import grpc
from kserve import InferenceGRPCClient, InferInput, InferRequest
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient

import src.externalscaler_pb2 as pb
import src.externalscaler_pb2_grpc as pb_grpc

PORT = os.getenv("PORT", 9090)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

try:
    config.load_incluster_config()
except config.ConfigException:
    asyncio.run(config.load_kube_config())


class PredictiveExternalScaler(pb_grpc.ExternalScalerServicer):
    async def IsActive(self, request, context):
        """Return True if we should activate scaling (avoid scale-to-0 if prediction > 0)"""
        try:
            predicted_value = await self._get_predicted_value(
                model_name=request.scalerMetadata["modelName"],
                model_namespace=request.namespace,
                horizon=int(request.scalerMetadata["horizon"]),
            )
            return pb.IsActiveResponse(result=predicted_value > 0)
        except Exception:
            return pb.IsActiveResponse(result=True)

    async def GetMetricSpec(self, request, context):
        """Tell KEDA what metric we provide and the target value"""
        return pb.GetMetricSpecResponse(
            metricSpecs=[
                pb.MetricSpec(
                    metricName=request.scalerMetadata["modelName"],
                    targetSizeFloat=float(request.scalerMetadata["targetValue"]),
                )
            ]
        )

    async def GetMetrics(self, request, context):
        """The core method: call KServe and return predicted replicas"""
        try:
            predicted_value = await self._get_predicted_value(
                model_name=request.scaledObjectRef.scalerMetadata["modelName"],
                model_namespace=request.scaledObjectRef.namespace,
                horizon=int(request.scaledObjectRef.scalerMetadata["horizon"]),
            )
            return pb.GetMetricsResponse(
                metricValues=[
                    pb.MetricValue(
                        metricName=request.scaledObjectRef.scalerMetadata["modelName"],
                        metricValueFloat=predicted_value,
                    )
                ]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get prediction: {str(e)}")
            return pb.GetMetricsResponse(
                metricValues=[
                    pb.MetricValue(
                        metricName=request.scaledObjectRef.scalerMetadata["modelName"],
                        metricValueFloat=1.0,
                    )
                ]
            )

    async def _get_predicted_value(
        self, model_name: str, model_namespace: str, horizon: int
    ):
        """Query Model CRD and call KServe model using URL from status.url"""
        async with ApiClient() as api_client:
            custom_client = client.CustomObjectsApi(api_client)
            model_crd = await custom_client.get_namespaced_custom_object(
                group="ppa.io",
                version="v1alpha1",
                plural="models",
                name=model_name,
                namespace=model_namespace,
            )

        is_ready = any(
            c["type"] == "Ready" and c["status"] == "True"
            for c in model_crd.get("status", {}).get("conditions", [])
        )
        if not is_ready:
            raise RuntimeError(f"Model {model_name} is not ready")

        model_url = model_crd["status"].get("url", "")
        use_ssl = model_url.startswith("https://")
        model_endpoint = model_url.replace("https://", "").replace("http://", "")

        async with InferenceGRPCClient(
            url=model_endpoint,
            use_ssl=use_ssl,
        ) as grpc_client:
            result = await grpc_client.infer(
                InferRequest(
                    model_name=model_name,
                    infer_inputs=[
                        InferInput(
                            name="horizon",
                            shape=[1],
                            datatype="INT32",
                            data=[horizon],
                        )
                    ],
                )
            )
        return result.outputs[0].data[0]


async def serve():
    server = grpc.aio.server()
    pb_grpc.add_ExternalScalerServicer_to_server(PredictiveExternalScaler(), server)
    listen_addr = f"[::]:{PORT}"
    server.add_insecure_port(listen_addr)

    logging.info(f"Starting server on {listen_addr}")
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        logging.info("Starting graceful shutdown...")
        await server.stop(grace=5)


async def main():
    loop = asyncio.get_running_loop()
    server_task = asyncio.create_task(serve())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, server_task.cancel)

    try:
        await server_task
    except asyncio.CancelledError:
        logging.info("Shutdown complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())
