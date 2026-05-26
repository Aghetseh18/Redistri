# Docker Setup Guide (FOR LOCAL TESTING ONLY)

⚠️ **IMPORTANT**: This docker-compose setup is **for local testing only**.

**In Production**:
- Only 1 Redis instance runs on this machine (master)
- The 5 slave/worker nodes run on separate Ubuntu servers at 192.168.1.101-105

This Docker guide is useful for:
- Local development and testing
- Testing without multiple physical machines
- Learning and prototyping

## Prerequisites

- Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop))
- Docker Compose included with Docker Desktop
- At least 2GB RAM available for Docker

## Quick Start with Docker (Local Testing)

### 1. Start All Redis Nodes Locally

From the project directory:

```bash
docker-compose up -d
```

This creates 6 Redis containers for testing (instead of remote Ubuntu servers):
- 1 Master Redis at localhost:6379
- 5 Slave Redis at localhost:6380-6384
- Redis Commander GUI at localhost:8081

### 2. Verify All Containers Running

```bash
docker-compose ps
```

You should see:
- redis-master (port 6379)
- redis-slave1 (port 6380)
- redis-slave2 (port 6381)
- redis-slave3 (port 6382)
- redis-slave4 (port 6383)
- redis-slave5 (port 6384)
- redis-commander (port 8081)

### 3. Access Docker Redis Nodes

**Master Node**:
```bash
redis-cli -h localhost -p 6379 ping
```

**Slave Nodes**:
```bash
redis-cli -h localhost -p 6380 ping    # Slave 1
redis-cli -h localhost -p 6381 ping    # Slave 2
# ... etc
```

### 4. Access Redis Commander GUI

Open in browser: **http://localhost:8081**

### 5. Configure FastAPI for Local Testing

Edit `config.py` and change the Redis nodes to localhost with Docker ports:

```python
REDIS_NODES = {
    "master": {
        "host": "localhost",
        "port": 6379,  # Docker mapped port
        "db": 0,
    },
    "slave1": {
        "host": "localhost",
        "port": 6380,  # Docker mapped port
        "db": 0,
    },
    "slave2": {
        "host": "localhost",
        "port": 6381,  # Docker mapped port
        "db": 0,
    },
    "slave3": {
        "host": "localhost",
        "port": 6382,  # Docker mapped port
        "db": 0,
    },
    "slave4": {
        "host": "localhost",
        "port": 6383,  # Docker mapped port
        "db": 0,
    },
    "slave5": {
        "host": "localhost",
        "port": 6384,  # Docker mapped port
        "db": 0,
    },
}
```

### 6. Run FastAPI

```bash
python main.py
```

Then test at: http://localhost:8000/docs

---

## Production Setup (Real Ubuntu Servers)

When deploying to production:

### 1. Stop Docker (testing is done)

```bash
docker-compose down
```

### 2. Restore `config.py` to Production Settings

```python
REDIS_NODES = {
    "master": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
    },
    "slave1": {
        "host": "192.168.1.101",  # Real Ubuntu server IP
        "port": 6379,
        "db": 0,
    },
    "slave2": {
        "host": "192.168.1.102",  # Real Ubuntu server IP
        "port": 6379,
        "db": 0,
    },
    "slave3": {
        "host": "192.168.1.103",  # Real Ubuntu server IP
        "port": 6379,
        "db": 0,
    },
    "slave4": {
        "host": "192.168.1.104",  # Real Ubuntu server IP
        "port": 6379,
        "db": 0,
    },
    "slave5": {
        "host": "192.168.1.105",  # Real Ubuntu server IP
        "port": 6379,
        "db": 0,
    },
}
```

### 3. Ensure Production Servers Have Redis

On this machine (master):
```bash
# Windows: Install native Redis or use WSL
# Or: docker run -d -p 6379:6379 redis:7-alpine
```

On Ubuntu machines (slaves):
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server  # Auto-start on reboot
```

### 4. Run FastAPI (Production)

```bash
python main.py
```

---

## Useful Docker Commands

### View Real-Time Logs

```bash
docker-compose logs -f redis-master
docker-compose logs -f redis-slave1
docker-compose logs redis-commander
```

### Stop All Containers

```bash
docker-compose stop
```

### Start All Containers (After Stopping)

```bash
docker-compose start
```

### Remove All Containers and Data

```bash
docker-compose down -v
```

### Restart Specific Container

```bash
docker-compose restart redis-slave1
```

### Execute Command in Container

```bash
docker-compose exec redis-master redis-cli ping
docker-compose exec redis-master redis-cli info replication
```

---

## Testing Replication (Docker)

### 1. Write to Master

```bash
redis-cli -h localhost -p 6379 SET testkey "hello from master"
```

### 2. Read from Slave

```bash
redis-cli -h localhost -p 6380 GET testkey
```

Should return: `"hello from master"`

This confirms replication is working.

---

## Docker Network

All containers are on the same Docker network (`redis-network`), which means:
- They can communicate with each other using container names
- External access uses localhost with mapped ports
- When running FastAPI in Docker as well, containers communicate directly

---

## Quick Reference

| Component | Docker Port | Real Production |
|-----------|-------------|-----------------|
| Master | localhost:6379 | localhost:6379 |
| Slave 1 | localhost:6380 | 192.168.1.101:6379 |
| Slave 2 | localhost:6381 | 192.168.1.102:6379 |
| Slave 3 | localhost:6382 | 192.168.1.103:6379 |
| Slave 4 | localhost:6383 | 192.168.1.104:6379 |
| Slave 5 | localhost:6384 | 192.168.1.105:6379 |
| Redis Commander | localhost:8081 | Not needed |
| FastAPI | localhost:8000 | localhost:8000 |

---

## Troubleshooting

### Container won't start

```bash
docker-compose logs redis-master
```

### Ports already in use

```bash
# Change ports in docker-compose.yml or:
lsof -i :6379
# Kill the process or use different ports
```

### Low memory

```bash
# Check Docker resource allocation
# Increase RAM in Docker Desktop settings
# Or reduce container count
```

### Replication not working

```bash
# Check replication status
docker-compose exec redis-master redis-cli info replication

# Restart slave
docker-compose restart redis-slave1
```

---

## Summary

- **For Testing**: Use `docker-compose up -d` with localhost ports
- **For Production**: Edit `config.py` with real Ubuntu IPs, ensure Redis running on each server
- **After Testing**: Use `docker-compose down` to clean up

For more details, see QUICKSTART.md and README.md
