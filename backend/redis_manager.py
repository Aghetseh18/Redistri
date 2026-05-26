"""
Redis manager — thin CRUD wrapper over ClusterManager.

main.py calls this exactly as before; all routing decisions are
delegated to cluster_manager transparently.
"""
import json
import logging
from typing import Any, Dict, List, Optional

import redis

from cluster_manager import cluster_manager, NodeInfo, NodeStatus

logger = logging.getLogger(__name__)


class RedisManager:
    """Provides the same CRUD interface used by main.py while delegating
    all topology / failover logic to ClusterManager."""

    # ── Cluster delegation ────────────────────────────────────────────────────

    @property
    def nodes(self) -> Dict[str, NodeInfo]:
        return {n.node_id: n for n in cluster_manager.get_all_nodes()}

    def get_node(self, node_id: str) -> Optional[redis.Redis]:
        return cluster_manager._connections.get(node_id)

    def get_node_for_entity(self, entity_type: str) -> Optional[redis.Redis]:
        return cluster_manager.get_connection_for_entity(entity_type)

    def health_check(self) -> Dict[str, bool]:
        return cluster_manager.health_check()

    def get_node_info(self, node_id: str) -> Optional[dict]:
        for node in cluster_manager.get_all_nodes():
            if node.node_id == node_id:
                return node.to_dict()
        return None

    def close_all(self):
        cluster_manager.stop()

    # ── Key-value operations ──────────────────────────────────────────────────

    def set(self, conn: redis.Redis, key: str, value: dict) -> bool:
        try:
            conn.set(key, json.dumps(value))
            return True
        except Exception as exc:
            logger.error(f"SET {key}: {exc}")
            return False

    def get(self, conn: redis.Redis, key: str) -> Optional[dict]:
        try:
            raw = conn.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.error(f"GET {key}: {exc}")
            return None

    def delete(self, conn: redis.Redis, key: str) -> bool:
        try:
            conn.delete(key)
            return True
        except Exception as exc:
            logger.error(f"DEL {key}: {exc}")
            return False

    def exists(self, conn: redis.Redis, key: str) -> bool:
        try:
            return conn.exists(key) > 0
        except Exception as exc:
            logger.error(f"EXISTS {key}: {exc}")
            return False

    def get_all_keys(self, conn: redis.Redis, pattern: str = "*") -> List[str]:
        try:
            return conn.keys(pattern)
        except Exception as exc:
            logger.error(f"KEYS {pattern}: {exc}")
            return []

    def get_counter(self, conn: redis.Redis, key: str) -> int:
        try:
            val = conn.get(key)
            return int(val) if val else 0
        except Exception as exc:
            logger.error(f"GET counter {key}: {exc}")
            return 0


# Singleton used throughout the application
redis_manager = RedisManager()
