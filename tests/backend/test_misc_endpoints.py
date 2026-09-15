"""
Tests for miscellaneous API endpoints (demand, backlog, spending).
"""
import pytest


class TestDemandEndpoints:
    """Test suite for demand forecast endpoints."""

    def test_get_demand_forecasts(self, client):
        """Test getting demand forecasts."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check structure if data exists
        if len(data) > 0:
            forecast = data[0]
            assert "id" in forecast
            assert "item_sku" in forecast
            assert "item_name" in forecast
            assert "current_demand" in forecast
            assert "forecasted_demand" in forecast
            assert "trend" in forecast
            assert "period" in forecast

    def test_demand_forecast_trends(self, client):
        """Test that demand forecasts have valid trend values."""
        response = client.get("/api/demand")
        data = response.json()

        valid_trends = ["increasing", "stable", "decreasing"]

        for forecast in data:
            assert forecast["trend"].lower() in valid_trends

    def test_demand_forecast_values(self, client):
        """Test that demand forecast values are non-negative."""
        response = client.get("/api/demand")
        data = response.json()

        for forecast in data:
            assert forecast["current_demand"] >= 0
            assert forecast["forecasted_demand"] >= 0

    def test_stable_demand_items_have_small_changes(self, client):
        """Test that items with 'stable' trend have less than 2% change."""
        response = client.get("/api/demand")
        data = response.json()

        stable_items = [item for item in data if item["trend"].lower() == "stable"]

        # Should have at least 5 stable items
        assert len(stable_items) >= 5, f"Expected at least 5 stable items, found {len(stable_items)}"

        for item in stable_items:
            current = item["current_demand"]
            forecasted = item["forecasted_demand"]

            # Calculate percentage change
            if current > 0:
                percent_change = abs((forecasted - current) / current) * 100
                assert percent_change < 2.0, \
                    f"Item {item['item_name']} has {percent_change:.2f}% change, expected < 2%"

    def test_demand_forecast_has_new_items(self, client):
        """Test that new demand forecast items exist."""
        response = client.get("/api/demand")
        data = response.json()

        # Check for the new items we added
        skus = [item["item_sku"] for item in data]

        # Should have Pressure Sensor Module and PWM Motor Controller
        assert "PRS-203" in skus, "Missing Pressure Sensor Module"
        assert "PWM-404" in skus, "Missing PWM Motor Controller"

        # Verify they are marked as stable
        for item in data:
            if item["item_sku"] in ["PRS-203", "PWM-404"]:
                assert item["trend"].lower() == "stable", \
                    f"New item {item['item_name']} should have stable trend"

    def test_demand_forecast_skus_exist_in_inventory(self, client):
        """Test that every forecast SKU refers to a real inventory item.

        Restocking joins demand to inventory for cost and stock level, so a
        forecast for a SKU we do not stock silently drops out of the plan.
        """
        inventory_skus = {item["sku"] for item in client.get("/api/inventory").json()}

        for forecast in client.get("/api/demand").json():
            assert forecast["item_sku"] in inventory_skus, \
                f"Forecast SKU {forecast['item_sku']} is not in inventory"


class TestBacklogEndpoints:
    """Test suite for backlog endpoints."""

    def test_get_backlog(self, client):
        """Test getting backlog items."""
        response = client.get("/api/backlog")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check structure if data exists
        if len(data) > 0:
            backlog_item = data[0]
            assert "id" in backlog_item
            assert "order_id" in backlog_item
            assert "item_sku" in backlog_item
            assert "item_name" in backlog_item
            assert "quantity_needed" in backlog_item
            assert "quantity_available" in backlog_item
            assert "days_delayed" in backlog_item
            assert "priority" in backlog_item

    def test_backlog_priority_values(self, client):
        """Test that backlog items have valid priority values."""
        response = client.get("/api/backlog")
        data = response.json()

        valid_priorities = ["high", "medium", "low"]

        for item in data:
            assert item["priority"].lower() in valid_priorities

    def test_backlog_quantity_logic(self, client):
        """Test that backlog quantities are non-negative."""
        response = client.get("/api/backlog")
        data = response.json()

        for item in data:
            # Quantities should be non-negative
            assert item["quantity_needed"] >= 0
            assert item["quantity_available"] >= 0

    def test_backlog_days_delayed(self, client):
        """Test that days delayed is non-negative."""
        response = client.get("/api/backlog")
        data = response.json()

        for item in data:
            assert item["days_delayed"] >= 0


class TestSpendingEndpoints:
    """Test suite for spending-related endpoints."""

    def test_get_spending_summary(self, client):
        """Test getting spending summary."""
        response = client.get("/api/spending/summary")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)

    def test_get_monthly_spending(self, client):
        """Test getting monthly spending data."""
        response = client.get("/api/spending/monthly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check structure if data exists
        if len(data) > 0:
            month_data = data[0]
            assert "month" in month_data or "period" in month_data

    def test_monthly_spending_has_all_cost_categories(self, client):
        """Test that monthly spending includes all cost categories."""
        response = client.get("/api/spending/monthly")
        data = response.json()

        required_fields = ["procurement", "operational", "labor", "overhead"]

        for month_data in data:
            for field in required_fields:
                assert field in month_data, f"Missing {field} in monthly spending"
                assert isinstance(month_data[field], (int, float))
                assert month_data[field] >= 0

    def test_monthly_spending_has_variety(self, client):
        """Test that monthly spending data has variety (not all the same)."""
        response = client.get("/api/spending/monthly")
        data = response.json()

        # Collect all procurement values
        procurement_values = [month["procurement"] for month in data]

        # Should have at least 3 different values (variety)
        unique_values = set(procurement_values)
        assert len(unique_values) >= 3, \
            "Monthly spending should have variety, not all the same values"

        # Same for other categories
        operational_values = set(month["operational"] for month in data)
        assert len(operational_values) >= 3, \
            "Operational costs should have variety across months"

    def test_get_category_spending(self, client):
        """Test getting spending by category."""
        response = client.get("/api/spending/categories")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check structure if data exists
        if len(data) > 0:
            category_data = data[0]
            assert "category" in category_data or "name" in category_data

    def test_category_spending_percentages_match_amounts(self, client):
        """Test that each category's percentage is its real share of the total.

        These percentages used to be stored next to the amounts in
        spending.json and had drifted: they summed to 123.6%, and Components
        was labelled a smaller share than Raw Materials despite being the
        larger amount. The client uses the number for the bar width as well as
        the label, so the bars were wrong too. They are derived now.
        """
        response = client.get("/api/spending/categories")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0

        total = sum(category["amount"] for category in data)
        assert total > 0

        for category in data:
            expected = round(category["amount"] / total * 100, 1)
            assert abs(category["percentage"] - expected) < 0.01, \
                f"{category['category']} reports {category['percentage']}%, expected {expected}%"

        assert abs(sum(category["percentage"] for category in data) - 100) < 0.5

    def test_category_spending_percentages_rank_with_amounts(self, client):
        """Test that a larger amount never reports a smaller percentage."""
        response = client.get("/api/spending/categories")
        data = response.json()

        by_amount = sorted(data, key=lambda category: category["amount"], reverse=True)
        percentages = [category["percentage"] for category in by_amount]

        assert percentages == sorted(percentages, reverse=True), \
            "Percentages should fall in the same order as the amounts"

    def test_get_recent_transactions(self, client):
        """Test getting recent transactions."""
        response = client.get("/api/spending/transactions")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check structure if data exists
        if len(data) > 0:
            transaction = data[0]
            # Transactions should have some identifying fields
            assert isinstance(transaction, dict)


class TestRootEndpoint:
    """Test suite for root endpoint."""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data or "version" in data

    def test_root_endpoint_structure(self, client):
        """Test root endpoint has expected structure."""
        response = client.get("/")
        data = response.json()

        # Should have message and version
        assert "message" in data
        assert "version" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["version"], str)
