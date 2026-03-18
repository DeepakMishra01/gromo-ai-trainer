"""
Text-to-Speech service.
Generates audio from text using Sarvam AI (primary) or Edge-TTS (fallback).
"""
import os
import base64
import logging
import asyncio
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Sarvam AI voice mapping (speaker names must be lowercase)
SARVAM_VOICE_MAP = {
    "hindi_female": "ritu",
    "hindi_male": "aditya",
    "hinglish_female": "priya",
    "hinglish_male": "shubh",
    "english_female": "neha",
    "english_male": "rahul",
    # Named voices
    "neerja": "priya",
    "ravi": "aditya",
    "aditi": "neha",
    "kabir": "shubh",
    "priya": "priya",
    "shubh": "shubh",
    "ritu": "ritu",
    "aditya": "aditya",
}

# Sarvam language code mapping
SARVAM_LANG_MAP = {
    "hindi": "hi-IN",
    "hinglish": "hi-IN",
    "english": "en-IN",
}

# Edge-TTS voice mapping (fallback)
EDGE_TTS_VOICE_MAP = {
    "neerja": "hi-IN-SwaraNeural",
    "ravi": "hi-IN-MadhurNeural",
    "aditi": "en-IN-NeerjaNeural",
    "kabir": "en-IN-PrabhatNeural",
    "hindi_female": "hi-IN-SwaraNeural",
    "hindi_male": "hi-IN-MadhurNeural",
    "english_female": "en-IN-NeerjaNeural",
    "english_male": "en-IN-PrabhatNeural",
}

DEFAULT_VOICE = {
    "hindi": "hi-IN-SwaraNeural",
    "hinglish": "en-IN-NeerjaNeural",
    "english": "en-IN-NeerjaNeural",
}


def generate_audio(
    text: str,
    voice_name: str,
    output_path: str,
    language: str = "hinglish",
    target_duration: Optional[float] = None,
) -> str:
    """
    Generate audio from text using the configured TTS provider.

    Args:
        text: Script text to convert to speech.
        voice_name: Voice identifier.
        output_path: Path to save the audio file.
        language: Language code.
        target_duration: Optional target duration in seconds.
            Used to adjust speech pace (Sarvam) or speech rate (Edge-TTS).
    """
    provider = settings.tts_provider
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Pre-process text for better TTS pronunciation
    text = _preprocess_for_tts(text, language)

    # Calculate pace adjustment based on target duration and text length
    pace = _calculate_pace(text, target_duration)

    try:
        if provider == "sarvam":
            return _generate_sarvam(text, voice_name, output_path, language, pace)
        elif provider == "edge_tts":
            return _generate_edge_tts(text, voice_name, output_path, language, pace)
        else:
            return _generate_demo_audio(text, output_path, target_duration)
    except Exception as e:
        logger.error(f"TTS generation failed with provider '{provider}': {e}")
        # Try edge_tts as secondary fallback
        try:
            logger.info("Trying edge_tts as fallback...")
            return _generate_edge_tts(text, voice_name, output_path, language, pace)
        except Exception as e2:
            logger.error(f"Edge-TTS fallback also failed: {e2}")
            return _generate_demo_audio(text, output_path, target_duration)


def _preprocess_for_tts(text: str, language: str = "hinglish") -> str:
    """
    Clean and preprocess text for better TTS pronunciation.
    - Removes script markers like [INTRO], [Screen:...], [SLIDE...]
    - Expands common abbreviations
    - Adds pauses (commas) for natural speech flow
    - Fixes common pronunciation issues with symbols
    """
    import re

    # Remove script markers (not spoken)
    text = re.sub(r'\[(?:INTRO|OUTRO|Screen|SLIDE|CTA|Section)[^\]]*\]', '', text)

    # Remove markdown-style formatting
    text = re.sub(r'[#*_]{1,3}', '', text)
    text = re.sub(r'^[-•→]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+[\.\)]\s*', '', text, flags=re.MULTILINE)

    # Expand currency symbols for proper pronunciation
    text = text.replace('₹', 'rupees ')
    text = text.replace('Rs.', 'rupees')
    text = text.replace('Rs ', 'rupees ')

    # Expand common abbreviations
    abbreviations = {
        'KYC': 'KY C',
        'OTP': 'O T P',
        'PAN': 'PAN card',
        'DOB': 'date of birth',
        'EMI': 'E M I',
        'SIP': 'S I P',
        'FnO': 'F and O',
        'F&O': 'F and O',
        'UPI': 'U P I',
        'NEFT': 'N E F T',
        'IMPS': 'I M P S',
        'ATM': 'A T M',
        'PIN': 'pin',
        'eKYC': 'e KY C',
        'App': 'app',
        'app': 'app',
        'IPO': 'I P O',
        'NRI': 'N R I',
        'AMC': 'A M C',
        'NAV': 'N A V',
        'GST': 'G S T',
        'TDS': 'T D S',
    }
    for abbr, expansion in abbreviations.items():
        text = re.sub(r'\b' + re.escape(abbr) + r'\b', expansion, text)

    # Add natural pauses after periods and before conjunctions
    text = re.sub(r'\.\s+', '. ', text)

    # Clean up excessive whitespace and newlines
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\n', ', ', text)
    text = re.sub(r'\s{2,}', ' ', text)

    # Remove empty parentheses or brackets
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\[\s*\]', '', text)

    # Remove specific payout amounts — payouts change frequently
    text = re.sub(
        r'(?:Rs\.?|₹|INR|rupees)\s*[\d,]+(?:\s*(?:per|/)\s*\w+)?',
        'check GroMo App for latest payout',
        text, flags=re.IGNORECASE,
    )
    text = re.sub(
        r'(?:earn|kamao|kamayein)\s+(?:Rs\.?|₹|rupees)?\s*[\d,]+',
        'earn commission, check GroMo App for latest payout',
        text, flags=re.IGNORECASE,
    )

    # Remove hyphens — Sarvam TTS glitches/loops on hyphenated words
    text = text.replace('-', ' ')

    # Clean trailing/leading whitespace
    text = text.strip()

    return text


def _calculate_pace(text: str, target_duration: Optional[float]) -> float:
    """
    Calculate speech pace based on target duration and text word count.
    Returns pace multiplier where lower = slower, higher = faster.
    Sarvam supports pace 0.5 to 2.0.

    Sarvam Bulbul v3 speaks at approximately 2.7 words/sec at pace=1.0.
    For clear training content, we target ~2.5 words/sec (pace ≈ 0.93).
    """
    import re

    # Default: significantly slower for clear, understandable training audio
    # Target ~2.0 words/sec for comfortable listening (2.0/2.7 ≈ 0.74)
    DEFAULT_PACE = 0.75

    if target_duration is None:
        return DEFAULT_PACE

    # Strip script markers like [INTRO], [Screen:...] etc. before counting words
    clean_text = re.sub(r'\[.*?\]', '', text)
    word_count = len(clean_text.split())

    if word_count <= 0:
        return DEFAULT_PACE

    # Sarvam Bulbul v3 base rate: ~2.7 words/sec at pace=1.0
    SARVAM_BASE_WPS = 2.7

    # Estimate how long Sarvam takes at pace=1.0
    sarvam_natural_duration = word_count / SARVAM_BASE_WPS

    if sarvam_natural_duration <= 0:
        return DEFAULT_PACE

    # pace = natural_duration / target_duration
    # If target is longer than natural → slow down (pace < 1)
    # If target is shorter than natural → speed up (pace > 1)
    raw_pace = sarvam_natural_duration / target_duration

    # Clamp: don't go below 0.55 (too slow/robotic) or above 1.1 (too fast for training)
    pace = max(0.55, min(1.1, raw_pace))

    logger.info(
        f"Duration control: {word_count} words, sarvam natural ~{sarvam_natural_duration:.0f}s, "
        f"target {target_duration:.0f}s → pace {pace:.2f}"
    )
    return pace


def _generate_sarvam(
    text: str,
    voice_name: str,
    output_path: str,
    language: str,
    pace: float = 1.0,
) -> str:
    """Generate audio using Sarvam AI TTS API (Bulbul v3)."""
    if not settings.sarvam_api_key:
        raise ValueError("Sarvam API key not configured")

    # Resolve voice
    voice_key = voice_name.lower().strip()
    speaker = SARVAM_VOICE_MAP.get(voice_key, "shubh")

    # Resolve language code
    lang_code = SARVAM_LANG_MAP.get(language.lower(), "hi-IN")

    # Sarvam TTS has a 2500 char limit per request for v3
    # Split text into chunks if needed
    chunks = _split_text_for_sarvam(text, max_chars=2400)

    all_audio_data = []

    for i, chunk in enumerate(chunks):
        logger.info(f"Sarvam TTS: Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")

        response = httpx.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={
                "api-subscription-key": settings.sarvam_api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": chunk,
                "target_language_code": lang_code,
                "speaker": speaker,
                "model": "bulbul:v3",
                "pace": round(pace, 2),
                "enable_preprocessing": True,
                "output_audio_codec": "mp3",
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        # Decode base64 audio
        audios = data.get("audios", [])
        if audios:
            audio_bytes = base64.b64decode(audios[0])
            all_audio_data.append(audio_bytes)
        else:
            logger.warning(f"Sarvam returned no audio for chunk {i+1}")

    if not all_audio_data:
        raise ValueError("Sarvam AI returned no audio data")

    # Ensure output path ends with .mp3
    if not output_path.endswith(".mp3"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp3" if "." in output_path else output_path + ".mp3"

    # Combine audio chunks
    if len(all_audio_data) == 1:
        with open(output_path, "wb") as f:
            f.write(all_audio_data[0])
    else:
        # Concatenate MP3 files (MP3 frames are independently decodable)
        with open(output_path, "wb") as f:
            for audio_data in all_audio_data:
                f.write(audio_data)

    logger.info(f"Sarvam TTS audio saved to {output_path} ({len(all_audio_data)} chunks)")
    return output_path


def _split_text_for_sarvam(text: str, max_chars: int = 2400) -> list:
    """Split text into chunks for Sarvam API (max 2500 chars per request)."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = text.replace('\n', '. ').split('. ')
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # If adding this sentence exceeds limit, save current chunk
        if len(current_chunk) + len(sentence) + 2 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
        else:
            current_chunk += sentence + ". "

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text[:max_chars]]


def _generate_edge_tts(
    text: str,
    voice_name: str,
    output_path: str,
    language: str,
    pace: float = 1.0,
) -> str:
    """Generate audio using edge-tts library (free Microsoft TTS)."""
    import edge_tts

    # Resolve voice
    voice_key = voice_name.lower().strip()
    voice_id = EDGE_TTS_VOICE_MAP.get(voice_key)
    if not voice_id:
        for map_key, vid in EDGE_TTS_VOICE_MAP.items():
            if map_key in voice_key or voice_key in map_key:
                voice_id = vid
                break
    if not voice_id:
        voice_id = DEFAULT_VOICE.get(language, "en-IN-NeerjaNeural")

    logger.info(f"Using edge-tts voice: {voice_id} (pace: {pace:.2f})")

    if not output_path.endswith(".mp3"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp3" if "." in output_path else output_path + ".mp3"

    # Convert pace to Edge-TTS rate string (e.g., "+20%", "-10%")
    # Pace 0.75 → -25% rate, pace 0.7 → -30%, pace 1.0 → 0%
    rate_pct = int((pace - 1.0) * 100)
    rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"
    logger.info(f"Edge-TTS rate adjustment: pace={pace:.2f} → rate={rate_str}")

    async def _run():
        communicate = edge_tts.Communicate(text, voice_id, rate=rate_str)
        await communicate.save(output_path)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_run())).result()
        else:
            loop.run_until_complete(_run())
    except RuntimeError:
        asyncio.run(_run())

    logger.info(f"Edge-TTS audio saved to {output_path}")
    return output_path


def _generate_demo_audio(text: str, output_path: str, target_duration: Optional[float] = None) -> str:
    """Create a silent placeholder audio file using moviepy 2.x."""
    from moviepy import AudioClip
    import numpy as np

    word_count = len(text.split())
    if target_duration:
        duration = max(10.0, min(target_duration, 300.0))
    else:
        duration = max(10.0, min(word_count / 3.0, 120.0))

    logger.info(f"Generating demo silent audio: {duration:.1f}s for {word_count} words")

    def make_frame(t):
        # Return shape (nsamples, nchannels) for mono
        if isinstance(t, (int, float)):
            return np.array([[0.001 * np.sin(2 * np.pi * 440 * t)]])
        return np.column_stack([0.001 * np.sin(2 * np.pi * 440 * t)])

    audio_clip = AudioClip(make_frame, duration=duration, fps=22050)

    if not output_path.endswith(".mp3"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp3" if "." in output_path else output_path + ".mp3"

    audio_clip.write_audiofile(output_path, fps=22050, nbytes=2, codec="libmp3lame", logger=None)
    audio_clip.close()

    logger.info(f"Demo audio saved to {output_path}")
    return output_path
