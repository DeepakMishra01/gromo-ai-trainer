"""
Live AI Trainer Service.
Generates conversational Hinglish narration scripts for live training sessions.
Uses GPT-4o-mini to convert structured product data into natural spoken narration.
"""
import logging
import uuid
from typing import List, Dict, Any, Optional

import httpx

from app.config import settings
from app.services.training_session import create_training_session

logger = logging.getLogger(__name__)


def generate_live_script(product_id: str, db) -> dict:
    """
    Generate a full live training script with narration segments and quiz.
    Each segment maps to one visual slide in the frontend.
    """
    # Get structured session data from existing service
    session = create_training_session(product_id, db)
    product_name = session["product_name"]
    category_name = session["category_name"]

    # Build narration for each section using LLM
    sections = session["sections"]
    quiz = session["quiz"]

    # Generate narration via LLM (single call for all sections)
    narration_segments = _generate_narration(product_name, category_name, sections)

    # Generate quiz narration segments
    quiz_segments = _generate_quiz_segments(product_name, quiz)

    return {
        "session_id": str(uuid.uuid4()),
        "product_id": session["product_id"],
        "product_name": product_name,
        "category_name": category_name,
        "segments": narration_segments,
        "quiz_segments": quiz_segments,
    }


def format_doubt_response(answer_text: str) -> str:
    """
    Format a doubt resolver answer into conversational speech.
    If OpenAI is available, reformat via LLM. Otherwise, do light cleanup.
    """
    if not answer_text:
        return "Maaf kijiye, is sawaal ka jawab abhi available nahi hai."

    # Light cleanup for speech — remove bullets, markdown, make conversational
    import re
    text = answer_text.strip()
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'[#*_]{1,3}', '', text)
    text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\.\s*\.', '.', text)
    text = text.strip()

    # Wrap in conversational frame
    if not text.startswith(("Achha", "Dekhiye", "Haan", "Bilkul", "Toh")):
        text = f"Achha, yeh bahut achha sawaal hai. {text}"

    return text


def _generate_narration(product_name: str, category_name: str, sections: list) -> list:
    """Generate conversational narration for each section using GPT-4o-mini."""
    # Build the section data for the prompt
    section_texts = []
    for s in sections:
        if s["content"]["type"] == "quiz":
            continue  # Quiz handled separately
        items_text = ""
        items = s["content"].get("items", [])
        if items:
            for item in items:
                label = item.get("label", "")
                value = item.get("value", "")
                if label and value:
                    items_text += f"  - {label}: {value}\n"
                elif value:
                    items_text += f"  - {value}\n"

        talking_points = "\n".join(f"  * {tp}" for tp in s.get("talking_points", []))
        tip = s["content"].get("tip", "")
        description = s["content"].get("description", "")
        summary = s["content"].get("summary", "")

        section_texts.append(
            f"Section {s['index'] + 1}: {s['title']}\n"
            f"Description: {description}\n"
            f"Summary: {summary}\n"
            f"Key Points:\n{items_text}"
            f"Talking Points:\n{talking_points}\n"
            f"Tip: {tip}"
        )

    all_sections_text = "\n---\n".join(section_texts)

    system_prompt = """You are Priya, a live AI trainer conducting a training class for GroMo sales partners on a video call.
You are speaking LIVE — write exactly how you would SPEAK, not write.

Rules:
- Use natural Hinglish (Roman Hindi mixed with English) — the way young Indians actually talk
- Short sentences with natural pauses (use commas and dashes)
- Be enthusiastic, energetic, and motivating — like an excited senior colleague
- Include engagement cues: "Samjhe?", "Achha suniye", "Yeh important hai", "Dekho", "Toh basically"
- Each section narration should be 80-150 words
- Do NOT use bullet points, numbers, markdown, or any formatting
- Do NOT use Devanagari script — only Roman (English) letters
- ONLY use facts from the provided data — NEVER fabricate information
- NEVER mention specific payout amounts — say "latest payout ke liye GroMo App check karein"
- Start with a warm greeting introducing yourself and the product
- Use transition phrases between sections: "Ab dekhte hain...", "Chalo aage badhte hain...", "Ab important part..."
- End the last section with excitement about selling: "Toh partners, ab aap ready ho!"

Output format — return ONLY a JSON array of objects, one per section:
[
  {"section_index": 0, "title": "...", "narration": "..."},
  {"section_index": 1, "title": "...", "narration": "..."},
  ...
]

IMPORTANT: The first object (section_index 0) must be a greeting/introduction. Include ALL sections."""

    user_prompt = f"""Product: {product_name}
Category: {category_name}

Sections to narrate:
{all_sections_text}

Generate conversational Hinglish narration for each section as Priya speaking LIVE on a training call. Return ONLY valid JSON array."""

    try:
        if settings.llm_provider == "openai" and settings.openai_api_key:
            return _call_openai_narration(system_prompt, user_prompt, sections)
        else:
            return _build_fallback_narration(product_name, category_name, sections)
    except Exception as e:
        logger.error(f"Failed to generate narration via LLM: {e}")
        return _build_fallback_narration(product_name, category_name, sections)


def _call_openai_narration(system_prompt: str, user_prompt: str, sections: list) -> list:
    """Call OpenAI GPT-4o-mini to generate narration."""
    import json as json_lib

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()

    # Parse JSON from response (handle markdown code blocks)
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    narrations = json_lib.loads(content)

    # Map narrations to segments with slide content
    segments = []
    section_map = {s["index"]: s for s in sections if s["content"]["type"] != "quiz"}

    for narr in narrations:
        idx = narr.get("section_index", len(segments))
        section = section_map.get(idx, {})
        segments.append({
            "index": len(segments),
            "section": section.get("content", {}).get("type", "intro"),
            "title": narr.get("title", section.get("title", "")),
            "narration": narr.get("narration", ""),
            "slide_content": section.get("content", {}),
            "talking_points": section.get("talking_points", []),
        })

    return segments


def _build_fallback_narration(product_name: str, category_name: str, sections: list) -> list:
    """Build template-based narration when LLM is unavailable."""
    segments = []

    for s in sections:
        if s["content"]["type"] == "quiz":
            continue

        content = s["content"]
        items = content.get("items", [])
        items_text = ""
        for item in items[:4]:
            label = item.get("label", "")
            value = item.get("value", "")
            if label and value:
                items_text += f" {label} — {value}."
            elif value:
                items_text += f" {value}."

        # Build template narration based on section type
        if content.get("type") == "intro":
            narration = (
                f"Namaste partners! Main Priya hoon, aapki AI trainer. "
                f"Aaj hum {product_name} ke baare mein detail mein seekhenge. "
                f"Yeh ek {category_name} category ka product hai. "
                f"{content.get('description', '')} "
                f"{content.get('summary', '')} "
                f"Toh chalo shuru karte hain!"
            )
        elif content.get("type") == "benefits":
            narration = (
                f"Ab dekhte hain {product_name} ke benefits kya hain. "
                f"Yeh bahut important hai kyunki customer ko convince karne ke liye "
                f"aapko benefits achhe se pata hone chahiye.{items_text} "
                f"Samjhe? Yeh sab benefits customer ko batayein."
            )
        elif content.get("type") == "process":
            narration = (
                f"Achha, ab important part — process kaise kaam karta hai. "
                f"Customer ko step by step samjhana hai.{items_text} "
                f"Simple hai na? Customer ko bhi aise hi easy tarike se samjhayein."
            )
        elif content.get("type") == "terms":
            narration = (
                f"Ab terms aur conditions ki baat karte hain. "
                f"Yeh bahut zaroori hai — customer ko sab kuch clearly batana chahiye.{items_text} "
                f"Transparency se customer ka trust badhta hai."
            )
        elif content.get("type") == "tips":
            narration = (
                f"Ab selling tips! Yeh golden tips hain jo aapki sales badhayenge.{items_text} "
                f"In tips ko follow karein aur dekhein aapki conversion rate kaise improve hoti hai. "
                f"Toh partners, ab aap ready ho {product_name} sell karne ke liye!"
            )
        else:
            narration = (
                f"Achha suniye, {s['title']} ke baare mein baat karte hain.{items_text}"
            )

        segments.append({
            "index": len(segments),
            "section": content.get("type", "info"),
            "title": s["title"],
            "narration": narration.strip(),
            "slide_content": content,
            "talking_points": s.get("talking_points", []),
        })

    return segments


def _generate_quiz_segments(product_name: str, quiz: list) -> list:
    """Generate quiz narration segments from quiz questions."""
    quiz_segments = []

    # Opening narration
    intro_narration = (
        f"Bahut achha! Ab ek quick quiz lete hain. "
        f"Dekhte hain aapne {product_name} ke baare mein kitna seekha. "
        f"Total {len(quiz)} questions hain. Ready? Chalo shuru karte hain!"
    )
    quiz_segments.append({
        "type": "quiz_intro",
        "narration": intro_narration,
    })

    ordinals = ["Pehla", "Doosra", "Teesra", "Chautha", "Paanchwa"]

    for i, q in enumerate(quiz):
        ordinal = ordinals[i] if i < len(ordinals) else f"Question number {i + 1}"
        options_text = ", ".join(
            f"option {chr(65 + j)}: {opt}"
            for j, opt in enumerate(q["options"])
        )

        question_narration = (
            f"{ordinal} sawaal. {q['question']} "
            f"Options hain — {options_text}. "
            f"Sochiye aur apna jawab select karein."
        )

        correct_letter = chr(65 + q["correct_answer"])
        correct_option = q["options"][q["correct_answer"]]

        correct_feedback = (
            f"Bilkul sahi! Jawab hai option {correct_letter}, {correct_option}. "
            f"Bahut badhiya, aap achhe se seekh rahe ho!"
        )

        incorrect_feedback = (
            f"Nahi, sahi jawab hai option {correct_letter}, {correct_option}. "
            f"Koi baat nahi, galtiyon se seekhte hain!"
        )

        quiz_segments.append({
            "type": "quiz_question",
            "question_index": i,
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "question_narration": question_narration,
            "correct_feedback": correct_feedback,
            "incorrect_feedback": incorrect_feedback,
            "explanation": q.get("explanation", ""),
        })

    return quiz_segments


def generate_completion_narration(score: int, total: int, product_name: str) -> str:
    """Generate a closing narration based on quiz score."""
    percentage = (score / total * 100) if total > 0 else 0

    if percentage >= 80:
        return (
            f"Waah, kamaal kar diya! Aapka score hai {score} out of {total}. "
            f"Aap {product_name} ke expert ban gaye ho. "
            f"Ab jaake confidently sell karo, best of luck!"
        )
    elif percentage >= 60:
        return (
            f"Achha hai! Aapka score hai {score} out of {total}. "
            f"Aap achhe track pe ho. Thoda aur practice karo aur aap top performer ban jaoge. "
            f"All the best!"
        )
    else:
        return (
            f"Aapka score hai {score} out of {total}. "
            f"Koi baat nahi, practice makes perfect! "
            f"Training ek baar aur review karo aur phir se try karo. "
            f"Aap zaroor achha karoge, main aap pe believe karti hoon!"
        )
