"""Proof-of-concept integration tests for OpenRouter API.

These tests make LIVE calls to OpenRouter and require OPENROUTER_API_KEY
to be set in the environment.  They are deliberately skipped when the key
is absent so they never break the standard CI suite.

Run manually:
    OPENROUTER_API_KEY=sk-or-... pytest web/tests/test_openrouter_integration.py -v

What is covered:
  - Chat completion (free text model round-trip)
  - Vision / image description (base64 image payload)
  - PDF text extraction via vision model (first-page image probe)
  - Audio transcription via Whisper-compatible endpoint
"""

from __future__ import annotations

import base64
import io
import os
import sys
import wave
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from acb_large_print_web.credentials import get_openrouter_api_key
from acb_large_print_web import ai_features
from acb_large_print_web import ai_features

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_AUDIO_URL = f"{OPENROUTER_BASE}/audio/transcriptions"

_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip() or get_openrouter_api_key()

skip_no_key = pytest.mark.skipif(
    (not _API_KEY) or (not ai_features.ai_chat_enabled()),
    reason="OpenRouter API key not set or AI chat disabled -- skipping live OpenRouter integration tests",
)


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_API_KEY}",
        "HTTP-Referer": "https://letitglow.app",
        "X-Title": "GLOW Integration Tests",
        "Content-Type": "application/json",
    }


def _chat(model: str, messages: list[dict], max_tokens: int = 128) -> str:
    """POST a chat completion and return the assistant text."""
    resp = requests.post(
        f"{OPENROUTER_BASE}/chat/completions",
        headers=_auth_headers(),
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _tiny_png_bytes() -> bytes:
    """Return a minimal valid 1x1 red PNG as bytes (no external file needed)."""
    import zlib
    import struct

    def _chunk(tag: bytes, data: bytes) -> bytes:
        c = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", c)

    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xFF\x00\x00"  # filter byte + R G B
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


def _silent_wav_bytes(duration_seconds: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Generate a minimal silent WAV file in memory."""
    buf = io.BytesIO()
    n_frames = int(sample_rate * duration_seconds)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Chat tests
# ---------------------------------------------------------------------------


@skip_no_key
class TestOpenRouterChat:
    """Basic chat completion round-trips."""

    def test_primary_model_responds(self) -> None:
        """The primary model returns a non-empty answer."""
        answer = _chat(
            "openai/gpt-4o-mini",
            [
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": "Reply with exactly the word: HELLO"},
            ],
        )
        assert answer  # non-empty
        assert len(answer) < 500  # reasonable length

    def test_response_contains_expected_word(self) -> None:
        """The model follows a strict instruction."""
        answer = _chat(
            "openai/gpt-4o-mini",
            [
                {"role": "user", "content": "What is 2+2? Reply with just the number."},
            ],
            max_tokens=10,
        )
        assert "4" in answer

    def test_fallback_model_responds(self) -> None:
        """The paid fallback model (gpt-4o-mini) also responds."""
        answer = _chat(
            "openai/gpt-4o-mini",
            [{"role": "user", "content": "Say 'OK' and nothing else."}],
            max_tokens=10,
        )
        assert answer

    def test_gateway_chat_function(self) -> None:
        """acb_large_print_web.ai_gateway.chat() returns a string."""
        from acb_large_print_web.ai_gateway import chat

        answer, escalated = chat(
            question="Reply with one word: GLOW",
            system_prompt="You are a concise assistant.",
            session_hash="test-integration-chat",
        )
        assert isinstance(answer, str)
        assert answer  # non-empty
        assert isinstance(escalated, bool)


# ---------------------------------------------------------------------------
# Vision / image description tests
# ---------------------------------------------------------------------------


@skip_no_key
class TestOpenRouterVision:
    """Image description round-trips using a vision-capable model."""

    _VISION_MODEL = "openai/gpt-4o-mini"

    def _describe_image(self, image_bytes: bytes, mime: str, prompt: str) -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_uri = f"data:{mime};base64,{encoded}"
        resp = requests.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers=_auth_headers(),
            json={
                "model": self._VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.0,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def test_describe_tiny_png(self) -> None:
        """Vision model returns a description for a minimal PNG."""
        desc = self._describe_image(
            _tiny_png_bytes(), "image/png", "Describe this image in one sentence."
        )
        assert desc  # non-empty description
        assert len(desc) < 1000

    def test_gateway_describe_image_function(self) -> None:
        """acb_large_print_web.ai_gateway.describe_image() returns a string."""
        from acb_large_print_web.ai_gateway import describe_image

        result = describe_image(
            image_bytes=_tiny_png_bytes(),
            mime_type="image/png",
            prompt="What is in this image?",
            session_hash="test-integration-vision",
        )
        assert isinstance(result, str)
        assert result


# ---------------------------------------------------------------------------
# PDF extraction via vision model
# ---------------------------------------------------------------------------


@skip_no_key
class TestOpenRouterPDFExtraction:
    """PDF text extraction using a vision model on a rendered page image.

    This is a probe test -- it uses a tiny synthetic image representing a
    'page' rather than a full PDF render pipeline.  The real converter uses
    WeasyPrint → PNG → OpenRouter, but the API contract is identical.
    """

    _VISION_MODEL = "openai/gpt-4o-mini"

    def test_extract_text_from_page_image(self) -> None:
        """Vision model can be prompted to extract text from an image of a page."""
        # Use our minimal PNG as a stand-in for a rendered PDF page.
        encoded = base64.b64encode(_tiny_png_bytes()).decode("ascii")
        data_uri = f"data:image/png;base64,{encoded}"
        resp = requests.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers=_auth_headers(),
            json={
                "model": self._VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "This is a rendered page image from a PDF. "
                                    "Extract all readable text from it. "
                                    "If there is no text, reply with: [no text found]"
                                ),
                            },
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                "max_tokens": 400,
                "temperature": 0.0,
            },
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"].strip()
        # A 1×1 solid-colour image has no text; the model should say so.
        assert result
        assert len(result) < 1000

    def test_pdf_extraction_response_structure(self) -> None:
        """OpenRouter response for a vision request has the expected shape."""
        encoded = base64.b64encode(_tiny_png_bytes()).decode("ascii")
        data_uri = f"data:image/png;base64,{encoded}"
        resp = requests.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers=_auth_headers(),
            json={
                "model": self._VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "List any text visible in this image."},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                "max_tokens": 100,
            },
            timeout=60,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]
        assert "usage" in data


# ---------------------------------------------------------------------------
# Audio transcription via Whisper
# ---------------------------------------------------------------------------


skip_whisper = pytest.mark.skipif(
    (not _API_KEY) or (not ai_features.ai_whisperer_enabled()),
    reason="OpenRouter Whisper not configured or AI whisperer disabled",
)


@skip_whisper
class TestOpenRouterWhisper:
    """Audio transcription round-trips using the OpenRouter Whisper endpoint."""

    _WHISPER_MODEL = "openai/whisper-large-v3"

    def test_transcribe_silent_wav(self) -> None:
        """Whisper accepts a silent WAV file and returns a string response."""
        audio_bytes = _silent_wav_bytes(duration_seconds=1.0)
        headers = {
            "Authorization": f"Bearer {_API_KEY}",
            "HTTP-Referer": "https://letitglow.app",
            "X-Title": "GLOW Integration Tests",
        }
        resp = requests.post(
            OPENROUTER_AUDIO_URL,
            headers=headers,
            files={"file": ("silent.wav", io.BytesIO(audio_bytes), "audio/wav")},
            data={"model": self._WHISPER_MODEL, "response_format": "text"},
            timeout=120,
        )
        # Upstream may occasionally return 5xx for this probe; treat that as a skip.
        if resp.status_code >= 500:
            pytest.skip(f"OpenRouter audio endpoint returned {resp.status_code}; upstream error")
        # Accept 200 OK or common client error responses (bad audio / unsupported)
        assert resp.status_code in {200, 400, 422}
        # Silent audio returns empty string or whitespace on success
        if resp.status_code == 200:
            assert isinstance(resp.text, str)

    def test_gateway_transcribe_function(self, tmp_path: Path) -> None:
        """acb_large_print_web.ai_gateway.transcribe() returns a string for silent audio."""
        from acb_large_print_web.ai_gateway import transcribe

        wav_path = tmp_path / "silent.wav"
        wav_path.write_bytes(_silent_wav_bytes(duration_seconds=1.0))

        result = transcribe(
            audio_path=wav_path,
            language="en",
            session_hash="test-integration-whisper",
        )
        assert isinstance(result, str)
        # Silent audio → empty or near-empty transcript, not an exception

    def test_transcribe_request_structure(self) -> None:
        """The multipart request to the Whisper endpoint has the correct shape."""
        audio_bytes = _silent_wav_bytes(duration_seconds=0.5)
        headers = {
            "Authorization": f"Bearer {_API_KEY}",
            "HTTP-Referer": "https://letitglow.app",
            "X-Title": "GLOW Integration Tests",
        }
        resp = requests.post(
            OPENROUTER_AUDIO_URL,
            headers=headers,
            files={"file": ("test.wav", io.BytesIO(audio_bytes), "audio/wav")},
            data={"model": self._WHISPER_MODEL, "response_format": "text", "language": "en"},
            timeout=120,
        )
        # Upstream may return 5xx; treat that as a skip. We care about HTTP 200
        # OR 400/422 (bad audio) when testing request structure.
        if resp.status_code >= 500:
            pytest.skip(f"OpenRouter audio endpoint returned {resp.status_code}; upstream error")
        assert resp.status_code in {200, 400, 422}
