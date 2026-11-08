from __future__ import annotations

import argparse
import bisect
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from .art import OUTPUT_HEIGHT, OUTPUT_WIDTH, caption, ease, scene_image
from .audio import FPS, TimedScene, make_music, prepare_timeline, write_narration

ROOT = Path(__file__).resolve().parent.parent


def frame_at(frame_number: int, timeline: list[TimedScene], total_frames: int) -> Image.Image:
    starts = [scene.start_frame for scene in timeline]
    index = max(0, bisect.bisect_right(starts, frame_number) - 1)
    scene = timeline[index]
    local_time = (frame_number - scene.start_frame) / FPS
    frame = scene_image(scene, local_time)
    if index and local_time < 0.30:
        previous = timeline[index - 1]
        last_frame = scene_image(previous, previous.duration - 1 / FPS)
        frame = Image.blend(last_frame, frame, ease(local_time / 0.30))
    caption(frame, scene, frame_number / FPS)
    if total_frames - frame_number < FPS * 0.35:
        amount = (total_frames - frame_number) / (FPS * 0.35)
        frame = Image.blend(Image.new('RGB', (OUTPUT_WIDTH, OUTPUT_HEIGHT), (9, 21, 28)), frame, ease(amount))
    return frame


def sample_frames(directory: Path, timeline: list[TimedScene]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    total_frames = timeline[-1].start_frame + timeline[-1].frames
    for scene in timeline:
        frame_number = scene.start_frame + min(round(scene.frames * 0.58), scene.frames - 1)
        frame_at(frame_number, timeline, total_frames).save(directory / f'scene-{scene.index + 1:02d}.jpg', quality=90)
    print(f'Saved {len(timeline)} sample frames to {directory}', flush=True)


def render(output: Path, timeline: list[TimedScene], voices, limit: float | None) -> None:
    total_frames = timeline[-1].start_frame + timeline[-1].frames
    encode_frames = min(total_frames, round(limit * FPS)) if limit else total_frames
    if encode_frames <= 0:
        raise ValueError('Duration must be positive')
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix='torcon-video-') as tmp:
        tmp_path = Path(tmp)
        speech = tmp_path / 'speech.wav'
        music = tmp_path / 'music.wav'
        log = tmp_path / 'ffmpeg.log'
        write_narration(speech, timeline, voices)
        make_music(music, total_frames)
        mix = ('[1:a]highpass=f=80,lowpass=f=14500,volume=1.0[voice];'
               '[2:a]volume=0.34[music];'
               '[voice][music]amix=inputs=2:duration=first:normalize=0,'
               'alimiter=limit=0.94,aformat=channel_layouts=stereo[a]')
        command = [
            ffmpeg, '-hide_banner', '-loglevel', 'warning', '-y',
            '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', f'{OUTPUT_WIDTH}x{OUTPUT_HEIGHT}',
            '-framerate', str(FPS), '-i', 'pipe:0', '-i', str(speech), '-i', str(music),
            '-filter_complex', mix, '-map', '0:v:0', '-map', '[a]',
            '-vf', ('scale=in_range=full:out_range=tv:out_color_matrix=bt709,'
                    'setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709'),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p',
            '-profile:v', 'high', '-level:v', '4.2', '-color_primaries', 'bt709',
            '-color_trc', 'bt709', '-colorspace', 'bt709',
            '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
            '-map_metadata', '-1', '-t', f'{encode_frames / FPS:.6f}', str(output),
        ]
        print('Rendering video', flush=True)
        with log.open('wb') as error_file:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=error_file)
            try:
                assert proc.stdin is not None
                for number in range(encode_frames):
                    proc.stdin.write(frame_at(number, timeline, total_frames).tobytes())
                proc.stdin.close()
            except (BrokenPipeError, OSError):
                proc.kill()
                proc.wait()
                raise RuntimeError(f'FFmpeg failed:\n{log.read_text(errors="replace")}') from None
            return_code = proc.wait()
        if return_code:
            raise RuntimeError(f'FFmpeg exited {return_code}:\n{log.read_text(errors="replace")}')
    print(f'Finished: {output} ({output.stat().st_size / 1_000_000:.1f} MB)', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'output' / 'torque-converter-1080p60.mp4')
    parser.add_argument('--sample-dir', type=Path)
    parser.add_argument('--limit', type=float)
    args = parser.parse_args()
    timeline, voices = prepare_timeline(ROOT / 'assets' / 'voice')
    if args.sample_dir:
        sample_frames(args.sample_dir, timeline)
    else:
        render(args.output, timeline, voices, args.limit)


if __name__ == '__main__':
    main()
