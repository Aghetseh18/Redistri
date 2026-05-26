# Redis Master Node - FastAPI CRUD Application

A distributed FastAPI application for managing data across multiple Redis nodes with full CRUD operations. The master node (this PC) controls 1 Redis instance, with 5 additional Redis instances running on separate Ubuntu machines.

## Architecture Overview

```
This Machine (Master Node)
├── Redis Server (Master) → localhost:6379
├── FastAPI Application → Port 8000
└── Stores: Clients, Articles

Ubuntu Servers (5 Slave/Worker Nodes)
├── Ubuntu 1 → Redis at 192.168.1.101:6379 (Stores: Commandes)
├── Ubuntu 2 → Redis at 192.168.1.102:6379 (Stores: Ligne Commandes)
├── Ubuntu 3 → Redis at 192.168.1.103:6379 (Stores: Livraisons)
├── Ubuntu 4 → Redis at 192.168.1.104:6379 (Stores: Detail Livraisons)
└── Ubuntu 5 → Redis at 192.168.1.105:6379 (Reserved for future use)
```

## Entity Distribution

- **Clients** → Master Node (localhost)
- **Articles** → Master Node (localhost)
- **Commandes** → Ubuntu 1 (192.168.1.101)
- **Ligne Commandes** → Ubuntu 2 (192.168.1.102)
- **Livraisons** → Ubuntu 3 (192.168.1.103)
- **Detail Livraisons** → Ubuntu 4 (192.168.1.104)

## Installation

### Prerequisites

- **This Machine**: Redis Server + Python 3.8+
- **5 Ubuntu Machines**: Redis Server running at 192.168.1.101-105 (configurable)

### Setup Steps

1. **Clone/Extract Project**

   ```bash
   cd c:\Users\VICTUS\Desktop\Projects\School Projects\Reddis
   ```

2. **Create Virtual Environment**

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Redis Nodes** (Optional)
   Edit `config.py` to update Redis node addresses and ports:

   ```python
   REDIS_NODES = {
       "master": {"host": "localhost", "port": 6379, "db": 0},
       "slave1": {"host": "192.168.1.101", "port": 6379, "db": 0},
       # ... etc
   }
   ```

5. **Run the Application**
   ```bash
   python main.py
   ```
   or
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## API Documentation

The application provides interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints Overview

### Health & Monitoring

- `GET /health` - Health check for all Redis nodes
- `GET /nodes/status` - Detailed status of all nodes
- `GET /` - API root information

### Clients (Master Node)

- `POST /clients` - Create client
- `GET /clients` - List all clients
- `GET /clients/{no_client}` - Get client by ID
- `PUT /clients/{no_client}` - Update client
- `DELETE /clients/{no_client}` - Delete client

### Articles (Master Node)

- `POST /articles` - Create article
- `GET /articles` - List all articles
- `GET /articles/{no_article}` - Get article by ID
- `PUT /articles/{no_article}` - Update article
- `DELETE /articles/{no_article}` - Delete article

### Commandes (Slave 1)

- `POST /commandes` - Create order
- `GET /commandes` - List all orders
- `GET /commandes/{no_commande}` - Get order by ID
- `PUT /commandes/{no_commande}` - Update order
- `DELETE /commandes/{no_commande}` - Delete order

### Ligne Commandes (Slave 2)

- `POST /ligne-commandes` - Create order line
- `GET /ligne-commandes` - List all order lines
- `GET /ligne-commandes/{no_commande}/{no_article}` - Get order line
- `PUT /ligne-commandes/{no_commande}/{no_article}` - Update order line
- `DELETE /ligne-commandes/{no_commande}/{no_article}` - Delete order line

### Livraisons (Slave 3)

- `POST /livraisons` - Create delivery
- `GET /livraisons` - List all deliveries
- `GET /livraisons/{no_livraison}` - Get delivery by ID
- `PUT /livraisons/{no_livraison}` - Update delivery
- `DELETE /livraisons/{no_livraison}` - Delete delivery

### Detail Livraisons (Slave 4)

- `POST /detail-livraisons` - Create delivery detail
- `GET /detail-livraisons` - List all delivery details
- `GET /detail-livraisons/{no_livraison}/{no_commande}/{no_article}` - Get delivery detail
- `PUT /detail-livraisons/{no_livraison}/{no_commande}/{no_article}` - Update delivery detail
- `DELETE /detail-livraisons/{no_livraison}/{no_commande}/{no_article}` - Delete delivery detail

## Usage Examples

### Create a Client

```bash
curl -X POST "http://localhost:8000/clients" \
  -H "Content-Type: application/json" \
  -d '{
    "no_client": 10,
    "nom_client": "Luc Sansom",
    "no_telephone": "(999)999-9999"
  }'
```

### Create an Article

```bash
curl -X POST "http://localhost:8000/articles" \
  -H "Content-Type: application/json" \
  -d '{
    "no_article": 10,
    "description": "Cèdre en boule",
    "prix_unitaire": 10.99,
    "quantite_en_stock": 10
  }'
```

### Create a Commande

```bash
curl -X POST "http://localhost:8000/commandes" \
  -H "Content-Type: application/json" \
  -d '{
    "no_commande": 1,
    "date_commande": "2000-06-01",
    "no_client": 10
  }'
```

### Create a Ligne Commande

```bash
curl -X POST "http://localhost:8000/ligne-commandes" \
  -H "Content-Type: application/json" \
  -d '{
    "no_commande": 1,
    "no_article": 10,
    "quantite": 5
  }'
```

### Get All Clients

```bash
curl -X GET "http://localhost:8000/clients"
```

### Update a Client

```bash
curl -X PUT "http://localhost:8000/clients/10" \
  -H "Content-Type: application/json" \
  -d '{
    "no_client": 10,
    "nom_client": "Luc Sansom Updated",
    "no_telephone": "(999)999-9998"
  }'
```

### Delete a Client

```bash
curl -X DELETE "http://localhost:8000/clients/10"
```

### Check Redis Node Status

```bash
curl -X GET "http://localhost:8000/nodes/status"
```

## Project Structure

```
Reddis/
├── main.py                 # FastAPI application with all CRUD endpoints
├── config.py              # Redis nodes configuration and mapping
├── models.py              # Pydantic models for all entities
├── redis_manager.py       # Redis connection management
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
└── README.md             # This file
```

## Key Features

✅ **Full CRUD Operations** - Create, Read, Update, Delete for all entities
✅ **Distributed Storage** - Data distributed across 6 Redis nodes
✅ **Health Monitoring** - Real-time health checks for all nodes
✅ **Connection Pooling** - Efficient connection management
✅ **Error Handling** - Comprehensive error messages and HTTP status codes
✅ **API Documentation** - Interactive Swagger UI and ReDoc
✅ **Transaction Support** - Each operation is atomic
✅ **Scalable** - Easy to add more nodes or entities

## Configuration

Edit `config.py` to customize:

```python
# Redis node addresses
REDIS_NODES = {
    "master": {"host": "localhost", "port": 6379, "db": 0},
    # ... other nodes
}

# Map entities to nodes
ENTITY_NODE_MAPPING = {
    "clients": "master",
    "articles": "master",
    # ... other mappings
}
```

## Troubleshooting

### Connection Issues

- Verify all Redis instances are running
- Check firewall settings for ports 6379
- Confirm IP addresses in `config.py`

### Performance

- Increase `CONNECTION_POOL_SIZE` in `config.py` for high load
- Monitor Redis memory usage
- Consider using Redis persistence options

### Debugging

- Check application logs for detailed error messages
- Use `/nodes/status` endpoint to verify node connectivity
- Use Redis CLI to manually inspect data: `redis-cli -h <host>`

## Testing

Test the API using the interactive documentation:

1. Open http://localhost:8000/docs
2. Click "Try it out" on any endpoint
3. Enter sample data and execute

Or use cURL commands from the Examples section above.

## Performance Tips

1. **Batch Operations**: For inserting multiple records, make requests sequentially or use connection pooling
2. **Caching**: Consider adding Redis caching for frequently accessed data
3. **Indexing**: Use Redis sorted sets for indexed lookups
4. **Replication**: Ensure Redis replication is configured for redundancy

## Future Enhancements

- [ ] Bulk operations endpoints
- [ ] Search/filter capabilities
- [ ] Pagination support
- [ ] Real-time WebSocket updates
- [ ] Transaction support (MULTI/EXEC)
- [ ] Backup and restore functionality
- [ ] Role-based access control (RBAC)
- [ ] Rate limiting

## Support & Debugging

For debugging:

```bash
# Check Redis connectivity
redis-cli -h localhost ping

# Monitor Redis commands
redis-cli monitor

# Get Redis info
redis-cli info
```

## License

This project is provided as-is for educational purposes.

## Contact

For issues or questions, check the application logs and API documentation.
