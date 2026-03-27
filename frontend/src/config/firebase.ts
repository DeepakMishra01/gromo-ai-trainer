import { initializeApp } from 'firebase/app'
import { getAuth, RecaptchaVerifier, signInWithPhoneNumber } from 'firebase/auth'

const firebaseConfig = {
  apiKey: "AIzaSyDEP7eGTNPSa3q4iEdpf3FjswyOpsN5dFM",
  authDomain: "gromo-ai-trainer.firebaseapp.com",
  projectId: "gromo-ai-trainer",
  storageBucket: "gromo-ai-trainer.firebasestorage.app",
  messagingSenderId: "1052334296154",
  appId: "1:1052334296154:web:6ad4cba7407f6bbd5c5c63",
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)

export { RecaptchaVerifier, signInWithPhoneNumber }
