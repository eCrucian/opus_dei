import { useState, useEffect, useRef } from 'react'
import { getStatus, getResults } from '../services/api'

const POLL_INTERVAL_MS = 3000
const DONE_STATUSES = ['done', 'error']

export function useValidation(jobId) {
  const [status, setStatus] = useState(null)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const timerRef = useRef(null)

  useEffect(() => {
    if (!jobId) return

    const poll = async () => {
      try {
        const s = await getStatus(jobId)
        setStatus(s)

        if (DONE_STATUSES.includes(s.status)) {
          clearInterval(timerRef.current)
          if (s.status === 'done') {
            const r = await getResults(jobId)
            setResults(r)
          } else {
            setError(s.error || 'Erro desconhecido')
          }
        }
      } catch (err) {
        setError(err.message)
        clearInterval(timerRef.current)
      }
    }

    poll()
    timerRef.current = setInterval(poll, POLL_INTERVAL_MS)
    return () => clearInterval(timerRef.current)
  }, [jobId])

  return { status, results, error }
}
