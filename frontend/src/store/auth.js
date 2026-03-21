import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  onIdTokenChanged,
} from 'firebase/auth'
import { auth, googleProvider, hasRequiredConfig } from '../firebase'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const idToken = ref(null)
  const loading = ref(true)
  const authError = ref('')

  const isSignedIn = computed(() => Boolean(user.value && idToken.value))
  const configOk = computed(() => hasRequiredConfig())

  let unsubAuth = null
  let unsubToken = null

  function attachListeners() {
    if (!hasRequiredConfig()) {
      loading.value = false
      authError.value =
        'Firebase is not configured. Add VITE_FIREBASE_* keys to your .env file.'
      return
    }

    if (!auth) {
      loading.value = false
      authError.value = 'Firebase auth could not be initialized.'
      return
    }

    unsubAuth = onAuthStateChanged(auth, (u) => {
      user.value = u
      if (!u) {
        idToken.value = null
        loading.value = false
      }
    })

    unsubToken = onIdTokenChanged(auth, async (u) => {
      try {
        if (u) {
          idToken.value = await u.getIdToken()
        } else {
          idToken.value = null
        }
      } finally {
        loading.value = false
      }
    })
  }

  async function signInWithGoogle() {
    authError.value = ''
    if (!hasRequiredConfig()) {
      authError.value =
        'Firebase is not configured. Set VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID, VITE_FIREBASE_APP_ID.'
      return
    }
    if (!auth) return
    try {
      await signInWithPopup(auth, googleProvider)
    } catch (e) {
      authError.value = e.message || 'Google sign-in failed'
      console.error(e)
    }
  }

  async function signOutUser() {
    authError.value = ''
    if (!auth) return
    try {
      await signOut(auth)
    } catch (e) {
      authError.value = e.message || 'Sign out failed'
    }
    user.value = null
    idToken.value = null
  }

  /** Called when API returns 401 — clear local session without throwing */
  function handleUnauthorized() {
    user.value = null
    idToken.value = null
    if (auth) {
      signOut(auth).catch(() => {})
    }
  }

  return {
    user,
    idToken,
    loading,
    authError,
    isSignedIn,
    configOk,
    attachListeners,
    signInWithGoogle,
    signOutUser,
    handleUnauthorized,
  }
})
