import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from redis.cluster import RedisCluster, ClusterNode

logger = logging.getLogger(__name__)

class NodeRole(str, Enum):
    MASTER  = "master"
    REPLICA = "replica"

class NodeStatus(str, Enum):
    HEALTHY      = "healthy"
    DEGRADED     = "degraded"
    FAILED       = "failed"
    JOINING      = "joining"

@dataclass
class NodeInfo:
    node_id:    str
    host:       str
    port:       int
    role:       NodeRole
    status:     NodeStatus
    priority:   int = 100
    last_seen:  float = field(default_factory=time.time)
    entities:   List[str] = field(default_factory=list)
    replica_of: Optional[str] = None
    metrics:    Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "node_id":    self.node_id,
            "host":       self.host,
            "port":       self.port,
            "role":       self.role,
            "status":     self.status,
            "priority":   self.priority,
            "last_seen":  self.last_seen,
            "entities":   self.entities,
            "replica_of": self.replica_of,
            "metrics":    self.metrics,
        }

class ClusterManager:
    def __init__(self):
        self.client: Optional[RedisCluster] = None
        self._event_listeners: List[Callable] = []
        self._connections: Dict[str, Any] = {}
        self._nodes: Dict[str, Any] = {}

    def start(self, bootstrap_nodes: List[Dict]):
        nodes = [ClusterNode(host=n["host"], port=n["port"]) for n in bootstrap_nodes]
        remap = [
            {"from_host": "10.108.135.244", "from_port": 7001, "to_host": "192.168.8.103", "to_port": 7001},
            {"from_host": "10.108.135.223", "from_port": 7002, "to_host": "192.168.8.102", "to_port": 7002},
            {"from_host": "10.108.135.172", "from_port": 7003, "to_host": "192.168.8.105", "to_port": 7003},
            {"from_host": "10.108.135.172", "from_port": 7004, "to_host": "192.168.8.100", "to_port": 7004},
            {"from_host": "10.108.135.139", "from_port": 7005, "to_host": "192.168.8.107", "to_port": 7005},
            {"from_host": "10.108.135.172", "from_port": 7006, "to_host": "192.168.8.106", "to_port": 7006},
        ]
        # skip_full_coverage_check=True to allow partial startup even if cluster is unhealthy
        self.client = RedisCluster(
            startup_nodes=nodes, 
            decode_responses=True,
            skip_full_coverage_check=True,
            host_port_remap=remap
        )
        self._connections = {"native-cluster": self.client}
        self._nodes = {"native-cluster": self.get_master()}
        logger.info("Native RedisCluster client started")

    def stop(self):
        if self.client:
            self.client.close()

    def add_event_listener(self, cb: Callable):
        self._event_listeners.append(cb)

    def get_topology(self) -> dict:
        nodes = self.get_all_nodes()
        healthy = sum(1 for n in nodes if n.status == NodeStatus.HEALTHY)
        failed = sum(1 for n in nodes if n.status == NodeStatus.FAILED)
        master = self.get_master()
        
        dist = {}
        if self.client:
            for entity in ["clients", "articles", "commandes", "livraisons", "ligne-commandes"]:
                try:
                    # 'clients:1', 'articles:1' etc. route to a specific hash slot
                    # We can ask the cluster which node handles that key
                    key = f"{entity}:1"
                    if entity == "ligne-commandes":
                        key = "ligne_commandes:1"  # just in case
                    node = self.client.get_node_from_key(key)
                    if node:
                        dist[entity] = f"{node.host}:{node.port}"
                except Exception as e:
                    logger.error(f"Failed to get node for entity {entity}: {e}")
                    
        return {
            "master_id": master.node_id if master else "native-cluster",
            "total_nodes": len(nodes),
            "healthy_nodes": healthy,
            "degraded_nodes": 0,
            "failed_nodes": failed,
            "entity_distribution": dist,
            "nodes": [n.to_dict() for n in nodes]
        }

    def get_all_nodes(self) -> List[NodeInfo]:
        if not self.client:
            return []
        try:
            nodes_info = self.client.cluster_nodes()
            
            try:
                metrics_info = self.client.info(target_nodes="all")
            except Exception as e:
                logger.error(f"Failed to fetch metrics: {e}")
                metrics_info = {}
                
            result = []
            
            # Map hex IDs to host:port for frontend readability
            id_to_ip = {}
            for address, info in nodes_info.items():
                if ":" in address:
                    host, port = address.rsplit(":", 1)
                else:
                    host, port = address, 6379
                id_to_ip[info.get("node_id", "")] = f"{host}:{port}"
                
            for address, info in nodes_info.items():
                if ":" in address:
                    host, port = address.rsplit(":", 1)
                else:
                    host, port = address, 6379
                flags = info.get("flags", "")
                role = NodeRole.MASTER if "master" in flags else NodeRole.REPLICA
                status = NodeStatus.FAILED if "fail" in flags else NodeStatus.HEALTHY
                
                master_hex = info.get("master_id")
                replica_of = id_to_ip.get(master_hex) if master_hex and master_hex != "-" else None
                
                # Some redis-py versions key by ClusterNode objects instead of strings
                node_metrics = metrics_info.get(address)
                if not node_metrics:
                    for k, v in metrics_info.items():
                        if str(k) == address or (getattr(k, 'host', None) == host and getattr(k, 'port', None) == int(port)):
                            node_metrics = v
                            break
                            
                result.append(NodeInfo(
                    node_id=f"{host}:{port}",
                    host=host,
                    port=int(port),
                    role=role,
                    status=status,
                    replica_of=replica_of,
                    metrics=node_metrics or {}
                ))
            return result
        except Exception as e:
            logger.error(f"Failed to get nodes: {e}")
            return []

    def get_master(self) -> NodeInfo:
        nodes = self.get_all_nodes()
        if not nodes:
            return NodeInfo(
                node_id="native-cluster",
                host="localhost",
                port=6379,
                role=NodeRole.MASTER,
                status=NodeStatus.HEALTHY
            )
        for node in nodes:
            if node.role == NodeRole.MASTER and node.status == NodeStatus.HEALTHY:
                return node
        return nodes[0]

    def get_connection_for_entity(self, entity_type: str):
        return self.client

    def get_node_for_entity(self, entity_type: str):
        return self.get_master()

    def register_node(self, host: str, port: int, priority: Optional[int] = None) -> str:
        return f"{host}:{port}"

    def remove_node(self, node_id: str):
        pass

    def force_failover(self, new_master_id: str):
        pass

    def manual_rebalance(self):
        pass

    def scan_subnet(self, subnet: str, port: int = 6379, start: int = 1, end: int = 254) -> List[str]:
        return []

    def health_check(self) -> Dict[str, bool]:
        return {"native-cluster": True}

cluster_manager = ClusterManager()
