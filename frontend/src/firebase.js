/**
 * Firebase client (Google Sign-In). Set VITE_FIREBASE_* in .env (see README / DEPLOY.md).
 */
import { initializeApp, getApps } from 'firebase/app'
import { getAuth, GoogleAuthProvider } from 'firebase/auth'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || undefined,
}

export function hasRequiredConfig() {
  return Boolean(
    firebaseConfig.apiKey &&
      firebaseConfig.authDomain &&
      firebaseConfig.projectId &&
      firebaseConfig.appId
  )
}

function getOrInitApp() {
  if (!hasRequiredConfig()) return null
  if (getApps().length) return getApps()[0]
  return initializeApp(firebaseConfig)
}

const app = getOrInitApp()

/** null when Firebase env vars are missing */
export const auth = app ? getAuth(app) : null
export const googleProvider = new GoogleAuthProvider()
