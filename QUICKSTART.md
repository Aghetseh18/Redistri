# Quick Start Guide

## Architecture

```
This Machine (Master Node)
├── Redis Server (Master) → Port 6379
└── FastAPI Application → Port 8000

Ubuntu Servers (5 Slave Nodes)
├── Ubuntu Machine 1 → Redis at 192.168.1.101:6379
├── Ubuntu Machine 2 → Redis at 192.168.1.102:6379
├── Ubuntu Machine 3 → Redis at 192.168.1.103:6379
├── Ubuntu Machine 4 → Redis at 192.168.1.104:6379
└── Ubuntu Machine 5 → Redis at 192.168.1.105:6379
```

## Fast Setup (5 minutes)

### Prerequisites
- **This Machine**: Redis Server + Python 3.8+
- **5 Ubuntu Servers**: Redis Server on each at 192.168.1.101-105

### Step 1: Install Redis on This Machine

**Windows with Docker (Recommended):**
```bash
docker run -d -p 6379:6379 --name redis-master redis:7-alpine
```

**Or download native Redis for Windows:**
https://github.com/microsoftarchive/redis/releases

**Verify Redis is running:**
```bash
redis-cli ping
```
Should return: `PONG`

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Start the FastAPI Application
```bash
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Verify Connection to All Redis Nodes
```bash
curl http://localhost:8000/nodes/status
```

This shows:
- Master node: localhost (this machine) ✓
- 5 Slave nodes: 192.168.1.101-105 ✓

### Step 5: Load Sample Data (Optional)
In another terminal:
```bash
python test_data.py
```

---

## Entity Storage Distribution

| Entity | Location | Notes |
|--------|----------|-------|
| **Clients** | Master (This Machine) | Fast local access |
| **Articles** | Master (This Machine) | Fast local access |
| **Commandes** | Ubuntu 1 (192.168.1.101) | Remote storage |
| **Ligne Commandes** | Ubuntu 2 (192.168.1.102) | Remote storage |
| **Livraisons** | Ubuntu 3 (192.168.1.103) | Remote storage |
| **Detail Livraisons** | Ubuntu 4 (192.168.1.104) | Remote storage |

---

## API Examples

### Health Check
```bash
curl http://localhost:8000/health
```

### Check Node Status
```bash
curl http://localhost:8000/nodes/status
```

### Create Client (stores on Master)
```bash
curl -X POST http://localhost:8000/clients \
  -H "Content-Type: application/json" \
  -d '{
    "no_client": 100,
    "nom_client": "John Doe",
    "no_telephone": "(123)456-7890"
  }'
```

### Get All Clients
```bash
curl http://localhost:8000/clients
```

### Create Commande (stores on Ubuntu 1)
```bash
curl -X POST http://localhost:8000/commandes \
  -H "Content-Type: application/json" \
  -d '{
    "no_commande": 101,
    "date_commande": "2024-05-23",
    "no_client": 100
  }'
```

### Update Client
```bash
curl -X PUT http://localhost:8000/clients/100 \
  -H "Content-Type: application/json" \
  -d '{
    "no_client": 100,
    "nom_client": "Jane Doe",
    "no_telephone": "(999)999-9999"
  }'
```

### Delete Client
```bash
curl -X DELETE http://localhost:8000/clients/100
```

---

## Configuration

Configuration is in `config.py`. Default setup:

```python
REDIS_NODES = {
    "master": {"host": "localhost", "port": 6379, "db": 0},      # This machine
    "slave1": {"host": "192.168.1.101", "port": 6379, "db": 0},  # Ubuntu 1
    "slave2": {"host": "192.168.1.102", "port": 6379, "db": 0},  # Ubuntu 2
    "slave3": {"host": "192.168.1.103", "port": 6379, "db": 0},  # Ubuntu 3
    "slave4": {"host": "192.168.1.104", "port": 6379, "db": 0},  # Ubuntu 4
    "slave5": {"host": "192.168.1.105", "port": 6379, "db": 0},  # Ubuntu 5
}
```

**If Ubuntu servers use different IPs:**
Edit `config.py` and update the IP addresses.

---

## Troubleshooting

### Master Redis not running
```bash
# Check if Redis is running
redis-cli ping

# Start Redis with Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or with native Redis (Windows)
redis-server
```

### Cannot connect to Ubuntu servers
```bash
# Test connection to Ubuntu 1
redis-cli -h 192.168.1.101 ping

# Should return: PONG
# If fails, ensure:
# 1. Ubuntu machines are on network
# 2. Redis is running: sudo systemctl status redis-server
# 3. Firewall allows port 6379
```

### API shows node unavailable
- Check Ubuntu servers are powered on
- Verify correct IP addresses in `config.py`
- Test with: `curl http://localhost:8000/nodes/status`

### Port 8000 already in use
```bash
# Use different port
python -m uvicorn main:app --port 8001
```

---

## Using Interactive API Docs

1. Open http://localhost:8000/docs
2. Click any endpoint to expand
3. Click "Try it out"
4. Enter data and click "Execute"

---

## CRUD Operations Reference

For any entity:

```bash
# CREATE
POST /{entity}

# READ (list)
GET /{entity}

# READ (one)
GET /{entity}/{id}

# UPDATE
PUT /{entity}/{id}

# DELETE
DELETE /{entity}/{id}
```

---

## Next Steps

1. ✅ Install Redis on this machine
2. ✅ Install Python dependencies: `pip install -r requirements.txt`
3. ✅ Ensure Ubuntu servers have Redis running
4. ✅ Run FastAPI: `python main.py`
5. ✅ Test: `curl http://localhost:8000/health`
6. ✅ Load sample data: `python test_data.py`
7. ✅ Access interactive docs: http://localhost:8000/docs

---

For advanced configuration, see `README.md`
