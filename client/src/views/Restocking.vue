<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-top">
          <div>
            <div class="budget-label">{{ t('restocking.availableBudget') }}</div>
            <p class="budget-help">{{ t('restocking.budgetHelp') }}</p>
          </div>
          <div class="budget-value num">{{ formatCurrency(budget, currentCurrency) }}</div>
        </div>
        <input
          type="range"
          min="0"
          max="500000"
          step="5000"
          v-model.number="budget"
          class="budget-slider"
          :style="sliderStyle"
        />
        <p v-if="plan" class="plan-cost">
          {{ t('restocking.planCost', { cost: formatCurrency(plan.total_recommended_cost, currentCurrency) }) }}
        </p>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.availableBudget') }}</div>
          <div class="stat-value num">{{ formatCurrency(budget, currentCurrency) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.allocated') }}</div>
          <div class="stat-value num">{{ formatCurrency(allocated, currentCurrency) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value num">{{ formatCurrency(remaining, currentCurrency) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.itemsSelected') }}</div>
          <div class="stat-value num">{{ includedCount }}</div>
        </div>
      </div>

      <div v-if="submittedOrder" class="success-banner">
        <span>{{ t('restocking.orderPlaced', { orderNumber: submittedOrder.order_number }) }}</span>
        <router-link to="/orders">{{ t('restocking.viewInOrders') }}</router-link>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
          <button
            class="place-order-btn"
            :disabled="includedCount === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="items.length === 0" class="no-data">{{ t('restocking.noRecommendations') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.warehouse') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.urgency') }}</th>
                <th>{{ t('restocking.table.onHand') }}</th>
                <th>{{ t('restocking.table.forecast') }}</th>
                <th>{{ t('restocking.table.recommendedQty') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.estimatedCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
                <th>{{ t('restocking.table.included') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in items"
                :key="item.item_sku"
                :class="{ 'excluded-row': !item.included }"
              >
                <td><strong class="num">{{ item.item_sku }}</strong></td>
                <td>{{ translateProductName(item.item_name) }}</td>
                <td>{{ item.warehouse }}</td>
                <td>{{ item.category }}</td>
                <td><span :class="['badge', item.urgency]">{{ t(`priority.${item.urgency}`) }}</span></td>
                <td><span class="num">{{ item.quantity_on_hand }}</span></td>
                <td><span class="num">{{ item.forecasted_demand }}</span></td>
                <td><strong class="num">{{ item.recommended_quantity }}</strong></td>
                <td><span class="num">{{ formatCurrency(item.unit_cost, currentCurrency) }}</span></td>
                <td><span class="num">{{ formatCurrency(item.estimated_cost, currentCurrency) }}</span></td>
                <td>{{ t('orders.leadTimeDays', { days: item.lead_time_days }) }}</td>
                <td>
                  <span v-if="item.included" class="included-badge">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      <path d="M2 7L5.5 10.5L12 3.5" style="stroke: var(--success)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    {{ t('restocking.included') }}
                  </span>
                  <span v-else class="excluded-text">{{ t('restocking.overBudget') }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const budget = ref(150000)
    const plan = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submittedOrder = ref(null)

    let budgetDebounceTimer = null
    // The budget watcher is debounced but the filter watcher is not, so two
    // requests can be in flight at once. Only the newest may write to `plan`.
    let latestRequestId = 0

    const items = computed(() => (plan.value && plan.value.items) || [])
    const includedItems = computed(() => items.value.filter(item => item.included))
    const includedCount = computed(() => (plan.value ? plan.value.included_count : 0))
    const allocated = computed(() => (plan.value ? plan.value.total_cost : 0))
    const remaining = computed(() => (plan.value ? plan.value.remaining_budget : budget.value))
    const sliderStyle = computed(() => {
      const percent = Math.min(100, Math.max(0, (budget.value / 500000) * 100))
      return {
        background: `linear-gradient(to right, var(--accent) 0%, var(--accent) ${percent}%, var(--border) ${percent}%, var(--border) 100%)`
      }
    })

    const loadRecommendations = async () => {
      const requestId = ++latestRequestId
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()
        const result = await api.getRestockRecommendations({
          budget: budget.value,
          warehouse: filters.warehouse,
          category: filters.category
        })
        if (requestId !== latestRequestId) return
        plan.value = result
      } catch (err) {
        if (requestId !== latestRequestId) return
        error.value = 'Failed to load restock recommendations: ' + err.message
      } finally {
        if (requestId === latestRequestId) loading.value = false
      }
    }

    watch([selectedLocation, selectedCategory], () => {
      loadRecommendations()
    })

    watch(budget, () => {
      if (budgetDebounceTimer) clearTimeout(budgetDebounceTimer)
      budgetDebounceTimer = setTimeout(() => {
        loadRecommendations()
      }, 200)
    })

    onMounted(loadRecommendations)

    onUnmounted(() => {
      if (budgetDebounceTimer) clearTimeout(budgetDebounceTimer)
    })

    const placeOrder = async () => {
      if (includedCount.value === 0 || submitting.value) return

      try {
        submitting.value = true
        error.value = null
        submittedOrder.value = await api.createRestockOrder({
          budget: budget.value,
          items: includedItems.value.map(item => ({
            item_sku: item.item_sku,
            quantity: item.recommended_quantity
          }))
        })
        await loadRecommendations()
      } catch (err) {
        error.value = 'Failed to place restock order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    return {
      t,
      currentCurrency,
      translateProductName,
      formatCurrency,
      budget,
      plan,
      loading,
      error,
      submitting,
      submittedOrder,
      items,
      includedCount,
      allocated,
      remaining,
      sliderStyle,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.budget-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6);
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-muted);
}

.budget-help {
  color: var(--text-muted);
  font-size: 0.875rem;
  margin-top: var(--space-1);
}

.budget-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: -0.025em;
  white-space: nowrap;
}

.budget-slider {
  width: 100%;
  height: 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-strong);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  margin: var(--space-5) 0 var(--space-3);
}

.budget-slider:focus {
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.4);
  transition: transform 0.15s ease;
}

.budget-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.4);
}

.budget-slider::-moz-range-track {
  height: 6px;
  border-radius: var(--radius-sm);
  background: var(--border);
}

.plan-cost {
  color: var(--text-muted);
  font-size: 0.875rem;
}

.success-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-5);
  font-size: 0.938rem;
}

.success-banner a {
  color: var(--success);
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}

.success-banner a:hover {
  text-decoration: underline;
}

.place-order-btn {
  padding: var(--space-2) var(--space-6);
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, opacity 0.2s ease;
  white-space: nowrap;
}

.place-order-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-data {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-muted);
  font-size: 0.938rem;
}

.excluded-row {
  opacity: 0.5;
}

.excluded-row td {
  color: #94a3b8;
}

.included-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--success);
  font-weight: 600;
  font-size: 0.813rem;
}

.excluded-text {
  color: #94a3b8;
  font-size: 0.813rem;
  font-style: italic;
}
</style>
