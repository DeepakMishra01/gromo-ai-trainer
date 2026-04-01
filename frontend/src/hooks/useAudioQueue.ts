import { useState, useRef, useCallback } from 'react'
import { authFetch } from '../api/authFetch'

export interface AudioSegment {
  index: number
  text: string
  audioUrl?: string
  status: 'pending' | 'loading' | 'ready' | 'playing' | 'done'
  duration?: number
}

interface UseAudioQueueOptions {
  speaker?: string
  pace?: number
  model?: string
  onSegmentStart?: (index: number) => void
  onSegmentEnd?: (index: number) => void
  onQueueComplete?: () => void
}

export function useAudioQueue(options: UseAudioQueueOptions = {}) {
  const [segments, setSegments] = useState<AudioSegment[]>([])
  const [currentIndex, setCurrentIndex] = useState(-1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const optionsRef = useRef(options)
  optionsRef.current = options
  const playbackRateRef = useRef(1.0)
  const segmentsRef = useRef<AudioSegment[]>([])

  // Fetch TTS audio for a segment
  const fetchAudio = useCallback(async (segIndex: number): Promise<string | null> => {
    const seg = segmentsRef.current[segIndex]
    if (!seg || seg.status === 'ready' || seg.status === 'playing' || seg.status === 'done') {
      return seg?.audioUrl || null
    }
    if (seg.status === 'loading') return null

    // Mark as loading
    segmentsRef.current = segmentsRef.current.map((s, i) =>
      i === segIndex ? { ...s, status: 'loading' as const } : s
    )
    setSegments([...segmentsRef.current])

    try {
      const body: Record<string, unknown> = { text: seg.text }
      if (optionsRef.current.speaker) body.speaker = optionsRef.current.speaker
      if (optionsRef.current.pace) body.pace = optionsRef.current.pace
      if (optionsRef.current.model) body.model = optionsRef.current.model

      const res = await authFetch('/api/agent/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) throw new Error('TTS failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)

      segmentsRef.current = segmentsRef.current.map((s, i) =>
        i === segIndex ? { ...s, status: 'ready' as const, audioUrl: url } : s
      )
      setSegments([...segmentsRef.current])
      return url
    } catch (err) {
      console.error(`Failed to fetch audio for segment ${segIndex}:`, err)
      // Mark as ready with no audio (will be skipped)
      segmentsRef.current = segmentsRef.current.map((s, i) =>
        i === segIndex ? { ...s, status: 'ready' as const } : s
      )
      setSegments([...segmentsRef.current])
      return null
    }
  }, [])

  // Preload upcoming segments
  const preloadAhead = useCallback((fromIndex: number) => {
    for (let i = fromIndex; i < Math.min(fromIndex + 2, segmentsRef.current.length); i++) {
      const seg = segmentsRef.current[i]
      if (seg && seg.status === 'pending') {
        fetchAudio(i)
      }
    }
  }, [fetchAudio])

  // Play a specific segment
  const playSegment = useCallback(async (index: number) => {
    if (index >= segmentsRef.current.length) {
      setIsPlaying(false)
      setCurrentIndex(-1)
      optionsRef.current.onQueueComplete?.()
      return
    }

    setCurrentIndex(index)
    setIsPlaying(true)
    setIsPaused(false)

    // Preload next segments
    preloadAhead(index + 1)

    // Fetch audio if not ready
    let url: string | null | undefined = segmentsRef.current[index]?.audioUrl
    if (!url) {
      url = await fetchAudio(index)
    }

    if (!url) {
      // Audio failed — show slide for a reasonable time based on narration length
      // Estimate ~3 words/sec reading speed as fallback display time
      const seg = segmentsRef.current[index]
      const wordCount = seg?.text?.split(/\s+/).length || 20
      const displayMs = Math.max(5000, Math.min(wordCount / 3 * 1000, 20000))

      optionsRef.current.onSegmentStart?.(index)
      segmentsRef.current = segmentsRef.current.map((s, i) =>
        i === index ? { ...s, status: 'done' as const } : s
      )
      setSegments([...segmentsRef.current])

      // Wait for reasonable reading time before advancing
      setTimeout(() => {
        optionsRef.current.onSegmentEnd?.(index)
        playSegment(index + 1)
      }, displayMs)
      return
    }

    // Mark as playing
    segmentsRef.current = segmentsRef.current.map((s, i) =>
      i === index ? { ...s, status: 'playing' as const } : s
    )
    setSegments([...segmentsRef.current])
    optionsRef.current.onSegmentStart?.(index)

    // Play audio
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = ''
    }
    const audio = new Audio(url)
    audio.playbackRate = playbackRateRef.current
    audioRef.current = audio

    audio.onended = () => {
      segmentsRef.current = segmentsRef.current.map((s, i) =>
        i === index ? { ...s, status: 'done' as const } : s
      )
      setSegments([...segmentsRef.current])
      optionsRef.current.onSegmentEnd?.(index)

      // Revoke old blob URL to free memory
      if (url) URL.revokeObjectURL(url)

      // Auto-advance
      playSegment(index + 1)
    }

    audio.onerror = () => {
      console.error(`Audio error for segment ${index}`)
      segmentsRef.current = segmentsRef.current.map((s, i) =>
        i === index ? { ...s, status: 'done' as const } : s
      )
      setSegments([...segmentsRef.current])
      optionsRef.current.onSegmentEnd?.(index)
      playSegment(index + 1)
    }

    try {
      await audio.play()
    } catch (err) {
      console.error('Audio play failed:', err)
      playSegment(index + 1)
    }
  }, [fetchAudio, preloadAhead])

  // Public API
  const loadSegments = useCallback((narrations: string[]) => {
    // Clean up old blob URLs
    segmentsRef.current.forEach(s => {
      if (s.audioUrl) URL.revokeObjectURL(s.audioUrl)
    })

    const newSegments: AudioSegment[] = narrations.map((text, i) => ({
      index: i,
      text,
      status: 'pending' as const,
    }))
    segmentsRef.current = newSegments
    setSegments(newSegments)
    setCurrentIndex(-1)
    setIsPlaying(false)
    setIsPaused(false)
  }, [])

  const play = useCallback(() => {
    const startFrom = currentIndex >= 0 ? currentIndex : 0
    playSegment(startFrom)
  }, [currentIndex, playSegment])

  const pause = useCallback(() => {
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause()
      setIsPaused(true)
      setIsPlaying(false)
    }
  }, [])

  const resume = useCallback(() => {
    if (audioRef.current && isPaused) {
      audioRef.current.play()
      setIsPaused(false)
      setIsPlaying(true)
    }
  }, [isPaused])

  const skipToSegment = useCallback((index: number) => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.onended = null
      audioRef.current.onerror = null
    }
    playSegment(index)
  }, [playSegment])

  const setPlaybackRate = useCallback((rate: number) => {
    playbackRateRef.current = rate
    if (audioRef.current) {
      audioRef.current.playbackRate = rate
    }
  }, [])

  // Play an interrupt audio (for doubt answers) — pauses main queue
  const playInterrupt = useCallback(async (text: string): Promise<void> => {
    return new Promise(async (resolve) => {
      // Pause current audio
      const wasPaused = isPaused
      if (audioRef.current && !audioRef.current.paused) {
        audioRef.current.pause()
      }

      try {
        const body: Record<string, unknown> = { text }
        if (optionsRef.current.speaker) body.speaker = optionsRef.current.speaker
        if (optionsRef.current.pace) body.pace = optionsRef.current.pace
        if (optionsRef.current.model) body.model = optionsRef.current.model

        const res = await authFetch('/api/agent/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })

        if (!res.ok) throw new Error('TTS failed')
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)

        const interruptAudio = new Audio(url)
        interruptAudio.playbackRate = playbackRateRef.current

        interruptAudio.onended = () => {
          URL.revokeObjectURL(url)
          // Resume main audio if it wasn't paused before
          if (!wasPaused && audioRef.current) {
            audioRef.current.play().catch(() => {})
            setIsPlaying(true)
            setIsPaused(false)
          }
          resolve()
        }

        interruptAudio.onerror = () => {
          URL.revokeObjectURL(url)
          if (!wasPaused && audioRef.current) {
            audioRef.current.play().catch(() => {})
          }
          resolve()
        }

        await interruptAudio.play()
      } catch {
        // Resume on failure
        if (!wasPaused && audioRef.current) {
          audioRef.current.play().catch(() => {})
        }
        resolve()
      }
    })
  }, [isPaused])

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.onended = null
      audioRef.current.onerror = null
      audioRef.current = null
    }
    if (abortRef.current) {
      abortRef.current.abort()
    }
    setIsPlaying(false)
    setIsPaused(false)
    setCurrentIndex(-1)
    // Clean up blob URLs
    segmentsRef.current.forEach(s => {
      if (s.audioUrl) URL.revokeObjectURL(s.audioUrl)
    })
  }, [])

  return {
    segments,
    currentIndex,
    isPlaying,
    isPaused,
    loadSegments,
    play,
    pause,
    resume,
    skipToSegment,
    setPlaybackRate,
    playInterrupt,
    stop,
  }
}
