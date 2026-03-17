import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // State
  const transactions = ref([])
  const currentStatement = ref(null)
  const uploadMessage = ref('')
  const phoneFilter = ref('')
  const sortBy = ref('date')
  const sortOrder = ref('desc')
  
  // Computed
  const filteredTransactions = computed(() => {
    let result = transactions.value
    
    if (phoneFilter.value) {
      result = result.filter(t => t.phone_number === phoneFilter.value)
    }
    
    // Sort
    result.sort((a, b) => {
      let aVal = a[sortBy.value]
      let bVal = b[sortBy.value]
      
      if (aVal === null) return 1
      if (bVal === null) return -1
      
      const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0
      return sortOrder.value === 'asc' ? comparison : -comparison
    })
    
    return result
  })
  
  const phoneNumbers = computed(() => {
    const phones = new Set(transactions.value
      .map(t => t.phone_number)
      .filter(p => p))
    return Array.from(phones).sort()
  })
  
  const transactionStats = computed(() => {
    const total = transactions.value.length
    const debits = transactions.value.filter(t => t.type === 'debit').length
    const credits = transactions.value.filter(t => t.type === 'credit').length
    
    return {
      total,
      debits,
      credits,
      uniquePhones: phoneNumbers.value.length
    }
  })
  
  // Actions
  const setTransactions = (txns) => {
    transactions.value = txns
  }
  
  const addTransactions = (txns) => {
    transactions.value = [...transactions.value, ...txns]
  }
  
  const clearTransactions = () => {
    transactions.value = []
  }
  
  const setCurrentStatement = (stmt) => {
    currentStatement.value = stmt
  }
  
  const setUploadMessage = (msg) => {
    uploadMessage.value = msg
    setTimeout(() => {
      uploadMessage.value = ''
    }, 5000)
  }
  
  const setPhoneFilter = (phone) => {
    phoneFilter.value = phone
  }
  
  const clearPhoneFilter = () => {
    phoneFilter.value = ''
  }
  
  const setSortBy = (field) => {
    sortBy.value = field
  }
  
  const setSortOrder = (order) => {
    sortOrder.value = order
  }
  
  return {
    // State
    transactions,
    currentStatement,
    uploadMessage,
    phoneFilter,
    sortBy,
    sortOrder,
    
    // Computed
    filteredTransactions,
    phoneNumbers,
    transactionStats,
    
    // Actions
    setTransactions,
    addTransactions,
    clearTransactions,
    setCurrentStatement,
    setUploadMessage,
    setPhoneFilter,
    clearPhoneFilter,
    setSortBy,
    setSortOrder
  }
})
