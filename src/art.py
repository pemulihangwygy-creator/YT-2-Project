from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .audio import TimedScene, caption_cues

WIDTH, HEIGHT = 720, 1280
ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / 'assets' / 'fonts'
WHITE = (241, 247, 244)
MUTED = (159, 190, 196)
YELLOW = (255, 213, 78)
ORANGE = (240, 139, 55)
BLUE = (58, 173, 222)
GREEN = (82, 198, 143)
RED = (255, 105, 98)
INK = (12, 29, 38)


def clamp(value: float, low: float = 0, high: float = 1) -> float:
    return max(low, min(high, value))


def ease(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def mix(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, round(c * factor))) for c in color)


@lru_cache(maxsize=None)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    names = {
        'display': 'BarlowCondensed-ExtraBold.ttf',
        'bold': 'Barlow-Bold.ttf',
        'body': 'Barlow-SemiBold.ttf',
    }
    return ImageFont.truetype(str(FONT_DIR / names[name]), size=size)


def fitted_font(draw: ImageDraw.ImageDraw, text: str, name: str, size: int, max_width: int):
    while size > 16 and draw.textlength(text, font=font(name, size)) > max_width:
        size -= 2
    return font(name, size)


def centered(draw, xy, text, name='bold', size=30, fill=WHITE, shadow=True, max_width=640):
    x, y = xy
    face = fitted_font(draw, text, name, size, max_width)
    if shadow:
        draw.text((x + 2, y + 3), text, font=face, fill=(6, 17, 23), anchor='mt')
    draw.text((x, y), text, font=face, fill=fill, anchor='mt')


@lru_cache(maxsize=1)
def background() -> Image.Image:
    x = np.linspace(-1, 1, WIDTH, dtype=np.float32)[None, :]
    y = np.linspace(0, 1, HEIGHT, dtype=np.float32)[:, None]
    glow = np.exp(-((x / 0.8) ** 2 + ((y - 0.51) / 0.47) ** 2) * 1.6)
    vignette = np.clip(1 - 0.18 * (x * x) - 0.20 * (y - 0.5) ** 2, 0.6, 1)
    grain = np.random.default_rng(19).normal(0, 0.75, (HEIGHT, WIDTH))
    image = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for channel, (base, add) in enumerate(((17, 19), (37, 30), (47, 31))):
        image[:, :, channel] = np.clip((base + add * glow) * vignette + grain, 0, 255)
    result = Image.fromarray(image, 'RGB')
    draw = ImageDraw.Draw(result, 'RGBA')
    for x0 in range(38, WIDTH, 54):
        for y0 in range(365, 1030, 54):
            draw.ellipse((x0, y0, x0 + 2, y0 + 2), fill=(198, 235, 231, 18))
    draw.ellipse((-160, 340, 880, 1380), outline=(181, 229, 231, 15), width=2)
    draw.ellipse((-85, 415, 805, 1305), outline=(181, 229, 231, 11), width=2)
    draw.rounded_rectangle((23, 23, 697, 1257), radius=24,
                           outline=(211, 238, 230, 23), width=2)
    return result


def capsule(draw, center, text, color=YELLOW, text_color=INK, size=23, pad=20, height=42):
    x, y = center
    face = font('bold', size)
    width = draw.textlength(text, font=face) + pad * 2
    box = (x - width / 2, y - height / 2, x + width / 2, y + height / 2)
    draw.rounded_rectangle(box, radius=height // 2, fill=color)
    draw.text((x, y - size * 0.49), text, font=face, fill=text_color, anchor='mt')


def outlined_capsule(draw, center, text, color=WHITE, size=22, pad=18, height=42):
    x, y = center
    face = font('bold', size)
    width = draw.textlength(text, font=face) + pad * 2
    box = (x - width / 2, y - height / 2, x + width / 2, y + height / 2)
    draw.rounded_rectangle(box, radius=height // 2, fill=(19, 42, 53), outline=color, width=2)
    draw.text((x, y - size * 0.49), text, font=face, fill=color, anchor='mt')


def header(image, scene: TimedScene, time: float, progress: float):
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.rounded_rectangle((47, 46, 673, 52), radius=3, fill=(184, 218, 213, 60))
    draw.rounded_rectangle((47, 46, 47 + max(5, 626 * clamp(progress)), 52),
                           radius=3, fill=(*YELLOW, 255))
    draw.ellipse((48, 76, 59, 87), fill=(*YELLOW, 255))
    draw.text((69, 72), 'SAINS OTOMOTIF', font=font('bold', 21), fill=(*WHITE, 255))
    right = f'{scene.index + 1:02d}  /  08'
    draw.text((672, 72), right, font=font('bold', 21), fill=(*MUTED, 255), anchor='ra')
    y = 126 + 17 * (1 - ease(time / 0.5))
    for index, line in enumerate(scene.scene.title):
        centered(draw, (360, y + index * 83), line, name='display', size=84,
                 fill=YELLOW if index == scene.scene.highlight else WHITE, max_width=620)
    for i in range(8):
        px = 59 + (i * 89 + time * (5 + i % 3)) % 600
        py = 377 + ((i * 109 + 15 * math.sin(time * 0.45 + i)) % 570)
        draw.ellipse((px, py, px + 3, py + 3), fill=(213, 241, 233, 46))


def disc(draw, x, y, r, fill, outline=None, width=1):
    draw.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=width)


def polar(x, y, radius, angle):
    return (x + radius * math.cos(angle), y + radius * math.sin(angle))


def rotor(image: Image.Image, x: float, y: float, r: float,
          color: tuple[int, int, int], angle: float, blades: int = 15):
    draw = ImageDraw.Draw(image, 'RGBA')
    disc(draw, x + 7, y + 12, r + 5, (4, 17, 24, 130))
    disc(draw, x, y, r + 7, (*WHITE, 255))
    disc(draw, x, y, r + 1, (38, 60, 70, 255))
    disc(draw, x, y, r - 5, (143, 163, 166, 255))
    disc(draw, x, y, r - 12, (67, 89, 98, 255))
    disc(draw, x, y, r - 19, (*mix(color, 0.54), 255))
    disc(draw, x, y, r * 0.78, (*mix(color, 0.86), 255))
    for n in range(blades):
        theta = angle + n * 2 * math.pi / blades
        points = [
            polar(x, y, r * 0.25, theta - 0.07),
            polar(x, y, r * 0.49, theta - 0.02),
            polar(x, y, r * 0.78, theta + 0.13),
            polar(x, y, r * 0.78, theta + 0.30),
            polar(x, y, r * 0.51, theta + 0.11),
            polar(x, y, r * 0.26, theta + 0.05),
        ]
        light = 1.03 + 0.16 * math.cos(theta - 2.3)
        draw.polygon(points, fill=(*mix(color, light), 255), outline=(*mix(color, 0.48), 255), width=2)
        draw.line([points[1], points[2]], fill=(*mix(color, 1.32), 225), width=max(2, round(r / 75)))
    draw.ellipse((x - r * 0.78, y - r * 0.78, x + r * 0.78, y + r * 0.78),
                 outline=(*mix(color, 1.28), 200), width=max(2, round(r / 55)))
    disc(draw, x, y, r * 0.29, (27, 49, 60, 255), (*WHITE, 255), max(2, round(r / 60)))
    disc(draw, x, y, r * 0.21, (164, 181, 181, 255))
    disc(draw, x, y, r * 0.13, (48, 68, 76, 255))
    disc(draw, x - r * 0.025, y - r * 0.025, r * 0.065, (18, 36, 45, 255))
    for n in range(8):
        bx, by = polar(x, y, r * 0.905, angle + n * math.tau / 8)
        disc(draw, bx, by, max(2, r * 0.018), (33, 49, 56, 255))


def arrow(draw, points, color=BLUE, width=8, tip=20):
    draw.line(points, fill=(*INK, 170), width=width + 7, joint='curve')
    draw.line(points, fill=(*color, 255), width=width, joint='curve')
    ex, ey = points[-1]
    px, py = points[-2]
    angle = math.atan2(ey - py, ex - px)
    a = (ex - tip * math.cos(angle - 0.55), ey - tip * math.sin(angle - 0.55))
    b = (ex - tip * math.cos(angle + 0.55), ey - tip * math.sin(angle + 0.55))
    draw.polygon(((ex, ey), a, b), fill=(*color, 255))


def flowing_dots(draw, x1, x2, y, time, color=BLUE, count=6, speed=0.19):
    for i in range(count):
        p = (time * speed + i / count) % 1
        x = x1 + (x2 - x1) * p
        yy = y + 5 * math.sin(p * math.tau * 2 + time * 1.4)
        disc(draw, x, yy, 5 + 2 * math.sin(p * math.pi), (*color, 220))


def engine(image, x, y, size):
    draw = ImageDraw.Draw(image, 'RGBA')
    s = size / 150
    def xy(a, b): return (x + a * s, y + b * s)
    draw.rounded_rectangle((*xy(-65, -29), *xy(64, 58)), radius=int(15*s),
                           fill=(100, 124, 129, 255), outline=(*WHITE, 255), width=max(3, int(5*s)))
    draw.polygon([xy(-54, -29), xy(-43, -58), xy(35, -58), xy(48, -29)],
                 fill=(132, 152, 151, 255), outline=(*WHITE, 255), width=max(3, int(5*s)))
    draw.line([xy(-40, -58), xy(-40, -75), xy(15, -75)], fill=(*WHITE, 255), width=max(3, int(5*s)))
    draw.line([xy(63, -4), xy(78, -4), xy(78, 32), xy(63, 32)], fill=(*WHITE, 255), width=max(3, int(5*s)))
    for a in (-37, -11, 15):
        draw.rounded_rectangle((*xy(a, -20), *xy(a + 14, 6)), radius=int(4*s), fill=(44, 66, 75, 255))
    disc(draw, *xy(-31, 31), 17*s, (44, 68, 77, 255), (*WHITE, 255), max(2, int(3*s)))
    disc(draw, *xy(-31, 31), 7*s, (*YELLOW, 255))
    draw.line([xy(3, 26), xy(43, 26)], fill=(*WHITE, 255), width=max(2, int(4*s)))
    draw.line([xy(3, 41), xy(35, 41)], fill=(*WHITE, 255), width=max(2, int(4*s)))


def gearbox(image, x, y, size):
    draw = ImageDraw.Draw(image, 'RGBA')
    s = size / 150
    def xy(a, b): return (x + a * s, y + b * s)
    points = [xy(-70, -44), xy(-30, -56), xy(35, -45), xy(62, -25),
              xy(68, 27), xy(35, 49), xy(-30, 56), xy(-70, 44)]
    draw.polygon(points, fill=(116, 140, 143, 255), outline=(*WHITE, 255), width=max(3, int(5*s)))
    disc(draw, *xy(-42, 0), 34*s, (61, 83, 91, 255), (*WHITE, 255), max(2, int(4*s)))
    disc(draw, *xy(-42, 0), 18*s, (157, 177, 176, 255))
    disc(draw, *xy(-42, 0), 8*s, (42, 65, 74, 255))
    for a in (-5, 11, 27, 43):
        draw.line([xy(a, -31), xy(a, 31)], fill=(50, 73, 81, 255), width=max(2, int(4*s)))


def car(image, x, y, width, time, braking=False):
    draw = ImageDraw.Draw(image, 'RGBA')
    s = width / 500
    def xy(a, b): return (x + a * s, y + b * s)
    def r(a): return a*s
    draw.ellipse((*xy(20, 164), *xy(485, 199)), fill=(5, 17, 24, 100))
    body = [xy(7, 116), xy(16, 91), xy(69, 76), xy(110, 33), xy(158, 15),
            xy(291, 15), xy(341, 33), xy(387, 72), xy(457, 86), xy(490, 110),
            xy(488, 152), xy(466, 164), xy(33, 164), xy(12, 152)]
    draw.polygon(body, fill=(130, 163, 170, 255), outline=(*WHITE, 255), width=max(4, int(r(6))))
    windows = [xy(83, 74), xy(122, 38), xy(160, 27), xy(224, 27), xy(224, 74)]
    draw.polygon(windows, fill=(29, 56, 68, 255), outline=(215, 232, 229, 255), width=max(2, int(r(3))))
    windows = [xy(238, 27), xy(288, 27), xy(332, 42), xy(365, 74), xy(238, 74)]
    draw.polygon(windows, fill=(31, 59, 70, 255), outline=(215, 232, 229, 255), width=max(2, int(r(3))))
    draw.line([xy(231, 80), xy(231, 147)], fill=(70, 99, 108, 255), width=max(2, int(r(3))))
    draw.line([xy(150, 96), xy(173, 96)], fill=(*WHITE, 255), width=max(2, int(r(4))))
    draw.line([xy(260, 96), xy(283, 96)], fill=(*WHITE, 255), width=max(2, int(r(4))))
    draw.rounded_rectangle((*xy(464, 105), *xy(489, 119)), radius=int(r(4)), fill=(*YELLOW, 255))
    draw.rounded_rectangle((*xy(9, 105), *xy(31, 119)), radius=int(r(4)), fill=(*RED, 255))
    if braking:
        draw.line([xy(-18, 110), xy(-4, 110)], fill=(*RED, 160), width=max(3, int(r(6))))
        draw.line([xy(-27, 122), xy(-4, 122)], fill=(*RED, 110), width=max(3, int(r(5))))
    for cx in (105, 389):
        wx, wy = xy(cx, 155)
        disc(draw, wx, wy, r(43), (12, 29, 38, 255), (*WHITE, 255), max(3, int(r(5))))
        disc(draw, wx, wy, r(25), (128, 153, 157, 255))
        disc(draw, wx, wy, r(9), (48, 75, 85, 255))
        for i in range(5):
            angle = time * 2 + i * math.tau / 5
            p1 = polar(wx, wy, r(10), angle)
            p2 = polar(wx, wy, r(22), angle)
            draw.line((p1, p2), fill=(*WHITE, 255), width=max(2, int(r(3))))


def road(draw, y, time, speed=75):
    draw.line((40, y, 680, y), fill=(200, 226, 222, 120), width=3)
    for i in range(-1, 9):
        x = 42 + i * 105 - (time * speed) % 105
        draw.rounded_rectangle((x, y + 22, x + 52, y + 28), radius=3, fill=(213, 233, 228, 90))


def visual_intro(image, time, duration):
    draw = ImageDraw.Draw(image, 'RGBA')
    if time < duration * 0.47:
        road(draw, 835, 0)
        shift = 52 * (1 - ease(time / 2.2))
        car(image, 105 - shift, 635, 510, min(time, 2.2), braking=time > 1.7)
        if time > 1.3:
            capsule(draw, (360, 490), 'REM DIINJAK', RED, WHITE, 24)
        outlined_capsule(draw, (360, 940), 'MESIN TETAP MENYALA', YELLOW, 23)
    else:
        local = time - duration * 0.47
        radius = 192 + 13 * ease(local / 0.8)
        for i in range(3):
            r = radius + 25 + i * 24
            draw.ellipse((360-r, 640-r, 360+r, 640+r), outline=(169, 214, 213, 35-i*8), width=2)
        rotor(image, 360, 640, radius, (150, 173, 178), local * 0.55, 18)
        capsule(draw, (360, 921), 'TORQUE CONVERTER', YELLOW, INK, 25, 26, 48)


def visual_connection(image, time, duration):
    draw = ImageDraw.Draw(image, 'RGBA')
    outlined_capsule(draw, (360, 381), 'TENAGA MENGALIR MELALUI OLI', BLUE, 21)
    draw.line((129, 618, 591, 618), fill=(161, 213, 218, 90), width=5)
    flowing_dots(draw, 145, 575, 617, time, YELLOW, 8, 0.15)
    engine(image, 124, 618, 140)
    rotor(image, 360, 618, 128, (151, 172, 174), time * 0.7, 17)
    gearbox(image, 596, 618, 140)
    for x, text in ((124, 'MESIN'), (360, 'TORCON'), (596, 'TRANSMISI')):
        centered(draw, (x, 790), text, 'display', 35, WHITE, max_width=190)
    centered(draw, (360, 911), 'MESIN  >  OLI  >  TRANSMISI', 'bold', 23, MUTED)


def visual_parts(image, time, duration):
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.line((89, 514, 631, 514), fill=(194, 225, 218, 85), width=4)
    rotor(image, 145, 516, 95, ORANGE, time * 0.55, 15)
    rotor(image, 360, 516, 82, GREEN, 0.15, 11)
    rotor(image, 575, 516, 95, BLUE, time * 0.35, 15)
    for x, text, color in ((145, 'IMPELER', ORANGE), (360, 'STATOR', GREEN), (575, 'TURBIN', BLUE)):
        capsule(draw, (x, 658), text, color, INK, 20, 14, 37)
    panel = (65, 728, 655, 953)
    draw.rounded_rectangle(panel, radius=24, fill=(10, 29, 38, 150), outline=(177, 211, 211, 50), width=2)
    lines = ((ORANGE, 'IMPELER', 'DIPUTAR MESIN'),
             (BLUE, 'TURBIN', 'TERHUBUNG KE TRANSMISI'),
             (GREEN, 'STATOR', 'MENGARAHKAN OLI'))
    for i, (color, label, description) in enumerate(lines):
        y = 763 + i * 64
        disc(draw, 98, y + 13, 7, (*color, 255))
        draw.text((120, y), label, font=font('bold', 25), fill=(*WHITE, 255))
        draw.text((305, y + 2), description, font=font('body', 21), fill=(*MUTED, 255))


def visual_flow(image, time, duration):
    draw = ImageDraw.Draw(image, 'RGBA')
    rotor(image, 190, 620, 139, ORANGE, time * 1.0, 15)
    rotor(image, 530, 620, 139, BLUE, time * 0.78, 15)
    arrow(draw, [(160, 444), (210, 398), (510, 398), (560, 445)], BLUE, 9, 23)
    flowing_dots(draw, 223, 495, 398, time, WHITE, 5, 0.12)
    arrow(draw, [(560, 796), (510, 837), (211, 837), (160, 796)], (100, 201, 221), 7, 20)
    capsule(draw, (360, 449), 'ALIRAN OLI', BLUE, INK, 23, 20, 42)
    outlined_capsule(draw, (190, 920), 'IMPELER', ORANGE, 21)
    outlined_capsule(draw, (530, 920), 'TURBIN', BLUE, 21)


def visual_idle(image, time, duration):
    draw = ImageDraw.Draw(image, 'RGBA')
    capsule(draw, (360, 382), 'REM DIINJAK', RED, WHITE, 23, 21, 44)
    rotor(image, 190, 625, 140, ORANGE, time * 1.1, 15)
    rotor(image, 530, 625, 140, BLUE, 0.2, 15)
    draw.rounded_rectangle((334, 589, 349, 660), radius=5, fill=(*WHITE, 230))
    draw.rounded_rectangle((371, 589, 386, 660), radius=5, fill=(*WHITE, 230))
    centered(draw, (190, 805), 'IMPELER', 'display', 39, ORANGE, max_width=260)
    centered(draw, (190, 851), 'BERPUTAR', 'bold', 22, WHITE, max_width=260)
    centered(draw, (530, 805), 'TURBIN', 'display', 39, BLUE, max_width=260)
    centered(draw, (530, 851), 'BISA DIAM', 'bold', 22, WHITE, max_width=260)
    outlined_capsule(draw, (360, 950), 'ADA SELISIH PUTARAN', YELLOW, 22)


def arc_points(x, y, radius, start, end, count=30):
    return [polar(x, y, radius, start + (end-start) * i / (count-1)) for i in range(count)]


def visual_stator(image, time, duration):
    draw = ImageDraw.Draw(image, 'RGBA')
    rotor(image, 360, 600, 165, GREEN, 0.1, 11)
    arrow(draw, arc_points(360, 600, 220, math.radians(210), math.radians(315)), ORANGE, 9, 23)
    arrow(draw, arc_points(360, 600, 220, math.radians(30), math.radians(135)), BLUE, 9, 23)
    capsule(draw, (360, 602), 'STATOR', GREEN, INK, 22, 18, 42)
    centered(draw, (360, 854), 'TARIKAN AWAL', 'bold', 22, MUTED)
    draw.rounded_rectangle((102, 908, 618, 932), radius=12, fill=(9, 27, 36, 220))
    end = 103 + 514 * (0.35 + 0.57 * ease(time / 3.5))
    draw.rounded_rectangle((103, 909, end, 931), radius=11, fill=(*YELLOW, 255))
    centered(draw, (360, 956), 'TORSI DAPAT MENINGKAT', 'bold', 22, WHITE)


def visual_lockup(image, time, duration):
    draw = ImageDraw.Draw(image, 'RGBA')
    close = ease(time / 2.8)
    left = 218 + close * 32
    right = 502 - close * 32
    rotor(image, left, 610, 130, ORANGE, time * 0.75, 15)
    rotor(image, right, 610, 130, BLUE, time * (0.4 + 0.35 * close), 15)
    draw.rounded_rectangle((313, 572, 407, 648), radius=22, fill=(13, 35, 43, 240),
                           outline=(*WHITE, 255), width=4)
    draw.rounded_rectangle((327, 588, 370, 622), radius=17, outline=(*YELLOW, 255), width=7)
    draw.rounded_rectangle((350, 600, 393, 634), radius=17, outline=(*YELLOW, 255), width=7)
    capsule(draw, (360, 391), 'LOCK-UP', YELLOW, INK, 22, 22, 42)
    centered(draw, (360, 820), 'KOPLING TERHUBUNG', 'display', 43, WHITE)
    outlined_capsule(draw, (360, 915), 'SELIP BERKURANG', BLUE, 22)


def visual_outro(image, time, duration):
    draw = ImageDraw.Draw(image, 'RGBA')
    capsule(draw, (360, 393), 'MESIN  >  TORCON  >  TRANSMISI', YELLOW, INK, 21, 21, 42)
    road(draw, 830, time)
    car(image, 105 + 12 * math.sin(time * 0.8), 632, 510, time)
    centered(draw, (360, 927), 'OLI MENYALURKAN TENAGA', 'bold', 25, WHITE)
    centered(draw, (360, 970), 'HALUS & EFISIEN', 'display', 35, YELLOW)


VISUALS = {
    'intro': visual_intro,
    'connection': visual_connection,
    'parts': visual_parts,
    'flow': visual_flow,
    'idle': visual_idle,
    'stator': visual_stator,
    'lockup': visual_lockup,
    'outro': visual_outro,
}


def scene_image(scene: TimedScene, time: float, progress: float) -> Image.Image:
    image = background().copy()
    header(image, scene, time, progress)
    VISUALS[scene.scene.visual](image, time, scene.duration)
    return image


@lru_cache(maxsize=32)
def cached_cues(scene: TimedScene):
    return caption_cues(scene)


def caption(image: Image.Image, scene: TimedScene, absolute_time: float):
    phrase = None
    for start, end, text in cached_cues(scene):
        if start <= absolute_time < end:
            phrase = text
            break
    if not phrase:
        return
    draw = ImageDraw.Draw(image, 'RGBA')
    face = fitted_font(draw, phrase, 'bold', 37, 590)
    width = draw.textlength(phrase, font=face)
    left = (WIDTH - width) / 2
    draw.rounded_rectangle((left - 23, 1080, left + width + 23, 1148), radius=18,
                           fill=(7, 19, 26, 225), outline=(185, 220, 214, 60), width=2)
    words = phrase.split(' ')
    space = draw.textlength(' ', font=face)
    for i, word in enumerate(words):
        fill = YELLOW if i == len(words) - 1 else WHITE
        draw.text((left + 1, 1093), word, font=face, fill=(0, 0, 0, 255), stroke_width=3,
                  stroke_fill=(0, 0, 0, 255))
        draw.text((left, 1091), word, font=face, fill=(*fill, 255))
        left += draw.textlength(word, font=face) + space
    centered(draw, (360, 1202), 'TORQUE CONVERTER  •  MOBIL MATIK', 'body', 18, MUTED, shadow=False)
