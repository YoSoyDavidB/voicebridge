from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

import sounddevice as sd


@dataclass(frozen=True)
class LocalSpeakerOutput:
    sample_rate: int
    channels: int
    device_id: Optional[int] = None
    _stream: sd.RawOutputStream = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_stream",
            sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                device=self.device_id,
            ),
        )

    def start(self) -> None:
        self._stream.start()

    def enqueue(self, pcm_bytes: bytes) -> None:
        self._stream.write(pcm_bytes)

    async def enqueue_async(self, pcm_bytes: bytes) -> None:
        await asyncio.to_thread(self.enqueue, pcm_bytes)

    def stop(self) -> None:
        self._stream.stop()

    def close(self) -> None:
        self._stream.close()
