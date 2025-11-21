import { useEffect, useState } from 'react'

export default function AnimatedCount({ value = 0, duration = 300 }) {
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    let start = display
    let startTime
    const animate = (ts) => {
      if (!startTime) startTime = ts
      const progress = Math.min(1, (ts - startTime) / duration)
      const next = Math.round(start + (value - start) * progress)
      setDisplay(next)
      if (progress < 1) requestAnimationFrame(animate)
    }
    requestAnimationFrame(animate)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return <span>{display}</span>
}
