"""
Tests for purchase order API endpoints.
"""
import pytest


@pytest.fixture
def backlog_item_id(client):
    """The id of a backlog item that has no purchase order yet."""
    response = client.get("/api/backlog")
    assert response.status_code == 200

    items = response.json()
    assert len(items) > 0

    return items[0]["id"]


@pytest.fixture
def new_purchase_order(backlog_item_id):
    """A valid CreatePurchaseOrderRequest payload."""
    return {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "FilterMax Inc",
        "quantity": 350,
        "unit_cost": 12.5,
        "expected_delivery_date": "2026-10-01",
        "notes": "Expedited to clear the shortage",
    }


class TestPurchaseOrderEndpoints:
    """Test suite for purchase-order-related endpoints."""

    def test_create_purchase_order(self, client, new_purchase_order):
        """Test raising a purchase order against a backlog item."""
        response = client.post("/api/purchase-orders", json=new_purchase_order)
        assert response.status_code == 201

        purchase_order = response.json()
        assert purchase_order["backlog_item_id"] == new_purchase_order["backlog_item_id"]
        assert purchase_order["supplier_name"] == new_purchase_order["supplier_name"]
        assert purchase_order["quantity"] == new_purchase_order["quantity"]
        assert purchase_order["unit_cost"] == new_purchase_order["unit_cost"]
        assert purchase_order["expected_delivery_date"] == new_purchase_order["expected_delivery_date"]
        assert purchase_order["notes"] == new_purchase_order["notes"]

    def test_created_purchase_order_structure(self, client, new_purchase_order):
        """Test that a created purchase order has all required fields."""
        response = client.post("/api/purchase-orders", json=new_purchase_order)
        purchase_order = response.json()

        for field in (
            "id",
            "backlog_item_id",
            "supplier_name",
            "quantity",
            "unit_cost",
            "expected_delivery_date",
            "status",
            "created_date",
        ):
            assert field in purchase_order

        assert isinstance(purchase_order["quantity"], int)
        assert isinstance(purchase_order["unit_cost"], (int, float))
        assert purchase_order["quantity"] > 0
        assert purchase_order["unit_cost"] >= 0

    def test_created_purchase_order_is_server_assigned(self, client, new_purchase_order):
        """Test that id, status and created date are set by the server."""
        response = client.post("/api/purchase-orders", json=new_purchase_order)
        purchase_order = response.json()

        assert purchase_order["id"].startswith("PO-")
        assert purchase_order["status"].lower() == "processing"
        # created_date is an ISO calendar date
        assert len(purchase_order["created_date"]) == 10
        assert purchase_order["created_date"].count("-") == 2

    def test_purchase_order_ids_are_unique(self, client):
        """Test that each purchase order gets its own id."""
        response = client.get("/api/backlog")
        items = response.json()
        assert len(items) >= 2, "Need at least two backlog items for this test"

        ids = []
        for item in items:
            response = client.post("/api/purchase-orders", json={
                "backlog_item_id": item["id"],
                "supplier_name": "Supplier Co",
                "quantity": 10,
                "unit_cost": 5.0,
                "expected_delivery_date": "2026-10-01",
            })
            assert response.status_code == 201
            ids.append(response.json()["id"])

        assert len(set(ids)) == len(ids)

    def test_get_purchase_order_by_backlog_item(self, client, new_purchase_order):
        """Test getting the purchase order raised against a backlog item."""
        created = client.post("/api/purchase-orders", json=new_purchase_order).json()

        response = client.get(f"/api/purchase-orders/{new_purchase_order['backlog_item_id']}")
        assert response.status_code == 200

        assert response.json() == created

    def test_get_purchase_order_for_item_without_one(self, client, backlog_item_id):
        """Test that a backlog item with no purchase order returns 404."""
        response = client.get(f"/api/purchase-orders/{backlog_item_id}")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_purchase_order_for_nonexistent_item(self, client):
        """Test getting a purchase order for a backlog item that doesn't exist."""
        response = client.get("/api/purchase-orders/nonexistent-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_create_duplicate_purchase_order(self, client, new_purchase_order):
        """Test that a backlog item can only have one purchase order.

        The dashboard swaps "Create PO" for "View PO" off this, and View can
        only ever show one order, so a second must be refused.
        """
        first = client.post("/api/purchase-orders", json=new_purchase_order)
        assert first.status_code == 201

        second = client.post("/api/purchase-orders", json=new_purchase_order)
        assert second.status_code == 409

        data = second.json()
        assert "detail" in data
        assert "already has a purchase order" in data["detail"].lower()

    def test_create_purchase_order_unknown_backlog_item(self, client, new_purchase_order):
        """Test that an unknown backlog item is rejected."""
        response = client.post("/api/purchase-orders", json={
            **new_purchase_order,
            "backlog_item_id": "nonexistent-999",
        })
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "unknown backlog item" in data["detail"].lower()

    @pytest.mark.parametrize("quantity", [0, -5])
    def test_create_purchase_order_invalid_quantity(self, client, new_purchase_order, quantity):
        """Test that a non-positive quantity is rejected."""
        response = client.post("/api/purchase-orders", json={
            **new_purchase_order,
            "quantity": quantity,
        })
        assert response.status_code == 400
        assert "quantity" in response.json()["detail"].lower()

    def test_create_purchase_order_negative_unit_cost(self, client, new_purchase_order):
        """Test that a negative unit cost is rejected."""
        response = client.post("/api/purchase-orders", json={
            **new_purchase_order,
            "unit_cost": -1.0,
        })
        assert response.status_code == 400
        assert "unit cost" in response.json()["detail"].lower()

    @pytest.mark.parametrize("supplier_name", ["", "   "])
    def test_create_purchase_order_blank_supplier(self, client, new_purchase_order, supplier_name):
        """Test that a blank supplier name is rejected."""
        response = client.post("/api/purchase-orders", json={
            **new_purchase_order,
            "supplier_name": supplier_name,
        })
        assert response.status_code == 400
        assert "supplier name" in response.json()["detail"].lower()

    def test_create_purchase_order_missing_field(self, client, backlog_item_id):
        """Test that a payload missing a required field fails validation."""
        response = client.post("/api/purchase-orders", json={
            "backlog_item_id": backlog_item_id,
            "supplier_name": "Supplier Co",
        })
        assert response.status_code == 422

    def test_notes_are_optional(self, client, new_purchase_order):
        """Test that notes can be omitted."""
        payload = {k: v for k, v in new_purchase_order.items() if k != "notes"}

        response = client.post("/api/purchase-orders", json=payload)
        assert response.status_code == 201
        assert response.json()["notes"] is None

    def test_supplier_name_is_trimmed(self, client, new_purchase_order):
        """Test that surrounding whitespace is stripped from the supplier name."""
        response = client.post("/api/purchase-orders", json={
            **new_purchase_order,
            "supplier_name": "  FilterMax Inc  ",
        })
        assert response.status_code == 201
        assert response.json()["supplier_name"] == "FilterMax Inc"

    def test_backlog_reflects_new_purchase_order(self, client, new_purchase_order):
        """Test that has_purchase_order flips once an order is raised.

        The dashboard reads this flag to decide whether to offer Create PO or
        View PO, so it has to follow the order.
        """
        item_id = new_purchase_order["backlog_item_id"]

        before = client.get("/api/backlog").json()
        assert next(item for item in before if item["id"] == item_id)["has_purchase_order"] is False

        client.post("/api/purchase-orders", json=new_purchase_order)

        after = client.get("/api/backlog").json()
        assert next(item for item in after if item["id"] == item_id)["has_purchase_order"] is True

        # Only the item that was ordered against should have changed.
        for item in after:
            if item["id"] != item_id:
                assert item["has_purchase_order"] is False
