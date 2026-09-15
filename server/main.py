import math
import threading
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders, restock_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# --- Restocking ---------------------------------------------------------
# No lead-time field exists anywhere in the data, so lead times are derived
# from the shipping origin and the handling a category needs.
WAREHOUSE_LEAD_TIME_DAYS = {'San Francisco': 5, 'London': 10, 'Tokyo': 14}
CATEGORY_LEAD_TIME_MODIFIER = {
    'circuit boards': 3,
    'sensors': 2,
    'actuators': 4,
    'controllers': 5,
    'power supplies': 1,
}
DEFAULT_LEAD_TIME_DAYS = 7

# POST handlers are sync `def`, so Starlette runs them in a threadpool and two
# submits can interleave. Reading len(restock_orders) and appending must happen
# as one atomic step or both orders get the same id and order_number.
#
# No test covers this: the race window is microseconds wide, so a concurrency
# test passes just as readily on the broken version. Verified by hand instead --
# widening the window with a sleep between the read and the append yields 43
# unique numbers out of 50 submits without this lock, and 50/50 with it.
# Note this project runs on free-threaded CPython 3.14 (GIL disabled), so there
# is no interpreter-level serialisation to fall back on.
_restock_order_lock = threading.Lock()

# Purchase orders are appended at runtime the same way, and the sequence number
# in their id is derived from the list length, so they need the same guard.
_purchase_order_lock = threading.Lock()

# Urgency must be ranked numerically. Sorting the strings directly would order
# them 'high' < 'low' < 'medium', quietly putting low-urgency items ahead of
# medium ones and inverting the whole recommendation.
URGENCY_RANK = {'high': 0, 'medium': 1, 'low': 2}

# Order enough to cover the forecast plus a safety buffer.
SAFETY_STOCK_FACTOR = 1.1


def get_lead_time_days(warehouse: Optional[str], category: Optional[str]) -> int:
    """Derive a deterministic delivery lead time for a restock line."""
    base = WAREHOUSE_LEAD_TIME_DAYS.get(warehouse or '', DEFAULT_LEAD_TIME_DAYS)
    return base + CATEGORY_LEAD_TIME_MODIFIER.get((category or '').lower(), 0)


def build_restock_candidates() -> list:
    """Join demand forecasts to inventory and size a restock for each item.

    current_demand is units demanded, not units held, so the order quantity is
    sized against the item's quantity_on_hand.
    """
    inventory_by_sku = {item['sku']: item for item in inventory_items}
    candidates = []

    for forecast in demand_forecasts:
        item = inventory_by_sku.get(forecast['item_sku'])
        if not item:
            # Demand for a SKU we do not stock: nothing to restock.
            continue

        target_stock = math.ceil(forecast['forecasted_demand'] * SAFETY_STOCK_FACTOR)
        quantity_on_hand = item['quantity_on_hand']
        recommended_quantity = max(target_stock - quantity_on_hand, 0)
        if recommended_quantity == 0:
            continue

        # target_stock > 0 whenever forecasted_demand > 0, so this is safe.
        coverage_gap = (target_stock - quantity_on_hand) / target_stock

        if quantity_on_hand <= item['reorder_point'] or coverage_gap >= 0.5:
            urgency = 'high'
        elif coverage_gap >= 0.2:
            urgency = 'medium'
        else:
            urgency = 'low'

        candidates.append({
            'item_sku': item['sku'],
            'item_name': item['name'],
            'category': item['category'],
            'warehouse': item['warehouse'],
            'unit_cost': item['unit_cost'],
            'quantity_on_hand': quantity_on_hand,
            'reorder_point': item['reorder_point'],
            'current_demand': forecast['current_demand'],
            'forecasted_demand': forecast['forecasted_demand'],
            'recommended_quantity': recommended_quantity,
            'estimated_cost': round(recommended_quantity * item['unit_cost'], 2),
            'urgency': urgency,
            'coverage_gap': coverage_gap,
            'lead_time_days': get_lead_time_days(item['warehouse'], item['category']),
        })

    candidates.sort(key=lambda c: (URGENCY_RANK[c['urgency']], -c['coverage_gap']))
    return candidates

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class RestockRecommendation(BaseModel):
    item_sku: str
    item_name: str
    category: str
    warehouse: str
    unit_cost: float
    quantity_on_hand: int
    reorder_point: int
    current_demand: int
    forecasted_demand: int
    recommended_quantity: int
    estimated_cost: float
    urgency: str
    lead_time_days: int
    included: bool

class RestockPlan(BaseModel):
    budget: float
    total_cost: float
    remaining_budget: float
    total_recommended_cost: float
    included_count: int
    items: List[RestockRecommendation]

class RestockOrderLine(BaseModel):
    item_sku: str
    item_name: str
    warehouse: str
    category: str
    quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int

class RestockOrder(BaseModel):
    id: str
    order_number: str
    status: str
    created_date: str
    budget: float
    total_cost: float
    items: List[RestockOrderLine]
    lead_time_days: int
    expected_delivery: str

class CreateRestockOrderLine(BaseModel):
    item_sku: str
    quantity: int

class CreateRestockOrderRequest(BaseModel):
    budget: float
    items: List[CreateRestockOrderLine]

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.post("/api/purchase-orders", response_model=PurchaseOrder, status_code=201)
def create_purchase_order(request: CreatePurchaseOrderRequest):
    """Raise a purchase order against a backlog item.

    Like restock_orders, this appends to a module-level list, so the order is
    visible to later requests but does not survive a restart.
    """
    backlog_item = next(
        (item for item in backlog_items if item["id"] == request.backlog_item_id),
        None
    )
    if not backlog_item:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown backlog item {request.backlog_item_id}"
        )

    if request.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

    if request.unit_cost < 0:
        raise HTTPException(status_code=400, detail="Unit cost cannot be negative")

    if not request.supplier_name.strip():
        raise HTTPException(status_code=400, detail="Supplier name is required")

    created = datetime.now()

    with _purchase_order_lock:
        # One PO per backlog item: the dashboard swaps "Create PO" for "View PO"
        # off this check, and View can only ever show one. Inside the lock so two
        # concurrent submits for the same item cannot both pass it.
        if any(po["backlog_item_id"] == request.backlog_item_id for po in purchase_orders):
            raise HTTPException(
                status_code=409,
                detail=f"Backlog item {request.backlog_item_id} already has a purchase order"
            )

        sequence = len(purchase_orders) + 1
        purchase_order = {
            "id": f"PO-{created.year}-{sequence:04d}",
            "backlog_item_id": request.backlog_item_id,
            "supplier_name": request.supplier_name.strip(),
            "quantity": request.quantity,
            "unit_cost": request.unit_cost,
            "expected_delivery_date": request.expected_delivery_date,
            "status": "Processing",
            "created_date": created.strftime("%Y-%m-%d"),
            "notes": request.notes,
        }
        purchase_orders.append(purchase_order)

    return purchase_order

@app.get("/api/purchase-orders/{backlog_item_id}", response_model=PurchaseOrder)
def get_purchase_order_by_backlog_item(backlog_item_id: str):
    """Get the purchase order raised against a backlog item, if there is one."""
    purchase_order = next(
        (po for po in purchase_orders if po["backlog_item_id"] == backlog_item_id),
        None
    )
    if not purchase_order:
        raise HTTPException(
            status_code=404,
            detail=f"Purchase order not found for backlog item {backlog_item_id}"
        )
    return purchase_order

@app.get("/api/restock/recommendations", response_model=RestockPlan)
def get_restock_recommendations(
    budget: float = 0,
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Recommend which forecasted items to restock within a budget.

    Candidates are ranked by urgency. Walking the full ranked list rather than
    stopping at the first item that does not fit lets cheaper, lower-priority
    items soak up the leftover budget.
    """
    candidates = apply_filters(build_restock_candidates(), warehouse, category)

    remaining = budget
    total_cost = 0.0
    included_count = 0
    items = []

    for candidate in candidates:
        item = {k: v for k, v in candidate.items() if k != 'coverage_gap'}
        if candidate['estimated_cost'] <= remaining:
            item['included'] = True
            remaining -= candidate['estimated_cost']
            total_cost += candidate['estimated_cost']
            included_count += 1
        else:
            item['included'] = False
        items.append(item)

    return {
        'budget': budget,
        'total_cost': round(total_cost, 2),
        'remaining_budget': round(remaining, 2),
        'total_recommended_cost': round(sum(c['estimated_cost'] for c in candidates), 2),
        'included_count': included_count,
        'items': items
    }

@app.post("/api/restock-orders", response_model=RestockOrder, status_code=201)
def create_restock_order(request: CreateRestockOrderRequest):
    """Submit a restocking order.

    Only SKUs and quantities are accepted; costs are recomputed here so the
    order total cannot be dictated by the caller.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="A restock order must contain at least one item")

    inventory_by_sku = {item['sku']: item for item in inventory_items}
    lines = []
    seen_skus = set()

    for line in request.items:
        item = inventory_by_sku.get(line.item_sku)
        if not item:
            raise HTTPException(status_code=400, detail=f"Unknown item SKU {line.item_sku}")
        if line.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Quantity for {line.item_sku} must be greater than zero")
        if line.item_sku in seen_skus:
            raise HTTPException(status_code=400, detail=f"Duplicate item SKU {line.item_sku} in order")
        seen_skus.add(line.item_sku)

        lines.append({
            'item_sku': item['sku'],
            'item_name': item['name'],
            'warehouse': item['warehouse'],
            'category': item['category'],
            'quantity': line.quantity,
            'unit_cost': item['unit_cost'],
            'line_total': round(line.quantity * item['unit_cost'], 2),
            'lead_time_days': get_lead_time_days(item['warehouse'], item['category'])
        })

    created = datetime.now()
    lead_time_days = max(line['lead_time_days'] for line in lines)

    with _restock_order_lock:
        sequence = len(restock_orders) + 1
        order = {
            'id': str(sequence),
            'order_number': f"RST-{created.year}-{sequence:04d}",
            'status': 'Processing',
            'created_date': created.strftime('%Y-%m-%dT%H:%M:%S'),
            'budget': request.budget,
            'total_cost': round(sum(line['line_total'] for line in lines), 2),
            'items': lines,
            'lead_time_days': lead_time_days,
            'expected_delivery': (created + timedelta(days=lead_time_days)).strftime('%Y-%m-%dT%H:%M:%S')
        }
        restock_orders.append(order)

    return order

@app.get("/api/restock-orders", response_model=List[RestockOrder])
def get_restock_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get submitted restocking orders, newest first.

    A single order can span warehouses and categories, so it matches a filter
    when any of its lines does. Filtering on a scalar order-level field would
    hide an order the user just placed.
    """
    filtered = restock_orders

    if warehouse and warehouse != 'all':
        filtered = [o for o in filtered
                    if any(line['warehouse'] == warehouse for line in o['items'])]

    if category and category != 'all':
        filtered = [o for o in filtered
                    if any(line['category'].lower() == category.lower() for line in o['items'])]

    return list(reversed(filtered))

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category, with each category's share of the total.

    The share is derived here rather than stored alongside the amounts. It used
    to be a hardcoded field in spending.json that had drifted out of step with
    them -- the four values summed to 123.6%, and Components was labelled a
    smaller share than Raw Materials despite being the larger amount. The client
    uses this number for the bar width as well as the label, so the bars were
    visibly wrong too.
    """
    total = sum(category['amount'] for category in category_spending)

    return [
        {
            **category,
            'percentage': round(category['amount'] / total * 100, 1) if total else 0.0,
        }
        for category in category_spending
    ]

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports():
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends():
    """Get month-over-month trends"""
    months = {}

    for order in orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
