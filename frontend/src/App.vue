<template>
  <div id="app">
    <header>
      <h1>📊 Transaction History Analyzer</h1>
      <p>Upload PDF bank statements and explore analytics by phone and date range</p>
    </header>
    
    <main>
      <!-- Tabs -->
      <nav class="tabs">
        <button
          :class="['tab', activeTab === 'load' ? 'active' : '']"
          @click="activeTab = 'load'"
        >
          Load_statement
        </button>
        <button
          :class="['tab', activeTab === 'analytics' ? 'active' : '']"
          @click="activeTab = 'analytics'"
        >
          Analytics
        </button>
      </nav>

      <!-- Load_statement Tab -->
      <section v-if="activeTab === 'load'">
        <section class="upload-section">
          <FileUpload @upload-success="handleUploadSuccess" />
        </section>
        
        <section v-if="store.transactions.length > 0" class="table-section">
          <TransactionTable :transactions="store.transactions" />
        </section>
        
        <div v-else class="placeholder">
          <p>Upload a PDF statement to see transactions</p>
        </div>
      </section>

      <!-- Analytics Tab -->
      <section v-else class="analytics-section">
        <AnalyticsView />
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAppStore } from './store/index'
import FileUpload from './components/FileUpload.vue'
import TransactionTable from './components/TransactionTable.vue'
import AnalyticsView from './components/AnalyticsView.vue'
import { getStatementTransactions } from './utils/api'

const store = useAppStore()
const activeTab = ref('load')

async function handleUploadSuccess(data) {
  // After storing, fetch ALL transactions for this statement (up to 500)
  const statementId = data.statement_id
  let allTxns = data.sample_transactions || []

  if (statementId) {
    try {
      const result = await getStatementTransactions(statementId, 1, 500)
      if (result.success && Array.isArray(result.transactions)) {
        allTxns = result.transactions
      }
    } catch (e) {
      // If fetching full set fails, fall back to sample data
      console.error('Failed to fetch full statement transactions:', e)
    }
  }

  store.setTransactions(allTxns)
  store.setCurrentStatement(statementId)
  const count = data.rows_updated || data.transaction_count || 0
  store.setUploadMessage(`✓ Successfully stored ${count} rows in Neon database`)
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background-color: #f5f5f5;
  color: #333;
}

#app {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

header {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  padding: 40px 20px;
  text-align: center;
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

header h1 {
  font-size: 2.5em;
  margin-bottom: 10px;
}

header p {
  font-size: 1.1em;
  opacity: 0.9;
}

main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.upload-section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  margin-bottom: 40px;
}

.table-section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.placeholder {
  text-align: center;
  padding: 80px 20px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 1.2em;
}

@media (max-width: 768px) {
  header h1 {
    font-size: 1.8em;
  }
  
  header p {
    font-size: 1em;
  }
  
  main {
    padding: 20px 10px;
  }
}
</style>
