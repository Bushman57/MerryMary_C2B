import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const uploadPDF = async (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (event) => {
        if (!onProgress || !event.total) return
        const percent = Math.round((event.loaded / event.total) * 100)
        onProgress(percent)
      },
    })
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Upload failed' }
  }
}

export const getHealth = async () => {
  try {
    const response = await api.get('/health')
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Health check failed' }
  }
}

export const getTransactions = async (filters = {}) => {
  try {
    const params = new URLSearchParams()
    
    if (filters.phone) params.append('phone', filters.phone)
    if (filters.statementId) params.append('statement_id', filters.statementId)
    if (filters.startDate) params.append('start_date', filters.startDate)
    if (filters.endDate) params.append('end_date', filters.endDate)
    if (filters.page) params.append('page', filters.page)
    if (filters.limit) params.append('limit', filters.limit)
    if (filters.sortBy) params.append('sort_by', filters.sortBy)
    if (filters.sortOrder) params.append('sort_order', filters.sortOrder)
    
    const response = await api.get('/transactions?' + params.toString())
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Failed to fetch transactions' }
  }
}

export const getTransactionById = async (id) => {
  try {
    const response = await api.get(`/transactions/${id}`)
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Failed to fetch transaction' }
  }
}

export const getStatements = async () => {
  try {
    const response = await api.get('/statements')
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Failed to fetch statements' }
  }
}

export const getStatementTransactions = async (statementId, page = 1, limit = 50) => {
  try {
    const response = await api.get(`/statements/${statementId}?page=${page}&limit=${limit}`)
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Failed to fetch statement transactions' }
  }
}

export const getTransactionsByPhone = async (phoneNumber, page = 1, limit = 50) => {
  try {
    const response = await api.get(`/transactions/phone/${phoneNumber}?page=${page}&limit=${limit}`)
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Failed to fetch transactions by phone' }
  }
}

export const deleteStatement = async (statementId) => {
  try {
    const response = await api.delete(`/statements/${statementId}`)
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Failed to delete statement' }
  }
}

export const getTransactionStats = async () => {
  try {
    const response = await api.get('/transactions/stats/summary')
    return response.data
  } catch (error) {
    throw error.response?.data || { error: 'Failed to fetch stats' }
  }
}

export default api
