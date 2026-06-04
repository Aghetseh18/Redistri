export type NodeRole = "master" | "replica";
export type NodeStatus = "healthy" | "degraded" | "failed" | "joining";

export interface NodeMetrics {
  redis_version?: string;
  uptime_seconds?: number;
  connected_clients?: number;
  used_memory_human?: string;
  used_memory_peak_human?: string;
  total_commands?: number;
  ops_per_sec?: number;
  keyspace_hits?: number;
  keyspace_misses?: number;
  db_size?: number;
  redis_role?: string;
}

export interface NodeInfo {
  node_id: string;
  host: string;
  port: number;
  role: NodeRole;
  status: NodeStatus;
  priority: number;
  last_seen: number;
  entities: string[];
  replica_of: string | null;
  metrics: NodeMetrics;
  master?: NodeInfo;
  repl: NodeInfo[];
}

export interface ClusterTopology {
  master_id: string | null;
  total_nodes: number;
  healthy_nodes: number;
  degraded_nodes: number;
  failed_nodes: number;
  entity_distribution: Record<string, string>;
  nodes: NodeInfo[];
}

export interface ClusterEvent {
  event: string;
  data: Record<string, unknown>;
  timestamp: number;
}

// ── Domain entities ───────────────────────────────────────────────────────────

export interface Client {
  no_client: number;
  nom_client: string;
  no_telephone: string;
}

export interface Article {
  no_article: number;
  description: string;
  prix_unitaire: number;
  quantite_en_stock: number;
}

export interface Commande {
  no_commande: number;
  date_commande: string;
  no_client: number;
}

export interface LigneCommande {
  no_commande: number;
  no_article: number;
  quantite: number;
}

export interface Livraison {
  no_livraison: number;
  date_livraison: string;
}

export interface DetailLivraison {
  no_livraison: number;
  no_commande: number;
  no_article: number;
  quantite_livree: number;
}

export interface OperationStatus {
  success: boolean;
  message: string;
  timestamp: string;
  data?: Record<string, unknown>;
}
