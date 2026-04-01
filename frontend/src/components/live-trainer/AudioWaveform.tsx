interface AudioWaveformProps {
  active: boolean
  barCount?: number
  className?: string
}

export default function AudioWaveform({ active, barCount = 5, className = '' }: AudioWaveformProps) {
  return (
    <div className={`flex items-end gap-0.5 h-5 ${className}`}>
      {Array.from({ length: barCount }).map((_, i) => (
        <div
          key={i}
          className={`w-1 rounded-full transition-all duration-150 ${
            active
              ? 'bg-primary-500 dark:bg-primary-400'
              : 'bg-gray-300 dark:bg-gray-600'
          }`}
          style={{
            height: active ? undefined : '4px',
            animation: active
              ? `waveform ${0.4 + i * 0.1}s ease-in-out infinite alternate`
              : 'none',
          }}
        />
      ))}
      <style>{`
        @keyframes waveform {
          0% { height: 4px; }
          100% { height: 20px; }
        }
      `}</style>
    </div>
  )
}
