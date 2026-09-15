<template>
  <div class="orders">
    <div class="page-header">
      <h2>{{ t('orders.title') }}</h2>
      <p>{{ t('orders.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card success">
          <div class="stat-label">{{ t('status.delivered') }}</div>
          <div class="stat-value num">{{ getOrdersByStatus('Delivered').length }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('status.shipped') }}</div>
          <div class="stat-value num">{{ getOrdersByStatus('Shipped').length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('status.processing') }}</div>
          <div class="stat-value num">{{ getOrdersByStatus('Processing').length }}</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">{{ t('status.backordered') }}</div>
          <div class="stat-value num">{{ getOrdersByStatus('Backordered').length }}</div>
        </div>
      </div>

      <div class="card" v-if="restockOrders.length">
        <div class="card-header">
          <h3 class="card-title">{{ t('orders.submittedOrders') }}</h3>
        </div>
        <p class="submitted-orders-note">{{ t('orders.submittedOrdersNote') }}</p>
        <div class="table-container">
          <table class="restock-orders-table">
            <thead>
              <tr>
                <th class="rcol-order-number">{{ t('orders.table.orderNumber') }}</th>
                <th class="rcol-date">{{ t('orders.table.date') }}</th>
                <th class="rcol-items">{{ t('orders.table.items') }}</th>
                <th class="rcol-value col-num">{{ t('orders.table.totalValue') }}</th>
                <th class="rcol-lead-time col-num">{{ t('orders.leadTime') }}</th>
                <th class="rcol-date">{{ t('orders.table.expectedDelivery') }}</th>
                <th class="rcol-status">{{ t('orders.table.status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in restockOrders" :key="order.id">
                <td class="rcol-order-number"><strong class="num">{{ order.order_number }}</strong></td>
                <td class="rcol-date num">{{ formatDate(order.created_date) }}</td>
                <td class="rcol-items">
                  <details class="items-details">
                    <summary class="items-summary">
                      {{ t('orders.itemsCount', { count: order.items.length }) }}
                    </summary>
                    <div class="items-dropdown">
                      <div v-for="line in order.items" :key="line.item_sku" class="item-entry">
                        <span class="item-name">{{ translateProductName(line.item_name) }}</span>
                        <span class="item-meta">{{ t('orders.quantity') }}: <span class="num">{{ line.quantity }}</span></span>
                      </div>
                    </div>
                  </details>
                </td>
                <td class="rcol-value col-num"><strong class="num">{{ formatCurrency(order.total_cost, currentCurrency) }}</strong></td>
                <td class="rcol-lead-time col-num num">{{ t('orders.leadTimeDays', { days: order.lead_time_days }) }}</td>
                <td class="rcol-date num">{{ formatDate(order.expected_delivery) }}</td>
                <td class="rcol-status">
                  <span :class="['badge', getOrderStatusClass(order.status)]">
                    {{ t('status.' + order.status.toLowerCase()) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('orders.allOrders') }} ({{ orders.length }})</h3>
        </div>
        <div class="table-container">
          <table class="orders-table">
            <thead>
              <tr>
                <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
                <th class="col-customer">{{ t('orders.table.customer') }}</th>
                <th class="col-items">{{ t('orders.table.items') }}</th>
                <th class="col-status">{{ t('orders.table.status') }}</th>
                <th class="col-date">{{ t('orders.table.orderDate') }}</th>
                <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
                <th class="col-value col-num">{{ t('orders.table.totalValue') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td class="col-order-number"><strong class="num">{{ order.order_number }}</strong></td>
                <td class="col-customer">{{ translateCustomerName(order.customer) }}</td>
                <td class="col-items">
                  <details class="items-details">
                    <summary class="items-summary">
                      {{ t('orders.itemsCount', { count: order.items.length }) }}
                    </summary>
                    <div class="items-dropdown">
                      <div v-for="(item, idx) in order.items" :key="idx" class="item-entry">
                        <span class="item-name">{{ translateProductName(item.name) }}</span>
                        <span class="item-meta num">{{ t('orders.quantity') }}: {{ item.quantity }} @ {{ currencySymbol }}{{ item.unit_price }}</span>
                      </div>
                    </div>
                  </details>
                </td>
                <td class="col-status">
                  <span :class="['badge', getOrderStatusClass(order.status)]">
                    {{ t(`status.${order.status.toLowerCase()}`) }}
                  </span>
                </td>
                <td class="col-date num">{{ formatDate(order.order_date) }}</td>
                <td class="col-date num">{{ formatDate(order.expected_delivery) }}</td>
                <td class="col-value col-num"><strong class="num">{{ currencySymbol }}{{ order.total_value.toLocaleString() }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Orders',
  setup() {
    const { t, currentCurrency, translateProductName, translateCustomerName } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })
    const loading = ref(true)
    const error = ref(null)
    const orders = ref([])
    const restockOrders = ref([])

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loadOrders = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()
        const fetchedOrders = await api.getOrders(filters)

        // Sort orders by order_date (earliest first)
        orders.value = fetchedOrders.sort((a, b) => {
          const dateA = new Date(a.order_date)
          const dateB = new Date(b.order_date)
          return dateA - dateB
        })
      } catch (err) {
        error.value = 'Failed to load orders: ' + err.message
      } finally {
        loading.value = false
      }

      try {
        restockOrders.value = await api.getRestockOrders(getCurrentFilters())
      } catch (err) {
        restockOrders.value = []
        console.error('Failed to load restock orders:', err)
      }
    }

    // Watch for filter changes and reload data
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadOrders()
    })

    const getOrdersByStatus = (status) => {
      return orders.value.filter(order => order.status === status)
    }

    const getOrderStatusClass = (status) => {
      const statusMap = {
        'Delivered': 'success',
        'Shipped': 'info',
        'Processing': 'warning',
        'Backordered': 'danger'
      }
      return statusMap[status] || 'info'
    }

    const formatDate = (dateString) => {
      const { currentLocale } = useI18n()
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return new Date(dateString).toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    onMounted(loadOrders)

    return {
      t,
      loading,
      error,
      orders,
      restockOrders,
      getOrdersByStatus,
      getOrderStatusClass,
      formatDate,
      currencySymbol,
      currentCurrency,
      formatCurrency,
      translateProductName,
      translateCustomerName
    }
  }
}
</script>

<style scoped>
/* Fixed table layout to prevent column shifting */
.orders-table {
  table-layout: fixed;
  width: 100%;
}

/* Column widths */
.col-order-number {
  width: 130px;
}

.col-customer {
  width: 180px;
}

.col-items {
  width: 200px;
}

.col-status {
  width: 130px;
}

.col-date {
  width: 140px;
}

.col-value {
  width: 120px;
}

.col-num {
  text-align: right;
}

/* Submitted orders section */
.submitted-orders-note {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: calc(-1 * var(--space-3)) 0 var(--space-4);
}

.restock-orders-table {
  table-layout: fixed;
  width: 100%;
}

.rcol-order-number {
  width: 140px;
}

.rcol-date {
  width: 140px;
}

.rcol-items {
  width: 200px;
}

.rcol-value {
  width: 130px;
}

.rcol-lead-time {
  width: 110px;
}

.rcol-status {
  width: 130px;
}

/* Items details styling */
.items-details {
  position: relative;
}

.items-summary {
  cursor: pointer;
  color: var(--accent);
  font-weight: 500;
  list-style: none;
  user-select: none;
  display: inline-block;
}

.items-summary::-webkit-details-marker {
  display: none;
}

.items-summary::before {
  content: '▶';
  display: inline-block;
  margin-right: var(--space-1);
  font-size: 0.75rem;
  transition: transform 0.2s;
}

.items-details[open] .items-summary::before {
  transform: rotate(90deg);
}

.items-summary:hover {
  color: var(--accent);
  text-decoration: underline;
}

/* Dropdown container - popover content card: elevated, no hairline-only treatment */
.items-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: var(--space-2);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--space-3);
  z-index: 10;
  min-width: 300px;
  max-width: 400px;
}

.item-entry {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2);
  border-bottom: 1px solid var(--canvas);
}

.item-entry:last-child {
  border-bottom: none;
}

.item-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text);
}

.item-meta {
  font-size: 0.813rem;
  color: var(--text-muted);
}
</style>
