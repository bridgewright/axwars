"""sounddevice 기반 AudioInterface — 시스템 portaudio(brew) 불필요.

sounddevice 휠은 PortAudio 바이너리를 번들로 포함하므로, `brew install portaudio` 없이도
로컬 마이크/스피커 실시간 입출력이 된다(이 Mac처럼 brew 가 없는 환경용).

ElevenLabs `DefaultAudioInterface` 와 동일한 계약을 그대로 구현:
  - 입력: 16kHz · mono · PCM16, input_callback(bytes) 로 전달
  - 출력: output(bytes) 큐잉 → 별도 스레드가 재생(인터럽트 시 큐 비움)
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Callable

import sounddevice as sd
from elevenlabs.conversational_ai.conversation import AudioInterface

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
INPUT_BLOCK = 4000   # 250ms @ 16kHz (DefaultAudioInterface 와 동일)
OUTPUT_BLOCK = 1000  # 62.5ms @ 16kHz


class SoundDeviceAudioInterface(AudioInterface):
    # 에이전트가 말하는 동안(+여운) 마이크 입력을 무음 처리 → 스피커→마이크 에코가
    # 서버 VAD 를 건드려 에이전트 발화를 끊는(barge-in 오인) 현상 방지 = half-duplex.
    # 이어폰을 쓰면 에코가 없어 이 게이팅이 사실상 작동할 일이 없다.
    OUTPUT_HANGOVER = 0.5  # 초

    def start(self, input_callback: Callable[[bytes], None]):
        self.input_callback = input_callback
        self.output_queue: "queue.Queue[bytes]" = queue.Queue()
        self.should_stop = threading.Event()
        self._output_active_until = 0.0

        def _in_cb(indata, frames, time_info, status):  # noqa: ANN001
            if not self.input_callback:
                return
            buf = bytes(indata)
            if time.monotonic() < self._output_active_until:
                buf = bytes(len(buf))  # 에이전트 발화 중엔 무음(zeros) 전송
            self.input_callback(buf)

        self.in_stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE,
            blocksize=INPUT_BLOCK, callback=_in_cb,
        )
        self.out_stream = sd.RawOutputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE,
            blocksize=OUTPUT_BLOCK,
        )
        self.in_stream.start()
        self.out_stream.start()
        self.output_thread = threading.Thread(target=self._output_thread, daemon=True)
        self.output_thread.start()

    def stop(self):
        self.should_stop.set()
        if getattr(self, "output_thread", None):
            self.output_thread.join(timeout=2.0)
        for s in (getattr(self, "in_stream", None), getattr(self, "out_stream", None)):
            if s is not None:
                try:
                    s.stop()
                    s.close()
                except Exception:
                    pass

    def output(self, audio: bytes):
        self.output_queue.put(audio)

    def interrupt(self):
        try:
            while True:
                self.output_queue.get_nowait()
        except queue.Empty:
            pass

    def _output_thread(self):
        while not self.should_stop.is_set():
            try:
                audio = self.output_queue.get(timeout=0.25)
                # write 는 블로킹(청크 길이만큼 소요) → 전후로 갱신해 재생 내내 마이크 무음 유지.
                self._output_active_until = time.monotonic() + self.OUTPUT_HANGOVER
                self.out_stream.write(audio)
                self._output_active_until = time.monotonic() + self.OUTPUT_HANGOVER
            except queue.Empty:
                pass
