<template>
  <div class="table-container">
    <div class="table-header">
      <h2>💰 Extracted Transactions</h2>
      
      <!-- Filter and Stats Section -->
      <div class="filter-section">
        <div class="stats">
          <div class="stat-card">
            <div class="stat-value">{{ store.transactionStats.total }}</div>
            <div class="stat-label">Total Transactions</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ store.transactionStats.uniquePhones }}</div>
            <div class="stat-label">Unique Phone Numbers</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ store.transactionStats.debits }}</div>
            <div class="stat-label">Debits</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ store.transactionStats.credits }}</div>
            <div class="stat-label">Credits</div>
          </div>
        </div>
        
        <!-- Phone Filter -->
        <div class="phone-filter">
          <label>Filter by Phone Number:</label>
          <div class="filter-control">
            <select v-model="selectedPhone" @change="applyPhoneFilter">
              <option value="">All Phone Numbers</option>
              <option v-for="phone in store.phoneNumbers" :key="phone" :value="phone">
                {{ phone }}
              </option>
            </select>
            <button 
              v-if="store.phoneFilter" 
              @click="clearFilter"
              class="clear-btn"
            >
              Clear Filter
            </button>
          </div>
        </div>
        
        <!-- Sorting -->
        <div class="sort-controls">
          <label>Sort by:</label>
          <select v-model="store.sortBy">
            <option value="value_date">Value Date</option>
            <option value="credit">Credit (Money In)</option>
            <option value="debit">Debit (Money Out)</option>
            <option value="balance">Balance</option>
          </select>
          <button 
            @click="toggleSortOrder"
            :class="['sort-btn', store.sortOrder]"
          >
            {{ store.sortOrder === 'desc' ? '↓ Descending' : '↑ Ascending' }}
          </button>
        </div>
      </div>
      
      <div v-if="store.phoneFilter" class="active-filter">
        Showing transactions for phone: <strong>{{ store.phoneFilter }}</strong>
        ({{ store.filteredTransactions.length }} transactions)
      </div>
    </div>
    
    <!-- Table -->
    <div class="table-wrapper">
      <table v-if="displayedTransactions.length > 0" class="transactions-table">
        <thead>
          <tr>
            <th>Value Date</th>
            <th>Transaction Details</th>
            <th>Payment Reference</th>
            <th>Credit (In)</th>
            <th>Debit (Out)</th>
            <th>Balance</th>
            <th>Phone Number</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="transaction in displayedTransactions" :key="transaction.id">
            <td class="date">{{ formatDate(transaction.value_date) }}</td>
            <td class="description">{{ truncate(transaction.transaction_details, 40) }}</td>
            <td class="reference">{{ transaction.payment_reference || '—' }}</td>
            <td class="credit">{{ transaction.credit ? formatAmount(transaction.credit) : '—' }}</td>
            <td class="debit">{{ transaction.debit ? formatAmount(transaction.debit) : '—' }}</td>
            <td class="balance">{{ formatAmount(transaction.balance) }}</td>
            <td class="phone">
              <span v-if="transaction.phone_number" class="phone-badge">
                {{ transaction.phone_number }}
              </span>
              <span v-else class="no-phone">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      
      <div v-else class="no-data">
        <p>No transactions found for the selected filters</p>
      </div>
    </div>
    
    <!-- Pagination -->
    <div v-if="displayedTransactions.length > 0" class="pagination">
      <p>Showing {{ displayedTransactions.length }} of {{ store.filteredTransactions.length }} transactions</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../store/index'

const store = useAppStore()
const selectedPhone = ref('')

const displayedTransactions = computed(() => {
  return store.filteredTransactions
})

function applyPhoneFilter() {
  store.setPhoneFilter(selectedPhone.value)
}

function clearFilter() {
  selectedPhone.value = ''
  store.clearPhoneFilter()
}

function toggleSortOrder() {
  store.setSortOrder(store.sortOrder === 'asc' ? 'desc' : 'asc')
}

function formatDate(date) {
  if (!date) return '—'
  const d = new Date(date)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatAmount(amount) {
  if (amount === null || amount === undefined) return '—'
  // Show plain numeric value without currency code/symbol
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(amount)
}

function truncate(text, length) {
  if (!text) return '—'
  return text.length > length ? text.substring(0, length) + '...' : text
}
</script>

<style scoped>
.table-container {
  width: 100%;
}

.table-header {
  margin-bottom: 30px;
}

.table-header h2 {
  margin-bottom: 20px;
  color: #333;
}

.filter-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 12px;
  opacity: 0.9;
}

.phone-filter {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.phone-filter label {
  font-weight: 600;
  color: #333;
}

.filter-control {
  display: flex;
  gap: 10px;
}

.filter-control select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.clear-btn {
  padding: 8px 16px;
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  color: #666;
}

.clear-btn:hover {
  background-color: #efefef;
}

.sort-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sort-controls label {
  font-weight: 600;
  color: #333;
}

.sort-controls select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.sort-btn {
  padding: 8px 16px;
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.3s ease;
}

.sort-btn:hover {
  background-color: #764ba2;
}

.active-filter {
  background-color: #e8f4f8;
  padding: 10px 12px;
  border-radius: 6px;
  border-left: 4px solid #667eea;
  font-size: 14px;
  color: #333;
}

.table-wrapper {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #ddd;
}

.transactions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.transactions-table thead {
  background-color: #f5f5f5;
  border-bottom: 2px solid #ddd;
}

.transactions-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
}

.transactions-table tbody tr {
  border-bottom: 1px solid #eee;
  transition: background-color 0.2s ease;
}

.transactions-table tbody tr:hover {
  background-color: #fafafa;
}

.transactions-table td {
  padding: 12px;
}

.date {
  color: #666;
  font-weight: 500;
  width: 110px;
}

.description {
  color: #333;
}

.reference {
  color: #666;
  font-size: 13px;
  width: 120px;
}

.credit {
  font-weight: 600;
  color: #3cb371;
  width: 110px;
  text-align: right;
}

.debit {
  font-weight: 600;
  color: #d32f2f;
  width: 110px;
  text-align: right;
}

.balance {
  color: #666;
  font-weight: 500;
  width: 100px;
  text-align: right;
}

.phone {
  width: 120px;
}

.phone-badge {
  display: inline-block;
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 13px;
}

.no-phone {
  color: #aaa;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #999;
}

.pagination {
  margin-top: 20px;
  text-align: center;
  color: #666;
  font-size: 14px;
}

@media (max-width: 1024px) {
  .filter-section {
    grid-template-columns: 1fr;
  }
  
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .transactions-table {
    font-size: 12px;
  }
  
  .transactions-table th,
  .transactions-table td {
    padding: 8px;
  }
  
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .phone-filter,
  .sort-controls {
    font-size: 13px;
  }
}
</style>
