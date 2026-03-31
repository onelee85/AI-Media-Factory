"""Text-to-Speech service using edge-tts with word-level timing extraction.

Generates MP3 audio from text and captures WordBoundary timing data via SubMaker
for use in subtitle synchronization (Phase 5) and video composition (Phase 6).
"""
import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

import edge_tts
from edge_tts import Communicate, SubMaker

from app.config import settings
from app.services.voice_manager import voice_manager_service


class TTSServiceError(Exception):
    """TTS generation error."""
    pass


class TTSService:
    """Generates audio files with word-level timing using edge-tts."""

    def __init__(self):
        self.storage_root = settings.storage_root

    async def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "zh",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate audio from text with word-level timing.

        Args:
            text: Text to synthesize (narration content from script section)
            voice: edge-tts voice name (e.g., "zh-CN-XiaoxiaoNeural").
                   If None, uses default for language.
            language: Language code ("zh" or "en") for default voice selection
            rate: Speech rate adjustment (e.g., "+10%", "-20%")
            volume: Volume adjustment (e.g., "+0%", "-50%")
            pitch: Pitch adjustment (e.g., "+0Hz", "-10Hz")
            output_path: Absolute path for MP3 output file.
                         If None, auto-generates in storage_root/tts/{uuid}.mp3

        Returns:
            {
                "audio_path": str,       # Absolute path to MP3 file
                "voice": str,            # Voice name used
                "language": str,         # Language code
                "duration_seconds": float,  # Audio duration (approximate from timing)
                "word_timing": [         # Word-level timing data
                    {
                        "word": str,     # Word text
                        "start": float,  # Start time in seconds
                        "end": float,    # End time in seconds
                        "offset": int,   # Raw TTS offset (100ns units)
                        "duration": int, # Raw TTS duration (100ns units)
                    }
                ],
                "srt_content": str,      # SRT formatted subtitles
            }

        Raises:
            TTSServiceError: If TTS generation fails
        """
        # Validate input
        if not text or not text.strip():
            raise TTSServiceError("Text must not be empty")

        # Resolve voice
        if voice is None:
            voice = voice_manager_service.get_default_voice(language)

        # Validate voice exists
        voice_info = voice_manager_service.get_voice(voice)
        if voice_info is None:
            raise TTSServiceError(f"Unknown voice: {voice}. Use list_voices() to see available voices.")

        # Prepare output path
        if output_path is None:
            tts_dir = self.storage_root / "tts"
            tts_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(tts_dir / f"{uuid.uuid4()}.mp3")

        # Ensure parent directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create Communicate instance
            communicate = Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
            )

            # Stream audio and capture word boundaries
            sub_maker = SubMaker()
            audio_chunks: List[bytes] = []

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    sub_maker.feed(chunk)

            # Write audio file
            if not audio_chunks:
                raise TTSServiceError("No audio data received from edge-tts")

            with open(output_path, "wb") as f:
                for chunk in audio_chunks:
                    f.write(chunk)

            # Extract word timing from SubMaker cues
            word_timing = []
            for cue in sub_maker.cues:
                word_timing.append({
                    "word": cue.content,
                    "start": cue.start.total_seconds(),
                    "end": cue.end.total_seconds(),
                    "offset": int(cue.start.total_seconds() * 10_000_000),
                    "duration": int((cue.end - cue.start).total_seconds() * 10_000_000),
                })

            # Calculate duration from last word
            duration_seconds = 0.0
            if word_timing:
                duration_seconds = word_timing[-1]["end"]

            # Generate SRT content
            srt_content = sub_maker.get_srt() if sub_maker.cues else ""

            return {
                "audio_path": output_path,
                "voice": voice,
                "language": voice_info.get("language", language),
                "duration_seconds": duration_seconds,
                "word_timing": word_timing,
                "srt_content": srt_content,
            }

        except TTSServiceError:
            raise
        except Exception as e:
            # Clean up partial file on error
            if os.path.exists(output_path):
                os.remove(output_path)
            raise TTSServiceError(f"TTS generation failed: {str(e)}")

    async def generate_from_script_sections(
        self,
        sections: List[Dict[str, Any]],
        voice: Optional[str] = None,
        language: str = "zh",
        output_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate audio for multiple script sections.

        Args:
            sections: List of dicts with 'content' (text) and 'heading' fields
            voice: Voice name (uses default if None)
            language: Language code for voice selection
            output_dir: Directory for output files (auto-generated if None)

        Returns:
            List of result dicts (same format as generate())
        """
        if output_dir is None:
            output_dir = str(self.storage_root / "tts" / str(uuid.uuid4()))

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        results = []
        for idx, section in enumerate(sections):
            content = section.get("content", "")
            if not content.strip():
                continue

            heading = section.get("heading", f"section_{idx+1}")
            # Sanitize heading for filename
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in heading)[:50]
            output_path = os.path.join(output_dir, f"{idx+1:02d}_{safe_name}.mp3")

            result = await self.generate(
                text=content,
                voice=voice,
                language=language,
                output_path=output_path,
            )
            result["heading"] = heading
            result["section_index"] = idx + 1
            results.append(result)

        return results

    def get_supported_voices(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of supported voices.

        Args:
            language: Filter by language ("zh" or "en")

        Returns:
            List of voice dicts
        """
        return voice_manager_service.list_voices(language=language)


# Module-level convenience function
async def generate_tts(
    text: str,
    voice: Optional[str] = None,
    language: str = "zh",
    output_path: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Convenience function for one-off TTS generation."""
    service = TTSService()
    return await service.generate(
        text=text,
        voice=voice,
        language=language,
        output_path=output_path,
        **kwargs,
    )
