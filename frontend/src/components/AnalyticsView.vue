<template>
  <div class="analytics-container">
    <!-- Filters -->
    <section class="filters">
      <div class="filter-row">
        <div class="filter-group">
          <label for="start-date">Start Date</label>
          <input
            id="start-date"
            type="date"
            v-model="startDate"
            :disabled="disabled"
          />
        </div>
        <div class="filter-group">
          <label for="end-date">End Date</label>
          <input
            id="end-date"
            type="date"
            v-model="endDate"
            :disabled="disabled"
          />
        </div>
      </div>

      <div class="filter-row">
        <div class="filter-group">
          <label for="phone">Phone Number</label>
          <input
            id="phone"
            type="text"
            v-model="phone"
            placeholder="e.g. 07*******"
            :disabled="disabled"
          />
        </div>
        <div class="filter-group">
          <label for="sort-by">Sort by</label>
          <select id="sort-by" v-model="sortBy" :disabled="disabled">
            <option value="value_date">Value Date</option>
            <option value="credit">Credit (In)</option>
          </select>
        </div>
        <div class="filter-group sort-order">
          <label>&nbsp;</label>
          <button type="button" :disabled="disabled" @click="toggleSortOrder">
            {{ sortOrder === 'desc' ? '↓ Desc' : '↑ Asc' }}
          </button>
        </div>
      </div>

      <div class="filter-actions">
        <button
          type="button"
          class="apply-btn"
          :disabled="disabled || !canApply || isLoading"
          @click="applyFilters"
        >
          <span v-if="isLoading" class="btn-spinner"></span>
          <span>{{ isLoading ? 'Loading…' : 'Apply filters' }}</span>
        </button>
        <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      </div>
    </section>

    <!-- Summary -->
    <section v-if="rows.length" class="summary">
      <div class="summary-card">
        <div class="summary-label">Total Credit (In)</div>
        <div class="summary-value">{{ formatAmount(totalAmount) }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">Records</div>
        <div class="summary-value">{{ rows.length }}</div>
      </div>
    </section>

    <!-- Table -->
    <section class="table-wrapper">
      <table v-if="rows.length" class="analytics-table">
        <thead>
          <tr>
            <th>Value Date</th>
            <th>Credit (In)</th>
            <th>Phone Number</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ formatDate(row.value_date) }}</td>
            <td class="amount">{{ formatAmount(row.credit) }}</td>
            <td>{{ row.phone_number || '—' }}</td>
          </tr>
        </tbody>
      </table>

      <div v-else class="no-data">
        <p>Set start date, end date, and phone number, then click “Apply filters” to see analytics.</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { getTransactions } from '../utils/api'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
})

const startDate = ref('')
const endDate = ref('')
const phone = ref('')
const sortBy = ref('value_date')
const sortOrder = ref('desc')

const isLoading = ref(false)
const errorMessage = ref('')
const rows = ref([])

const canApply = computed(() => {
  return !!startDate.value && !!endDate.value && !!phone.value
})

const totalAmount = computed(() =>
  rows.value.reduce((sum, r) => sum + (r.credit || 0), 0)
)

function toggleSortOrder() {
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
}

async function applyFilters() {
  if (!canApply.value) return
  isLoading.value = true
  errorMessage.value = ''
  rows.value = []

  try {
    const data = await getTransactions({
      phone: phone.value,
      startDate: startDate.value,
      endDate: endDate.value,
      sortBy: sortBy.value,
      sortOrder: sortOrder.value,
      page: 1,
      limit: 500
    })

    if (data && data.success && Array.isArray(data.transactions)) {
      rows.value = data.transactions
    } else {
      errorMessage.value = data.error || 'Failed to load analytics data'
    }
  } catch (err) {
    errorMessage.value = err.error || err.message || 'Failed to load analytics data'
  } finally {
    isLoading.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

function formatAmount(amount) {
  if (amount === null || amount === undefined) return '—'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(amount)
}
</script>

<style scoped>
.analytics-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filters {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-group {
  flex: 1;
  min-width: 140px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group label {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.filter-group input,
.filter-group select {
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #ddd;
  font-size: 14px;
}

.sort-order button {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #ddd;
  background: #f5f5f5;
  cursor: pointer;
  font-size: 14px;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.apply-btn {
  padding: 10px 18px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.apply-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-text {
  font-size: 13px;
  color: #d32f2f;
}

.summary {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.summary-card {
  flex: 1;
  min-width: 150px;
  background: #ffffff;
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.summary-label {
  font-size: 12px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.summary-value {
  margin-top: 6px;
  font-size: 20px;
  font-weight: 700;
  color: #333;
}

.table-wrapper {
  border-radius: 12px;
  border: 1px solid #ddd;
  overflow-x: auto;
  background: #ffffff;
}

.analytics-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.analytics-table thead {
  background-color: #f5f5f5;
}

.analytics-table th,
.analytics-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.analytics-table th {
  font-weight: 600;
  color: #333;
}

.analytics-table tbody tr:hover {
  background-color: #fafafa;
}

.amount {
  text-align: right;
  font-weight: 600;
  color: #3cb371;
}

.no-data {
  padding: 24px;
  text-align: center;
  color: #777;
  font-size: 14px;
}

@media (max-width: 768px) {
  .filters {
    padding: 16px;
  }

  .filter-row {
    flex-direction: column;
  }

  .analytics-table {
    font-size: 13px;
  }
}
</style>

