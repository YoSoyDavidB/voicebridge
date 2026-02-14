"""OpenAI translation client for Spanish to English translation.

Uses GPT-4o-mini for fast, high-quality conversational translation.
"""

from __future__ import annotations

import asyncio
import time

from openai import OpenAI

from voicebridge.core.exceptions import TranslationError
from voicebridge.core.models import TranscriptResult, TranslationResult


class OpenAITranslationClient:
    """OpenAI translation client.

    Uses GPT-4o-mini API to translate Spanish transcripts to English
    with conversational context and low latency.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
    ) -> None:
        """Initialize OpenAI translation client.

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., 'gpt-4o-mini')
            temperature: Sampling temperature (0.0-2.0, lower = more deterministic)
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

        # Initialize OpenAI client
        self._client = OpenAI(api_key=api_key)

        # System prompt for translation
        self._system_prompt = """You are a real-time interpreter translating spoken Spanish to English.

CRITICAL RULES:
1. Translate the spoken Spanish text to natural, conversational English.
2. Maintain the speaker's tone, intent, and register (formal/informal).
3. Do NOT add explanations, notes, or commentary.
4. Do NOT translate proper nouns (names, company names, etc.).
5. Handle filler words naturally: "este..." → "um...", "o sea" → "I mean".
6. Preserve technical jargon when it's used in English in the source (common in tech meetings).
7. If the input is unclear or incomplete, translate what you can and keep the same level of ambiguity.
8. Output ONLY the English translation, nothing else.
9. Match the formality level: "usted" → formal English, "tú" → casual English.
10. For numbers, dates, and measurements, use the English convention."""

        # State
        self._input_queue: asyncio.Queue[TranscriptResult] | None = None
        self._output_queue: asyncio.Queue[TranslationResult] | None = None
        self._sequence_number = 0
        self._is_running = False

    def set_input_queue(self, queue: asyncio.Queue[TranscriptResult]) -> None:
        """Set the queue to read transcripts from.

        Args:
            queue: Input queue with TranscriptResult objects
        """
        self._input_queue = queue

    def set_output_queue(self, queue: asyncio.Queue[TranslationResult]) -> None:
        """Set the queue to push translation results to.

        Args:
            queue: Output queue for TranslationResult objects
        """
        self._output_queue = queue

    async def start(self) -> None:
        """Start the translation client processing loop."""
        if self._input_queue is None or self._output_queue is None:
            msg = "Input and output queues must be set before starting"
            raise RuntimeError(msg)

        self._is_running = True
        await self._process_loop()

    async def stop(self) -> None:
        """Stop the translation client."""
        self._is_running = False

    async def _process_loop(self) -> None:
        """Main processing loop.

        Reads TranscriptResult from input queue, translates to English,
        and emits TranslationResult to output queue.
        """
        while self._is_running:
            if self._input_queue is None or self._output_queue is None:
                break

            try:
                # Get next transcript
                transcript = await asyncio.wait_for(
                    self._input_queue.get(),
                    timeout=0.1,
                )

                # Translate
                start_time = time.monotonic()
                translation = await self._translate_text(transcript.text, start_time)

                if translation is not None:
                    await self._output_queue.put(translation)

            except asyncio.TimeoutError:
                # No transcripts available, continue
                continue
            except Exception as e:
                raise TranslationError(f"Error translating text: {e}") from e

    async def _translate_text(
        self,
        text: str,
        start_time: float,
    ) -> TranslationResult | None:
        """Translate Spanish text to English.

        Args:
            text: Spanish text to translate
            start_time: Timestamp when processing started

        Returns:
            TranslationResult if valid translation, None otherwise
        """
        # Ignore empty input
        if not text.strip():
            return None

        try:
            # Call OpenAI API
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=self.temperature,
                max_tokens=500,
            )

            # Extract translation
            translated_text = response.choices[0].message.content.strip()

            # Calculate latency
            end_time = time.monotonic()
            latency_ms = (end_time - start_time) * 1000.0

            result = TranslationResult(
                original_text=text,
                translated_text=translated_text,
                start_timestamp_ms=0.0,  # Will be set by orchestrator
                processing_latency_ms=latency_ms,
                sequence_number=self._sequence_number,
            )

            self._sequence_number += 1

            return result

        except Exception as e:
            raise TranslationError(f"OpenAI API error: {e}") from e
