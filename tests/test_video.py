import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from src.art import HEIGHT, WIDTH, VISUALS
from src.audio import (FPS, LEAD_IN, SAMPLE_RATE, SAMPLES_PER_FRAME,
                       caption_cues, make_music, prepare_timeline, write_narration)
from src.render import frame_at
from src.story import SCENES

ROOT = Path(__file__).resolve().parent.parent


class VideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.timeline, cls.voices = prepare_timeline(ROOT / 'assets' / 'voice')
        cls.total_frames = cls.timeline[-1].start_frame + cls.timeline[-1].frames

    def test_source_and_timeline(self):
        self.assertEqual(len(SCENES), 8)
        self.assertGreater(self.total_frames / FPS, 70)
        self.assertLess(self.total_frames / FPS, 110)
        previous_end = 0
        for scene, voice in zip(self.timeline, self.voices, strict=True):
            self.assertEqual(scene.start_frame, previous_end)
            self.assertIn(scene.scene.visual, VISUALS)
            self.assertGreater(voice.size, SAMPLE_RATE * 3)
            self.assertGreater(scene.duration, scene.speech_duration)
            self.assertTrue(scene.scene.captions)
            previous_end = scene.start_frame + scene.frames

    def test_captions_stay_with_their_audio(self):
        for scene in self.timeline:
            cues = caption_cues(scene)
            self.assertAlmostEqual(cues[0][0], scene.start + LEAD_IN + scene.speech_start)
            self.assertEqual([cue[2] for cue in cues], list(scene.scene.captions))
            for i, (start, end, text) in enumerate(cues):
                self.assertLess(start, end)
                self.assertLessEqual(end, scene.start + LEAD_IN + scene.speech_duration)
                self.assertTrue(text.strip())
                if i:
                    self.assertAlmostEqual(start, cues[i - 1][1])

    def test_every_scene_and_transition_renders(self):
        for scene in self.timeline:
            for relative in (0, scene.frames // 2, scene.frames - 1):
                image = frame_at(scene.start_frame + relative, self.timeline, self.total_frames)
                self.assertEqual(image.mode, 'RGB')
                self.assertEqual(image.size, (WIDTH, HEIGHT))

    def test_audio_tracks_are_deterministic_and_exact_length(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            voice = path / 'narration.wav'
            write_narration(voice, self.timeline, self.voices)
            with wave.open(str(voice), 'rb') as stream:
                self.assertEqual(stream.getframerate(), SAMPLE_RATE)
                self.assertEqual(stream.getnframes(), self.total_frames * SAMPLES_PER_FRAME)
            first, second = path / 'music1.wav', path / 'music2.wav'
            make_music(first, FPS * 2)
            make_music(second, FPS * 2)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with wave.open(str(first), 'rb') as stream:
                samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2')
                self.assertEqual(len(samples), FPS * 2 * SAMPLES_PER_FRAME)
                self.assertGreater(np.max(np.abs(samples)), 100)
                self.assertLess(np.max(np.abs(samples)), 30000)


if __name__ == '__main__':
    unittest.main()
