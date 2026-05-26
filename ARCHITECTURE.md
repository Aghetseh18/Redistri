# Architecture Guide

## System Overview

This is a **distributed Redis-based API system** with:

- **1 Master Node** (this machine) managing clients and articles
- **5 Worker Nodes** (Ubuntu servers) managing orders, deliveries, and related data

```
┌────────────────────────────────────────────────────────────────┐
│                      YOUR MACHINE (Windows/Linux)              │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (http://localhost:8000)           │  │
│  │  - Routes requests to appropriate Redis nodes          │  │
│  │  - Manages CRUD operations across 6 nodes             │  │
│  │  - Provides REST API for clients                       │  │
│  └────────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌────────────────────────▼────────────────────────────────┐  │
│  │  Redis Master Node (localhost:6379)                    │  │
│  │  ├─ Clients    (fast local access)                     │  │
│  │  └─ Articles   (fast local access)                     │  │
│  └────────────────────────┬────────────────────────────────┘  │
│                           │                                   │
│                       Network Interface                       │
└───────────────────────────┼────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
    ┌───▼───┐          ┌───▼───┐          ┌───▼───┐
    │Ubuntu │          │Ubuntu │          │Ubuntu │
    │ Srv 1 │          │ Srv 2 │          │ Srv 3 │
    │.101   │          │.102   │          │.103   │
    ├───────┤          ├───────┤          ├───────┤
    │ Redis │          │ Redis │          │ Redis │
    │       │          │       │          │       │
    │Comman-│          │ Ligne │          │Livrai-│
    │des    │          │Command│          │sons   │
    └───────┘          └───────┘          └───────┘

    ┌───────┐          ┌───────┐
    │Ubuntu │          │Ubuntu │
    │ Srv 4 │          │ Srv 5 │
    │.104   │          │.105   │
    ├───────┤          ├───────┤
    │ Redis │          │ Redis │
    │       │          │       │
    │Detail │          │Reserved
    │Livrai-│          │
    │sons   │          │
    └───────┘          └───────┘
```

## Data Distribution Strategy

The system distributes data across 6 Redis instances for:

- **Load Balancing**: Each node handles ~17% of queries
- **Scalability**: Easy to add more nodes
- **Fault Isolation**: If one node fails, 5 still work
- **Performance**: Faster access to frequently used local data

### Entity-to-Node Mapping

```
┌─────────────────────────┬──────────────────────────┬────────────────┐
│ Entity                  │ Storage Location         │ Access Pattern │
├─────────────────────────┼──────────────────────────┼────────────────┤
│ Clients                 │ Master (localhost)       │ Local (Fast)   │
├─────────────────────────┼──────────────────────────┼────────────────┤
│ Articles                │ Master (localhost)       │ Local (Fast)   │
├─────────────────────────┼──────────────────────────┼────────────────┤
│ Commandes               │ Ubuntu 1 (192.168.1.101) │ Remote         │
├─────────────────────────┼──────────────────────────┼────────────────┤
│ Ligne Commandes         │ Ubuntu 2 (192.168.1.102) │ Remote         │
├─────────────────────────┼──────────────────────────┼────────────────┤
│ Livraisons              │ Ubuntu 3 (192.168.1.103) │ Remote         │
├─────────────────────────┼──────────────────────────┼────────────────┤
│ Detail Livraisons       │ Ubuntu 4 (192.168.1.104) │ Remote         │
└─────────────────────────┴──────────────────────────┴────────────────┘
```

## Request Flow

```
1. Client sends HTTP request
   ↓
2. FastAPI application receives request
   ↓
3. API routes to appropriate Redis node based on entity type
   ↓
4. Redis performs operation (GET, SET, DELETE, etc.)
   ↓
5. Redis returns result to API
   ↓
6. API returns JSON response to client
   ↓
7. Client receives data

Example:
GET /clients/10    →  [Master Node] → Returns client data (fast)
GET /commandes/1   →  [Ubuntu 1]    → Returns order data (network latency)
```

## Component Responsibilities

### FastAPI Application (This Machine)

- Receives HTTP requests from clients
- Routes to appropriate Redis node
- Validates input data
- Returns JSON responses
- Handles errors and edge cases

### Master Redis Node (This Machine)

- Stores frequently accessed data (Clients, Articles)
- Low latency local access
- Can handle ~10,000 ops/sec
- Data stored in memory (fast)

### Worker Redis Nodes (Ubuntu Servers)

- Distributed storage for related order/delivery data
- Each handles ~10,000 ops/sec
- Parallel processing of requests
- Can be scaled independently

## Security Model

```
┌─────────────────┐
│   Client        │
│   Application   │
└────────┬────────┘
         │ HTTP/REST (Port 8000)
         │ Authentication layer (Optional)
         │
┌────────▼────────┐
│   FastAPI API   │──────────── Optional Rate Limiting
└────────┬────────┘
         │ Direct Redis Connection (Port 6379)
         │ Same Machine/Internal Network Only
         │
┌────────▼────────┐
│  Redis Nodes    │ Protected by:
│  (Master + 5x)  │ - Firewall (internal network only)
└─────────────────┘ - No external internet exposure
                     - Optional password protection
```

## Error Handling & Failover

```
Normal Operation:
Request → Redis Node A → Success → Response

If Node A is Down:
Request → Redis Node A (fails)
       → API returns 503 Service Unavailable
       → Client can retry or contact operator

Future Enhancement:
Request → Redis Node A (fails)
       → Automatically retry to Node B
       → Transparent failover (no client sees error)
```

## Scalability Model

### Current Setup (6 Nodes)

```
       Master (2 entities)
       /      \
      /        \
   Clients   Articles

   + 5 Worker Nodes (1 entity each)

Total: ~60,000 operations/second
```

### Add More Entities

```
1. Add Ubuntu server with Redis
2. Update config.py with new IP
3. Assign entity to new node
4. Restart API
```

### Add Replicas for HA

```
Current:  1 Master + 5 Workers
Future:   1 Master + 1 Master Replica
          5 Workers + 5 Worker Replicas

Enables automatic failover
```

## Data Flow Examples

### Create a Client (Stores on Master)

```
POST /clients
{
  "no_client": 100,
  "nom_client": "John Doe",
  "no_telephone": "(123)456-7890"
}
     │
     ├─→ Validate input (Pydantic model)
     │
     ├─→ Get Master Redis node
     │
     ├─→ Store as JSON key:
     │   client:100 = {
     │     "no_client": 100,
     │     "nom_client": "John Doe",
     │     "no_telephone": "(123)456-7890"
     │   }
     │
     └─→ Return 200 OK with status
```

### Create a Commande (Stores on Ubuntu 1)

```
POST /commandes
{
  "no_commande": 1001,
  "date_commande": "2024-05-23",
  "no_client": 100
}
     │
     ├─→ Validate input
     │
     ├─→ Get Ubuntu 1 (192.168.1.101) Redis node
     │
     ├─→ Network call to Ubuntu 1:6379
     │
     ├─→ Store as JSON key:
     │   commande:1001 = {
     │     "no_commande": 1001,
     │     "date_commande": "2024-05-23",
     │     "no_client": 100
     │   }
     │
     └─→ Return 200 OK with status
```

### List All Articles (Reads from Master)

```
GET /articles
     │
     ├─→ Get Master Redis node
     │
     ├─→ Get all keys matching pattern "article:*"
     │
     ├─→ For each key:
     │   ├─ Retrieve JSON value
     │   ├─ Deserialize to Article object
     │   └─ Add to result list
     │
     └─→ Return list of all articles
```

## Performance Characteristics

### Local Operations (Clients, Articles)

- Response time: ~1-5ms
- Throughput: ~10,000 ops/sec
- Reason: Same machine, no network latency

### Remote Operations (Orders, Deliveries)

- Response time: ~5-50ms
- Throughput: ~5,000 ops/sec
- Reason: Network latency to Ubuntu servers

### Bulk Operations

- Can be parallelized across nodes
- Total throughput: Sum of all nodes
- Example: Loading 48 sample records ~200ms

## Future Enhancements

1. **Caching Layer**
   - Add Redis Cache for frequently accessed data
   - Reduce database queries

2. **Replication**
   - Master-slave replication for each node
   - Automatic failover with Sentinel

3. **Clustering**
   - Redis Cluster for automatic sharding
   - No manual entity-to-node mapping

4. **Transactions**
   - Multi-command operations (MULTI/EXEC)
   - ACID guarantees

5. **Pub/Sub**
   - Real-time notifications
   - WebSocket integration

6. **Batch Operations**
   - Bulk import/export
   - Data migration

## Configuration Details

### In `config.py`:

```python
# Node definitions
REDIS_NODES = {
    "master": {"host": "localhost", "port": 6379, "db": 0},
    "slave1": {"host": "192.168.1.101", "port": 6379, "db": 0},
    # ...
}

# Entity-to-node mapping
ENTITY_NODE_MAPPING = {
    "clients": "master",
    "articles": "master",
    "commandes": "slave1",
    # ...
}

# Connection settings
CONNECTION_POOL_SIZE = 10  # Connections per node
```

## Monitoring & Debugging

### Health Check Endpoint

```bash
GET /health
```

Returns status of all 6 nodes

### Node Status Endpoint

```bash
GET /nodes/status
```

Returns detailed info: uptime, memory, connected clients

### Redis CLI Access (Debugging)

```bash
redis-cli                        # Master
redis-cli -h 192.168.1.101      # Ubuntu 1
```

---

For implementation details, see README.md
For setup instructions, see SETUP.md
For quick start, see QUICKSTART.md
