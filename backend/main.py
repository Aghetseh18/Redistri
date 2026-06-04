"""
FastAPI application — Redis Auto-Cluster
Full CRUD for domain entities + dynamic cluster management + live monitoring.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from cluster_manager import cluster_manager, NodeRole, NodeStatus
from config import API_DESCRIPTION, API_TITLE, API_VERSION, BOOTSTRAP_NODES
from models import (
    Article,
    ArticleResponse,
    BulkArticleCreate,
    BulkClientCreate,
    BulkCommandeCreate,
    Client,
    ClientResponse,
    ClusterEventMessage,
    ClusterTopologyResponse,
    Commande,
    CommandeResponse,
    DetailLivraison,
    DetailLivraisonResponse,
    HealthStatus,
    LigneCommande,
    LigneCommandeResponse,
    Livraison,
    LivraisonResponse,
    NodeMetrics,
    NodeRegistration,
    OperationStatus,
    ReplicationSetup,
    SubnetScanRequest,
)
from redis_manager import redis_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── WebSocket event bus ───────────────────────────────────────────────────────
# The cluster_manager's background thread fires events; we need to push them
# to all connected WebSocket clients on the asyncio event loop.

_event_loop: Optional[asyncio.AbstractEventLoop] = None
_ws_clients: List[WebSocket] = []


def _on_cluster_event(event: str, data: dict):
    """Called from the monitor thread — schedule a broadcast on the event loop."""
    if _event_loop and not _event_loop.is_closed():
        asyncio.run_coroutine_threadsafe(
            _broadcast({"event": event, "data": data, "timestamp": time.time()}),
            _event_loop,
        )


async def _broadcast(msg: dict):
    for ws in _ws_clients[:]:
        try:
            await ws.send_json(msg)
        except Exception:
            if ws in _ws_clients:
                _ws_clients.remove(ws)


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _event_loop
    _event_loop = asyncio.get_event_loop()
    cluster_manager.add_event_listener(_on_cluster_event)
    cluster_manager.start(BOOTSTRAP_NODES)
    logger.info("Redis cluster manager initialised")
    yield
    logger.info("Shutting down cluster manager")
    cluster_manager.stop()


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  Root
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Root"])
async def root():
    topo = cluster_manager.get_topology()
    return {
        "message":    "Redis Auto-Cluster API",
        "version":    API_VERSION,
        "docs":       "/docs",
        "health":     "/health",
        "topology":   "/cluster/topology",
        "monitor_ws": "ws://<host>/ws/monitor",
        "master":     topo.get("master_id"),
        "nodes":      f"{topo['healthy_nodes']}/{topo['total_nodes']} healthy",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Health & basic monitoring
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", response_model=OperationStatus, tags=["Health"])
async def health_check():
    topo = cluster_manager.get_topology()
    all_ok = topo["failed_nodes"] == 0 and topo["healthy_nodes"] > 0
    return OperationStatus(
        success=all_ok,
        message=(
            "All nodes healthy"
            if all_ok
            else f"{topo['failed_nodes']} node(s) failed, "
                 f"{topo['healthy_nodes']} healthy"
        ),
        data={
            "master_id":     topo["master_id"],
            "healthy_nodes": topo["healthy_nodes"],
            "failed_nodes":  topo["failed_nodes"],
        },
    )


@app.get("/nodes/status", response_model=List[HealthStatus], tags=["Health"])
async def nodes_status():
    results = []
    for node in cluster_manager.get_all_nodes():
        t0 = time.time()
        # Rely on the cluster's internal state for health instead of a custom pool
        connected = (node.status == NodeStatus.HEALTHY)
        ms = (time.time() - t0) * 1000
        results.append(
            HealthStatus(
                node_id          = node.node_id,
                role             = node.role,
                status           = node.status,
                is_connected     = connected,
                response_time_ms = round(ms, 2),
                entities         = node.entities,
                info             = node.metrics or None,
            )
        )
    return results


# ══════════════════════════════════════════════════════════════════════════════
#  Cluster management
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/cluster/nodes", response_model=OperationStatus, tags=["Cluster"])
async def register_node(body: NodeRegistration):
    """Register a new Redis node with the cluster."""
    try:
        node_id = cluster_manager.register_node(
            host=body.host, port=body.port, priority=body.priority
        )
        node = cluster_manager._nodes[node_id]
        return OperationStatus(
            success=True,
            message=f"Node {node_id} registered as {node.role.value}",
            data=node.to_dict(),
        )
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/cluster/nodes/{node_id:path}", response_model=OperationStatus, tags=["Cluster"])
async def deregister_node(node_id: str):
    """Remove a node from the cluster (graceful)."""
    try:
        cluster_manager.remove_node(node_id)
        return OperationStatus(success=True, message=f"Node {node_id} removed")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/cluster/nodes", response_model=List[Dict[str, Any]], tags=["Cluster"])
async def list_nodes():
    """List all known nodes with their current role, status, and entity assignments."""
    return [n.to_dict() for n in cluster_manager.get_all_nodes()]


@app.get("/cluster/topology", response_model=ClusterTopologyResponse, tags=["Cluster"])
async def get_topology():
    """Full cluster topology snapshot."""
    return cluster_manager.get_topology()


@app.get("/cluster/master", tags=["Cluster"])
async def get_master():
    """Return the current master node info."""
    master = cluster_manager.get_master()
    if not master:
        raise HTTPException(status_code=503, detail="No master elected yet")
    return master.to_dict()


@app.post(
    "/cluster/nodes/{node_id:path}/failover",
    response_model=OperationStatus,
    tags=["Cluster"],
)
async def force_failover(node_id: str):
    """Manually promote a node to master (forces re-election with priority 0)."""
    try:
        cluster_manager.force_failover(node_id)
        return OperationStatus(
            success=True,
            message=f"Failover triggered — {node_id} is now master",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/cluster/rebalance", response_model=OperationStatus, tags=["Cluster"])
async def rebalance():
    """Force a full redistribution of entity types across healthy nodes."""
    cluster_manager.manual_rebalance()
    topo = cluster_manager.get_topology()
    return OperationStatus(
        success=True,
        message="Entity types rebalanced",
        data={"entity_distribution": topo["entity_distribution"]},
    )


@app.post("/cluster/scan", response_model=OperationStatus, tags=["Cluster"])
async def scan_subnet(body: SubnetScanRequest):
    """
    Scan an IP range for reachable Redis instances and auto-register them.

    All discovered nodes are immediately integrated into the cluster.
    """
    found = cluster_manager.scan_subnet(
        subnet=body.subnet, port=body.port,
        start=body.start, end=body.end,
    )
    return OperationStatus(
        success=True,
        message=f"Scan complete — {len(found)} new node(s) discovered",
        data={"discovered": found},
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Monitoring
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/cluster/metrics", response_model=List[NodeMetrics], tags=["Monitoring"])
async def cluster_metrics():
    """Detailed per-node Redis metrics (memory, ops/s, hit rate, etc.)."""
    results = []
    for node in cluster_manager.get_all_nodes():
        m = node.metrics or {}
        results.append(NodeMetrics(
            node_id                = node.node_id,
            role                   = node.role,
            status                 = node.status,
            priority               = node.priority,
            entities               = node.entities,
            redis_version          = m.get("redis_version"),
            uptime_seconds         = m.get("uptime_seconds"),
            connected_clients      = m.get("connected_clients"),
            used_memory_human      = m.get("used_memory_human"),
            used_memory_peak_human = m.get("used_memory_peak_human"),
            total_commands         = m.get("total_commands"),
            ops_per_sec            = m.get("ops_per_sec"),
            keyspace_hits          = m.get("keyspace_hits"),
            keyspace_misses        = m.get("keyspace_misses"),
            db_size                = m.get("db_size"),
        ))
    return results


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Prometheus text-format metrics endpoint (scrape at /metrics)."""
    lines = []
    lines.append("# HELP redis_node_up 1 if node is healthy, 0 otherwise")
    lines.append("# TYPE redis_node_up gauge")
    lines.append("# HELP redis_node_is_master 1 if node is master")
    lines.append("# TYPE redis_node_is_master gauge")
    lines.append("# HELP redis_db_size Number of keys in the database")
    lines.append("# TYPE redis_db_size gauge")
    lines.append("# HELP redis_ops_per_sec Instantaneous operations per second")
    lines.append("# TYPE redis_ops_per_sec gauge")
    lines.append("# HELP redis_connected_clients Number of connected clients")
    lines.append("# TYPE redis_connected_clients gauge")
    lines.append("# HELP redis_uptime_seconds Node uptime in seconds")
    lines.append("# TYPE redis_uptime_seconds counter")

    for node in cluster_manager.get_all_nodes():
        lbl = f'node="{node.node_id}"'
        up  = 1 if node.status == NodeStatus.HEALTHY else 0
        mst = 1 if node.role  == NodeRole.MASTER      else 0
        lines.append(f"redis_node_up{{{lbl}}} {up}")
        lines.append(f"redis_node_is_master{{{lbl}}} {mst}")
        m = node.metrics
        if m:
            for metric, key in [
                ("redis_db_size",           "db_size"),
                ("redis_ops_per_sec",       "ops_per_sec"),
                ("redis_connected_clients", "connected_clients"),
                ("redis_uptime_seconds",    "uptime_seconds"),
            ]:
                val = m.get(key)
                if val is not None:
                    lines.append(f"{metric}{{{lbl}}} {val}")

    return PlainTextResponse("\n".join(lines) + "\n")


# ── WebSocket live monitor ────────────────────────────────────────────────────

@app.websocket("/ws/monitor")
async def ws_monitor(ws: WebSocket):
    """
    WebSocket stream of cluster events.

    Events pushed automatically:
      node_joined, node_removed, node_failed, node_rejoined,
      master_elected, failover_forced, entities_rebalanced

    A ``heartbeat`` event with the full topology is also sent every 5 s.
    """
    await ws.accept()
    _ws_clients.append(ws)
    try:
        # Send current snapshot immediately on connect
        await ws.send_json({
            "event":     "connected",
            "data":      cluster_manager.get_topology(),
            "timestamp": time.time(),
        })
        # Keep the connection alive; the event bus handles real-time updates
        while True:
            await asyncio.sleep(5)
            await ws.send_json({
                "event":     "heartbeat",
                "data":      cluster_manager.get_topology(),
                "timestamp": time.time(),
            })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


# ══════════════════════════════════════════════════════════════════════════════
#  DÉMONSTRATION — écrire sur un nœud, lire sur un autre
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/demo/entity-distribution", tags=["Démonstration"])
async def demo_entity_distribution():
    """
    Montre sur quelle machine physique (nœud Redis) chaque type d'entité est stocké.

    Illustre « écrire sur une machine, lire sur une autre » :
    chaque entité vit sur un nœud différent du cluster.
    Les écritures POST /clients et POST /articles, par exemple,
    aboutissent sur deux machines distinctes.
    """
    topo = cluster_manager.get_topology()
    nodes_by_id = {n["node_id"]: n for n in topo["nodes"]}
    dist = topo["entity_distribution"]

    per_entity = {}
    per_node: Dict[str, List[str]] = {}
    for entity, node_id in dist.items():
        n = nodes_by_id.get(node_id, {})
        per_entity[entity] = {
            "node_id": node_id,
            "host":    n.get("host", "?"),
            "port":    n.get("port", 0),
            "role":    n.get("role", "?"),
            "status":  n.get("status", "?"),
        }
        per_node.setdefault(node_id, []).append(entity)

    return {
        "entity_to_node": per_entity,
        "node_to_entities": per_node,
        "explanation": (
            "Chaque POST (écriture) atterrit sur le nœud assigné à ce type d'entité. "
            "Chaque GET (lecture) provient de ce même nœud. "
            "Quand ces nœuds sont sur des machines physiques différentes, "
            "les opérations traversent le réseau — c'est la distribution des données."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  REQUÊTES DISTRIBUÉES — JOIN et GROUP BY simulés
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/query/join/commande/{no_commande}", tags=["Requêtes Distribuées"])
async def join_commande(no_commande: int):
    """
    **JOIN simulé** — assemble une commande complète depuis plusieurs nœuds Redis.

    Étapes :
    1. Lecture de la Commande   → nœud **commandes**
    2. Lecture du Client         → nœud **clients**   (JOIN sur no_client)
    3. Lecture des LigneCommande → nœud **ligne_commandes** (JOIN sur no_commande)
    4. Lecture de chaque Article → nœud **articles**  (JOIN sur no_article)

    Le champ `_node_sources` montre quel nœud physique a fourni chaque données.
    """
    node_sources: Dict[str, str] = {}

    # ── 1. Commande ────────────────────────────────────────────────────────────
    conn_cmd = redis_manager.get_node_for_entity("commandes")
    if not conn_cmd:
        raise HTTPException(status_code=503, detail="Nœud commandes indisponible")
    commande = redis_manager.get(conn_cmd, f"commande:{no_commande}")
    if not commande:
        raise HTTPException(status_code=404, detail=f"Commande {no_commande} introuvable")
    info_cmd = cluster_manager.get_node_for_entity("commandes")
    node_sources["commandes"] = info_cmd.node_id if info_cmd else "?"

    # ── 2. Client (JOIN sur no_client) ────────────────────────────────────────
    client = None
    conn_cli = redis_manager.get_node_for_entity("clients")
    if conn_cli and commande.get("no_client") is not None:
        client = redis_manager.get(conn_cli, f"client:{commande['no_client']}")
        info_cli = cluster_manager.get_node_for_entity("clients")
        node_sources["clients"] = info_cli.node_id if info_cli else "?"

    # ── 3. Lignes commande (JOIN sur no_commande) ─────────────────────────────
    conn_lc = redis_manager.get_node_for_entity("ligne_commandes")
    lignes: List[dict] = []
    if conn_lc:
        lc_keys = redis_manager.get_all_keys(conn_lc, f"ligne_commande:{no_commande}:*")
        lignes = [d for k in lc_keys for d in [redis_manager.get(conn_lc, k)] if d]
        info_lc = cluster_manager.get_node_for_entity("ligne_commandes")
        node_sources["ligne_commandes"] = info_lc.node_id if info_lc else "?"

    # ── 4. Article pour chaque ligne (JOIN sur no_article) ────────────────────
    conn_art = redis_manager.get_node_for_entity("articles")
    lignes_enriched = []
    for ligne in lignes:
        article = None
        if conn_art and ligne.get("no_article") is not None:
            article = redis_manager.get(conn_art, f"article:{ligne['no_article']}")
            info_art = cluster_manager.get_node_for_entity("articles")
            node_sources["articles"] = info_art.node_id if info_art else "?"
        lignes_enriched.append({**ligne, "article": article})

    nodes_queried = list(set(node_sources.values()))
    return {
        "commande":          commande,
        "client":            client,
        "lignes":            lignes_enriched,
        "_node_sources":     node_sources,
        "_nodes_queried":    nodes_queried,
        "_description": (
            f"JOIN distribué : données agrégées depuis {len(nodes_queried)} nœud(s) Redis différent(s)"
        ),
    }


@app.get("/query/groupby/commandes-par-client", tags=["Requêtes Distribuées"])
async def groupby_commandes_par_client():
    """
    **GROUP BY simulé** — nombre de commandes par client.

    Lit les Clients (nœud A) et les Commandes (nœud B) indépendamment,
    puis agrège en mémoire — équivalent de :

    ```sql
    SELECT c.*, COUNT(cmd.no_commande) AS nb_commandes
    FROM clients c LEFT JOIN commandes cmd ON c.no_client = cmd.no_client
    GROUP BY c.no_client
    ```
    """
    conn_cli = redis_manager.get_node_for_entity("clients")
    conn_cmd = redis_manager.get_node_for_entity("commandes")
    if not conn_cli or not conn_cmd:
        raise HTTPException(status_code=503, detail="Nœuds clients ou commandes indisponibles")

    info_cli = cluster_manager.get_node_for_entity("clients")
    info_cmd = cluster_manager.get_node_for_entity("commandes")

    clients = {
        d["no_client"]: d
        for k in redis_manager.get_all_keys(conn_cli, "client:*")
        for d in [redis_manager.get(conn_cli, k)]
        if d
    }

    groups: Dict[int, List[int]] = {cid: [] for cid in clients}
    for k in redis_manager.get_all_keys(conn_cmd, "commande:*"):
        cmd = redis_manager.get(conn_cmd, k)
        if cmd and cmd.get("no_client") in groups:
            groups[cmd["no_client"]].append(cmd["no_commande"])

    results = sorted(
        [
            {"client": clients[cid], "nb_commandes": len(cmds), "no_commandes": cmds}
            for cid, cmds in groups.items()
        ],
        key=lambda r: r["nb_commandes"],
        reverse=True,
    )

    return {
        "results": results,
        "_node_sources": {
            "clients":   info_cli.node_id if info_cli else "?",
            "commandes": info_cmd.node_id if info_cmd else "?",
        },
        "_description": "GROUP BY simulé : agrégation cross-nœuds — commandes par client",
    }


@app.get("/query/groupby/quantite-par-article", tags=["Requêtes Distribuées"])
async def groupby_quantite_par_article():
    """
    **GROUP BY simulé** — quantité totale commandée par article.

    Lit les LigneCommandes (nœud A) et les Articles (nœud B) séparément,
    puis agrège en mémoire — équivalent de :

    ```sql
    SELECT a.*, SUM(lc.quantite) AS total_commande
    FROM ligne_commandes lc JOIN articles a ON lc.no_article = a.no_article
    GROUP BY a.no_article
    ORDER BY total_commande DESC
    ```
    """
    conn_lc  = redis_manager.get_node_for_entity("ligne_commandes")
    conn_art = redis_manager.get_node_for_entity("articles")
    if not conn_lc:
        raise HTTPException(status_code=503, detail="Nœud ligne_commandes indisponible")

    info_lc  = cluster_manager.get_node_for_entity("ligne_commandes")
    info_art = cluster_manager.get_node_for_entity("articles")

    totals: Dict[int, int] = {}
    for k in redis_manager.get_all_keys(conn_lc, "ligne_commande:*"):
        ligne = redis_manager.get(conn_lc, k)
        if ligne and ligne.get("no_article") is not None:
            no_art = ligne["no_article"]
            totals[no_art] = totals.get(no_art, 0) + (ligne.get("quantite") or 0)

    results = []
    for no_art, total_qt in sorted(totals.items(), key=lambda x: -x[1]):
        article = redis_manager.get(conn_art, f"article:{no_art}") if conn_art else None
        results.append({
            "no_article":              no_art,
            "article":                 article,
            "total_quantite_commandee": total_qt,
        })

    sources: Dict[str, str] = {"ligne_commandes": info_lc.node_id if info_lc else "?"}
    if info_art:
        sources["articles"] = info_art.node_id

    return {
        "results": results,
        "_node_sources": sources,
        "_description": "GROUP BY simulé : agrégation cross-nœuds — quantité commandée par article",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT CRUD
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/clients", response_model=OperationStatus, tags=["Clients"])
async def create_client(client: Client):
    node = redis_manager.get_node_for_entity("clients")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for clients")
    key = f"client:{client.no_client}"
    if redis_manager.exists(node, key):
        raise HTTPException(status_code=409, detail=f"Client {client.no_client} already exists")
    if redis_manager.set(node, key, client.model_dump()):
        return OperationStatus(success=True, message=f"Client {client.no_client} created",
                               data={"no_client": client.no_client})
    raise HTTPException(status_code=500, detail="Failed to create client")


@app.get("/clients/{no_client}", response_model=ClientResponse, tags=["Clients"])
async def get_client(no_client: int):
    node = redis_manager.get_node_for_entity("clients")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for clients")
    data = redis_manager.get(node, f"client:{no_client}")
    if not data:
        raise HTTPException(status_code=404, detail=f"Client {no_client} not found")
    return ClientResponse(**data)


@app.get("/clients", response_model=List[ClientResponse], tags=["Clients"])
async def list_clients():
    node = redis_manager.get_node_for_entity("clients")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for clients")
    return [
        ClientResponse(**redis_manager.get(node, k))
        for k in redis_manager.get_all_keys(node, "client:*")
        if redis_manager.get(node, k)
    ]


@app.put("/clients/{no_client}", response_model=OperationStatus, tags=["Clients"])
async def update_client(no_client: int, client: Client):
    if client.no_client != no_client:
        raise HTTPException(status_code=400, detail="Client ID mismatch")
    node = redis_manager.get_node_for_entity("clients")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for clients")
    key = f"client:{no_client}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail=f"Client {no_client} not found")
    if redis_manager.set(node, key, client.model_dump()):
        return OperationStatus(success=True, message=f"Client {no_client} updated")
    raise HTTPException(status_code=500, detail="Failed to update client")


@app.delete("/clients/{no_client}", response_model=OperationStatus, tags=["Clients"])
async def delete_client(no_client: int):
    node = redis_manager.get_node_for_entity("clients")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for clients")
    key = f"client:{no_client}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail=f"Client {no_client} not found")
    if redis_manager.delete(node, key):
        return OperationStatus(success=True, message=f"Client {no_client} deleted")
    raise HTTPException(status_code=500, detail="Failed to delete client")


# ══════════════════════════════════════════════════════════════════════════════
#  ARTICLE CRUD
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/articles", response_model=OperationStatus, tags=["Articles"])
async def create_article(article: Article):
    node = redis_manager.get_node_for_entity("articles")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for articles")
    key = f"article:{article.no_article}"
    if redis_manager.exists(node, key):
        raise HTTPException(status_code=409, detail=f"Article {article.no_article} already exists")
    if redis_manager.set(node, key, article.model_dump()):
        return OperationStatus(success=True, message=f"Article {article.no_article} created",
                               data={"no_article": article.no_article})
    raise HTTPException(status_code=500, detail="Failed to create article")


@app.get("/articles/{no_article}", response_model=ArticleResponse, tags=["Articles"])
async def get_article(no_article: int):
    node = redis_manager.get_node_for_entity("articles")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for articles")
    data = redis_manager.get(node, f"article:{no_article}")
    if not data:
        raise HTTPException(status_code=404, detail=f"Article {no_article} not found")
    return ArticleResponse(**data)


@app.get("/articles", response_model=List[ArticleResponse], tags=["Articles"])
async def list_articles():
    node = redis_manager.get_node_for_entity("articles")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for articles")
    return [
        ArticleResponse(**redis_manager.get(node, k))
        for k in redis_manager.get_all_keys(node, "article:*")
        if redis_manager.get(node, k)
    ]


@app.put("/articles/{no_article}", response_model=OperationStatus, tags=["Articles"])
async def update_article(no_article: int, article: Article):
    if article.no_article != no_article:
        raise HTTPException(status_code=400, detail="Article ID mismatch")
    node = redis_manager.get_node_for_entity("articles")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for articles")
    key = f"article:{no_article}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail=f"Article {no_article} not found")
    if redis_manager.set(node, key, article.model_dump()):
        return OperationStatus(success=True, message=f"Article {no_article} updated")
    raise HTTPException(status_code=500, detail="Failed to update article")


@app.delete("/articles/{no_article}", response_model=OperationStatus, tags=["Articles"])
async def delete_article(no_article: int):
    node = redis_manager.get_node_for_entity("articles")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for articles")
    key = f"article:{no_article}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail=f"Article {no_article} not found")
    if redis_manager.delete(node, key):
        return OperationStatus(success=True, message=f"Article {no_article} deleted")
    raise HTTPException(status_code=500, detail="Failed to delete article")


# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDE CRUD
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/commandes", response_model=OperationStatus, tags=["Commandes"])
async def create_commande(commande: Commande):
    node = redis_manager.get_node_for_entity("commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for commandes")
    key = f"commande:{commande.no_commande}"
    if redis_manager.exists(node, key):
        raise HTTPException(status_code=409, detail=f"Commande {commande.no_commande} already exists")
    if redis_manager.set(node, key, commande.model_dump(mode="json")):
        return OperationStatus(success=True, message=f"Commande {commande.no_commande} created",
                               data={"no_commande": commande.no_commande})
    raise HTTPException(status_code=500, detail="Failed to create commande")


@app.get("/commandes/{no_commande}", response_model=CommandeResponse, tags=["Commandes"])
async def get_commande(no_commande: int):
    node = redis_manager.get_node_for_entity("commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for commandes")
    data = redis_manager.get(node, f"commande:{no_commande}")
    if not data:
        raise HTTPException(status_code=404, detail=f"Commande {no_commande} not found")
    return CommandeResponse(**data)


@app.get("/commandes", response_model=List[CommandeResponse], tags=["Commandes"])
async def list_commandes():
    node = redis_manager.get_node_for_entity("commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for commandes")
    return [
        CommandeResponse(**redis_manager.get(node, k))
        for k in redis_manager.get_all_keys(node, "commande:*")
        if redis_manager.get(node, k)
    ]


@app.put("/commandes/{no_commande}", response_model=OperationStatus, tags=["Commandes"])
async def update_commande(no_commande: int, commande: Commande):
    if commande.no_commande != no_commande:
        raise HTTPException(status_code=400, detail="Commande ID mismatch")
    node = redis_manager.get_node_for_entity("commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for commandes")
    key = f"commande:{no_commande}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail=f"Commande {no_commande} not found")
    if redis_manager.set(node, key, commande.model_dump(mode="json")):
        return OperationStatus(success=True, message=f"Commande {no_commande} updated")
    raise HTTPException(status_code=500, detail="Failed to update commande")


@app.delete("/commandes/{no_commande}", response_model=OperationStatus, tags=["Commandes"])
async def delete_commande(no_commande: int):
    node = redis_manager.get_node_for_entity("commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for commandes")
    key = f"commande:{no_commande}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail=f"Commande {no_commande} not found")
    if redis_manager.delete(node, key):
        return OperationStatus(success=True, message=f"Commande {no_commande} deleted")
    raise HTTPException(status_code=500, detail="Failed to delete commande")


# ══════════════════════════════════════════════════════════════════════════════
#  LIGNE COMMANDE CRUD
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/ligne-commandes", response_model=OperationStatus, tags=["Ligne Commandes"])
async def create_ligne_commande(ligne: LigneCommande):
    node = redis_manager.get_node_for_entity("ligne_commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for ligne_commandes")
    key = f"ligne_commande:{ligne.no_commande}:{ligne.no_article}"
    if redis_manager.exists(node, key):
        raise HTTPException(status_code=409, detail="Ligne commande already exists")
    if redis_manager.set(node, key, ligne.model_dump()):
        return OperationStatus(success=True, message="Ligne commande created",
                               data={"no_commande": ligne.no_commande, "no_article": ligne.no_article})
    raise HTTPException(status_code=500, detail="Failed to create ligne commande")


@app.get("/ligne-commandes/{no_commande}/{no_article}",
         response_model=LigneCommandeResponse, tags=["Ligne Commandes"])
async def get_ligne_commande(no_commande: int, no_article: int):
    node = redis_manager.get_node_for_entity("ligne_commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for ligne_commandes")
    data = redis_manager.get(node, f"ligne_commande:{no_commande}:{no_article}")
    if not data:
        raise HTTPException(status_code=404, detail="Ligne commande not found")
    return LigneCommandeResponse(**data)


@app.get("/ligne-commandes", response_model=List[LigneCommandeResponse], tags=["Ligne Commandes"])
async def list_ligne_commandes():
    node = redis_manager.get_node_for_entity("ligne_commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for ligne_commandes")
    return [
        LigneCommandeResponse(**redis_manager.get(node, k))
        for k in redis_manager.get_all_keys(node, "ligne_commande:*")
        if redis_manager.get(node, k)
    ]


@app.put("/ligne-commandes/{no_commande}/{no_article}",
         response_model=OperationStatus, tags=["Ligne Commandes"])
async def update_ligne_commande(no_commande: int, no_article: int, ligne: LigneCommande):
    if ligne.no_commande != no_commande or ligne.no_article != no_article:
        raise HTTPException(status_code=400, detail="ID mismatch")
    node = redis_manager.get_node_for_entity("ligne_commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for ligne_commandes")
    key = f"ligne_commande:{no_commande}:{no_article}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail="Ligne commande not found")
    if redis_manager.set(node, key, ligne.model_dump()):
        return OperationStatus(success=True, message="Ligne commande updated")
    raise HTTPException(status_code=500, detail="Failed to update ligne commande")


@app.delete("/ligne-commandes/{no_commande}/{no_article}",
            response_model=OperationStatus, tags=["Ligne Commandes"])
async def delete_ligne_commande(no_commande: int, no_article: int):
    node = redis_manager.get_node_for_entity("ligne_commandes")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for ligne_commandes")
    key = f"ligne_commande:{no_commande}:{no_article}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail="Ligne commande not found")
    if redis_manager.delete(node, key):
        return OperationStatus(success=True, message="Ligne commande deleted")
    raise HTTPException(status_code=500, detail="Failed to delete ligne commande")


# ══════════════════════════════════════════════════════════════════════════════
#  LIVRAISON CRUD
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/livraisons", response_model=OperationStatus, tags=["Livraisons"])
async def create_livraison(livraison: Livraison):
    node = redis_manager.get_node_for_entity("livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for livraisons")
    key = f"livraison:{livraison.no_livraison}"
    if redis_manager.exists(node, key):
        raise HTTPException(status_code=409, detail=f"Livraison {livraison.no_livraison} already exists")
    if redis_manager.set(node, key, livraison.model_dump(mode="json")):
        return OperationStatus(success=True, message=f"Livraison {livraison.no_livraison} created",
                               data={"no_livraison": livraison.no_livraison})
    raise HTTPException(status_code=500, detail="Failed to create livraison")


@app.get("/livraisons/{no_livraison}", response_model=LivraisonResponse, tags=["Livraisons"])
async def get_livraison(no_livraison: int):
    node = redis_manager.get_node_for_entity("livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for livraisons")
    data = redis_manager.get(node, f"livraison:{no_livraison}")
    if not data:
        raise HTTPException(status_code=404, detail=f"Livraison {no_livraison} not found")
    return LivraisonResponse(**data)


@app.get("/livraisons", response_model=List[LivraisonResponse], tags=["Livraisons"])
async def list_livraisons():
    node = redis_manager.get_node_for_entity("livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for livraisons")
    return [
        LivraisonResponse(**redis_manager.get(node, k))
        for k in redis_manager.get_all_keys(node, "livraison:*")
        if redis_manager.get(node, k)
    ]


@app.put("/livraisons/{no_livraison}", response_model=OperationStatus, tags=["Livraisons"])
async def update_livraison(no_livraison: int, livraison: Livraison):
    if livraison.no_livraison != no_livraison:
        raise HTTPException(status_code=400, detail="Livraison ID mismatch")
    node = redis_manager.get_node_for_entity("livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for livraisons")
    key = f"livraison:{no_livraison}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail=f"Livraison {no_livraison} not found")
    if redis_manager.set(node, key, livraison.model_dump(mode="json")):
        return OperationStatus(success=True, message=f"Livraison {no_livraison} updated")
    raise HTTPException(status_code=500, detail="Failed to update livraison")


@app.delete("/livraisons/{no_livraison}", response_model=OperationStatus, tags=["Livraisons"])
async def delete_livraison(no_livraison: int):
    node = redis_manager.get_node_for_entity("livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for livraisons")
    key = f"livraison:{no_livraison}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail=f"Livraison {no_livraison} not found")
    if redis_manager.delete(node, key):
        return OperationStatus(success=True, message=f"Livraison {no_livraison} deleted")
    raise HTTPException(status_code=500, detail="Failed to delete livraison")


# ══════════════════════════════════════════════════════════════════════════════
#  DETAIL LIVRAISON CRUD
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/detail-livraisons", response_model=OperationStatus, tags=["Detail Livraisons"])
async def create_detail_livraison(detail: DetailLivraison):
    node = redis_manager.get_node_for_entity("detail_livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for detail_livraisons")
    key = f"detail_livraison:{detail.no_livraison}:{detail.no_commande}:{detail.no_article}"
    if redis_manager.exists(node, key):
        raise HTTPException(status_code=409, detail="Detail livraison already exists")
    if redis_manager.set(node, key, detail.model_dump()):
        return OperationStatus(success=True, message="Detail livraison created",
                               data={"no_livraison": detail.no_livraison,
                                     "no_commande": detail.no_commande,
                                     "no_article": detail.no_article})
    raise HTTPException(status_code=500, detail="Failed to create detail livraison")


@app.get("/detail-livraisons/{no_livraison}/{no_commande}/{no_article}",
         response_model=DetailLivraisonResponse, tags=["Detail Livraisons"])
async def get_detail_livraison(no_livraison: int, no_commande: int, no_article: int):
    node = redis_manager.get_node_for_entity("detail_livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for detail_livraisons")
    data = redis_manager.get(node, f"detail_livraison:{no_livraison}:{no_commande}:{no_article}")
    if not data:
        raise HTTPException(status_code=404, detail="Detail livraison not found")
    return DetailLivraisonResponse(**data)


@app.get("/detail-livraisons", response_model=List[DetailLivraisonResponse], tags=["Detail Livraisons"])
async def list_detail_livraisons():
    node = redis_manager.get_node_for_entity("detail_livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for detail_livraisons")
    return [
        DetailLivraisonResponse(**redis_manager.get(node, k))
        for k in redis_manager.get_all_keys(node, "detail_livraison:*")
        if redis_manager.get(node, k)
    ]


@app.put("/detail-livraisons/{no_livraison}/{no_commande}/{no_article}",
         response_model=OperationStatus, tags=["Detail Livraisons"])
async def update_detail_livraison(no_livraison: int, no_commande: int, no_article: int,
                                  detail: DetailLivraison):
    if (detail.no_livraison != no_livraison or detail.no_commande != no_commande
            or detail.no_article != no_article):
        raise HTTPException(status_code=400, detail="ID mismatch")
    node = redis_manager.get_node_for_entity("detail_livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for detail_livraisons")
    key = f"detail_livraison:{no_livraison}:{no_commande}:{no_article}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail="Detail livraison not found")
    if redis_manager.set(node, key, detail.model_dump()):
        return OperationStatus(success=True, message="Detail livraison updated")
    raise HTTPException(status_code=500, detail="Failed to update detail livraison")


@app.delete("/detail-livraisons/{no_livraison}/{no_commande}/{no_article}",
            response_model=OperationStatus, tags=["Detail Livraisons"])
async def delete_detail_livraison(no_livraison: int, no_commande: int, no_article: int):
    node = redis_manager.get_node_for_entity("detail_livraisons")
    if not node:
        raise HTTPException(status_code=503, detail="No node available for detail_livraisons")
    key = f"detail_livraison:{no_livraison}:{no_commande}:{no_article}"
    if not redis_manager.exists(node, key):
        raise HTTPException(status_code=404, detail="Detail livraison not found")
    if redis_manager.delete(node, key):
        return OperationStatus(success=True, message="Detail livraison deleted")
    raise HTTPException(status_code=500, detail="Failed to delete detail livraison")


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#  DISTRIBUTED QUERIES — Simulated JOIN and GROUP BY
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/query/join/commande/{no_commande}", tags=["Requêtes Distribuées"])
async def join_commande(no_commande: int):
    """
    Simulated JOIN — assembles a full order from multiple Redis nodes.

    Joins: Commande (node A) + Client (node B) + LigneCommandes (node C) + Articles (node D).
    Each piece of data may come from a different physical machine.
    """
    sources: dict = {}

    conn_cmd = redis_manager.get_node_for_entity("commandes")
    if not conn_cmd:
        raise HTTPException(status_code=503, detail="Node for commandes unavailable")
    node_cmd = cluster_manager.get_node_for_entity("commandes")
    commande = redis_manager.get(conn_cmd, f"commande:{no_commande}")
    if not commande:
        raise HTTPException(status_code=404, detail=f"Commande {no_commande} not found")
    sources["commandes"] = node_cmd.node_id if node_cmd else "unknown"

    client = None
    conn_cli = redis_manager.get_node_for_entity("clients")
    node_cli = cluster_manager.get_node_for_entity("clients")
    if conn_cli and commande.get("no_client"):
        client = redis_manager.get(conn_cli, f"client:{commande['no_client']}")
        sources["clients"] = node_cli.node_id if node_cli else "unknown"

    conn_lc = redis_manager.get_node_for_entity("ligne_commandes")
    node_lc = cluster_manager.get_node_for_entity("ligne_commandes")
    lignes_raw = []
    if conn_lc:
        keys = redis_manager.get_all_keys(conn_lc, f"ligne_commande:{no_commande}:*")
        for k in keys:
            d = redis_manager.get(conn_lc, k)
            if d:
                lignes_raw.append(d)
        sources["ligne_commandes"] = node_lc.node_id if node_lc else "unknown"

    conn_art = redis_manager.get_node_for_entity("articles")
    node_art = cluster_manager.get_node_for_entity("articles")
    lignes_enriched = []
    for ligne in lignes_raw:
        article = None
        if conn_art and ligne.get("no_article"):
            article = redis_manager.get(conn_art, f"article:{ligne['no_article']}")
            sources["articles"] = node_art.node_id if node_art else "unknown"
        lignes_enriched.append({**ligne, "article": article})

    return {
        "commande": commande,
        "client": client,
        "lignes": lignes_enriched,
        "_node_sources": sources,
        "_note": "Data aggregated from multiple distributed Redis nodes — simulating a SQL JOIN",
    }


@app.get("/query/groupby/commandes-par-client", tags=["Requêtes Distribuées"])
async def groupby_commandes_par_client():
    """
    Simulated GROUP BY — order count and list per client.

    Reads Clients (node A) + Commandes (node B), aggregates in Python.
    """
    conn_cli = redis_manager.get_node_for_entity("clients")
    conn_cmd = redis_manager.get_node_for_entity("commandes")
    node_cli = cluster_manager.get_node_for_entity("clients")
    node_cmd = cluster_manager.get_node_for_entity("commandes")

    if not conn_cli or not conn_cmd:
        raise HTTPException(status_code=503, detail="Clients or commandes node unavailable")

    clients = {}
    for k in redis_manager.get_all_keys(conn_cli, "client:*"):
        d = redis_manager.get(conn_cli, k)
        if d:
            clients[d["no_client"]] = d

    groups: Dict[int, List[int]] = {c: [] for c in clients}
    for k in redis_manager.get_all_keys(conn_cmd, "commande:*"):
        cmd = redis_manager.get(conn_cmd, k)
        if cmd and cmd.get("no_client") in groups:
            groups[cmd["no_client"]].append(cmd["no_commande"])

    return {
        "results": [
            {
                "client": clients[c],
                "nb_commandes": len(cmds),
                "commandes": sorted(cmds),
            }
            for c, cmds in groups.items()
        ],
        "_node_sources": {
            "clients": node_cli.node_id if node_cli else "unknown",
            "commandes": node_cmd.node_id if node_cmd else "unknown",
        },
        "_note": "GROUP BY client — cross-node aggregation, no SQL needed",
    }


@app.get("/query/groupby/quantite-par-article", tags=["Requêtes Distribuées"])
async def groupby_quantite_par_article():
    """
    Simulated GROUP BY — total quantity ordered per article.

    Reads LigneCommandes (node A) + Articles (node B), aggregates in Python.
    """
    conn_lc  = redis_manager.get_node_for_entity("ligne_commandes")
    conn_art = redis_manager.get_node_for_entity("articles")
    node_lc  = cluster_manager.get_node_for_entity("ligne_commandes")
    node_art = cluster_manager.get_node_for_entity("articles")

    if not conn_lc:
        raise HTTPException(status_code=503, detail="Node for ligne_commandes unavailable")

    totals: Dict[int, int] = {}
    for k in redis_manager.get_all_keys(conn_lc, "ligne_commande:*"):
        ligne = redis_manager.get(conn_lc, k)
        if ligne and ligne.get("no_article") is not None:
            no_art = ligne["no_article"]
            totals[no_art] = totals.get(no_art, 0) + (ligne.get("quantite") or 0)

    results = []
    for no_art, total_qt in sorted(totals.items(), key=lambda x: -x[1]):
        article = redis_manager.get(conn_art, f"article:{no_art}") if conn_art else None
        results.append({
            "no_article": no_art,
            "article": article,
            "total_quantite_commandee": total_qt,
        })

    sources: dict = {}
    if node_lc:
        sources["ligne_commandes"] = node_lc.node_id
    if node_art:
        sources["articles"] = node_art.node_id

    return {
        "results": results,
        "_node_sources": sources,
        "_note": "GROUP BY article on ordered quantities — cross-node aggregation",
    }


@app.get("/query/entity-distribution", tags=["Requêtes Distribuées"])
async def entity_distribution():
    """Shows which physical machine (Redis node) stores each entity type."""
    topo = cluster_manager.get_topology()
    nodes_info = {n.node_id: n for n in cluster_manager.get_all_nodes()}
    result = {}
    for entity, node_id in topo["entity_distribution"].items():
        node = nodes_info.get(node_id)
        result[entity] = {
            "node_id": node_id,
            "host": node.host if node else "?",
            "port": node.port if node else 0,
            "role": node.role if node else "?",
            "status": node.status if node else "?",
        }
    return {
        "entity_distribution": result,
        "explanation": (
            "Each entity type is stored on a different Redis node. "
            "Writing /clients goes to the 'clients' node; reading /articles "
            "comes from the 'articles' node. When nodes are on different "
            "physical machines, reads and writes cross the network."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  REPLICATION — Write on master, read from replica
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/cluster/replication/setup", tags=["Réplication"])
async def setup_replication(body: ReplicationSetup):
    """
    **Configure Redis replication** — sends `REPLICAOF <master_host> <master_port>`
    to the replica node so it mirrors all data from the master in real time.

    After calling this, any key written to the master will be readable from the
    replica within milliseconds.  Use `/demo/replication/{master_id}` to verify.
    """
    try:
        result = cluster_manager.setup_replication_pair(body.master_id, body.replica_id)
        return result
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.delete("/cluster/replication/{replica_id}", tags=["Réplication"])
async def stop_replication(replica_id: str):
    """
    **Stop replication** — sends `REPLICAOF NO ONE` to the replica, making it
    an independent Redis instance again.  Its data is retained.
    """
    try:
        return cluster_manager.stop_replication(replica_id)
    except (KeyError, ConnectionError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/cluster/replication/status", tags=["Réplication"])
async def replication_status():
    """
    **Replication status** — calls `INFO replication` on every cluster node and
    returns offsets, link status, and lag for each master/replica pair.
    """
    return {"nodes": cluster_manager.get_replication_status()}


@app.get("/demo/replication/{master_id}", tags=["Réplication"])
async def demo_replication(master_id: str):
    """
    **Live replication demo** — writes a timestamped key to the master node,
    waits up to 500 ms, then reads the same key from the configured replica.

    Returns `replication_ok: true` when the replica successfully mirrored the
    write — proving that data written on one machine can be read from another.

    **Prerequisite:** call `POST /cluster/replication/setup` first.
    """
    try:
        return cluster_manager.replication_write_read_demo(master_id)
    except (KeyError, ConnectionError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
