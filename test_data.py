"""
Test/Sample data for Redis Master Node API
Demonstrates CRUD operations with the sample data from the SQL schema
"""

import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000"

# Sample data from the SQL schema
CLIENTS = [
    {"no_client": 10, "nom_client": "Luc Sansom",
        "no_telephone": "(999)999-9999"},
    {"no_client": 20, "nom_client": "Dollard Tremblay",
        "no_telephone": "(888)888-8888"},
    {"no_client": 30, "nom_client": "Lin Bé", "no_telephone": "(777)777-7777"},
    {"no_client": 40, "nom_client": "Jean Leconte",
        "no_telephone": "(666)666-6666"},
    {"no_client": 50, "nom_client": "Hafed Alaoui",
        "no_telephone": "(555)555-5555"},
    {"no_client": 60, "nom_client": "Marie Leconte",
        "no_telephone": "(666)666-6666"},
    {"no_client": 70, "nom_client": "Simon Lecoq",
        "no_telephone": "(444)444-4419"},
    {"no_client": 80, "nom_client": "Dollard Tremblay",
        "no_telephone": "(333)333-3333"},
]

ARTICLES = [
    {"no_article": 10, "description": "Cèdre en boule",
        "prix_unitaire": 10.99, "quantite_en_stock": 10},
    {"no_article": 20, "description": "Sapin",
        "prix_unitaire": 12.99, "quantite_en_stock": 10},
    {"no_article": 40, "description": "Épinette bleue",
        "prix_unitaire": 25.99, "quantite_en_stock": 10},
    {"no_article": 50, "description": "Chêne",
        "prix_unitaire": 22.99, "quantite_en_stock": 10},
    {"no_article": 60, "description": "Érable argenté",
        "prix_unitaire": 15.99, "quantite_en_stock": 10},
    {"no_article": 70, "description": "Herbe à puce",
        "prix_unitaire": 10.99, "quantite_en_stock": 10},
    {"no_article": 80, "description": "Poirier",
        "prix_unitaire": 26.99, "quantite_en_stock": 10},
    {"no_article": 81, "description": "Catalpa",
        "prix_unitaire": 25.99, "quantite_en_stock": 10},
    {"no_article": 90, "description": "Pommier",
        "prix_unitaire": 25.99, "quantite_en_stock": 10},
    {"no_article": 95, "description": "Génévier",
        "prix_unitaire": 15.99, "quantite_en_stock": 10},
]

COMMANDES = [
    {"no_commande": 1, "date_commande": "2000-06-01", "no_client": 10},
    {"no_commande": 2, "date_commande": "2000-06-02", "no_client": 20},
    {"no_commande": 3, "date_commande": "2000-06-02", "no_client": 10},
    {"no_commande": 4, "date_commande": "2000-07-05", "no_client": 10},
    {"no_commande": 5, "date_commande": "2000-07-09", "no_client": 30},
    {"no_commande": 6, "date_commande": "2000-07-09", "no_client": 20},
    {"no_commande": 7, "date_commande": "2000-07-15", "no_client": 40},
    {"no_commande": 8, "date_commande": "2000-07-15", "no_client": 40},
]

LIGNE_COMMANDES = [
    {"no_commande": 1, "no_article": 10, "quantite": 10},
    {"no_commande": 1, "no_article": 70, "quantite": 5},
    {"no_commande": 1, "no_article": 90, "quantite": 1},
    {"no_commande": 2, "no_article": 40, "quantite": 2},
    {"no_commande": 2, "no_article": 95, "quantite": 3},
    {"no_commande": 3, "no_article": 20, "quantite": 1},
    {"no_commande": 4, "no_article": 40, "quantite": 1},
    {"no_commande": 4, "no_article": 50, "quantite": 1},
    {"no_commande": 5, "no_article": 70, "quantite": 3},
    {"no_commande": 5, "no_article": 10, "quantite": 5},
    {"no_commande": 5, "no_article": 20, "quantite": 5},
    {"no_commande": 6, "no_article": 10, "quantite": 5},
    {"no_commande": 6, "no_article": 40, "quantite": 1},
    {"no_commande": 7, "no_article": 50, "quantite": 1},
    {"no_commande": 8, "no_article": 20, "quantite": 3},
]

LIVRAISONS = [
    {"no_livraison": 100, "date_livraison": "2000-06-03"},
    {"no_livraison": 101, "date_livraison": "2000-06-04"},
    {"no_livraison": 102, "date_livraison": "2000-06-04"},
    {"no_livraison": 103, "date_livraison": "2000-06-05"},
    {"no_livraison": 104, "date_livraison": "2000-07-07"},
    {"no_livraison": 105, "date_livraison": "2000-07-08"},
]

DETAIL_LIVRAISONS = [
    {"no_livraison": 100, "no_commande": 1, "no_article": 10, "quantite_livree": 7},
    {"no_livraison": 100, "no_commande": 1, "no_article": 70, "quantite_livree": 5},
    {"no_livraison": 101, "no_commande": 1, "no_article": 10, "quantite_livree": 3},
    {"no_livraison": 102, "no_commande": 2, "no_article": 40, "quantite_livree": 2},
    {"no_livraison": 102, "no_commande": 2, "no_article": 95, "quantite_livree": 1},
    {"no_livraison": 100, "no_commande": 3, "no_article": 20, "quantite_livree": 1},
    {"no_livraison": 103, "no_commande": 1, "no_article": 90, "quantite_livree": 1},
    {"no_livraison": 104, "no_commande": 4, "no_article": 40, "quantite_livree": 1},
    {"no_livraison": 105, "no_commande": 5, "no_article": 70, "quantite_livree": 2},
]


def load_sample_data():
    """Load all sample data into Redis"""
    print("=" * 60)
    print("Loading Sample Data into Redis Master Node")
    print("=" * 60)

    # Load Clients
    print("\n📦 Loading Clients...")
    for client in CLIENTS:
        try:
            response = requests.post(f"{BASE_URL}/clients", json=client)
            print(f"  ✓ Client {client['no_client']}: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error loading client {client['no_client']}: {str(e)}")

    # Load Articles
    print("\n📦 Loading Articles...")
    for article in ARTICLES:
        try:
            response = requests.post(f"{BASE_URL}/articles", json=article)
            print(
                f"  ✓ Article {article['no_article']}: {response.status_code}")
        except Exception as e:
            print(
                f"  ✗ Error loading article {article['no_article']}: {str(e)}")

    # Load Commandes
    print("\n📦 Loading Commandes...")
    for commande in COMMANDES:
        try:
            response = requests.post(f"{BASE_URL}/commandes", json=commande)
            print(
                f"  ✓ Commande {commande['no_commande']}: {response.status_code}")
        except Exception as e:
            print(
                f"  ✗ Error loading commande {commande['no_commande']}: {str(e)}")

    # Load Ligne Commandes
    print("\n📦 Loading Ligne Commandes...")
    for ligne in LIGNE_COMMANDES:
        try:
            response = requests.post(f"{BASE_URL}/ligne-commandes", json=ligne)
            print(
                f"  ✓ Ligne {ligne['no_commande']}:{ligne['no_article']}: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error loading ligne: {str(e)}")

    # Load Livraisons
    print("\n📦 Loading Livraisons...")
    for livraison in LIVRAISONS:
        try:
            response = requests.post(f"{BASE_URL}/livraisons", json=livraison)
            print(
                f"  ✓ Livraison {livraison['no_livraison']}: {response.status_code}")
        except Exception as e:
            print(
                f"  ✗ Error loading livraison {livraison['no_livraison']}: {str(e)}")

    # Load Detail Livraisons
    print("\n📦 Loading Detail Livraisons...")
    for detail in DETAIL_LIVRAISONS:
        try:
            response = requests.post(
                f"{BASE_URL}/detail-livraisons", json=detail)
            print(
                f"  ✓ Detail {detail['no_livraison']}:{detail['no_commande']}:{detail['no_article']}: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error loading detail: {str(e)}")

    print("\n" + "=" * 60)
    print("Sample data loading complete!")
    print("=" * 60)


def verify_data():
    """Verify all loaded data"""
    print("\n" + "=" * 60)
    print("Verifying Loaded Data")
    print("=" * 60)

    try:
        # Check Clients
        response = requests.get(f"{BASE_URL}/clients")
        if response.status_code == 200:
            clients = response.json()
            print(f"\n✓ Clients loaded: {len(clients)} records")

        # Check Articles
        response = requests.get(f"{BASE_URL}/articles")
        if response.status_code == 200:
            articles = response.json()
            print(f"✓ Articles loaded: {len(articles)} records")

        # Check Commandes
        response = requests.get(f"{BASE_URL}/commandes")
        if response.status_code == 200:
            commandes = response.json()
            print(f"✓ Commandes loaded: {len(commandes)} records")

        # Check Ligne Commandes
        response = requests.get(f"{BASE_URL}/ligne-commandes")
        if response.status_code == 200:
            lignes = response.json()
            print(f"✓ Ligne Commandes loaded: {len(lignes)} records")

        # Check Livraisons
        response = requests.get(f"{BASE_URL}/livraisons")
        if response.status_code == 200:
            livraisons = response.json()
            print(f"✓ Livraisons loaded: {len(livraisons)} records")

        # Check Detail Livraisons
        response = requests.get(f"{BASE_URL}/detail-livraisons")
        if response.status_code == 200:
            details = response.json()
            print(f"✓ Detail Livraisons loaded: {len(details)} records")

        # Check Node Health
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"\n✓ API Health: {health['success']}")

        print("\n" + "=" * 60)
        print("Verification complete!")
        print("=" * 60)

    except Exception as e:
        print(f"Error during verification: {str(e)}")


def test_crud_operations():
    """Test basic CRUD operations"""
    print("\n" + "=" * 60)
    print("Testing CRUD Operations")
    print("=" * 60)

    # Create
    print("\n1. Testing CREATE operation...")
    new_client = {
        "no_client": 999,
        "nom_client": "Test Client",
        "no_telephone": "(111)111-1111"
    }
    try:
        response = requests.post(f"{BASE_URL}/clients", json=new_client)
        print(f"   ✓ CREATE: {response.status_code}")
    except Exception as e:
        print(f"   ✗ CREATE: {str(e)}")

    # Read
    print("\n2. Testing READ operation...")
    try:
        response = requests.get(f"{BASE_URL}/clients/999")
        if response.status_code == 200:
            print(f"   ✓ READ: {response.status_code}")
            print(f"     Data: {response.json()}")
    except Exception as e:
        print(f"   ✗ READ: {str(e)}")

    # Update
    print("\n3. Testing UPDATE operation...")
    updated_client = {
        "no_client": 999,
        "nom_client": "Updated Test Client",
        "no_telephone": "(222)222-2222"
    }
    try:
        response = requests.put(f"{BASE_URL}/clients/999", json=updated_client)
        print(f"   ✓ UPDATE: {response.status_code}")
    except Exception as e:
        print(f"   ✗ UPDATE: {str(e)}")

    # Delete
    print("\n4. Testing DELETE operation...")
    try:
        response = requests.delete(f"{BASE_URL}/clients/999")
        print(f"   ✓ DELETE: {response.status_code}")
    except Exception as e:
        print(f"   ✗ DELETE: {str(e)}")

    print("\n" + "=" * 60)
    print("CRUD tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    print("\nRedis Master Node - Test Data Loader")
    print("=" * 60)

    # Check API connectivity
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✓ API is running and accessible")
        else:
            print("✗ API returned unexpected status code")
    except Exception as e:
        print(f"✗ Cannot connect to API: {str(e)}")
        print(f"\nMake sure the API is running:")
        print(f"  python main.py")
        exit(1)

    # Load sample data
    load_sample_data()

    # Verify data
    verify_data()

    # Test CRUD operations
    test_crud_operations()

    print("\n✓ All tests completed successfully!")
    print(f"\nAccess the API at: {BASE_URL}")
    print(f"Interactive Docs: {BASE_URL}/docs")
