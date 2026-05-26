"""
Dynamic Redis Cluster Manager

Handles:
  - Node registration / deregistration
  - Priority-based master election (bully-style)
  - Automatic failover when a node goes dark
  - Entity-type distribution across healthy nodes (least-loaded)
  - Background heartbeat monitor thread
  - Subnet scanning for auto-discovery
  - Cluster state persistence to master Redis
  - Event bus for WebSocket live updates
"""
import json
import logging
import socket
import threading
import time
import concurrent.futures
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


def _local_lan_ip() -> str:
    """Return the machine's LAN IP (used when master is 'localhost')."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

import redis

logger = logging.getLogger(__name__)

# ── Tuning constants (can be overridden from config) ──────────────────────────
HEARTBEAT_INTERVAL = 5       # seconds between health-check sweeps
FAILURE_THRESHOLD  = 15      # seconds without a successful PING → FAILED
RECONNECT_INTERVAL = 30      # seconds between reconnect attempts for failed nodes

# All entity types the API manages
ENTITY_TYPES: List[str] = [
    "clients",
    "articles",
    "commandes",
    "ligne_commandes",
    "livraisons",
    "detail_livraisons",
]

# Redis key where the cluster saves its own state (on the master node)
CLUSTER_REGISTRY_KEY = "__cluster:registry"


# ── Enums ─────────────────────────────────────────────────────────────────────

class NodeRole(str, Enum):
    MASTER  = "master"
    REPLICA = "replica"


class NodeStatus(str, Enum):
    HEALTHY      = "healthy"
    DEGRADED     = "degraded"   # missed 1+ heartbeats but not yet failed
    FAILED       = "failed"
    JOINING      = "joining"    # registered but not yet confirmed healthy


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class NodeInfo:
    node_id:    str
    host:       str
    port:       int
    role:       NodeRole
    status:     NodeStatus
    priority:   int                       # lower number → higher election priority
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

    @classmethod
    def from_dict(cls, d: dict) -> "NodeInfo":
        return cls(
            node_id    = d["node_id"],
            host       = d["host"],
            port       = d["port"],
            role       = NodeRole(d["role"]),
            status     = NodeStatus(d["status"]),
            priority   = d.get("priority", 100),
            last_seen  = d.get("last_seen", time.time()),
            entities   = d.get("entities", []),
            replica_of = d.get("replica_of"),
            metrics    = d.get("metrics", {}),
        )


# ── ClusterManager ────────────────────────────────────────────────────────────

class ClusterManager:
    """
    Manages a pool of independent Redis instances as a logical cluster.

    Usage:
        cluster_manager.start(bootstrap_nodes)   # call once at app startup
        cluster_manager.stop()                    # call at app shutdown
    """

    def __init__(self):
        self._nodes:       Dict[str, NodeInfo]    = {}   # node_id → NodeInfo
        self._connections: Dict[str, redis.Redis] = {}   # node_id → connection
        self._entity_map:  Dict[str, str]         = {}   # entity_type → node_id
        self._master_id:   Optional[str]          = None

        self._lock              = threading.RLock()
        self._running           = False
        self._monitor_thread:   Optional[threading.Thread] = None
        self._event_listeners:  List[Callable]    = []
        self._priority_counter  = 10              # auto-priority seeds here
        self._replication_pairs: Dict[str, str]   = {}   # replica_id → master_id

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, bootstrap_nodes: List[Dict]):
        """Connect to bootstrap nodes and launch the heartbeat thread."""
        self._running = True

        for conf in bootstrap_nodes:
            try:
                self.register_node(
                    host     = conf["host"],
                    port     = conf["port"],
                    priority = conf.get("priority", self._next_priority()),
                )
            except Exception as exc:
                logger.warning(
                    f"Bootstrap node {conf['host']}:{conf['port']} unreachable: {exc}"
                )

        # After all bootstrap nodes are connected, do a full rebalance so
        # entity types are spread evenly rather than piling on the first node.
        if len(self._nodes) > 1:
            self.manual_rebalance()

        self._monitor_thread = threading.Thread(
            target = self._monitor_loop,
            name   = "cluster-monitor",
            daemon = True,
        )
        self._monitor_thread.start()
        logger.info(
            f"Cluster manager started — {len(self._nodes)} bootstrap node(s) online"
        )

    def stop(self):
        """Graceful shutdown: stop monitor thread and close all connections."""
        self._running = False
        with self._lock:
            for conn in self._connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
        logger.info("Cluster manager stopped")

    # ── Node management ───────────────────────────────────────────────────────

    def register_node(
        self,
        host:     str,
        port:     int,
        priority: Optional[int] = None,
    ) -> str:
        """
        Register a Redis instance with the cluster.

        - Connects to the instance (raises ConnectionError if unreachable).
        - Runs master election and entity rebalancing.
        - Returns the node_id (``"host:port"``).
        """
        node_id = f"{host}:{port}"
        if priority is None:
            priority = self._next_priority()

        with self._lock:
            existing = self._nodes.get(node_id)
            if existing and existing.status != NodeStatus.FAILED:
                return node_id                         # already live

            conn = self._make_connection(host, port, timeout=5)  # raises on fail

            self._connections[node_id] = conn

            node = NodeInfo(
                node_id  = node_id,
                host     = host,
                port     = port,
                role     = NodeRole.REPLICA,           # election corrects this
                status   = NodeStatus.JOINING,
                priority = priority,
            )
            self._nodes[node_id] = node

            self._elect_master()
            self._rebalance_entities()
            node.status = NodeStatus.HEALTHY

            self._persist_state()
            self._notify("node_joined", node.to_dict())
            logger.info(f"Node {node_id} registered as {node.role.value} (priority={priority})")
            return node_id

    def remove_node(self, node_id: str):
        """Remove a node from the cluster and rebalance."""
        with self._lock:
            if node_id not in self._nodes:
                raise KeyError(f"Node '{node_id}' not found")

            node = self._nodes.pop(node_id)
            conn = self._connections.pop(node_id, None)
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

            was_master = (self._master_id == node_id)
            if was_master:
                self._master_id = None

            self._elect_master()
            self._rebalance_entities()
            self._persist_state()
            self._notify("node_removed", {"node_id": node_id, "was_master": was_master})
            logger.info(f"Node {node_id} removed (was_master={was_master})")

    def force_failover(self, new_master_id: str):
        """Manually promote a specific node to master."""
        with self._lock:
            node = self._nodes.get(new_master_id)
            if not node:
                raise KeyError(f"Node '{new_master_id}' not found")
            if node.status == NodeStatus.FAILED:
                raise ValueError("Cannot promote a failed node")

            # Give it the lowest possible priority so it wins the next election
            node.priority = 0
            self._elect_master()
            self._persist_state()
            self._notify("failover_forced", {"new_master": new_master_id})

    def manual_rebalance(self):
        """Force a full redistribution of entity types across healthy nodes."""
        with self._lock:
            self._entity_map.clear()
            for n in self._nodes.values():
                n.entities = []
            self._rebalance_entities()
            self._persist_state()

    # ── Subnet auto-discovery ─────────────────────────────────────────────────

    def scan_subnet(
        self,
        subnet:  str,
        port:    int = 6379,
        start:   int = 1,
        end:     int = 254,
    ) -> List[str]:
        """
        Concurrently probe every host in ``subnet.start`` … ``subnet.end``
        for a reachable Redis instance and auto-register any found.

        Example::
            scan_subnet("192.168.1", 6379, 100, 110)
        """
        found: List[str] = []

        def _probe(host: str):
            node_id = f"{host}:{port}"
            if node_id in self._nodes:
                return
            try:
                r = redis.Redis(
                    host=host, port=port,
                    socket_connect_timeout=1, socket_timeout=1,
                    decode_responses=True,
                )
                r.ping()
                self.register_node(host, port)
                found.append(node_id)
                logger.info(f"Auto-discovered Redis at {host}:{port}")
            except Exception:
                pass

        hosts = [f"{subnet}.{i}" for i in range(start, end + 1)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as exe:
            exe.map(_probe, hosts)

        return found

    # ── Query helpers ─────────────────────────────────────────────────────────

    def get_connection_for_entity(self, entity_type: str) -> Optional[redis.Redis]:
        with self._lock:
            nid = self._entity_map.get(entity_type)
            return self._connections.get(nid) if nid else None

    def get_node_for_entity(self, entity_type: str) -> Optional[NodeInfo]:
        with self._lock:
            nid = self._entity_map.get(entity_type)
            return self._nodes.get(nid) if nid else None

    def get_all_nodes(self) -> List[NodeInfo]:
        with self._lock:
            return list(self._nodes.values())

    def get_master(self) -> Optional[NodeInfo]:
        with self._lock:
            return self._nodes.get(self._master_id) if self._master_id else None

    def health_check(self) -> Dict[str, bool]:
        with self._lock:
            return {
                nid: n.status == NodeStatus.HEALTHY
                for nid, n in self._nodes.items()
            }

    def get_topology(self) -> dict:
        with self._lock:
            nodes = list(self._nodes.values())
            return {
                "master_id":          self._master_id,
                "total_nodes":        len(nodes),
                "healthy_nodes":      sum(1 for n in nodes if n.status == NodeStatus.HEALTHY),
                "degraded_nodes":     sum(1 for n in nodes if n.status == NodeStatus.DEGRADED),
                "failed_nodes":       sum(1 for n in nodes if n.status == NodeStatus.FAILED),
                "entity_distribution": dict(self._entity_map),
                "nodes":              [n.to_dict() for n in nodes],
            }

    def add_event_listener(self, cb: Callable):
        """Register a callback invoked on every cluster topology change."""
        self._event_listeners.append(cb)

    # ── Replication management ────────────────────────────────────────────────

    def setup_replication_pair(self, master_id: str, replica_id: str) -> dict:
        """Send REPLICAOF <master_host> <master_port> to the replica node."""
        with self._lock:
            master = self._nodes.get(master_id)
            replica = self._nodes.get(replica_id)
            if not master:
                raise KeyError(f"Master node '{master_id}' not found")
            if not replica:
                raise KeyError(f"Replica node '{replica_id}' not found")
            if master.status == NodeStatus.FAILED:
                raise ValueError("Cannot replicate from a failed master")
            if replica.status == NodeStatus.FAILED:
                raise ValueError("Cannot configure replication on a failed replica")

            replica_conn = self._connections.get(replica_id)
            if not replica_conn:
                raise ConnectionError(f"No connection to replica '{replica_id}'")

            # Resolve master host: remote nodes cannot reach 'localhost'
            master_host = master.host
            if master_host in ("localhost", "127.0.0.1"):
                master_host = _local_lan_ip()

            replica_conn.execute_command("REPLICAOF", master_host, master.port)
            self._replication_pairs[replica_id] = master_id
            self._notify("replication_configured", {
                "master": master_id,
                "replica": replica_id,
                "master_host_used": master_host,
            })
            logger.info(f"REPLICAOF configured: {replica_id} → {master_host}:{master.port}")
            return {
                "master": master_id,
                "replica": replica_id,
                "master_host_used": master_host,
                "master_port": master.port,
                "status": "replication_started",
            }

    def stop_replication(self, replica_id: str) -> dict:
        """Send REPLICAOF NO ONE to the replica, making it independent again."""
        with self._lock:
            replica = self._nodes.get(replica_id)
            if not replica:
                raise KeyError(f"Replica node '{replica_id}' not found")

            replica_conn = self._connections.get(replica_id)
            if not replica_conn:
                raise ConnectionError(f"No connection to replica '{replica_id}'")

            replica_conn.execute_command("REPLICAOF", "NO", "ONE")
            self._replication_pairs.pop(replica_id, None)
            self._notify("replication_stopped", {"replica": replica_id})
            logger.info(f"REPLICAOF stopped on {replica_id}")
            return {"replica": replica_id, "status": "replication_stopped"}

    def replication_write_read_demo(self, master_id: str) -> dict:
        """
        Write a timestamped key to the master, then read it back from a replica.
        Returns which machines were involved and whether replication worked.
        """
        import time as _time
        with self._lock:
            master = self._nodes.get(master_id)
            if not master:
                raise KeyError(f"Master node '{master_id}' not found")

            master_conn = self._connections.get(master_id)
            if not master_conn:
                raise ConnectionError(f"No connection to master '{master_id}'")

            # Find a replica that is replicating from this master
            replica_id = next(
                (rid for rid, mid in self._replication_pairs.items() if mid == master_id),
                None,
            )

            test_key = f"replication_demo:{int(_time.time() * 1000)}"
            test_val = f"written_at={_time.strftime('%H:%M:%S')}_from={master_id}"

            # Write to master
            master_conn.set(test_key, test_val, ex=60)  # TTL 60s

            result = {
                "key": test_key,
                "write": {
                    "node": master_id,
                    "host": master.host,
                    "port": master.port,
                    "value": test_val,
                },
                "read": None,
                "replication_ok": False,
                "replication_lag_ms": None,
            }

            if not replica_id:
                result["error"] = "No replica configured for this master. Call /cluster/replication/setup first."
                return result

            replica = self._nodes.get(replica_id)
            replica_conn = self._connections.get(replica_id)
            if not replica_conn:
                result["error"] = f"No connection to replica '{replica_id}'"
                return result

            # Wait up to 500ms for replication to propagate
            t0 = _time.time()
            read_val = None
            for _ in range(5):
                _time.sleep(0.1)
                try:
                    read_val = replica_conn.get(test_key)
                    if read_val is not None:
                        break
                except Exception:
                    break

            lag_ms = round((_time.time() - t0) * 1000)
            result["read"] = {
                "node": replica_id,
                "host": replica.host,
                "port": replica.port,
                "value": read_val,
            }
            result["replication_ok"] = read_val == test_val
            result["replication_lag_ms"] = lag_ms
            return result

    def get_replication_status(self) -> List[dict]:
        """Return INFO replication from every node in the cluster."""
        statuses = []
        with self._lock:
            for node_id, node in self._nodes.items():
                conn = self._connections.get(node_id)
                entry: dict = {
                    "node_id": node_id,
                    "host": node.host,
                    "port": node.port,
                    "cluster_role": node.role,
                    "status": node.status,
                    "replicating_from": self._replication_pairs.get(node_id),
                    "replicas_configured": [
                        rid for rid, mid in self._replication_pairs.items()
                        if mid == node_id
                    ],
                }
                if conn:
                    try:
                        info = conn.info("replication")
                        entry["redis_role"] = info.get("role")
                        entry["connected_slaves"] = info.get("connected_slaves", 0)
                        entry["master_replid"] = info.get("master_replid")
                        entry["master_repl_offset"] = info.get("master_repl_offset")
                        entry["repl_backlog_size"] = info.get("repl_backlog_size")
                        # slave-specific fields
                        entry["master_host"] = info.get("master_host")
                        entry["master_port"] = info.get("master_port")
                        entry["master_link_status"] = info.get("master_link_status")
                        entry["master_last_io_seconds_ago"] = info.get("master_last_io_seconds_ago")
                    except Exception as exc:
                        entry["error"] = str(exc)
                else:
                    entry["error"] = "no connection"
                statuses.append(entry)
        return statuses

    # ── Internal: election ────────────────────────────────────────────────────

    def _elect_master(self):
        """
        Priority-based election: the healthy node with the *lowest* priority
        number becomes master.  Ties broken by node_id lexicographic order.
        """
        candidates = [
            n for n in self._nodes.values()
            if n.status in (NodeStatus.HEALTHY, NodeStatus.JOINING)
        ]
        if not candidates:
            self._master_id = None
            logger.warning("No healthy nodes available — cluster has no master")
            return

        candidates.sort(key=lambda n: (n.priority, n.node_id))
        winner = candidates[0]

        # Update roles
        for node in self._nodes.values():
            if node.status != NodeStatus.FAILED:
                if node.node_id == winner.node_id:
                    node.role       = NodeRole.MASTER
                    node.replica_of = None
                else:
                    node.role       = NodeRole.REPLICA
                    node.replica_of = winner.node_id

        if self._master_id != winner.node_id:
            old = self._master_id
            self._master_id = winner.node_id
            logger.info(
                f"Master elected: {winner.node_id}"
                + (f" (replaced {old})" if old else "")
            )
            self._notify("master_elected", {
                "new_master":      winner.node_id,
                "previous_master": old,
            })

    # ── Internal: entity distribution ─────────────────────────────────────────

    def _rebalance_entities(self):
        """
        Assign ENTITY_TYPES to healthy nodes using a least-loaded strategy.
        Only orphaned (failed-node) assignments are moved; stable ones remain.
        """
        healthy_ids = {
            n.node_id for n in self._nodes.values()
            if n.status in (NodeStatus.HEALTHY, NodeStatus.JOINING)
        }

        if not healthy_ids:
            self._entity_map.clear()
            for n in self._nodes.values():
                n.entities = []
            return

        # Drop assignments whose owner is gone or failed
        orphaned = [e for e, nid in list(self._entity_map.items())
                    if nid not in healthy_ids]
        for e in orphaned:
            del self._entity_map[e]

        # Assign every unassigned entity type to the least-loaded healthy node
        unassigned = [e for e in ENTITY_TYPES if e not in self._entity_map]
        if unassigned:
            load = {
                nid: sum(1 for v in self._entity_map.values() if v == nid)
                for nid in healthy_ids
            }
            for entity in unassigned:
                least = min(load, key=load.get)
                self._entity_map[entity] = least
                load[least] += 1

        # Spread load: if any healthy node has 0 entities and another has >1,
        # move one entity from the most-loaded to the least-loaded node.
        load = {
            nid: sum(1 for v in self._entity_map.values() if v == nid)
            for nid in healthy_ids
        }
        avg = len(ENTITY_TYPES) / len(healthy_ids)
        for _ in range(len(ENTITY_TYPES)):
            most_loaded  = max(load, key=load.get)
            least_loaded = min(load, key=load.get)
            if load[most_loaded] - load[least_loaded] <= 1:
                break
            # Move one entity from most → least
            for entity, nid in list(self._entity_map.items()):
                if nid == most_loaded:
                    self._entity_map[entity] = least_loaded
                    load[most_loaded]  -= 1
                    load[least_loaded] += 1
                    break

        # Sync node.entities lists
        for node in self._nodes.values():
            node.entities = [
                e for e, nid in self._entity_map.items()
                if nid == node.node_id
            ]

        logger.info(f"Entity map after rebalance: {self._entity_map}")
        self._notify("entities_rebalanced", {"entity_map": dict(self._entity_map)})

    # ── Internal: heartbeat monitor ───────────────────────────────────────────

    def _monitor_loop(self):
        while self._running:
            try:
                self._check_all_nodes()
            except Exception as exc:
                logger.error(f"Monitor loop error: {exc}")
            time.sleep(HEARTBEAT_INTERVAL)

    def _check_all_nodes(self):
        now = time.time()
        with self._lock:
            for node_id, node in list(self._nodes.items()):
                if node.status == NodeStatus.FAILED:
                    # Periodic reconnect attempt
                    if now - node.last_seen >= RECONNECT_INTERVAL:
                        self._try_reconnect(node)
                    continue

                conn = self._connections.get(node_id)
                try:
                    if conn is None:
                        conn = self._make_connection(node.host, node.port, timeout=2)
                        self._connections[node_id] = conn
                    conn.ping()
                    node.last_seen = now
                    node.status    = NodeStatus.HEALTHY
                    node.metrics   = self._collect_metrics(conn)

                except Exception:
                    elapsed = now - node.last_seen
                    if elapsed >= FAILURE_THRESHOLD:
                        was_master  = (node_id == self._master_id)
                        node.status = NodeStatus.FAILED
                        self._connections.pop(node_id, None)
                        logger.warning(
                            f"Node {node_id} → FAILED "
                            f"(no heartbeat for {elapsed:.0f}s, was_master={was_master})"
                        )
                        self._notify("node_failed", {
                            "node_id":    node_id,
                            "was_master": was_master,
                        })
                        if was_master:
                            self._elect_master()
                        self._rebalance_entities()
                        self._persist_state()
                    else:
                        node.status = NodeStatus.DEGRADED

    def _try_reconnect(self, node: NodeInfo):
        try:
            conn = self._make_connection(node.host, node.port, timeout=2)
            self._connections[node.node_id] = conn
            node.status    = NodeStatus.JOINING
            node.last_seen = time.time()
            self._elect_master()
            self._rebalance_entities()
            node.status = NodeStatus.HEALTHY
            logger.info(f"Node {node.node_id} reconnected and re-integrated")
            self._persist_state()
            self._notify("node_rejoined", node.to_dict())
        except Exception:
            node.last_seen = time.time()   # reset to avoid tight retry loop

    # ── Internal: helpers ─────────────────────────────────────────────────────

    def _make_connection(self, host: str, port: int, timeout: int = 3) -> redis.Redis:
        conn = redis.Redis(
            host=host, port=port,
            decode_responses=True,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
        )
        conn.ping()   # raises redis.exceptions.ConnectionError if unreachable
        return conn

    def _collect_metrics(self, conn: redis.Redis) -> dict:
        try:
            info = conn.info()
            return {
                "redis_version":          info.get("redis_version"),
                "uptime_seconds":         info.get("uptime_in_seconds"),
                "connected_clients":      info.get("connected_clients"),
                "used_memory_human":      info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "total_commands":         info.get("total_commands_processed"),
                "ops_per_sec":            info.get("instantaneous_ops_per_sec"),
                "keyspace_hits":          info.get("keyspace_hits"),
                "keyspace_misses":        info.get("keyspace_misses"),
                "db_size":                conn.dbsize(),
                "redis_role":             info.get("role"),
            }
        except Exception:
            return {}

    def _persist_state(self):
        """Best-effort: write cluster registry JSON to the master node."""
        if not self._master_id:
            return
        conn = self._connections.get(self._master_id)
        if not conn:
            return
        try:
            state = {
                "nodes":      {nid: n.to_dict() for nid, n in self._nodes.items()},
                "entity_map": self._entity_map,
                "master_id":  self._master_id,
            }
            conn.set(CLUSTER_REGISTRY_KEY, json.dumps(state))
        except Exception:
            pass   # non-fatal — state is rebuilt from live nodes on restart

    def _next_priority(self) -> int:
        p = self._priority_counter
        self._priority_counter += 10
        return p

    def _notify(self, event: str, data: dict):
        for cb in self._event_listeners:
            try:
                cb(event, data)
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
cluster_manager = ClusterManager()
