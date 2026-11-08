import tempfile
import unittest
from unittest.mock import patch
import wave
from pathlib import Path

import numpy as np

from PIL import ImageDraw

from src import art, geometry
from src.art import OUTPUT_HEIGHT, OUTPUT_WIDTH, SCALE, VISUALS, cue_start, ramp_rotation, scene_image
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
                self.assertEqual(image.size, (OUTPUT_WIDTH, OUTPUT_HEIGHT))

    def test_native_full_hd_and_ninety_distinct_frames_per_second(self):
        self.assertEqual((OUTPUT_WIDTH, OUTPUT_HEIGHT), (1080, 1920))
        self.assertEqual(FPS, 90)
        self.assertEqual(SAMPLES_PER_FRAME, 490)
        scene = self.timeline[3]
        position = scene.start_frame + 4 * FPS
        first = np.asarray(frame_at(position, self.timeline, self.total_frames), dtype=np.int16)
        second = np.asarray(frame_at(position + 1, self.timeline, self.total_frames), dtype=np.int16)
        self.assertGreater(np.count_nonzero(np.abs(first - second) > 4), 1000)

    def test_narration_matches_burned_in_captions(self):
        for scene in SCENES:
            self.assertEqual(' '.join(scene.captions), scene.narration)

    def test_visuals_are_animated_without_channel_or_playback_labels(self):
        captured = []
        original_text = ImageDraw.ImageDraw.text

        def record_text(draw, xy, text, *args, **kwargs):
            captured.append(str(text))
            return original_text(draw, xy, text, *args, **kwargs)

        with patch.object(ImageDraw.ImageDraw, 'text', new=record_text):
            for scene in self.timeline:
                first = scene_image(scene, scene.duration * 0.35)
                second = scene_image(scene, scene.duration * 0.85)
                pixels = np.asarray(first, dtype=np.int16) - np.asarray(second, dtype=np.int16)
                self.assertGreater(np.count_nonzero(np.abs(pixels) > 15), 3000)
        text = ' '.join(captured).upper()
        self.assertNotIn('SAINS OTOMOTIF', text)
        self.assertNotRegex(text, r'\b\d{1,2}\s*/\s*\d{1,2}\b')
        self.assertNotRegex(text, r'\b\d{1,2}:\d{2}\b')

    def test_component_reveals_follow_narration(self):
        parts = self.timeline[2]
        impeller = cue_start(parts, 'Impeler berputar', 0)
        turbine = cue_start(parts, 'turbin tersambung', 0)
        stator = cue_start(parts, 'stator mengatur', 0)
        self.assertLess(impeller, turbine)
        self.assertLess(turbine, stator)

    def test_mechanical_motion_and_no_decorative_particles(self):
        self.assertFalse(any(name in vars(art) for name in ('particles', 'spark', 'orbit', 'ambience')))
        for kind in ('impeller', 'turbine', 'stator'):
            self.assertGreater(np.ptp(geometry.rotor(kind).vertices[:, 2]), 0.35)
        stopped = self.timeline[4]
        first = np.asarray(scene_image(stopped, 3), dtype=np.int16)
        second = np.asarray(scene_image(stopped, 3.5), dtype=np.int16)
        delta = np.abs(first - second)
        y1, y2 = round(400*SCALE), round(780*SCALE)
        middle = round(360*SCALE)
        self.assertGreater(np.count_nonzero(delta[y1:y2, :middle] > 5), 1000)
        self.assertEqual(np.count_nonzero(delta[y1:y2, middle:] > 5), 0)

    def test_three_dimensional_depth_occlusion_and_car_parts(self):
        points = np.array([[2,2,.1], [12,2,.1], [2,12,.1],
                           [2,2,.8], [12,2,.8], [2,12,.8]], dtype=np.float32)
        normals = np.tile(np.array([[0,0,1]], dtype=np.float32), (6,1))
        faces = np.array([[3,4,5], [0,1,2]], dtype=np.int32)
        colors = np.array([[0,0,230], [230,0,0]], dtype=np.float32)
        out = np.zeros((16,16,4), dtype=np.uint8)
        depth = np.full((16,16), -100, dtype=np.float32)
        geometry._raster(points, normals, faces, colors, out, depth)
        self.assertGreater(out[4,4,2], out[4,4,0])
        self.assertAlmostEqual(float(depth[4,4]), .8, places=5)
        models = geometry.car_model(False)
        self.assertEqual(len(models), 5)
        self.assertGreater(np.ptp(models[0][0].vertices[:, 2]), .5)
        self.assertFalse(np.array_equal(models[1][1], models[2][1]))

    def test_turbine_accelerates_smoothly_after_oil_engages(self):
        self.assertEqual(ramp_rotation(.5, 1., 1.2, .8), 0)
        values = [ramp_rotation(t, 1., 1.2, .8) for t in (1., 1.3, 1.6, 2.2, 3.2)]
        self.assertEqual(values, sorted(values))
        self.assertAlmostEqual(values[-1] - values[-2], .8, places=6)

    def test_stopped_car_and_oil_flow_are_smooth(self):
        scene = self.timeline[0]
        stop = cue_start(scene, 'bisa berhenti', 1)
        go = cue_start(scene, 'Tapi, begitu gas diinjak,', 3)
        first = np.asarray(scene_image(scene, stop + (go-stop)*.3))
        second = np.asarray(scene_image(scene, stop + (go-stop)*.7))
        self.assertTrue(np.array_equal(first, second))

        class Capture:
            def __init__(self):
                self.highlights = []
            def line(self, points, fill, **kwargs):
                if fill == (204,242,244,240):
                    self.highlights.append(points)
            def polygon(self, *args, **kwargs):
                pass

        path = art.bezier((0,0), (60,0), (120,80), (180,80))
        a, b = Capture(), Capture()
        art.fluid(a, path, 1., speed=.17)
        art.fluid(b, path, 1. + 1/FPS, speed=.17)
        self.assertNotEqual(a.highlights[0][0], b.highlights[0][0])

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
