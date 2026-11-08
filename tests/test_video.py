import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import wave

import numpy as np
from PIL import Image, ImageDraw

from src import art, vector
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
                    self.assertAlmostEqual(start, cues[i-1][1])

    def test_every_scene_and_transition_renders(self):
        for scene in self.timeline:
            for relative in (0, scene.frames//2, scene.frames-1):
                image = frame_at(scene.start_frame+relative, self.timeline, self.total_frames)
                self.assertEqual(image.mode, 'RGB')
                self.assertEqual(image.size, (OUTPUT_WIDTH, OUTPUT_HEIGHT))

    def test_native_full_hd_and_ninety_fps(self):
        self.assertEqual((OUTPUT_WIDTH,OUTPUT_HEIGHT),(1080,1920))
        self.assertEqual(FPS,90)
        self.assertEqual(SAMPLES_PER_FRAME,490)
        scene=self.timeline[3]
        position=scene.start_frame+5*FPS
        first=np.asarray(frame_at(position,self.timeline,self.total_frames),dtype=np.int16)
        second=np.asarray(frame_at(position+1,self.timeline,self.total_frames),dtype=np.int16)
        self.assertGreater(np.count_nonzero(np.abs(first-second)>4),1000)

    def test_narration_matches_burned_in_captions(self):
        for scene in SCENES:
            self.assertEqual(' '.join(scene.captions),scene.narration)

    def test_2d_assets_and_no_3d_dependencies(self):
        for kind in ('impeller','turbine','stator'):
            sprite=vector.rotor(kind)
            self.assertIs(sprite,vector.rotor(kind))
            self.assertEqual(sprite.mode,'RGBA')
            self.assertEqual(sprite.size,(768,768))
            self.assertEqual(sprite.getpixel((0,0))[3],0)
            self.assertGreater(sprite.getpixel((384,384))[3],0)
        self.assertFalse((ROOT/'src'/'geometry.py').exists())
        requirements=(ROOT/'requirements.txt').read_text().lower()
        self.assertIn('resvg-py',requirements)
        self.assertIn('aggdraw',requirements)
        self.assertNotIn('mitsuba',requirements)
        self.assertNotIn('drjit',requirements)

    def test_visuals_animated_without_channel_or_playback_labels(self):
        captured=[]
        original_text=ImageDraw.ImageDraw.text
        def record_text(draw,xy,text,*args,**kwargs):
            captured.append(str(text))
            return original_text(draw,xy,text,*args,**kwargs)
        with patch.object(ImageDraw.ImageDraw,'text',new=record_text):
            for scene in self.timeline:
                first=np.asarray(scene_image(scene,scene.duration*.35),dtype=np.int16)
                second=np.asarray(scene_image(scene,scene.duration*.85),dtype=np.int16)
                self.assertGreater(np.count_nonzero(np.abs(first-second)>15),3000)
        text=' '.join(captured).upper()
        self.assertNotIn('SAINS OTOMOTIF',text)
        self.assertNotRegex(text,r'\b\d{1,2}\s*/\s*\d{1,2}\b')
        self.assertNotRegex(text,r'\b\d{1,2}:\d{2}\b')
        self.assertFalse(any(name in vars(art) for name in ('particles','spark','orbit','ambience')))

    def test_component_reveals_follow_narration(self):
        scene=self.timeline[2]
        impeller=cue_start(scene,'Impeler berputar',0)
        turbine=cue_start(scene,'turbin tersambung',0)
        stator=cue_start(scene,'stator mengatur',0)
        self.assertLess(impeller,turbine)
        self.assertLess(turbine,stator)

    def test_pump_rotates_while_turbine_is_stopped(self):
        scene=self.timeline[4]
        first=np.asarray(scene_image(scene,3),dtype=np.int16)
        second=np.asarray(scene_image(scene,3.5),dtype=np.int16)
        delta=np.abs(first-second)
        y1,y2=round(400*SCALE),round(720*SCALE)
        middle=round(360*SCALE)
        self.assertGreater(np.count_nonzero(delta[y1:y2,:middle]>5),1000)
        self.assertEqual(np.count_nonzero(delta[y1:y2,middle:]>5),0)

    def test_turbine_accelerates_smoothly_after_oil_engages(self):
        self.assertEqual(ramp_rotation(.5,1.,1.2,.8),0)
        values=[ramp_rotation(t,1.,1.2,.8) for t in (1.,1.3,1.6,2.2,3.2)]
        self.assertEqual(values,sorted(values))
        self.assertAlmostEqual(values[-1]-values[-2],.8,places=6)

    def test_oil_paths_show_both_directions(self):
        paths=[]
        def record(image,points,time,color=art.BLUE,speed=.2):
            paths.append(points)
        with patch.object(art,'fluid',new=record):
            art._flow_diagram(Image.new('RGB',(OUTPUT_WIDTH,OUTPUT_HEIGHT)),2,.5)
        self.assertEqual(len(paths),2)
        self.assertLess(paths[0][0][0],paths[0][-1][0])
        self.assertGreater(paths[1][0][0],paths[1][-1][0])
        self.assertGreater(len(paths[0]),40)

    def test_stopped_car_and_oil_flow_are_smooth(self):
        scene=self.timeline[0]
        stop=cue_start(scene,'bisa berhenti',1)
        go=cue_start(scene,'Tapi, begitu gas diinjak,',3)
        first=np.asarray(scene_image(scene,stop+(go-stop)*.3))
        second=np.asarray(scene_image(scene,stop+(go-stop)*.7))
        self.assertTrue(np.array_equal(first,second))
        path=art.bezier((50,50),(80,20),(180,20),(210,50))
        a=Image.new('RGB',(400,200),(0,0,0));b=a.copy()
        art.fluid(a,path,1.,speed=.17)
        art.fluid(b,path,1.+1/FPS,speed=.17)
        self.assertFalse(np.array_equal(np.asarray(a),np.asarray(b)))

    def test_audio_tracks_are_deterministic_and_exact_length(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            voice=path/'narration.wav'
            write_narration(voice,self.timeline,self.voices)
            with wave.open(str(voice),'rb') as stream:
                self.assertEqual(stream.getframerate(),SAMPLE_RATE)
                self.assertEqual(stream.getnframes(),self.total_frames*SAMPLES_PER_FRAME)
            first,second=path/'music1.wav',path/'music2.wav'
            make_music(first,FPS*2);make_music(second,FPS*2)
            self.assertEqual(first.read_bytes(),second.read_bytes())
            with wave.open(str(first),'rb') as stream:
                samples=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2')
                self.assertEqual(len(samples),FPS*2*SAMPLES_PER_FRAME)
                self.assertGreater(np.max(np.abs(samples)),100)
                self.assertLess(np.max(np.abs(samples)),30000)


if __name__ == '__main__':
    unittest.main()
