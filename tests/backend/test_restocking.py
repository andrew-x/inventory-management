"""
Tests for restocking API endpoints.
"""
import pytest


class TestRestockingEndpoints:
    """Test suite for restocking recommendation and order endpoints."""

    def test_get_restock_recommendations(self, client):
        """Test getting restocking recommendations."""
        response = client.get("/api/restock/recommendations?budget=150000")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "budget" in data
        assert "total_cost" in data
        assert "remaining_budget" in data
        assert "total_recommended_cost" in data
        assert "included_count" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0

        # Verify structure of first recommendation
        first_item = data["items"][0]
        assert "item_sku" in first_item
        assert "item_name" in first_item
        assert "category" in first_item
        assert "warehouse" in first_item
        assert "unit_cost" in first_item
        assert "quantity_on_hand" in first_item
        assert "reorder_point" in first_item
        assert "recommended_quantity" in first_item
        assert "estimated_cost" in first_item
        assert "urgency" in first_item
        assert "lead_time_days" in first_item
        assert "included" in first_item

    def test_recommendation_value_types(self, client):
        """Test that recommendation numeric fields have proper types."""
        response = client.get("/api/restock/recommendations?budget=150000")
        data = response.json()

        for item in data["items"]:
            assert isinstance(item["recommended_quantity"], int)
            assert isinstance(item["quantity_on_hand"], int)
            assert isinstance(item["lead_time_days"], int)
            assert isinstance(item["estimated_cost"], (int, float))
            assert isinstance(item["included"], bool)
            assert item["recommended_quantity"] > 0
            assert item["lead_time_days"] > 0

    def test_recommendation_cost_calculation(self, client):
        """Test that estimated cost matches quantity times unit cost."""
        response = client.get("/api/restock/recommendations?budget=500000")
        data = response.json()

        for item in data["items"]:
            calculated = item["recommended_quantity"] * item["unit_cost"]
            assert abs(item["estimated_cost"] - calculated) < 0.01

    def test_zero_budget_includes_nothing(self, client):
        """Test that a zero budget selects no items but still lists candidates."""
        response = client.get("/api/restock/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["total_cost"] == 0
        assert data["included_count"] == 0
        assert len(data["items"]) > 0
        assert all(item["included"] is False for item in data["items"])

    def test_large_budget_includes_everything(self, client):
        """Test that an ample budget selects every candidate."""
        response = client.get("/api/restock/recommendations?budget=100000000")
        data = response.json()

        assert data["included_count"] == len(data["items"])
        assert all(item["included"] is True for item in data["items"])
        assert abs(data["total_cost"] - data["total_recommended_cost"]) < 0.01

    def test_total_cost_never_exceeds_budget(self, client):
        """Test that allocation stays within budget at every budget level."""
        for budget in [0, 1000, 25000, 50000, 150000, 300000, 500000]:
            response = client.get(f"/api/restock/recommendations?budget={budget}")
            assert response.status_code == 200

            data = response.json()
            assert data["total_cost"] <= budget, \
                f"Budget {budget} allocated {data['total_cost']}"
            assert data["remaining_budget"] >= 0

            # Allocated plus remaining should account for the whole budget
            assert abs(data["total_cost"] + data["remaining_budget"] - budget) < 0.01

    def test_included_costs_sum_to_total(self, client):
        """Test that total_cost equals the sum of the included items."""
        response = client.get("/api/restock/recommendations?budget=150000")
        data = response.json()

        included_sum = sum(
            item["estimated_cost"] for item in data["items"] if item["included"]
        )
        assert abs(data["total_cost"] - included_sum) < 0.01
        assert data["included_count"] == sum(
            1 for item in data["items"] if item["included"]
        )

    def test_recommendations_ordered_by_urgency(self, client):
        """Test that candidates are ranked high, then medium, then low.

        Guards against sorting the urgency strings directly, which would order
        them 'high' < 'low' < 'medium' and bury medium-urgency items.
        """
        response = client.get("/api/restock/recommendations?budget=150000")
        data = response.json()

        rank = {"high": 0, "medium": 1, "low": 2}
        ranks = [rank[item["urgency"]] for item in data["items"]]
        assert ranks == sorted(ranks), "Recommendations are not ordered by urgency"

    def test_urgency_values(self, client):
        """Test that recommendations have valid urgency values."""
        response = client.get("/api/restock/recommendations?budget=150000")
        data = response.json()

        valid_urgencies = ["high", "medium", "low"]
        for item in data["items"]:
            assert item["urgency"] in valid_urgencies

    def test_items_below_reorder_point_are_high_urgency(self, client):
        """Test that stock at or below the reorder point is always urgent."""
        response = client.get("/api/restock/recommendations?budget=150000")
        data = response.json()

        for item in data["items"]:
            if item["quantity_on_hand"] <= item["reorder_point"]:
                assert item["urgency"] == "high", \
                    f"{item['item_sku']} is below reorder point but not high urgency"

    def test_greedy_fill_skips_unaffordable_item(self, client):
        """Test that an unaffordable item is skipped without stopping the fill.

        A budget that runs out partway should still pick up cheaper items
        further down the ranking rather than halting at the first miss.
        """
        response = client.get("/api/restock/recommendations?budget=150000")
        data = response.json()

        included_flags = [item["included"] for item in data["items"]]
        assert False in included_flags, "Budget was too large to exercise a skip"
        first_skip = included_flags.index(False)
        assert True in included_flags[first_skip:], \
            "Fill stopped at the first unaffordable item instead of continuing"

    def test_excluded_items_do_not_fit_remaining_budget(self, client):
        """Test that every excluded item genuinely exceeds what was left."""
        response = client.get("/api/restock/recommendations?budget=150000")
        data = response.json()

        for item in data["items"]:
            if not item["included"]:
                assert item["estimated_cost"] > data["remaining_budget"]

    def test_recommendations_by_warehouse(self, client):
        """Test filtering recommendations by warehouse."""
        response = client.get("/api/restock/recommendations?budget=500000&warehouse=Tokyo")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert item["warehouse"] == "Tokyo"

    def test_recommendations_by_category(self, client):
        """Test filtering recommendations by lowercase category."""
        response = client.get(
            "/api/restock/recommendations?budget=500000&category=circuit boards"
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert item["category"].lower() == "circuit boards"

    def test_recommendations_multiple_filters(self, client):
        """Test filtering recommendations by warehouse and category together."""
        response = client.get(
            "/api/restock/recommendations?budget=500000&warehouse=London&category=sensors"
        )
        assert response.status_code == 200

        for item in response.json()["items"]:
            assert item["warehouse"] == "London"
            assert item["category"].lower() == "sensors"

    def test_recommendations_all_sentinel_ignored(self, client):
        """Test that the 'all' sentinel does not filter anything out."""
        unfiltered = client.get("/api/restock/recommendations?budget=500000").json()
        sentinel = client.get(
            "/api/restock/recommendations?budget=500000&warehouse=all&category=all"
        ).json()

        assert len(sentinel["items"]) == len(unfiltered["items"])

    def test_lead_time_is_deterministic_per_warehouse(self, client):
        """Test that lead time depends only on warehouse and category."""
        data = client.get("/api/restock/recommendations?budget=500000").json()

        by_key = {}
        for item in data["items"]:
            key = (item["warehouse"], item["category"].lower())
            by_key.setdefault(key, set()).add(item["lead_time_days"])

        for key, lead_times in by_key.items():
            assert len(lead_times) == 1, f"{key} has inconsistent lead times"

        # San Francisco ships fastest, Tokyo slowest, for the same category
        sf = [i["lead_time_days"] for i in data["items"] if i["warehouse"] == "San Francisco"]
        tokyo = [i["lead_time_days"] for i in data["items"] if i["warehouse"] == "Tokyo"]
        assert min(sf) < max(tokyo)

    def test_create_restock_order(self, client):
        """Test submitting a restocking order."""
        response = client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [
                {"item_sku": "PCB-001", "quantity": 210},
                {"item_sku": "SRV-302", "quantity": 72}
            ]
        })
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Processing"
        assert order["budget"] == 150000
        assert len(order["items"]) == 2
        assert order["lead_time_days"] > 0
        assert "T" in order["created_date"]
        assert "T" in order["expected_delivery"]
        assert order["expected_delivery"] > order["created_date"]

    def test_created_order_total_matches_lines(self, client):
        """Test that the order total is the sum of its line totals."""
        response = client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [
                {"item_sku": "PCB-001", "quantity": 210},
                {"item_sku": "SRV-302", "quantity": 72}
            ]
        })
        order = response.json()

        line_sum = sum(line["line_total"] for line in order["items"])
        assert abs(order["total_cost"] - line_sum) < 0.01

        for line in order["items"]:
            assert abs(line["line_total"] - line["quantity"] * line["unit_cost"]) < 0.01

    def test_order_costs_come_from_inventory_not_request(self, client):
        """Test that a caller cannot dictate the price of an order.

        Costs are recomputed server-side, so extra pricing fields in the
        request body have no effect on the stored total.
        """
        inventory = client.get("/api/inventory").json()
        pcb = next(item for item in inventory if item["sku"] == "PCB-001")

        response = client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [{"item_sku": "PCB-001", "quantity": 10, "unit_cost": 0.01}]
        })
        assert response.status_code == 201

        order = response.json()
        assert order["items"][0]["unit_cost"] == pcb["unit_cost"]
        assert abs(order["total_cost"] - 10 * pcb["unit_cost"]) < 0.01

    def test_order_lead_time_is_max_of_lines(self, client):
        """Test that order lead time is the slowest line's lead time."""
        response = client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [
                {"item_sku": "PCB-001", "quantity": 10},
                {"item_sku": "SRV-302", "quantity": 5}
            ]
        })
        order = response.json()

        assert order["lead_time_days"] == max(
            line["lead_time_days"] for line in order["items"]
        )

    def test_create_restock_order_empty_items(self, client):
        """Test that an order with no items is rejected."""
        response = client.post("/api/restock-orders", json={"budget": 1000, "items": []})
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "at least one item" in data["detail"].lower()

    def test_create_restock_order_unknown_sku(self, client):
        """Test that an order for an unknown SKU is rejected."""
        response = client.post("/api/restock-orders", json={
            "budget": 1000,
            "items": [{"item_sku": "NOPE-999", "quantity": 5}]
        })
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "nope-999" in data["detail"].lower()

    def test_create_restock_order_invalid_quantity(self, client):
        """Test that a non-positive quantity is rejected."""
        response = client.post("/api/restock-orders", json={
            "budget": 1000,
            "items": [{"item_sku": "PCB-001", "quantity": 0}]
        })
        assert response.status_code == 400

    def test_create_restock_order_duplicate_sku(self, client):
        """Test that the same SKU cannot appear twice in one order.

        The Orders view keys restock lines on item_sku, so a duplicate would
        also break list rendering.
        """
        response = client.post("/api/restock-orders", json={
            "budget": 1000,
            "items": [
                {"item_sku": "PCB-001", "quantity": 5},
                {"item_sku": "PCB-001", "quantity": 7}
            ]
        })
        assert response.status_code == 400

        data = response.json()
        assert "duplicate" in data["detail"].lower()

    def test_get_restock_orders_empty_by_default(self, client):
        """Test that no restocking orders exist before any are submitted."""
        response = client.get("/api/restock-orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_submitted_order_is_retrievable(self, client):
        """Test that a submitted order comes back from the list endpoint."""
        created = client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [{"item_sku": "PCB-001", "quantity": 210}]
        }).json()

        response = client.get("/api/restock-orders")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["order_number"] == created["order_number"]

    def test_restock_orders_newest_first(self, client):
        """Test that submitted orders are returned newest first."""
        first = client.post("/api/restock-orders", json={
            "budget": 1000, "items": [{"item_sku": "PCB-001", "quantity": 1}]
        }).json()
        second = client.post("/api/restock-orders", json={
            "budget": 1000, "items": [{"item_sku": "PCB-002", "quantity": 1}]
        }).json()

        data = client.get("/api/restock-orders").json()
        assert [o["order_number"] for o in data] == [
            second["order_number"], first["order_number"]
        ]

    def test_multi_warehouse_order_matches_any_line_warehouse(self, client):
        """Test that a multi-warehouse order survives a warehouse filter.

        PCB-001 ships from San Francisco and SRV-302 from Tokyo. Filtering on
        either warehouse must still find the order; filtering on a third must
        not. An order-level scalar field would hide it from both.
        """
        client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [
                {"item_sku": "PCB-001", "quantity": 10},
                {"item_sku": "SRV-302", "quantity": 5}
            ]
        })

        assert len(client.get("/api/restock-orders?warehouse=San Francisco").json()) == 1
        assert len(client.get("/api/restock-orders?warehouse=Tokyo").json()) == 1
        assert len(client.get("/api/restock-orders?warehouse=London").json()) == 0

    def test_restock_orders_by_category(self, client):
        """Test filtering submitted orders by category."""
        client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [{"item_sku": "PCB-001", "quantity": 10}]
        })

        assert len(client.get("/api/restock-orders?category=circuit boards").json()) == 1
        assert len(client.get("/api/restock-orders?category=actuators").json()) == 0

    def test_restock_orders_all_sentinel_ignored(self, client):
        """Test that the 'all' sentinel does not filter submitted orders."""
        client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [{"item_sku": "PCB-001", "quantity": 10}]
        })

        response = client.get("/api/restock-orders?warehouse=all&category=all")
        assert len(response.json()) == 1

    def test_order_does_not_leak_into_customer_orders(self, client):
        """Test that restocking orders stay out of /api/orders.

        The Orders view splits them into their own section, and letting them
        into the shared list would skew the dashboard and order counts.
        """
        before = len(client.get("/api/orders").json())

        client.post("/api/restock-orders", json={
            "budget": 150000,
            "items": [{"item_sku": "PCB-001", "quantity": 210}]
        })

        assert len(client.get("/api/orders").json()) == before

    def test_recommended_plan_can_be_submitted(self, client):
        """Test the full flow: recommend within a budget, then order it."""
        plan = client.get("/api/restock/recommendations?budget=150000").json()
        included = [item for item in plan["items"] if item["included"]]
        assert len(included) > 0

        response = client.post("/api/restock-orders", json={
            "budget": plan["budget"],
            "items": [
                {"item_sku": item["item_sku"], "quantity": item["recommended_quantity"]}
                for item in included
            ]
        })
        assert response.status_code == 201

        order = response.json()
        assert len(order["items"]) == len(included)
        assert abs(order["total_cost"] - plan["total_cost"]) < 0.01
        assert order["total_cost"] <= plan["budget"]
