"""
Pydantic models — domain entities + cluster management.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
#  Domain entities
# ══════════════════════════════════════════════════════════════════════════════

class Client(BaseModel):
    no_client:    int = Field(..., description="Client ID")
    nom_client:   str = Field(..., description="Client name")
    no_telephone: str = Field(..., description="Phone number")

    model_config = {
        "json_schema_extra": {
            "example": {
                "no_client":    10,
                "nom_client":   "Luc Sansom",
                "no_telephone": "(999)999-9999",
            }
        }
    }


class Article(BaseModel):
    no_article:         int   = Field(..., description="Article ID")
    description:        str   = Field(..., description="Description")
    prix_unitaire:      float = Field(..., description="Unit price")
    quantite_en_stock:  int   = Field(default=0, description="Stock quantity")

    model_config = {
        "json_schema_extra": {
            "example": {
                "no_article":        10,
                "description":       "Cèdre en boule",
                "prix_unitaire":     10.99,
                "quantite_en_stock": 10,
            }
        }
    }


class Commande(BaseModel):
    no_commande:    int  = Field(..., description="Order ID")
    date_commande:  date = Field(..., description="Order date")
    no_client:      int  = Field(..., description="Client ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "no_commande":   1,
                "date_commande": "2000-06-01",
                "no_client":     10,
            }
        }
    }


class LigneCommande(BaseModel):
    no_commande: int = Field(..., description="Order ID")
    no_article:  int = Field(..., description="Article ID")
    quantite:    int = Field(..., gt=0, description="Quantity ordered")

    model_config = {
        "json_schema_extra": {
            "example": {"no_commande": 1, "no_article": 10, "quantite": 10}
        }
    }


class Livraison(BaseModel):
    no_livraison:   int  = Field(..., description="Delivery ID")
    date_livraison: date = Field(..., description="Delivery date")

    model_config = {
        "json_schema_extra": {
            "example": {"no_livraison": 100, "date_livraison": "2000-06-03"}
        }
    }


class DetailLivraison(BaseModel):
    no_livraison:    int = Field(..., description="Delivery ID")
    no_commande:     int = Field(..., description="Order ID")
    no_article:      int = Field(..., description="Article ID")
    quantite_livree: int = Field(..., gt=0, description="Quantity delivered")

    model_config = {
        "json_schema_extra": {
            "example": {
                "no_livraison":    100,
                "no_commande":     1,
                "no_article":      10,
                "quantite_livree": 7,
            }
        }
    }


# Response aliases (kept for API compatibility)
class ClientResponse(Client):        pass
class ArticleResponse(Article):      pass
class CommandeResponse(Commande):    pass
class LigneCommandeResponse(LigneCommande): pass
class LivraisonResponse(Livraison):  pass
class DetailLivraisonResponse(DetailLivraison): pass


# Bulk-create helpers
class BulkClientCreate(BaseModel):
    clients: List[Client]

class BulkArticleCreate(BaseModel):
    articles: List[Article]

class BulkCommandeCreate(BaseModel):
    commandes: List[Commande]


# ══════════════════════════════════════════════════════════════════════════════
#  Generic operation responses
# ══════════════════════════════════════════════════════════════════════════════

class OperationStatus(BaseModel):
    success:   bool
    message:   str
    timestamp: datetime = Field(default_factory=datetime.now)
    data:      Optional[dict] = None


class HealthStatus(BaseModel):
    """Per-node health snapshot (used by /health and /nodes/status)."""
    node_id:         str
    role:            str
    status:          str
    is_connected:    bool
    response_time_ms: float
    entities:        List[str] = []
    info:            Optional[dict] = None


# ══════════════════════════════════════════════════════════════════════════════
#  Cluster management models
# ══════════════════════════════════════════════════════════════════════════════

class NodeRegistration(BaseModel):
    """Body for POST /cluster/nodes — register a new Redis instance."""
    host:     str = Field(..., description="Redis host (IP or hostname)")
    port:     int = Field(..., ge=1, le=65535, description="Redis port")
    priority: Optional[int] = Field(
        None,
        ge=0,
        description="Election priority: lower number → preferred as master. "
                    "Auto-assigned if omitted.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {"host": "192.168.1.101", "port": 6379, "priority": 20}
        }
    }


class SubnetScanRequest(BaseModel):
    """Body for POST /cluster/scan — auto-discover Redis on a subnet."""
    subnet: str = Field(..., description="Network prefix, e.g. '192.168.1'")
    port:   int = Field(default=6379, ge=1, le=65535)
    start:  int = Field(default=1,   ge=1,  le=254, description="First host octet")
    end:    int = Field(default=254, ge=1,  le=254, description="Last host octet")

    model_config = {
        "json_schema_extra": {
            "example": {"subnet": "192.168.1", "port": 6379, "start": 100, "end": 110}
        }
    }


class NodeMetrics(BaseModel):
    """Detailed metrics for one node."""
    node_id:                  str
    role:                     str
    status:                   str
    priority:                 int
    entities:                 List[str]
    redis_version:            Optional[str]   = None
    uptime_seconds:           Optional[int]   = None
    connected_clients:        Optional[int]   = None
    used_memory_human:        Optional[str]   = None
    used_memory_peak_human:   Optional[str]   = None
    total_commands:           Optional[int]   = None
    ops_per_sec:              Optional[int]   = None
    keyspace_hits:            Optional[int]   = None
    keyspace_misses:          Optional[int]   = None
    db_size:                  Optional[int]   = None


class ClusterTopologyResponse(BaseModel):
    """Full cluster topology snapshot."""
    master_id:           Optional[str]
    total_nodes:         int
    healthy_nodes:       int
    degraded_nodes:      int
    failed_nodes:        int
    entity_distribution: Dict[str, str]       # entity_type → node_id
    nodes:               List[Dict[str, Any]]


class ClusterEventMessage(BaseModel):
    """Shape of messages pushed over the WebSocket monitor stream."""
    event:     str
    data:      Dict[str, Any]
    timestamp: float


class ReplicationSetup(BaseModel):
    """Body for POST /cluster/replication/setup."""
    master_id:  str = Field(..., description="node_id of the master, e.g. 'localhost:6379'")
    replica_id: str = Field(..., description="node_id of the replica, e.g. '10.108.135.244:7001'")

    model_config = {
        "json_schema_extra": {
            "example": {
                "master_id":  "localhost:6379",
                "replica_id": "10.108.135.244:7001",
            }
        }
    }
