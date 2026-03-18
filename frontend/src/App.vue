<template>
  <div id="app">
    <header>
      <h1>📊 Transaction History Analyzer</h1>
      <p>Upload PDF bank statements and explore analytics by phone and date range</p>
    </header>
    
    <main>
      <!-- Tabs -->
      <nav class="tabs" role="tablist" aria-label="Main views">
        <button
          :class="['tab', activeTab === 'load' ? 'active' : '']"
          role="tab"
          aria-selected="true"
          aria-pressed="activeTab === 'load'"
          @click="activeTab = 'load'"
        >
          Load statement
        </button>
        <button
          :class="['tab', activeTab === 'analytics' ? 'active' : '']"
          role="tab"
          :aria-selected="activeTab === 'analytics'"
          :aria-pressed="activeTab === 'analytics'"
          @click="activeTab = 'analytics'"
        >
          Analytics
        </button>
      </nav>

      <!-- Load_statement Tab -->
      <section v-if="activeTab === 'load'">
        <section class="upload-section">
          <FileUpload
            :disabled="!isBackendReady"
            @upload-success="handleUploadSuccess"
          />
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
        <AnalyticsView :disabled="!isBackendReady" />
      </section>
    </main>

    <!-- Global backend booting overlay -->
    <div
      v-if="!isBackendReady && isCheckingBackend"
      class="boot-overlay"
    >
      <div class="boot-card">
        <div class="boot-spinner"></div>
        <h2>Starting your analysis engine…</h2>
        <p>
          Warming up the server on Render. This can take a few seconds.
          You can upload statements and view analytics as soon as it is ready.
        </p>
      </div>
    </div>
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
const isBackendReady = ref(false)
const isCheckingBackend = ref(true)

async function checkBackendHealth(retries = 10, delayMs = 1500) {
  isCheckingBackend.value = true
  isBackendReady.value = false

  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const res = await fetch('/api/health')
      if (res.ok) {
        const data = await res.json().catch(() => ({}))
        if (data.status === 'ok' || res.ok) {
          isBackendReady.value = true
          break
        }
      }
    } catch (e) {
      // ignore and retry
    }

    await new Promise((resolve) => setTimeout(resolve, delayMs))
  }

  isCheckingBackend.value = false
}

checkBackendHealth()

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

.tabs {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 4px;
  margin: 0 auto 32px auto;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(16px);
}

.tab {
  position: relative;
  min-width: 140px;
  padding: 10px 18px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.85);
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: color 0.2s ease, background-color 0.2s ease, transform 0.15s ease;
}

.tab:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateY(-1px);
}

.tab.active {
  background: #ffffff;
  color: #4b3aa8;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.tab.active:hover {
  background: #ffffff;
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

  .tabs {
    width: 100%;
    justify-content: space-between;
    margin-bottom: 24px;
  }

  .tab {
    flex: 1;
    min-width: 0;
    padding-inline: 8px;
  }
}
</style>
