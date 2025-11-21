import { useEffect, useRef, useState } from 'react'

const wsUrl = () => {
  const base = import.meta.env.VITE_WS_BASE || ''
  if (base) return base
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws/logs`
}

export default function useWebSocketLog() {
  const [logs, setLogs] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    const connect = () => {
      const socket = new WebSocket(wsUrl())
      wsRef.current = socket
      socket.onopen = () => setConnected(true)
      socket.onclose = () => {
        setConnected(false)
        setTimeout(connect, 2000)
      }
      socket.onerror = () => socket.close()
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLogs((prev) => [...prev.slice(-300), data])
        } catch (e) {
          // ignore
        }
      }
    }

    connect()
    return () => {
      wsRef.current && wsRef.current.close()
    }
  }, [])

  return { logs, connected }
}
