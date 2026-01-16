import os
import random
import time

import httpx

NAMESPACE = os.getenv("KUBE_NAMESPACE")
CLUSTER_DOMAIN = os.getenv("CLUSTER_DOMAIN")


def simulate_temperature(
    start_range: int,
    end_range: int,
    duration: float,
    station_name: str = "wms-sim-s1",
):
    start_time = time.time()
    while (time.time() - start_time) <= duration:
        value = random.randrange(start_range * 308, end_range * 308)
        httpx.get(
            f"http://{station_name}.{NAMESPACE}.svc.{CLUSTER_DOMAIN}:8080"
            f"/api/registers?register=11&value={value}&submit=Set"
        )


def simulate_windspeed(
    start_range: int,
    end_range: int,
    duration: float,
    station_name: str = "wms-sim-s1",
):
    start_time = time.time()
    while (time.time() - start_time) <= duration:
        value = random.randrange(start_range * 308, end_range * 308)
        httpx.get(
            f"http://{station_name}.{NAMESPACE}.svc.{CLUSTER_DOMAIN}:8080"
            f"/api/registers?register=9&value={value}&submit=Set"
        )
