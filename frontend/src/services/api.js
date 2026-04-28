import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const startValidation = async (documentFile, implFiles = []) => {
  const form = new FormData()
  form.append('document', documentFile)
  implFiles.forEach(f => form.append('implementations', f))
  const { data } = await api.post('/upload/start', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const getJobs = async () => {
  const { data } = await api.get('/upload/jobs')
  return data
}

export const getStatus = async (jobId) => {
  const { data } = await api.get(`/validation/${jobId}/status`)
  return data
}

export const getResults = async (jobId) => {
  const { data } = await api.get(`/validation/${jobId}/results`)
  return data
}

export const getReportUrl = (jobId) => `/api/report/${jobId}`
export const getDownloadUrl = (jobId) => `/api/report/${jobId}/download`

export const checkHealth = async () => {
  const { data } = await api.get('/health')
  return data
}

export default api
