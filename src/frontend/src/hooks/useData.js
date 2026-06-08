import { useState, useEffect, useRef } from 'react'

/**
 * Generic data-fetching hook.
 * @param {() => Promise<any[]>} fetchFn  A stable function from services/api.js
 * @returns {{ data: any[], loading: boolean, error: string|null, reload: () => void }}
 */
export function useData(fetchFn) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const fetchRef = useRef(fetchFn)

  const load = () => {
    setLoading(true)
    setError(null)
    let cancelled = false
    fetchRef.current()
      .then(d => { if (!cancelled) setData(Array.isArray(d) ? d : []) })
      .catch(e => { if (!cancelled) setError(e.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }

  useEffect(() => {
    const cleanup = load()
    return cleanup
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error, reload: load }
}
