from __future__ import annotations

from dataclasses import dataclass, field

import sounddevice as sd


@dataclass(slots=True)
class LocalSpeakerOutput:
    sample_rate: int
    channels: int
    _stream: sd.OutputStream = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )

    def start(self) -> None:
        self._stream.start()

    def enqueue(self, pcm_bytes: bytes) -> None:
        self._stream.write(pcm_bytes)
