<template>
  <div id="app">
    <header>
      <div class="header-inner">
        <div class="header-titles">
          <h1>📊 Transaction History Analyzer</h1>
          <p>Upload PDF bank statements and explore analytics by phone and date range</p>
        </div>
        <div v-if="authStore.configOk && authStore.isSignedIn" class="header-auth">
          <span class="user-email" :title="authStore.user?.email || ''">{{
            authStore.user?.email
          }}</span>
          <button type="button" class="btn-signout" @click="authStore.signOutUser">
            Sign out
          </button>
        </div>
      </div>
    </header>

    <main v-if="authStore.loading" class="auth-loading">
      <div class="auth-loading-card">
        <div class="boot-spinner small"></div>
        <p>Checking sign-in…</p>
      </div>
    </main>

    <main v-else-if="!authStore.isSignedIn" class="auth-gate">
      <div class="auth-card">
        <h2>Sign in</h2>
        <p class="auth-sub">Login  to access uploads and analytics.</p>
        <p v-if="authStore.authError" class="auth-err">{{ authStore.authError }}</p>
        <button
          type="button"
          class="btn-google"
          :disabled="!authStore.configOk"
          aria-label="Sign in with Google"
          @click="authStore.signInWithGoogle"
        >
          <span class="btn-google__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" focusable="false">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
          </span>
          <span class="btn-google__label">Sign in with Google</span>
        </button>
        <p v-if="!authStore.configOk" class="auth-hint">
          Add <code>VITE_FIREBASE_*</code> variables to your frontend <code>.env</code> (see
          README).
        </p>
      </div>
    </main>

    <main v-else>
      <!-- Tabs -->
      <nav class="tabs" role="tablist" aria-label="Main views">
        <button
          :class="['tab', activeTab === 'load' ? 'active' : '']"
          role="tab"
          :aria-selected="activeTab === 'load'"
          :aria-pressed="activeTab === 'load'"
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
          <FileUpload :disabled="!canUseApp" @upload-success="handleUploadSuccess" />
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
        <AnalyticsView :disabled="!canUseApp" />
      </section>
    </main>

    <!-- Backend cold start (only after signed in) -->
    <div
      v-if="authStore.isSignedIn && !isBackendReady && isCheckingBackend"
      class="boot-overlay"
    >
      <div class="boot-card">
        <div class="boot-spinner"></div>
        <h2>Starting your analysis engine…</h2>
        <p>
          Warming up the server on Render. This can take a few seconds. You can upload statements
          and view analytics as soon as it is ready.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAppStore } from './store/index'
import { useAuthStore } from './store/auth'
import FileUpload from './components/FileUpload.vue'
import TransactionTable from './components/TransactionTable.vue'
import AnalyticsView from './components/AnalyticsView.vue'
import { getHealth, getStatementTransactions } from './utils/api'

const store = useAppStore()
const authStore = useAuthStore()
const activeTab = ref('load')
const isBackendReady = ref(false)
const isCheckingBackend = ref(true)

const canUseApp = computed(() => isBackendReady.value && authStore.isSignedIn)

async function checkBackendHealth(retries = 10, delayMs = 1500) {
  isCheckingBackend.value = true
  isBackendReady.value = false

  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const data = await getHealth()
      if (data && data.status === 'ok') {
        isBackendReady.value = true
        break
      }
    } catch (e) {
      // ignore and retry
    }

    await new Promise((resolve) => setTimeout(resolve, delayMs))
  }

  isCheckingBackend.value = false
}

watch(
  () => authStore.isSignedIn,
  (signedIn) => {
    if (signedIn) {
      checkBackendHealth()
    } else {
      isBackendReady.value = false
      isCheckingBackend.value = false
    }
  },
  { immediate: true }
)

async function handleUploadSuccess(data) {
  const statementId = data.statement_id
  let allTxns = data.sample_transactions || []

  if (statementId) {
    try {
      const result = await getStatementTransactions(statementId, 1, 500)
      if (result.success && Array.isArray(result.transactions)) {
        allTxns = result.transactions
      }
    } catch (e) {
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
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell,
    sans-serif;
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
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.header-titles {
  text-align: center;
  flex: 1;
  min-width: 200px;
}

.header-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-email {
  font-size: 0.9rem;
  opacity: 0.95;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-signout {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.15);
  color: white;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-signout:hover {
  background: rgba(255, 255, 255, 0.25);
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

.auth-loading,
.auth-gate {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 48px;
}

.auth-loading-card,
.auth-card {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12);
  max-width: 420px;
  width: 100%;
  text-align: center;
}

.auth-card h2 {
  margin-bottom: 8px;
  color: #333;
}

.auth-sub {
  color: #666;
  font-size: 0.95rem;
  margin-bottom: 20px;
}

.auth-err {
  color: #c62828;
  font-size: 0.9rem;
  margin-bottom: 16px;
}

.auth-hint {
  margin-top: 16px;
  font-size: 0.85rem;
  color: #777;
}

.auth-hint code {
  font-size: 0.8rem;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
}

/* Google Sign-In branded button (aligned with common "Sign in with Google" appearance) */
.btn-google {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 40px;
  padding: 0 16px 0 14px;
  margin: 0 auto;
  font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.25px;
  color: #1f1f1f;
  background: #fff;
  border: 1px solid #747775;
  border-radius: 4px;
  box-shadow:
    0 1px 2px 0 rgba(60, 64, 67, 0.3),
    0 1px 3px 1px rgba(60, 64, 67, 0.15);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    box-shadow 0.15s ease;
}

.btn-google__icon {
  display: flex;
  flex-shrink: 0;
  width: 20px;
  height: 20px;
}

.btn-google__icon svg {
  width: 100%;
  height: 100%;
  display: block;
}

.btn-google__label {
  line-height: 1;
  padding: 1px 0;
}

.btn-google:hover:not(:disabled) {
  background: #f8f9fa;
  box-shadow:
    0 1px 2px 0 rgba(60, 64, 67, 0.3),
    0 2px 6px 2px rgba(60, 64, 67, 0.15);
}

.btn-google:active:not(:disabled) {
  background: #f1f3f4;
  box-shadow:
    0 1px 2px 0 rgba(60, 64, 67, 0.3),
    0 1px 3px 1px rgba(60, 64, 67, 0.15);
}

.btn-google:focus-visible {
  outline: 2px solid #1a73e8;
  outline-offset: 2px;
}

.btn-google:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.boot-spinner.small {
  width: 28px;
  height: 28px;
  margin: 0 auto 12px;
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

.boot-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top, rgba(255, 255, 255, 0.28), rgba(0, 0, 0, 0.65));
  z-index: 999;
}

.boot-card {
  max-width: 420px;
  width: 90%;
  padding: 24px 22px 20px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.9);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.4);
  color: #eef2ff;
  text-align: center;
}

.boot-card h2 {
  font-size: 1.3rem;
  margin-bottom: 8px;
}

.boot-card p {
  font-size: 0.9rem;
  opacity: 0.9;
}

.boot-spinner {
  width: 36px;
  height: 36px;
  margin: 0 auto 14px;
  border-radius: 999px;
  border: 3px solid rgba(129, 140, 248, 0.3);
  border-top-color: #a5b4fc;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
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
