import LogStream from '../components/LogStream'

export default function Logs() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-1 gap-4" style={{ minHeight: '480px' }}>
      <LogStream />
    </div>
  )
}
