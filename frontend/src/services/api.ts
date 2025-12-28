/**
 * API 클라이언트 설정
 */

import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30초 타임아웃
})

// 응답 인터셉터
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 에러 로깅
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default api
