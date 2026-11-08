import hashlib
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import ImageDraw

from src import sim_art
from src.art import OUTPUT_HEIGHT, OUTPUT_WIDTH, cue_start
from src.audio import FPS, LEAD_IN, SAMPLE_RATE, caption_cues, prepare_timeline
from src.sim_story import SCENES, SOURCE_ANTARA, SOURCE_KORLANTAS, SOURCE_LOCAL
from src.sim_video import frame_at

ROOT = Path(__file__).resolve().parent.parent


class SimShortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.timeline, cls.voices = prepare_timeline(ROOT / 'assets' / 'voice' / 'sim-2026', SCENES)
        cls.total = cls.timeline[-1].start_frame + cls.timeline[-1].frames

    def test_voice_script_and_timeline(self):
        self.assertEqual(len(SCENES), 6)
        self.assertTrue(40 < self.total / FPS < 60)
        previous_end = 0
        for timed, voice in zip(self.timeline, self.voices, strict=True):
            self.assertEqual(timed.start_frame, previous_end)
            self.assertEqual(' '.join(timed.scene.captions), timed.scene.narration)
            self.assertGreater(voice.size, 3 * SAMPLE_RATE)
            self.assertGreater(np.max(np.abs(voice.astype(np.int32))), 2000)
            self.assertGreater(timed.duration, timed.speech_duration)
            self.assertIn(timed.scene.visual, sim_art.VISUALS)
            previous_end += timed.frames

    def test_fact_check_distinguishes_a_viral_claim_from_local_programs(self):
        narrative = ' '.join(scene.narration for scene in SCENES).lower()
        self.assertIn('dibantah korlantas polri', narrative)
        self.assertIn('bukan pengumuman resmi', narrative)
        self.assertIn('berlaku lima tahun', narrative)
        self.assertIn('program khusus di daerah bisa saja ada', narrative)
        self.assertIn('tanggal dan syaratnya', narrative)
        self.assertIn('kode otp', narrative)
        self.assertIn('jangan transfer ke rekening yang belum jelas', narrative)
        self.assertNotIn('semua sim gratis', narrative)
        self.assertTrue(SOURCE_KORLANTAS.startswith('https://korlantas.polri.go.id/'))
        self.assertTrue(SOURCE_LOCAL.startswith('https://korlantas.polri.go.id/'))
        self.assertIn('antaranews.com', SOURCE_ANTARA)

    def test_subtitles_follow_each_speech_segment(self):
        for scene in self.timeline:
            cues = caption_cues(scene)
            self.assertEqual([cue[2] for cue in cues], list(scene.scene.captions))
            self.assertAlmostEqual(cues[0][0], scene.start + LEAD_IN + scene.speech_start)
            for index, (start, end, content) in enumerate(cues):
                self.assertLess(start, end)
                self.assertTrue(content.strip())
                self.assertLessEqual(end, scene.start + LEAD_IN + scene.speech_duration)
                if index:
                    self.assertAlmostEqual(cues[index-1][1], start)

    def test_original_flat_assets_are_cached_and_transparent(self):
        for key, factory in sim_art.ASSETS.items():
            image = factory()
            self.assertIs(image, factory(), key)
            self.assertEqual(image.mode, 'RGBA')
            self.assertEqual(image.getpixel((0, 0))[3], 0, key)
            self.assertGreater(image.width, 100)
            self.assertGreater(image.height, 100)

    def test_every_scene_and_transition_renders_full_hd(self):
        self.assertEqual(FPS, 90)
        self.assertEqual((OUTPUT_WIDTH, OUTPUT_HEIGHT), (1080, 1920))
        for scene in self.timeline:
            for relative in (0, scene.frames // 2, scene.frames - 1):
                frame = frame_at(scene.start_frame + relative, self.timeline, self.total)
                self.assertEqual(frame.mode, 'RGB')
                self.assertEqual(frame.size, (OUTPUT_WIDTH, OUTPUT_HEIGHT))

    def test_subpixel_motion_remains_smooth_at_ninety_fps(self):
        scene = self.timeline[0]
        hashes = set()
        for offset in range(12):
            frame = frame_at(scene.start_frame + 3*FPS + offset, self.timeline, self.total)
            hashes.add(hashlib.blake2s(frame.crop((100, 380, 980, 1450)).tobytes()).digest())
        self.assertEqual(len(hashes), 12)

    def test_animation_and_no_channel_or_playback_indicators(self):
        captured = []
        draw_text = ImageDraw.ImageDraw.text

        def record(draw, xy, content, *args, **kwargs):
            captured.append(str(content))
            return draw_text(draw, xy, content, *args, **kwargs)

        with patch.object(ImageDraw.ImageDraw, 'text', new=record):
            for scene in self.timeline:
                early = np.asarray(sim_art.scene_image(scene, scene.duration*.35), dtype=np.int16)
                late = np.asarray(sim_art.scene_image(scene, scene.duration*.85), dtype=np.int16)
                self.assertGreater(np.count_nonzero(np.abs(early-late) > 15), 3000)
        text = ' '.join(captured).upper()
        self.assertNotIn('SAINS OTOMOTIF', text)
        self.assertIsNone(re.search(r'\b\d{1,2}\s*/\s*\d{1,2}\b', text))
        self.assertIsNone(re.search(r'\b\d{1,2}:\d{2}\b', text))
        self.assertFalse(any(name in vars(sim_art) for name in ('particles', 'spark', 'orbit', 'ambience')))

    def test_individual_risk_rows_reveal_with_the_narration(self):
        scene = self.timeline[3]
        cues = [cue_start(scene, key, 0) for key in
                ('yang meminta data pribadi,', 'foto identitas,', 'atau kode OTP!')]
        self.assertEqual(cues, sorted(cues))
        for index, label in enumerate(('DATA PRIBADI', 'FOTO IDENTITAS', 'KODE OTP')):
            colors = []
            for when in (cues[index]-.05, cues[index]+.05):
                with patch.object(sim_art, 'text', wraps=sim_art.text) as record:
                    sim_art.scene_image(scene, when)
                call = next(call for call in record.call_args_list if call.args[1] == label)
                colors.append(call.args[5])
            self.assertEqual(colors, [sim_art.INK, sim_art.DARK_RED])

    def test_local_program_scene_points_to_official_checks(self):
        scene = self.timeline[4]
        at = cue_start(scene, 'Tapi cek tanggal', 0)
        labels = []
        for when in (at-.30, at+1):
            with patch.object(sim_art, 'text', wraps=sim_art.text) as record:
                sim_art.scene_image(scene, when)
            labels.append([call.args[1] for call in record.call_args_list])
        self.assertIn('PROGRAM LOKAL BISA BERBEDA', labels[0])
        self.assertIn('CEK TANGGAL & SYARAT', labels[1])
        self.assertIn('LANGSUNG KE KANAL RESMI', labels[1])
        self.assertIn('SUMBER: KORLANTAS POLRI • 6 AGU 2026', labels[1])


if __name__ == '__main__':
    unittest.main()
