<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'create' ? t('purchaseOrder.createTitle') : t('purchaseOrder.viewTitle') }}
            </h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="item-summary">
            <div class="item-summary-header">
              <h4 class="item-name">{{ translateProductName(backlogItem.item_name) }}</h4>
              <div class="item-sku">SKU: <span class="num">{{ backlogItem.item_sku }}</span></div>
            </div>
            <div class="item-summary-stats">
              <div class="stat">
                <span class="stat-label">{{ t('dashboard.inventoryShortages.shortage') }}</span>
                <span class="stat-value num">{{ shortage }} {{ t('dashboard.inventoryShortages.unitsShort') }}</span>
              </div>
              <div class="stat">
                <span class="stat-label">{{ t('dashboard.inventoryShortages.orderId') }}</span>
                <span class="stat-value num">{{ backlogItem.order_id }}</span>
              </div>
            </div>
          </div>

          <!-- Create mode -->
          <form v-if="mode === 'create'" @submit.prevent="handleSubmit">
            <div class="modal-body">
              <div class="form-group">
                <label for="po-supplier">{{ t('purchaseOrder.supplierName') }}</label>
                <input
                  id="po-supplier"
                  v-model="form.supplier_name"
                  type="text"
                  class="po-input"
                  :class="{ 'input-error': fieldErrors.supplier_name }"
                  :placeholder="t('purchaseOrder.supplierNamePlaceholder')"
                />
                <span v-if="fieldErrors.supplier_name" class="field-error">{{ fieldErrors.supplier_name }}</span>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                  <input
                    id="po-quantity"
                    v-model.number="form.quantity"
                    type="number"
                    min="1"
                    step="1"
                    class="po-input"
                    :class="{ 'input-error': fieldErrors.quantity }"
                  />
                  <span v-if="fieldErrors.quantity" class="field-error">{{ fieldErrors.quantity }}</span>
                </div>

                <div class="form-group">
                  <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }}</label>
                  <input
                    id="po-unit-cost"
                    v-model.number="form.unit_cost"
                    type="number"
                    min="0"
                    step="0.01"
                    class="po-input"
                    :class="{ 'input-error': fieldErrors.unit_cost }"
                  />
                  <span v-if="fieldErrors.unit_cost" class="field-error">{{ fieldErrors.unit_cost }}</span>
                </div>
              </div>

              <div class="form-group">
                <label for="po-delivery-date">{{ t('purchaseOrder.expectedDeliveryDate') }}</label>
                <input
                  id="po-delivery-date"
                  v-model="form.expected_delivery_date"
                  type="date"
                  class="po-input"
                  :class="{ 'input-error': fieldErrors.expected_delivery_date }"
                />
                <span v-if="fieldErrors.expected_delivery_date" class="field-error">{{ fieldErrors.expected_delivery_date }}</span>
              </div>

              <div class="form-group">
                <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                <textarea
                  id="po-notes"
                  v-model="form.notes"
                  class="po-textarea"
                  rows="3"
                  :placeholder="t('purchaseOrder.notesPlaceholder')"
                ></textarea>
              </div>

              <div v-if="submitError" class="error">{{ submitError }}</div>
            </div>

            <div class="modal-footer">
              <button type="button" class="btn-secondary" @click="close">{{ t('common.cancel') }}</button>
              <button type="submit" class="btn-primary" :disabled="submitting">
                {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
              </button>
            </div>
          </form>

          <!-- View mode -->
          <template v-else>
            <div class="modal-body">
              <div v-if="loadingView" class="loading">{{ t('common.loading') }}</div>
              <div v-else-if="viewError" class="error">{{ viewError }}</div>
              <div v-else-if="poData" class="info-grid">
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.supplierName') }}</div>
                  <div class="info-value">{{ poData.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value num">{{ poData.quantity }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                  <div class="info-value num">{{ formatCurrency(poData.unit_cost, selectedCurrency) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.totalCost') }}</div>
                  <div class="info-value num">{{ formatCurrency(poData.unit_cost * poData.quantity, selectedCurrency) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.expectedDeliveryDate') }}</div>
                  <div class="info-value num">{{ formatDate(poData.expected_delivery_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                  <div class="info-value">
                    <span class="badge" :class="statusBadgeClass(poData.status)">{{ poData.status }}</span>
                  </div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                  <div class="info-value num">{{ formatDate(poData.created_date) }}</div>
                </div>
                <div v-if="poData.notes" class="info-item info-item-full">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value">{{ poData.notes }}</div>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-secondary" @click="close">{{ t('common.close') }}</button>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { reactive, ref, computed, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'PurchaseOrderModal',
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    backlogItem: {
      type: Object,
      default: null
    },
    mode: {
      type: String,
      default: 'create',
      validator: (value) => ['create', 'view'].includes(value)
    }
  },
  emits: ['close', 'po-created'],
  setup(props, { emit }) {
    const { t, translateProductName, currentLocale, currentCurrency } = useI18n()

    const form = reactive({
      supplier_name: '',
      quantity: 1,
      unit_cost: '',
      expected_delivery_date: '',
      notes: ''
    })
    const fieldErrors = ref({})
    const submitError = ref(null)
    const submitting = ref(false)

    const poData = ref(null)
    const loadingView = ref(false)
    const viewError = ref(null)

    const shortage = computed(() => {
      if (!props.backlogItem) return 0
      return props.backlogItem.quantity_needed - props.backlogItem.quantity_available
    })

    const resetForm = () => {
      form.supplier_name = ''
      form.quantity = shortage.value > 0 ? shortage.value : 1
      form.unit_cost = ''
      form.expected_delivery_date = ''
      form.notes = ''
      fieldErrors.value = {}
      submitError.value = null
    }

    const loadPurchaseOrder = async () => {
      if (!props.backlogItem) return
      loadingView.value = true
      viewError.value = null
      poData.value = null
      try {
        poData.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
      } catch (err) {
        console.error('Failed to load purchase order:', err)
        if (err.response && err.response.status === 404) {
          viewError.value = t('purchaseOrder.errors.notFound')
        } else {
          viewError.value = t('purchaseOrder.errors.loadFailed')
        }
      } finally {
        loadingView.value = false
      }
    }

    // Initialize the modal's state whenever it is opened for a given item/mode
    watch(
      () => [props.isOpen, props.mode, props.backlogItem],
      () => {
        if (!props.isOpen || !props.backlogItem) return
        if (props.mode === 'create') {
          resetForm()
        } else {
          loadPurchaseOrder()
        }
      },
      { immediate: true }
    )

    const validate = () => {
      const errors = {}
      if (!form.supplier_name || !form.supplier_name.trim()) {
        errors.supplier_name = t('purchaseOrder.errors.supplierRequired')
      }
      const quantity = Number(form.quantity)
      if (form.quantity === '' || form.quantity === null || isNaN(quantity) || quantity <= 0) {
        errors.quantity = t('purchaseOrder.errors.quantityPositive')
      }
      const unitCost = Number(form.unit_cost)
      if (form.unit_cost === '' || form.unit_cost === null || isNaN(unitCost)) {
        errors.unit_cost = t('purchaseOrder.errors.unitCostRequired')
      } else if (unitCost < 0) {
        errors.unit_cost = t('purchaseOrder.errors.unitCostNonNegative')
      }
      if (!form.expected_delivery_date) {
        errors.expected_delivery_date = t('purchaseOrder.errors.deliveryDateRequired')
      }
      fieldErrors.value = errors
      return Object.keys(errors).length === 0
    }

    const handleSubmit = async () => {
      submitError.value = null
      if (!validate() || !props.backlogItem) return

      submitting.value = true
      try {
        const response = await api.createPurchaseOrder({
          backlog_item_id: props.backlogItem.id,
          supplier_name: form.supplier_name.trim(),
          quantity: Number(form.quantity),
          unit_cost: Number(form.unit_cost),
          expected_delivery_date: form.expected_delivery_date,
          notes: form.notes.trim() ? form.notes.trim() : undefined
        })
        emit('po-created', response)
      } catch (err) {
        console.error('Failed to create purchase order:', err)
        if (err.response && err.response.status === 409) {
          submitError.value = t('purchaseOrder.errors.duplicate')
        } else if (err.response && err.response.data && typeof err.response.data.detail === 'string') {
          submitError.value = err.response.data.detail
        } else {
          submitError.value = t('purchaseOrder.errors.createFailed')
        }
      } finally {
        submitting.value = false
      }
    }

    const statusBadgeClass = (status) => {
      const normalized = (status || '').toLowerCase()
      if (['approved', 'fulfilled', 'delivered', 'completed'].includes(normalized)) return 'success'
      if (['pending', 'processing', 'ordered'].includes(normalized)) return 'warning'
      if (['cancelled', 'canceled', 'rejected'].includes(normalized)) return 'danger'
      return 'info'
    }

    const formatDate = (dateString) => {
      if (!dateString) return '-'
      // Purchase order dates are date-only (YYYY-MM-DD). Those parse as UTC
      // midnight, which renders as the previous day anywhere west of UTC --
      // an expected delivery of 2026-10-15 showed as October 14 in PDT.
      // Adding a time component forces local-time parsing. Dates that already
      // carry a time, as elsewhere in the app, are left alone.
      const isDateOnly = /^\d{4}-\d{2}-\d{2}$/.test(dateString)
      const date = new Date(isDateOnly ? `${dateString}T00:00:00` : dateString)
      if (isNaN(date.getTime())) return '-'
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' })
    }

    const close = () => {
      emit('close')
    }

    return {
      t,
      translateProductName,
      selectedCurrency: currentCurrency,
      formatCurrency,
      form,
      fieldErrors,
      submitError,
      submitting,
      poData,
      loadingView,
      viewError,
      shortage,
      handleSubmit,
      statusBadgeClass,
      formatDate,
      close
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: var(--space-4);
}

.modal-container {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.close-button:hover {
  background: var(--canvas);
  color: var(--text);
}

.item-summary {
  padding: var(--space-4) var(--space-5);
  background: var(--canvas);
  border-bottom: 1px solid var(--border);
}

.item-summary-header {
  margin-bottom: var(--space-3);
}

.item-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 var(--space-1) 0;
}

.item-sku {
  font-size: 0.813rem;
  color: var(--text-muted);
}

.item-summary-stats {
  display: flex;
  gap: var(--space-6);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.stat-label {
  font-size: 0.688rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.stat-value {
  font-size: 0.938rem;
  font-weight: 700;
  color: var(--text);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-row {
  display: flex;
  gap: var(--space-3);
}

.form-row .form-group {
  flex: 1;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

label {
  font-size: 0.813rem;
  font-weight: 600;
  color: var(--text-muted);
}

.po-input,
.po-textarea {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-family: inherit;
  color: var(--text);
  background: var(--surface);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.po-textarea {
  resize: vertical;
}

.po-input:focus,
.po-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.po-input.input-error,
.po-textarea.input-error {
  border-color: var(--danger);
}

.field-error {
  font-size: 0.75rem;
  color: var(--danger);
}

.modal-footer {
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.btn-secondary {
  padding: var(--space-2) var(--space-4);
  background: var(--canvas);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary:hover {
  background: var(--border);
  border-color: var(--border-strong);
}

.btn-primary {
  padding: var(--space-2) var(--space-4);
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: filter 0.15s ease, opacity 0.15s ease;
  font-family: inherit;
}

.btn-primary:hover:not(:disabled) {
  filter: brightness(0.92);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-4);
}

.info-item-full {
  grid-column: 1 / -1;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
}

.info-value {
  font-size: 0.875rem;
  color: var(--text);
  font-weight: 500;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}

@media (max-width: 640px) {
  .modal-overlay {
    padding: var(--space-2);
  }

  .modal-container {
    max-height: 95vh;
  }

  .modal-header,
  .item-summary,
  .modal-body,
  .modal-footer {
    padding: var(--space-4);
  }

  .form-row {
    flex-direction: column;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
