import { useState, useRef, useEffect, useCallback } from 'react'

interface UseVoiceOptions {
  lang?: string
  autoSend?: boolean
  onTranscriptReady?: (text: string) => void
}

export function useVoice(options: UseVoiceOptions = {}) {
  const { lang = 'hi-IN', autoSend = true, onTranscriptReady } = options

  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [speakingId, setSpeakingId] = useState<string | null>(null)

  const recognitionRef = useRef<any>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const speakIdRef = useRef(0) // Track latest speakText call to prevent stale plays
  const onTranscriptReadyRef = useRef(onTranscriptReady)

  // Keep callback ref up to date
  useEffect(() => {
    onTranscriptReadyRef.current = onTranscriptReady
  }, [onTranscriptReady])

  // Initialize speech recognition
  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) return

    const recognition = new SR()
    recognition.lang = lang
    recognition.continuous = false
    recognition.interimResults = true

    recognition.onresult = (event: any) => {
      let finalText = ''
      let interimText = ''
      for (let i = 0; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalText += event.results[i][0].transcript
        } else {
          interimText += event.results[i][0].transcript
        }
      }
      setTranscript(finalText || interimText)
    }

    recognition.onend = () => {
      setIsListening(false)
      setTranscript(prev => {
        if (prev.trim() && autoSend && onTranscriptReadyRef.current) {
          const text = prev.trim()
          setTimeout(() => onTranscriptReadyRef.current?.(text), 300)
        }
        return ''
      })
    }

    recognition.onerror = () => {
      setIsListening(false)
      setTranscript('')
    }

    recognitionRef.current = recognition

    return () => {
      try { recognition.stop() } catch {}
    }
  }, [lang, autoSend])

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return
    // Stop any playing audio first
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
      setIsSpeaking(false)
      setSpeakingId(null)
    }
    setTranscript('')
    setIsListening(true)
    try {
      recognitionRef.current.start()
    } catch {
      setIsListening(false)
    }
  }, [])

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return
    recognitionRef.current.stop()
    setIsListening(false)
  }, [])

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }, [isListening, startListening, stopListening])

  const speakText = useCallback(async (text: string, id?: string) => {
    try {
      // Cancel any in-flight TTS request
      if (abortRef.current) {
        abortRef.current.abort()
      }

      // Stop any currently playing audio
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.currentTime = 0
        audioRef.current = null
      }

      // Track this call — if a newer call comes in, this one should not play
      const callId = ++speakIdRef.current

      setIsSpeaking(true)
      setSpeakingId(id || text.slice(0, 20))

      const controller = new AbortController()
      abortRef.current = controller

      const res = await fetch('/api/agent/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal: controller.signal,
      })

      // If a newer speakText call was made while we were fetching, don't play this one
      if (callId !== speakIdRef.current) return

      if (!res.ok) throw new Error('TTS failed')

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)

      // Double-check we're still the latest call before playing
      if (callId !== speakIdRef.current) {
        URL.revokeObjectURL(url)
        return
      }

      audioRef.current = audio
      abortRef.current = null

      audio.onended = () => {
        setIsSpeaking(false)
        setSpeakingId(null)
        URL.revokeObjectURL(url)
        audioRef.current = null
      }

      audio.onerror = () => {
        setIsSpeaking(false)
        setSpeakingId(null)
        URL.revokeObjectURL(url)
        audioRef.current = null
      }

      await audio.play()
    } catch (err: any) {
      // Don't reset state if this was an intentional abort
      if (err?.name === 'AbortError') return
      setIsSpeaking(false)
      setSpeakingId(null)
    }
  }, [])

  const stopSpeaking = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current = null
    }
    setIsSpeaking(false)
    setSpeakingId(null)
  }, [])

  const hasSpeechRecognition = !!(
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  )

  return {
    // Speech recognition
    isListening,
    transcript,
    startListening,
    stopListening,
    toggleListening,
    hasSpeechRecognition,

    // TTS
    isSpeaking,
    speakingId,
    speakText,
    stopSpeaking,
  }
}
