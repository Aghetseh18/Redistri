"""
Cluster configuration.

Bootstrap nodes are the initial Redis instances the cluster manager tries
to connect to on startup.  Unreachable nodes are silently skipped.

Override via environment variable:
    BOOTSTRAP_NODES="192.168.1.100:6379,192.168.1.101:6379,192.168.1.102:6379"
"""
import os
from typing import Dict, List


def _parse_env_nodes(raw: str) -> List[Dict]:
    nodes = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            host, port_str = part.rsplit(":", 1)
            nodes.append({"host": host.strip(), "port": int(port_str.strip())})
    return nodes


_env = os.getenv("BOOTSTRAP_NODES", "").strip()
BOOTSTRAP_NODES: List[Dict] = (
    _parse_env_nodes(_env)
    if _env
    else [
        {"host": "192.168.8.103", "port": 7001},  # master (this machine)
        {"host": "192.168.8.102", "port": 7002},  # slave 1
        {"host": "192.168.8.105", "port": 7003},  # slave 2 (note: ordered by IP group)
        {"host": "192.168.8.100", "port": 7004},
        {"host": "192.168.8.107", "port": 7005},
        {"host": "192.168.8.106", "port": 7006},  # slave 3
       
    ]
)

# Cluster behaviour knobs
CLUSTER_CONFIG = {
    "heartbeat_interval": 5,    # seconds between health-check sweeps
    "failure_threshold":  15,   # seconds without heartbeat → FAILED
    "reconnect_interval": 30,   # seconds between reconnect attempts
}

# API metadata
API_VERSION     = "v2"
API_TITLE       = "Redis Auto-Cluster API"
API_DESCRIPTION = (
    "Distributed Redis API with automatic master election, failover, "
    "dynamic entity distribution, live monitoring, and subnet auto-discovery."
)

# Monitoring service ports (used by docker-compose / Prometheus scraping)
MONITORING_CONFIG = {
    "prometheus_port":     9090,
    "grafana_port":        3000,
    "redis_exporter_port": 9121,
}
