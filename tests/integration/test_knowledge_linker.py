#!/usr/bin/env python3
"""
Integration test for the Knowledge Linker functionality.

Tests the complete pipeline from code analysis to concept discovery
and enrichment from natural language documentation.
"""
import sys
import os
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from regionai.pipeline.api import (
    build_knowledge_graph, discover_domain_model
)
from regionai.knowledge.graph import Concept, Relation


def test_enriched_knowledge_graph():
    """Test building a knowledge graph enriched from documentation."""
    print("Testing enriched knowledge graph construction...")
    
    # Sample code with rich documentation
    code = '''
class User:
    """
    Represents a user in the system.
    
    Each user has a profile that contains their personal information.
    Users can create multiple orders and belong to one or more groups.
    """
    def __init__(self, name, email):
        self.name = name
        self.email = email

def create_user(name, email):
    """
    Creates a new user account.
    
    This function creates a user and automatically generates a profile
    for them. The user is initially assigned to the 'default' group.
    """
    user = User(name, email)
    create_profile(user)
    assign_to_group(user, 'default')
    return user

def create_profile(user):
    """
    Creates a profile for a user.
    
    Each user has exactly one profile that stores additional information
    like bio, avatar, and preferences.
    """
    profile = {
        'user_id': user.id,
        'bio': '',
        'avatar': None
    }
    save_profile(profile)

def create_order(user_id, items):
    """
    Creates an order for a user.
    
    Orders belong to a specific user and contain multiple items.
    Each order is associated with exactly one user, but users
    can have many orders.
    """
    order = {
        'user_id': user_id,
        'items': items,
        'status': 'pending'
    }
    return save_order(order)

def assign_to_group(user, group_name):
    """
    Assigns a user to a group.
    
    Users can belong to multiple groups, and groups can have
    multiple users. This creates a many-to-many relationship
    between users and groups.
    """
    membership = {
        'user_id': user.id,
        'group_name': group_name
    }
    save_membership(membership)

def get_user_orders(user_id):
    """Gets all orders for a user. A user has many orders."""
    return fetch_orders_by_user(user_id)

def get_order_items(order_id):
    """
    Gets items in an order.
    
    Each order contains multiple items. Items can appear in
    multiple orders, creating a many-to-many relationship.
    """
    return fetch_items_by_order(order_id)
'''
    
    # Build knowledge graph without enrichment
    print("\n1. Building graph from code patterns only...")
    hub_basic = build_knowledge_graph(code, include_source=True, enrich_from_docs=False)
    kg_basic = hub_basic.wkg
    print(f"Basic graph: {len(kg_basic)} concepts, {len(kg_basic.graph.edges())} relationships")
    
    # Build knowledge graph with enrichment
    print("\n2. Building graph with documentation enrichment...")
    hub_enriched = build_knowledge_graph(code, include_source=True, enrich_from_docs=True)
    kg_enriched = hub_enriched.wkg
    print(f"Enriched graph: {len(kg_enriched)} concepts, {len(kg_enriched.graph.edges())} relationships")
    
    # Verify enrichment added relationships
    assert len(kg_enriched.graph.edges()) > len(kg_basic.graph.edges())
    
    # Check specific relationships from documentation
    user_profile_rels = kg_enriched.get_relations_with_confidence("User")
    has_profile_rel = any(
        str(r['target']) == "Profile" and str(r['relation']) == "HAS_ONE"
        for r in user_profile_rels
    )
    assert has_profile_rel, "Should find User HAS_ONE Profile from documentation"
    
    print("✓ Enriched knowledge graph built successfully")


def test_domain_model_with_enrichment():
    """Test complete domain model discovery with enrichment."""
    print("\nTesting domain model discovery with enrichment...")
    
    # E-commerce domain with detailed documentation
    code = '''
class Product:
    """
    Represents a product in the catalog.
    
    Products belong to categories and can have multiple variants.
    Each product is created by a vendor and can be reviewed by customers.
    """
    def __init__(self, name, price, category_id, vendor_id):
        self.name = name
        self.price = price
        self.category_id = category_id
        self.vendor_id = vendor_id

def create_product(name, price, category_id, vendor_id):
    """
    Creates a new product in the catalog.
    
    The product is assigned to a category and linked to its vendor.
    Categories can contain multiple products, but each product
    belongs to exactly one category.
    """
    product = Product(name, price, category_id, vendor_id)
    return save_product(product)

def create_product_variant(product_id, size, color, sku):
    """
    Creates a variant of a product.
    
    Products can have multiple variants (e.g., different sizes and colors).
    Each variant belongs to exactly one product.
    """
    variant = {
        'product_id': product_id,
        'size': size,
        'color': color,
        'sku': sku
    }
    return save_variant(variant)

def create_review(product_id, customer_id, rating, comment):
    """
    Creates a customer review for a product.
    
    Customers can review products they have purchased. A product
    can have many reviews, and a customer can write many reviews,
    but each review is for one product by one customer.
    """
    review = {
        'product_id': product_id,
        'customer_id': customer_id,
        'rating': rating,
        'comment': comment
    }
    return save_review(review)

def get_category_products(category_id):
    """Gets all products in a category. Categories have many products."""
    return fetch_products_by_category(category_id)

def get_vendor_products(vendor_id):
    """
    Gets all products from a vendor.
    
    Vendors can create multiple products. Each product is created
    by exactly one vendor, establishing a one-to-many relationship.
    """
    return fetch_products_by_vendor(vendor_id)
'''
    
    # Discover domain model
    result = discover_domain_model(code, enrich_from_docs=True)
    
    # Check results
    assert 'knowledge_graph' in result
    assert 'concepts' in result
    assert 'relationships' in result
    assert 'discovery_report' in result
    assert 'enrichment_report' in result
    
    # Verify concepts discovered
    concept_names = [c['name'] for c in result['concepts']]
    assert 'Product' in concept_names
    assert 'Category' in concept_names
    assert 'Vendor' in concept_names
    assert 'Customer' in concept_names
    assert 'Review' in concept_names
    
    # Print reports
    print("\nDiscovery Report:")
    print(result['discovery_report'])
    
    print("\nEnrichment Report:")
    print(result['enrichment_report'])
    
    print("\nVisualization:")
    print(result['visualization'])
    
    print("✓ Domain model discovery with enrichment works correctly")


def test_confidence_and_evidence():
    """Test that relationships have proper confidence and evidence."""
    print("\nTesting confidence scores and evidence tracking...")
    
    code = '''
def create_employee(name, department_id):
    """
    Creates an employee record.
    
    Each employee belongs to exactly one department. Departments
    can have multiple employees. This establishes a many-to-one
    relationship where employees belong to departments.
    
    The employee is also assigned a manager who is another employee,
    creating a self-referential relationship.
    """
    employee = {
        'name': name,
        'department_id': department_id,
        'created_at': datetime.now()
    }
    return save_employee(employee)

def assign_manager(employee_id, manager_id):
    """
    Assigns a manager to an employee.
    
    Each employee has one manager (who is also an employee).
    A manager can manage multiple employees.
    """
    update_employee(employee_id, {'manager_id': manager_id})
'''
    
    # Build enriched graph
    hub = build_knowledge_graph(code, include_source=True, enrich_from_docs=True)
    kg = hub.wkg  # Get the world knowledge graph from the hub
    
    # Check employee-department relationship
    employee_rels = kg.get_relations_with_confidence("Employee")
    
    dept_rel = next(
        (r for r in employee_rels if 
         str(r['target']) == "Department" and str(r['relation']) == "BELONGS_TO"),
        None
    )
    
    assert dept_rel is not None
    assert dept_rel['confidence'] > 0
    assert dept_rel['evidence'] is not None
    # Check that the evidence mentions the relationship between employees and departments
    assert ("employees belong to departments" in dept_rel['evidence'].lower() or
            "employee belongs to" in dept_rel['evidence'].lower())
    
    print(f"✓ Found Employee->Department relationship:")
    print(f"  Confidence: {dept_rel['confidence']:.2f}")
    print(f"  Evidence: \"{dept_rel['evidence'][:60]}...\"")
    
    # Check self-referential manager relationship
    manager_rel = next(
        (r for r in employee_rels if 
         str(r['target']) == "Employee" and "manager" in str(r['relation']).lower()),
        None
    )
    
    if manager_rel:
        print(f"✓ Found self-referential manager relationship")
    
    print("✓ Confidence and evidence tracking works correctly")


def test_integration_with_multiple_sources():
    """Test enrichment from multiple documentation sources."""
    print("\nTesting integration with multiple documentation sources...")
    
    code = '''
def create_project(name, team_id):
    """
    Creates a new project.
    
    Projects are owned by teams. Each project belongs to exactly
    one team, but teams can have multiple projects.
    """
    # Additional context: Projects require approval from team lead
    project = {'name': name, 'team_id': team_id}
    return save_project(project)

def add_task_to_project(project_id, task_description):
    """Adds a task to a project. Projects contain many tasks."""
    task = {
        'project_id': project_id,
        'description': task_description,
        'status': 'pending'
    }
    # Tasks are the building blocks of projects
    return save_task(task)

def assign_project_member(project_id, user_id, role):
    """
    Assigns a user to a project with a specific role.
    
    Users can work on multiple projects, and projects can have
    multiple users, creating a many-to-many relationship. The
    role (e.g., 'developer', 'tester') defines the user's
    responsibilities in the project.
    """
    assignment = {
        'project_id': project_id,
        'user_id': user_id,
        'role': role
    }
    return save_assignment(assignment)
'''
    
    # Discover domain model
    result = discover_domain_model(code, enrich_from_docs=True)
    
    # The enrichment should find relationships from both docstrings and comments
    enrichment_report = result['enrichment_report']
    
    # Check that multiple relationship types were discovered
    assert "HAS_MANY" in enrichment_report
    assert "BELONGS_TO" in enrichment_report
    
    # Check specific concepts
    kg = result['knowledge_graph']
    assert "Project" in kg
    assert "Team" in kg
    assert "Task" in kg
    assert "User" in kg
    
    print("✓ Multiple documentation sources processed successfully")


def test_semantic_relationship_inference():
    """Test that co-occurring concepts form relationships."""
    print("\nTesting semantic relationship inference...")
    
    # Test with a function that has multiple concepts in name and docs
    code = '''
def get_customer_order_details(customer_id, order_id):
    """
    Retrieves detailed information about a customer's order.
    
    This function fetches the complete order details including
    the customer information, order items, and shipping details.
    It combines data from multiple sources to provide a comprehensive
    view of the customer's order.
    """
    customer = fetch_customer(customer_id)
    order = fetch_order(order_id)
    # Merge customer and order data with shipping details
    details = {
        'customer': customer,
        'order': order,
        'shipping': get_shipping_info(order_id)
    }
    return details

def update_customer_shipping_address(customer_id, shipping_address):
    """
    Updates the shipping address for a customer.
    
    The shipping address is used for all future orders
    placed by this customer.
    """
    customer = get_customer(customer_id)
    customer['shipping_address'] = shipping_address
    save_customer(customer)
'''
    
    # Build the knowledge graph with enrichment
    hub = build_knowledge_graph(code, include_source=True, enrich_from_docs=True)
    kg = hub.wkg
    
    # Check that concepts were discovered
    assert "Customer" in kg, "Customer concept should be discovered"
    assert "Order" in kg, "Order concept should be discovered"
    assert "Details" in kg, "Details concept should be discovered"
    assert "Shipping" in kg, "Shipping concept should be discovered"
    
    # Check that relationships exist between co-occurring concepts
    # Get all edges in the graph
    edges = list(kg.graph.edges(data=True))
    
    # Helper function to check if a relationship exists
    def has_relationship(concept1: str, concept2: str, rel_type: str = "RELATED_TO") -> bool:
        c1 = Concept(concept1)
        c2 = Concept(concept2)
        
        # Check both directions
        for source, target, data in edges:
            if ((source == c1 and target == c2) or (source == c2 and target == c1)):
                if data.get('label') == Relation(rel_type):
                    return True
        return False
    
    # Check specific co-occurrence relationships
    assert has_relationship("Customer", "Order"), \
        "Customer and Order should be related (co-occur in function name)"
    assert has_relationship("Customer", "Details"), \
        "Customer and Details should be related (co-occur in function name)"
    assert has_relationship("Order", "Details"), \
        "Order and Details should be related (co-occur in function name)"
    assert has_relationship("Customer", "Shipping"), \
        "Customer and Shipping should be related (co-occur in text)"
    
    # Check that these relationships have updated certainty
    customer_rels = kg.get_relations_with_confidence("Customer")
    
    # Find RELATED_TO relationships
    related_rels = [r for r in customer_rels if str(r['relation']) == "RELATED_TO"]
    assert len(related_rels) > 0, "Customer should have RELATED_TO relationships"
    
    # Check that at least one has confidence > 0.5
    high_confidence_rel = any(r['confidence'] > 0.5 for r in related_rels)
    assert high_confidence_rel, "At least one RELATED_TO relationship should have confidence > 0.5"
    
    # Print some relationships for verification
    print(f"✓ Found {len(related_rels)} RELATED_TO relationships for Customer")
    for rel in related_rels[:3]:  # Show first 3
        print(f"  Customer -> {rel['target']} (confidence: {rel['confidence']:.3f})")
    
    print("✓ Semantic relationship inference works correctly")


def test_bayesian_belief_updates():
    """Test that concept certainty scores increase with evidence."""
    print("\nTesting Bayesian belief updates...")
    
    # Test with an empty knowledge graph starting point
    code = '''
def get_customer_record(customer_id):
    """
    Retrieves a customer record from the database.
    
    Each customer has a unique record that contains their
    contact information, purchase history, and preferences.
    """
    record = fetch_from_db('customers', customer_id)
    return record

def update_customer_preferences(customer_id, preferences):
    """
    Updates the preferences for a customer.
    
    Customer preferences include notification settings,
    favorite categories, and delivery options.
    """
    # Update customer record with new preferences
    customer = get_customer_record(customer_id)
    customer['preferences'] = preferences
    save_customer(customer)
    return customer

def create_customer(name, email):
    """Creates a new customer in the system."""
    customer = {
        'name': name,
        'email': email,
        'created_at': datetime.now()
    }
    # New customers get default preferences
    customer['preferences'] = get_default_preferences()
    return save_customer(customer)
'''
    
    # Build the knowledge graph with enrichment
    hub = build_knowledge_graph(code, include_source=True, enrich_from_docs=True)
    kg = hub.wkg
    
    # Check that 'Customer' and 'Record' concepts exist
    assert "Customer" in kg, "Customer concept should be discovered"
    assert "Record" in kg, "Record concept should be discovered"
    
    # Get the metadata for these concepts
    customer_metadata = kg.get_concept_metadata("Customer")
    record_metadata = kg.get_concept_metadata("Record")
    
    assert customer_metadata is not None, "Customer should have metadata"
    assert record_metadata is not None, "Record should have metadata"
    
    # Check that certainty (confidence) is greater than initial value
    # Initial uniform distribution has confidence = 0.5 (alpha=1, beta=1)
    assert customer_metadata.confidence > 0.5, \
        f"Customer confidence ({customer_metadata.confidence}) should be > 0.5"
    assert record_metadata.confidence > 0.5, \
        f"Record confidence ({record_metadata.confidence}) should be > 0.5"
    
    # Check that concepts mentioned more frequently have higher confidence
    # 'Customer' appears in all three function names, 'Record' appears once
    assert customer_metadata.confidence > record_metadata.confidence, \
        "Customer (mentioned more) should have higher confidence than Record"
    
    print(f"✓ Customer concept confidence: {customer_metadata.confidence:.3f}")
    print(f"✓ Record concept confidence: {record_metadata.confidence:.3f}")
    print(f"✓ Customer alpha/beta: {customer_metadata.alpha:.2f}/{customer_metadata.beta:.2f}")
    print(f"✓ Record alpha/beta: {record_metadata.alpha:.2f}/{record_metadata.beta:.2f}")
    
    # Test relationships also have updated beliefs
    customer_rels = kg.get_relations_with_confidence("Customer")
    if customer_rels:
        # Find any relationship involving Record
        record_rel = next(
            (r for r in customer_rels if "Record" in str(r['target'])),
            None
        )
        if record_rel:
            print(f"✓ Customer->Record relationship confidence: {record_rel['confidence']:.3f}")
    
    print("✓ Bayesian belief updates work correctly")


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Knowledge Linker Integration Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_enriched_knowledge_graph,
        test_domain_model_with_enrichment,
        test_confidence_and_evidence,
        test_integration_with_multiple_sources,
        test_semantic_relationship_inference,
        test_bayesian_belief_updates
    ]
    
    failed = 0
    for test_func in test_functions:
        try:
            test_func()
            print("")  # Blank line between tests
        except Exception as e:
            print(f"\n✗ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print("")
    
    print("=" * 60)
    if failed == 0:
        print("✓ All integration tests passed!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)