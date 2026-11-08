from __future__ import annotations

import argparse
import bisect
from functools import lru_cache
from pathlib import Path

from PIL import Image

from .art import OUTPUT_HEIGHT, OUTPUT_WIDTH, caption, ease
from .audio import FPS, TimedScene, prepare_timeline
from .render import ROOT, render
from .sim_art import scene_image
from .sim_story import SCENES, SOURCE_ANTARA, SOURCE_KORLANTAS, SOURCE_LOCAL


@lru_cache(maxsize=8)
def _transition_end(scene: TimedScene) -> Image.Image:
    return scene_image(scene, scene.duration - 1 / FPS)


def frame_at(number: int, timeline: list[TimedScene], total_frames: int) -> Image.Image:
    starts = [scene.start_frame for scene in timeline]
    index = max(0, bisect.bisect_right(starts, number) - 1)
    scene = timeline[index]
    local_time = (number - scene.start_frame) / FPS
    frame = scene_image(scene, local_time)
    if index and local_time < .30:
        frame = Image.blend(_transition_end(timeline[index-1]), frame, ease(local_time / .30))
    caption(frame, scene, number / FPS)
    if total_frames - number < FPS * .35:
        amount = (total_frames-number) / (FPS*.35)
        frame = Image.blend(Image.new('RGB', (OUTPUT_WIDTH, OUTPUT_HEIGHT), (21, 27, 42)),
                            frame, ease(amount))
    return frame


def sample_frames(directory: Path, timeline: list[TimedScene]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    total = timeline[-1].start_frame + timeline[-1].frames
    for scene in timeline:
        for label, fraction in (('early', .35), ('late', .8)):
            number = scene.start_frame + min(round(scene.frames*fraction), scene.frames-1)
            frame_at(number, timeline, total).save(directory / f'{scene.index+1:02d}-{label}.jpg', quality=91)
    print(f'Saved sample frames to {directory}', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'output' / 'cek-fakta-sim-2d-1080p90.mp4')
    parser.add_argument('--sample-dir', type=Path)
    parser.add_argument('--limit', type=float)
    args = parser.parse_args()
    timeline, voices = prepare_timeline(ROOT / 'assets' / 'voice' / 'sim-2026', SCENES)
    if args.sample_dir:
        sample_frames(args.sample_dir, timeline)
    else:
        sources = f'Korlantas: {SOURCE_KORLANTAS} | ANTARA: {SOURCE_ANTARA} | Program lokal: {SOURCE_LOCAL}'
        render(args.output, timeline, voices, args.limit, frame_renderer=frame_at,
               source_comment=sources, voice_gain=1.55)


if __name__ == '__main__':
    main()
