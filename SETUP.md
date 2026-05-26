# SETUP INSTRUCTIONS - Production Deployment

This document explains how to set up the Redis Master Node API for **production deployment**.

## Architecture Summary

```
YOUR MACHINE (Master Node - Windows/Linux)
├── Redis Server Instance (localhost:6379)
├── FastAPI Application (localhost:8000)
└── Stores: Clients & Articles

UBUNTU SERVERS (5 Worker Nodes)
├── Ubuntu 1 (192.168.1.101) - Redis on port 6379 - Stores Commandes
├── Ubuntu 2 (192.168.1.102) - Redis on port 6379 - Stores Ligne Commandes
├── Ubuntu 3 (192.168.1.103) - Redis on port 6379 - Stores Livraisons
├── Ubuntu 4 (192.168.1.104) - Redis on port 6379 - Stores Detail Livraisons
└── Ubuntu 5 (192.168.1.105) - Redis on port 6379 - Reserved
```

---

## Step 1: Set Up Redis on This Machine

### Option A: Using Docker (Recommended for Windows)

```bash
docker run -d --name redis-master -p 6379:6379 redis:7-alpine
```

### Option B: Native Redis for Windows

1. Download: https://github.com/microsoftarchive/redis/releases
2. Extract and run `redis-server.exe`

### Option C: WSL (Windows Subsystem for Linux)

```bash
wsl --install Ubuntu
wsl
sudo apt-get update
sudo apt-get install redis-server
redis-server
```

### Verify Redis is Running

```bash
redis-cli ping
```

Expected output: `PONG`

---

## Step 2: Set Up Redis on Ubuntu Servers

On **each** of the 5 Ubuntu machines (192.168.1.101-105):

### 1. SSH into the Ubuntu machine

```bash
ssh ubuntu@192.168.1.101
# (repeat for .102, .103, .104, .105)
```

### 2. Install Redis

```bash
sudo apt-get update
sudo apt-get install -y redis-server
```

### 3. Start and Enable Redis

```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server  # Auto-start on reboot
```

### 4. Verify Redis is Running

```bash
redis-cli ping
```

Expected output: `PONG`

### 5. Test from Remote (from your machine)

```bash
redis-cli -h 192.168.1.101 ping
redis-cli -h 192.168.1.102 ping
redis-cli -h 192.168.1.103 ping
redis-cli -h 192.168.1.104 ping
redis-cli -h 192.168.1.105 ping
```

Each should return: `PONG`

---

## Step 3: Install Python Application

On **this machine**:

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Configuration

Check `config.py` has correct IP addresses:

```python
REDIS_NODES = {
    "master": {"host": "localhost", "port": 6379, "db": 0},
    "slave1": {"host": "192.168.1.101", "port": 6379, "db": 0},
    "slave2": {"host": "192.168.1.102", "port": 6379, "db": 0},
    "slave3": {"host": "192.168.1.103", "port": 6379, "db": 0},
    "slave4": {"host": "192.168.1.104", "port": 6379, "db": 0},
    "slave5": {"host": "192.168.1.105", "port": 6379, "db": 0},
}
```

**Update if your Ubuntu servers have different IP addresses.**

### 3. Start the FastAPI Application

```bash
python main.py
```

Expected output:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## Step 4: Verify Everything Works

### 1. Check API Health

```bash
curl http://localhost:8000/health
```

Should return: `{"success": true, "message": "All nodes healthy"}`

### 2. Check All Node Status

```bash
curl http://localhost:8000/nodes/status
```

Shows connection status of all 6 Redis nodes.

### 3. Load Sample Data (Optional)

```bash
python test_data.py
```

This loads 48 sample records into the Redis system.

### 4. Access Interactive API Documentation

Open browser: **http://localhost:8000/docs**

---

## Quick Test Sequence

### Create a Client (stores on Master/localhost)

```bash
curl -X POST http://localhost:8000/clients \
  -H "Content-Type: application/json" \
  -d '{
    "no_client": 10,
    "nom_client": "Luc Sansom",
    "no_telephone": "(999)999-9999"
  }'
```

### Create a Commande (stores on Ubuntu 1/192.168.1.101)

```bash
curl -X POST http://localhost:8000/commandes \
  -H "Content-Type: application/json" \
  -d '{
    "no_commande": 1,
    "date_commande": "2024-05-23",
    "no_client": 10
  }'
```

### Verify Data was Stored

**On this machine** (Master):

```bash
redis-cli GET client:10
```

**On Ubuntu 1** (Slave):

```bash
redis-cli -h 192.168.1.101 GET commande:1
```

---

## Configuration Customization

### If Ubuntu Servers Have Different IP Addresses

Edit `config.py`:

```python
REDIS_NODES = {
    "master": {"host": "localhost", "port": 6379, "db": 0},
    "slave1": {"host": "YOUR_IP_1", "port": 6379, "db": 0},  # Change this
    "slave2": {"host": "YOUR_IP_2", "port": 6379, "db": 0},  # Change this
    # ... etc
}
```

### If Redis Runs on Different Port

Edit `config.py`:

```python
"master": {"host": "localhost", "port": 6380, "db": 0},  # Change port
```

### If You Want to Change API Port

```bash
python -m uvicorn main:app --port 8080
```

---

## Running as a Service (Optional)

### Windows: Create Batch File

Create `run_api.bat`:

```batch
@echo off
cd /d "c:\Users\VICTUS\Desktop\Projects\School Projects\Reddis"
python main.py
pause
```

Double-click to run.

### Linux/WSL: Create Systemd Service

Create `/etc/systemd/system/redis-api.service`:

```ini
[Unit]
Description=Redis Master API
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Reddis
ExecStart=/usr/bin/python3 /path/to/Reddis/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable redis-api
sudo systemctl start redis-api
```

---

## Troubleshooting

### "Cannot connect to Redis on localhost"

```bash
# Check if Redis is running
redis-cli ping

# If not:
# - Docker: docker run -d -p 6379:6379 redis:7-alpine
# - WSL: redis-server
# - Native Windows: Run redis-server.exe
```

### "Cannot connect to Ubuntu servers"

```bash
# Test each Ubuntu server
redis-cli -h 192.168.1.101 ping

# If fails:
# 1. Verify Ubuntu is on network (ping 192.168.1.101)
# 2. SSH in and check: sudo systemctl status redis-server
# 3. Start if needed: sudo systemctl start redis-server
# 4. Check firewall allows port 6379
```

### API returns 503 (Service Unavailable)

```bash
# Run this to see which nodes are down:
curl http://localhost:8000/nodes/status

# Fix and restart that node's Redis
```

### Port 8000 Already in Use

```bash
# Use different port:
python -m uvicorn main:app --port 8080
```

### Connection Pool Issues

Edit `config.py`:

```python
CONNECTION_POOL_SIZE = 20  # Increase from 10
```

---

## Performance Optimization

### For High Load

```python
# In config.py
CONNECTION_POOL_SIZE = 50
```

### Enable Redis Persistence (Optional)

On each Ubuntu server:

```bash
sudo nano /etc/redis/redis.conf
# Uncomment: save 900 1
sudo systemctl restart redis-server
```

---

## Security Considerations

### 1. Firewall

```bash
# Only allow Redis on internal network (not exposed to internet)
# Ubuntu firewall example:
sudo ufw allow from 192.168.1.0/24 to any port 6379
```

### 2. Redis Authentication (Optional)

In Ubuntu `/etc/redis/redis.conf`:

```
requirepass your_secure_password
```

Then update `config.py`:

```python
"slave1": {
    "host": "192.168.1.101",
    "port": 6379,
    "db": 0,
    "password": "your_secure_password"
}
```

### 3. API Rate Limiting

Consider adding rate limiting in production (see README.md for advanced features).

---

## Backup Strategy

### Backup Redis Data on Master

```bash
# Periodic backup
redis-cli BGSAVE  # Background save to dump.rdb
cp /path/to/dump.rdb /backup/location/
```

### Backup on Ubuntu Servers

```bash
sudo -u redis redis-cli BGSAVE
sudo cp /var/lib/redis/dump.rdb /backup/location/
```

---

## Monitoring

### Check API Status

```bash
curl http://localhost:8000/health
```

### Monitor Redis Memory

```bash
redis-cli info memory
redis-cli -h 192.168.1.101 info memory
```

### Check All Nodes

```bash
curl http://localhost:8000/nodes/status | python -m json.tool
```

---

## Summary Checklist

- [ ] Redis running on this machine (localhost:6379)
- [ ] Redis running on all 5 Ubuntu servers (192.168.1.101-105)
- [ ] Python dependencies installed: `pip install -r requirements.txt`
- [ ] `config.py` has correct IP addresses
- [ ] FastAPI started: `python main.py`
- [ ] API accessible: `http://localhost:8000/docs`
- [ ] All nodes showing as healthy: `curl http://localhost:8000/health`
- [ ] Sample data loaded (optional): `python test_data.py`

---

## Next Steps

1. Start using the API - see QUICKSTART.md
2. Load your data - see test_data.py
3. Monitor performance - use `/nodes/status` endpoint
4. Scale if needed - add more Ubuntu servers

For advanced configuration, see README.md
