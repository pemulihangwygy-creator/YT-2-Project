from __future__ import annotations

import math
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from .story import SCENES, Scene

SAMPLE_RATE = 44_100
FPS = 30
SAMPLES_PER_FRAME = SAMPLE_RATE // FPS
LEAD_IN = 0.22


@dataclass(frozen=True)
class TimedScene:
    scene: Scene
    index: int
    start_frame: int
    frames: int
    speech_samples: int
    speech_start: float
    speech_end: float
    pauses: tuple[float, ...]

    @property
    def start(self) -> float:
        return self.start_frame / FPS

    @property
    def duration(self) -> float:
        return self.frames / FPS

    @property
    def speech_duration(self) -> float:
        return self.speech_samples / SAMPLE_RATE


def decode_voice(path: Path) -> np.ndarray:
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(path),
        '-f', 's16le', '-acodec', 'pcm_s16le', '-ac', '1',
        '-ar', str(SAMPLE_RATE), '-',
    ]
    audio = subprocess.run(command, check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(audio, dtype='<i2').copy()


def speech_landmarks(voice: np.ndarray) -> tuple[float, float, tuple[float, ...]]:
    window = SAMPLE_RATE // 100
    count = len(voice) // window
    peaks = np.max(np.abs(voice[:count * window].astype(np.int32)).reshape(count, window), axis=1)
    silent = peaks < 655
    changes = np.diff(np.r_[False, silent, False].astype(np.int8))
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    runs = [(a / 100, b / 100) for a, b in zip(starts, ends, strict=True) if b - a >= 15]
    speech_start = runs[0][1] if runs and runs[0][0] == 0 else 0.0
    duration = len(voice) / SAMPLE_RATE
    speech_end = runs[-1][0] if runs and runs[-1][1] >= count / 100 - 0.02 else duration
    pauses = tuple(b for a, b in runs if a > 0 and b < speech_end)
    return speech_start, speech_end, pauses


def prepare_timeline(voice_dir: Path) -> tuple[list[TimedScene], list[np.ndarray]]:
    timed = []
    voices = []
    start_frame = 0
    for index, scene in enumerate(SCENES):
        voice = decode_voice(voice_dir / scene.audio)
        if not voice.size:
            raise ValueError(f'Empty narration: {scene.audio}')
        tail = 1.20 if index == len(SCENES) - 1 else 0.38
        frames = math.ceil((LEAD_IN + len(voice) / SAMPLE_RATE + tail) * FPS)
        speech_start, speech_end, pauses = speech_landmarks(voice)
        timed.append(TimedScene(scene, index, start_frame, frames, len(voice),
                                speech_start, speech_end, pauses))
        voices.append(voice)
        start_frame += frames
    return timed, voices


def write_wave(path: Path, samples: np.ndarray) -> None:
    pcm = np.asarray(samples, dtype='<i2')
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(pcm.tobytes())


def write_narration(path: Path, timeline: list[TimedScene], voices: list[np.ndarray]) -> None:
    length = (timeline[-1].start_frame + timeline[-1].frames) * SAMPLES_PER_FRAME
    audio = np.zeros(length, dtype=np.int16)
    for scene, voice in zip(timeline, voices, strict=True):
        start = scene.start_frame * SAMPLES_PER_FRAME + round(LEAD_IN * SAMPLE_RATE)
        audio[start:start + len(voice)] = voice
    write_wave(path, audio)


def _add(track: np.ndarray, start: float, tone: np.ndarray) -> None:
    first = round(start * SAMPLE_RATE)
    if first >= len(track):
        return
    count = min(len(tone), len(track) - first)
    if count > 0:
        track[first:first + count] += tone[:count]


def make_music(path: Path, total_frames: int) -> None:
    size = total_frames * SAMPLES_PER_FRAME
    duration = size / SAMPLE_RATE
    track = np.zeros(size, dtype=np.float32)
    beat = 60 / 96
    rng = np.random.default_rng(240731)

    # Original, deliberately quiet electronic bed; all tones are synthesized.
    chords = ((220.00, 261.63, 329.63), (174.61, 220.00, 261.63),
              (130.81, 164.81, 196.00), (196.00, 246.94, 293.66))
    bar = beat * 8
    for chord_index, start in enumerate(np.arange(0, duration, bar)):
        length = min(bar + 0.5, duration - start)
        t = np.arange(round(length * SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
        envelope = np.minimum(1, t / 0.8) * np.minimum(1, (length - t) / 0.8)
        pad = np.zeros_like(t)
        for freq in chords[chord_index % len(chords)]:
            pad += np.sin(2 * np.pi * freq * t) + 0.18 * np.sin(2 * np.pi * freq * 2 * t)
        _add(track, float(start), pad * envelope * 0.015)

    bass_notes = (110.00, 87.31, 65.41, 98.00)
    for n, start in enumerate(np.arange(0, duration, beat)):
        t = np.arange(round(0.42 * SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
        freq = bass_notes[(n // 8) % len(bass_notes)]
        bass = np.sin(2 * np.pi * freq * t) * np.exp(-t * 7)
        _add(track, float(start), bass * (0.055 if n % 4 == 0 else 0.032))

        kt = np.arange(round(0.18 * SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
        phase = 2 * np.pi * (47 * kt + 13 * (1 - np.exp(-kt * 25)))
        kick = np.sin(phase) * np.exp(-kt * 24)
        _add(track, float(start), kick * (0.065 if n % 4 == 0 else 0.035))

        if n % 2 == 1:
            ht = np.arange(round(0.055 * SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
            noise = rng.normal(0, 1, len(ht)).astype(np.float32)
            hat = (noise - np.roll(noise, 1)) * np.exp(-ht * 85)
            _add(track, float(start), hat * 0.012)

    fade = min(round(1.2 * SAMPLE_RATE), size // 2)
    track[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
    track[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    write_wave(path, (np.clip(track, -0.8, 0.8) * 32767).astype(np.int16))


def caption_cues(scene: TimedScene) -> list[tuple[float, float, str]]:
    phrases = scene.scene.captions
    weights = [max(8, sum(1 for c in phrase if c.isalnum()) + 2 * phrase.count(','))
               for phrase in phrases]
    count = len(phrases)
    speech_start, speech_end = scene.speech_start, scene.speech_end
    span = max(0.2, speech_end - speech_start)
    predicted = [speech_start + span * sum(weights[:i]) / sum(weights)
                 for i in range(count + 1)]
    candidates = []
    for pause in scene.pauses:
        for boundary in range(1, count):
            distance = abs(predicted[boundary] - pause)
            if distance <= 0.9:
                punctuation_bonus = 0.32 if phrases[boundary - 1].rstrip().endswith((',', '.', ':', '?')) else 0
                candidates.append((distance - punctuation_bonus, boundary, pause))
    anchors = [(0, speech_start), (count, speech_end)]
    for _, boundary, pause in sorted(candidates):
        if any(i == boundary or abs(t - pause) < 0.01 for i, t in anchors):
            continue
        before = max((item for item in anchors if item[0] < boundary), key=lambda item: item[0])
        after = min((item for item in anchors if item[0] > boundary), key=lambda item: item[0])
        if pause - before[1] < 0.30 * (boundary - before[0]):
            continue
        if after[1] - pause < 0.30 * (after[0] - boundary):
            continue
        anchors.append((boundary, pause))
    anchors.sort()
    boundaries = [speech_start] * (count + 1)
    for (first, first_time), (last, last_time) in zip(anchors, anchors[1:]):
        segment_weights = weights[first:last]
        for i in range(first, last + 1):
            fraction = sum(weights[first:i]) / sum(segment_weights)
            boundaries[i] = first_time + fraction * (last_time - first_time)
    offset = scene.start + LEAD_IN
    return [(offset + boundaries[i], offset + boundaries[i + 1], phrase)
            for i, phrase in enumerate(phrases)]
