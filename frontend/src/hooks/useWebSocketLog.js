import { useEffect, useRef, useState } from 'react'

export default function useWebSocketLog() {
  const [logs, setLogs] = useState([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef(null)

  useEffect(() => {
    const streamUrl = '/logs/stream'
    const es = new EventSource(streamUrl)
    esRef.current = es
    es.onopen = () => setConnected(true)
    es.onerror = () => {
      setConnected(false)
    }
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setLogs((prev) => [...prev.slice(-300), data])
      } catch (e) {
        // ignore
      }
    }
    return () => {
      esRef.current && esRef.current.close()
    }
  }, [])

  return { logs, connected }
}
