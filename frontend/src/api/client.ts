import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? '/api'

export const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
})
