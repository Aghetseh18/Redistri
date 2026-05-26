# Redis Master Node API - Project Files Index

## 📚 Documentation Files (Start Here)

| File                | Purpose                                     | Read First? |
| ------------------- | ------------------------------------------- | ----------- |
| **ARCHITECTURE.md** | System design, data flow, scalability model | ⭐ YES      |
| **SETUP.md**        | Step-by-step production deployment guide    | ⭐ YES      |
| **QUICKSTART.md**   | Fast 5-minute setup for testing             | ✓ YES       |
| **README.md**       | Comprehensive feature overview              | Reference   |
| **DOCKER_SETUP.md** | Local testing with Docker containers        | Optional    |
| **INDEX.md**        | This file - file overview                   | Reference   |

---

## 🔧 Core Application Files

### `main.py` (FastAPI Application)

- **Size**: ~1500 lines
- **Purpose**: Main FastAPI application with all CRUD endpoints
- **Contains**:
  - Health check endpoints
  - Client CRUD operations (Master node)
  - Article CRUD operations (Master node)
  - Commande CRUD operations (Ubuntu 1)
  - Ligne Commande CRUD operations (Ubuntu 2)
  - Livraison CRUD operations (Ubuntu 3)
  - Detail Livraison CRUD operations (Ubuntu 4)
- **Endpoints**: 42 total (7 operations × 6 entities)
- **Dependencies**: FastAPI, Redis, Pydantic

### `models.py` (Data Models)

- **Size**: ~200 lines
- **Purpose**: Pydantic models for input validation and documentation
- **Contains**:
  - Client model
  - Article model
  - Commande model
  - Ligne Commande model
  - Livraison model
  - Detail Livraison model
  - Response models
  - Status models
- **Used by**: FastAPI for request/response validation

### `config.py` (Configuration)

- **Size**: ~50 lines
- **Purpose**: Redis nodes configuration and entity mapping
- **Contains**:
  - Redis node addresses (Master + 5 Ubuntu servers)
  - Entity-to-node mapping
  - Connection pool settings
  - API configuration
- **Key IPs**:
  - Master: localhost:6379 (this machine)
  - Slaves: 192.168.1.101-105 (Ubuntu servers)

### `redis_manager.py` (Redis Connection Manager)

- **Size**: ~300 lines
- **Purpose**: Manages connections to all Redis nodes
- **Contains**:
  - RedisManager class
  - Connection pooling
  - CRUD operations wrapper
  - Health checks
  - Node info retrieval
- **Used by**: main.py for all Redis operations

---

## 🚀 Execution Files

### `test_data.py` (Sample Data Loader)

- **Size**: ~300 lines
- **Purpose**: Load sample data from SQL schema into Redis
- **Contains**:
  - Sample Clients, Articles, Commandes, etc.
  - CRUD operation tests
  - Health verification
  - Data verification
- **Usage**: `python test_data.py`
- **Loads**: 48 sample records total

---

## 📦 Configuration Files

### `requirements.txt` (Python Dependencies)

- **Purpose**: Lists all Python packages needed
- **Key packages**:
  - fastapi==0.104.1
  - uvicorn==0.24.0
  - redis==5.0.1
  - pydantic==2.5.0
- **Usage**: `pip install -r requirements.txt`

### `.env.example` (Environment Template)

- **Purpose**: Template for environment variables
- **Contains**: Redis node IPs, API settings
- **Usage**: Copy to `.env` and customize if needed

### `.gitignore` (Git Ignore Rules)

- **Purpose**: Prevents committing Python cache, env files, etc.
- **Excludes**: `__pycache__/`, `.env`, `*.pyc`, `venv/`

### `docker-compose.yml` (Docker Configuration)

- **Purpose**: Local testing with 6 Redis containers
- **Contains**:
  - 1 Master Redis container
  - 5 Slave Redis containers
  - Redis Commander GUI
  - Networking and volumes
- **Note**: For testing only - NOT used in production
- **Usage**: `docker-compose up -d`

---

## 🏗️ System Architecture

```
YOUR MACHINE (Master Node)
├── main.py
│   ├── Receives HTTP requests
│   ├── Routes to appropriate Redis node
│   └── Returns JSON responses
├── models.py
│   └── Validates input data
├── config.py
│   └── Defines node locations:
│       ├── Master: localhost:6379 (THIS MACHINE)
│       └── Slaves: 192.168.1.101-105 (UBUNTU SERVERS)
├── redis_manager.py
│   └── Manages connections
└── Redis Server (localhost:6379)
    ├── Stores: Clients
    └── Stores: Articles

UBUNTU SERVERS (5 Worker Nodes)
├── Ubuntu 1 (192.168.1.101) - Redis - Commandes
├── Ubuntu 2 (192.168.1.102) - Redis - Ligne Commandes
├── Ubuntu 3 (192.168.1.103) - Redis - Livraisons
├── Ubuntu 4 (192.168.1.104) - Redis - Detail Livraisons
└── Ubuntu 5 (192.168.1.105) - Redis - Reserved
```

---

## 📋 Entity Storage Map

```
┌──────────────────────┬─────────────────────┬─────────────────┐
│ Entity               │ Storage Location    │ Redis Node      │
├──────────────────────┼─────────────────────┼─────────────────┤
│ Client               │ This Machine        │ Master          │
│ Article              │ This Machine        │ Master          │
│ Commande             │ Ubuntu 1            │ Slave 1         │
│ Ligne Commande       │ Ubuntu 2            │ Slave 2         │
│ Livraison            │ Ubuntu 3            │ Slave 3         │
│ Detail Livraison     │ Ubuntu 4            │ Slave 4         │
└──────────────────────┴─────────────────────┴─────────────────┘
```

---

## 🚀 Quick Start Flow

1. **Read**: ARCHITECTURE.md (understand the design)
2. **Read**: SETUP.md (follow deployment steps)
3. **Install**: `pip install -r requirements.txt`
4. **Configure**: Edit config.py if Ubuntu IPs are different
5. **Start**: `python main.py`
6. **Test**: Open http://localhost:8000/docs
7. **Load**: `python test_data.py` (optional)

---

## 🔍 File Purposes Summary

### For Deployment

- **SETUP.md** ← Start here
- **config.py** ← Configure node addresses
- **requirements.txt** ← Install dependencies

### For Understanding

- **ARCHITECTURE.md** ← Read first
- **main.py** ← See all endpoints
- **models.py** ← See data structures

### For Testing

- **QUICKSTART.md** ← Quick local test
- **test_data.py** ← Load sample data
- **docker-compose.yml** ← Local Redis setup

### For Development

- **redis_manager.py** ← Understand Redis layer
- **config.py** ← Customize configuration
- **.env.example** ← Set env variables

---

## 📌 Important Notes

### ⚠️ Single Redis on Master

- **Only 1 Redis instance** runs on this machine (Master node)
- **5 Redis instances** run on separate Ubuntu servers
- This is NOT a single-machine setup with 6 local Redis instances
- Network communication only goes to 192.168.1.101-105

### 🐳 Docker is for Testing

- `docker-compose.yml` creates 6 local Redis containers
- **Use Docker only for development/testing**
- In production, only 1 Redis runs on this machine
- Ubuntu servers use native Redis installations

### 🔐 Security

- Redis nodes are on internal network only
- No external internet exposure
- Optional authentication can be added to config.py

---

## 💡 Key Concepts

| Concept          | Explanation                                   |
| ---------------- | --------------------------------------------- |
| **Master Node**  | This machine - handles API and fast data      |
| **Worker Nodes** | Ubuntu servers - handle orders and deliveries |
| **Entity**       | Data type (Client, Article, Commande, etc.)   |
| **Node Mapping** | Which node stores which entities              |
| **CRUD**         | Create, Read, Update, Delete operations       |
| **Endpoint**     | HTTP URL that performs an action              |
| **Redis Key**    | How data is stored: e.g., `client:10`         |

---

## 📞 API Endpoints Reference

### Health & Status

- `GET /` - API root information
- `GET /health` - All nodes health check
- `GET /nodes/status` - Detailed node status

### Clients (Master)

- `POST /clients` - Create
- `GET /clients` - List all
- `GET /clients/{id}` - Get one
- `PUT /clients/{id}` - Update
- `DELETE /clients/{id}` - Delete

### Articles (Master)

- `POST /articles` - Create
- `GET /articles` - List all
- `GET /articles/{id}` - Get one
- `PUT /articles/{id}` - Update
- `DELETE /articles/{id}` - Delete

### Commandes (Ubuntu 1)

- `POST /commandes` - Create
- `GET /commandes` - List all
- `GET /commandes/{id}` - Get one
- `PUT /commandes/{id}` - Update
- `DELETE /commandes/{id}` - Delete

### Ligne Commandes (Ubuntu 2)

- `POST /ligne-commandes` - Create
- `GET /ligne-commandes` - List all
- `GET /ligne-commandes/{id1}/{id2}` - Get one
- `PUT /ligne-commandes/{id1}/{id2}` - Update
- `DELETE /ligne-commandes/{id1}/{id2}` - Delete

### Livraisons (Ubuntu 3)

- `POST /livraisons` - Create
- `GET /livraisons` - List all
- `GET /livraisons/{id}` - Get one
- `PUT /livraisons/{id}` - Update
- `DELETE /livraisons/{id}` - Delete

### Detail Livraisons (Ubuntu 4)

- `POST /detail-livraisons` - Create
- `GET /detail-livraisons` - List all
- `GET /detail-livraisons/{id1}/{id2}/{id3}` - Get one
- `PUT /detail-livraisons/{id1}/{id2}/{id3}` - Update
- `DELETE /detail-livraisons/{id1}/{id2}/{id3}` - Delete

---

## 🆘 Troubleshooting Quick Links

| Issue                            | File to Check                   |
| -------------------------------- | ------------------------------- |
| Cannot connect to Redis          | SETUP.md → Step 1               |
| Cannot connect to Ubuntu servers | SETUP.md → Step 2               |
| Wrong IP addresses               | config.py                       |
| API won't start                  | QUICKSTART.md → Troubleshooting |
| Need to understand architecture  | ARCHITECTURE.md                 |
| Want to use Docker               | DOCKER_SETUP.md                 |
| Need sample data                 | test_data.py                    |

---

## 📝 Files at a Glance

```
c:\Users\VICTUS\Desktop\Projects\School Projects\Reddis\
│
├── 📖 DOCUMENTATION
│   ├── ARCHITECTURE.md          (System design & data flow)
│   ├── SETUP.md                 (Production setup steps)
│   ├── QUICKSTART.md            (5-minute quick start)
│   ├── README.md                (Full feature reference)
│   ├── DOCKER_SETUP.md          (Local testing with Docker)
│   └── INDEX.md                 (This file)
│
├── 🔧 APPLICATION CODE
│   ├── main.py                  (FastAPI app - 1500 lines)
│   ├── models.py                (Data models - 200 lines)
│   ├── redis_manager.py         (Redis connection manager)
│   └── config.py                (Configuration)
│
├── 🚀 SCRIPTS
│   └── test_data.py             (Load sample data)
│
├── 📦 CONFIGURATION
│   ├── requirements.txt          (Python dependencies)
│   ├── .env.example              (Environment template)
│   ├── .gitignore                (Git ignore rules)
│   └── docker-compose.yml        (Docker test setup)
```

---

## ✅ Getting Started Checklist

- [ ] Read ARCHITECTURE.md (15 minutes)
- [ ] Read SETUP.md (15 minutes)
- [ ] Install Redis on this machine
- [ ] Install Redis on all 5 Ubuntu servers
- [ ] Install Python dependencies: `pip install -r requirements.txt`
- [ ] Update config.py if Ubuntu IPs differ
- [ ] Start FastAPI: `python main.py`
- [ ] Test API: http://localhost:8000/docs
- [ ] Load sample data: `python test_data.py`
- [ ] Check node status: http://localhost:8000/nodes/status

---

For questions or issues, check the relevant documentation file above.
