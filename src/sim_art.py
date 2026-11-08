from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image

from . import sim_vector
from .art import (OUTPUT_HEIGHT, OUTPUT_WIDTH, SCALE, canvas, cue_start, ease,
                  fitted_font, font)
from .audio import TimedScene

INK = (25, 43, 59)
CREAM = (255, 246, 222)
YELLOW = (255, 211, 110)
RED = (240, 99, 87)
MINT = (140, 226, 204)
DARK_RED = (144, 48, 49)


@lru_cache(maxsize=8)
def background(kind: str) -> Image.Image:
    palettes = {
        'claim': ((48, 34, 72), (132, 77, 107)),
        'verdict': ((31, 46, 78), (57, 103, 126)),
        'validity': ((29, 73, 76), (74, 148, 126)),
        'phishing': ((75, 39, 61), (151, 79, 79)),
        'verify': ((29, 69, 76), (78, 149, 145)),
        'protect': ((49, 45, 78), (119, 96, 133)),
    }
    top, bottom = palettes[kind]
    yy = np.linspace(0, 1, OUTPUT_HEIGHT, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, OUTPUT_WIDTH, dtype=np.float32)[None, :]
    vignette = np.clip(1 - .15 * xx * xx, .82, 1)
    focus = np.exp(-(xx / .82) ** 2 - ((yy - .46) / .4) ** 2) * 10
    data = np.empty((OUTPUT_HEIGHT, OUTPUT_WIDTH, 3), dtype=np.uint8)
    for channel in range(3):
        data[:, :, channel] = np.clip(
            (top[channel] * (1 - yy) + bottom[channel] * yy) * vignette + focus,
            0, 255,
        )
    return Image.fromarray(data, 'RGB')


ASSETS = {
    'phone': sim_vector.phone,
    'shield': sim_vector.shield,
    'sim': sim_vector.sim_card,
    'calendar': sim_vector.calendar,
    'warning': sim_vector.warning,
    'building': sim_vector.building,
    'bank': sim_vector.bank_card,
    'share': sim_vector.share,
}


@lru_cache(maxsize=180)
def _resized(name: str, pixels: int) -> Image.Image:
    source = ASSETS[name]()
    height = max(1, round(source.height * pixels / source.width))
    return source.resize((pixels, height), Image.Resampling.LANCZOS)


@lru_cache(maxsize=64)
def _fractional_sprite(name: str, pixels: int, fx: int, fy: int) -> Image.Image:
    picture = _resized(name, pixels)
    if not (fx or fy):
        return picture
    return picture.transform((picture.width+1, picture.height+1), Image.Transform.AFFINE,
                             (1, 0, -fx/16, 0, 1, -fy/16),
                             resample=Image.Resampling.BILINEAR)


def sprite(image: Image.Image, name: str, x: float, y: float, width: float) -> None:
    pixels = max(1, round(width * SCALE / 3) * 3)
    original = _resized(name, pixels)
    left = round((x * SCALE - original.width/2) * 16)
    top = round((y * SCALE - original.height/2) * 16)
    ix, fx = divmod(left, 16)
    iy, fy = divmod(top, 16)
    picture = _fractional_sprite(name, pixels, fx, fy)
    image.paste(picture, (ix, iy), picture)


def text(image: Image.Image, content: str, x: float, y: float, size: float,
         color=CREAM, max_width: float = 620, *, face: str = 'display') -> None:
    d = canvas(image)
    selected = fitted_font(d, content, face, size, max_width)
    d.text((x, y), content, selected, (*color, 255), anchor='mm')


def plate(image: Image.Image, content: str, x: float, y: float, width: float,
          height: float, fill, color=INK, size=34, *, outline=None) -> None:
    d = canvas(image)
    d.rounded_rectangle((x - width / 2, y - height / 2, x + width / 2, y + height / 2),
                        radius=height * .2, fill=(*fill, 255),
                        outline=(*outline, 255) if outline else None, width=3)
    text(image, content, x, y - 1, size, color, width - 24)


def source(image: Image.Image, *, local: bool = False) -> None:
    date = '6 AGU 2026' if local else '4 NOV 2026'
    text(image, f'SUMBER: KORLANTAS POLRI • {date}', 360, 1124, 22,
         (225, 239, 225), 610, face='bold')


def _bob(time: float, speed: float = 1.1, distance: float = 6.0) -> float:
    return math.sin(time * speed) * distance


def _sway(time: float) -> float:
    return math.sin(time * .83 + .7) * 5.0


def _phone_header(image: Image.Image, x: float, y: float, width: float, content: str) -> None:
    d = canvas(image)
    d.rounded_rectangle((x-width/2, y-24, x+width/2, y+24), 8,
                        fill=(235, 224, 205, 255))
    d.ellipse((x-width/2+12, y-12, x-width/2+36, y+12), fill=(*RED, 255))
    text(image, content, x+14, y-1, 25, INK, width-64)


def claim(image: Image.Image, t: float, scene: TimedScene) -> None:
    rise = 55 * (1 - ease(t / .55))
    x, y = 360 + _sway(t), 625 + rise + _bob(t)
    sprite(image, 'phone', x, y, 430)
    dy = y - 625
    _phone_header(image, x, 343 + dy, 334, 'KLAIM VIRAL • NOV 2026')
    text(image, 'SIM GRATIS?', x, 460 + dy, 72, INK, 350)
    emphasis = DARK_RED if t >= cue_start(scene, 'bahkan berlaku', 2) else INK
    text(image, 'SEUMUR HIDUP?', x, 535 + dy, 60, emphasis, 355)
    d = canvas(image)
    d.line((x-159, 595+dy, x+159, 595+dy), fill=(202, 188, 166, 255), width=3)
    plate(image, 'KLAIM YANG DIBANTAH', x, 656+dy, 334, 54,
          (250, 219, 201), DARK_RED, 28)
    # The verdict is already visible early, before the spoken warning finishes.
    stamp = ease((t-.9)/.35)
    accent = (t - cue_start(scene, 'Eits,', 4.2)) / .55
    pulse = 1 + .08 * math.sin(math.pi * max(0, min(1, accent)))
    if stamp > .05:
        plate(image, 'HOAKS', x, 758+dy, 300*stamp*pulse, 96*stamp*pulse,
              RED, CREAM, max(20, 69*stamp*pulse), outline=(132, 42, 46))
    text(image, 'JANGAN LANGSUNG PERCAYA', x, 862+dy, 25, INK, 340, face='bold')
    source(image)


def verdict(image: Image.Image, t: float, scene: TimedScene) -> None:
    slide = ease(t / .6)
    phone_x = 202 + 48 * (1-slide) + _sway(t)
    y = 565 + _bob(t)
    sprite(image, 'phone', phone_x, y, 285)
    _phone_header(image, phone_x, y-193, 215, 'KLAIM VIRAL')
    text(image, 'SIM GRATIS?', phone_x, y-111, 45, INK, 214)
    text(image, 'SEUMUR HIDUP?', phone_x, y-54, 34, INK, 215)
    plate(image, 'DIBANTAH', phone_x, y+55, 205, 55, RED, CREAM, 34)
    d = canvas(image)
    arrow = ease((t-.35)/.6)
    tip = 348 + 42*arrow
    if arrow > 0:
        d.line((348, 570, tip, 570), fill=(*CREAM, 255), width=9)
        d.polygon(((tip, 548), (tip+31, 570), (tip, 592)), fill=(*CREAM, 255))
    pop = ease((t - cue_start(scene, 'dibantah Korlantas', .9) + .35) / .55)
    sprite(image, 'shield', 517-_sway(t), y, 210 + 45*pop)
    plate(image, 'DIBANTAH', 360, 872, 285, 72, RED, CREAM, 49)
    text(image, 'KORLANTAS POLRI', 360, 943, 48, CREAM, 580)
    text(image, 'BUKAN PENGUMUMAN RESMI', 360, 1001, 26, (222, 237, 226), 570, face='bold')
    source(image)


def validity(image: Image.Image, t: float, scene: TimedScene) -> None:
    rise = 45 * (1 - ease(t / .55))
    bob = _bob(t)
    plate(image, 'MASA BERLAKU SIM', 360, 324, 340, 62, MINT, INK, 37)
    x, y, width = 325 - 95*(1-ease(t/.65)) + _sway(t), 555+rise+bob, 545
    sprite(image, 'sim', x, y, width)
    top = y - width * 380 / 620 / 2
    text(image, 'SIM', x - 204, top + 57, 47, INK, 110)
    text(image, 'ILUSTRASI', x + 190, top + 57, 20, INK, 116, face='bold')
    pop = ease((t - cue_start(scene, 'lima tahun', 1.2) + .15) / .45)
    size = 160 + 48*pop
    cal_y = 720 + 10*(1-pop) + bob
    cal_x = 500 - _sway(t)
    sprite(image, 'calendar', cal_x, cal_y, size)
    text(image, '5', cal_x, cal_y+12, 82, INK, 100)
    plate(image, '5 TAHUN', 360, 863, 268, 77, YELLOW, INK, 58)
    if t > cue_start(scene, 'dan bisa diperpanjang', 2.2):
        text(image, 'DAPAT DIPERPANJANG', 360, 934, 35, CREAM, 550)
    if t > cue_start(scene, 'Biaya serta prosedurnya', 4.2):
        text(image, 'BIAYA SESUAI KETENTUAN', 360, 990, 24, (227, 241, 224), 565, face='bold')
    source(image)


def phishing(image: Image.Image, t: float, scene: TimedScene) -> None:
    rise = 38 * (1 - ease(t / .5))
    dx, y = _sway(t), 625 + rise + _bob(t)
    dy = y - 625
    sprite(image, 'phone', 360+dx, y, 430)
    _phone_header(image, 360+dx, 341+dy, 332, 'TAUTAN TAK DIKENAL')
    text(image, 'FORMULIR', 360+dx, 414+dy, 43, INK, 330)
    labels = ('DATA PRIBADI', 'FOTO IDENTITAS', 'KODE OTP')
    cues = ('yang meminta data pribadi,', 'foto identitas,', 'atau kode OTP!')
    for index, (content, cue) in enumerate(zip(labels, cues, strict=True)):
        cy = 500 + index*105 + dy
        active = t >= cue_start(scene, cue, 2 + index)
        fill = (250, 216, 202) if active else (235, 229, 211)
        edge = RED if active else (194, 190, 176)
        d = canvas(image)
        d.rounded_rectangle((192+dx, cy-38, 528+dx, cy+38), 9, fill=(*fill, 255),
                            outline=(*edge, 255), width=3)
        text(image, content, 335+dx, cy, 30, DARK_RED if active else INK, 238)
        if active:
            text(image, '×', 497+dx, cy, 40, DARK_RED, 36, face='bold')
    plate(image, 'JANGAN ASAL ISI', 360+dx, 846+dy, 325, 62, RED, CREAM, 35)
    sprite(image, 'warning', 537+dx, 337+dy, 112)
    source(image)


def verify(image: Image.Image, t: float, scene: TimedScene) -> None:
    plate(image, 'PROGRAM KHUSUS?', 360, 326, 340, 64, YELLOW, INK, 38)
    rise = 45 * (1 - ease(t / .6))
    x, y = 360 + _sway(t), 596 + rise + _bob(t)
    width = 530
    sprite(image, 'building', x, y, width)
    top = y - width * 430 / 600 / 2
    text(image, 'SATPAS', x, top + width * 186 / 600, 42, INK, 234)
    check = ease((t - cue_start(scene, 'Tapi cek tanggal', 2.5) + .2) / .45)
    if check > 0:
        plate(image, 'CEK TANGGAL & SYARAT', 360, 868, 490, 70, MINT, INK, 39)
        text(image, 'LANGSUNG KE KANAL RESMI', 360, 946, 31, CREAM, 590, face='bold')
    else:
        text(image, 'PROGRAM LOKAL BISA BERBEDA', 360, 900, 30, CREAM, 590, face='bold')
    official = ease((t - cue_start(scene, 'langsung lewat kanal resmi', 5.2)) / .5)
    if official > 0:
        sprite(image, 'shield', 578, 437, 90*official)
    source(image, local=True)


def protect(image: Image.Image, t: float, scene: TimedScene) -> None:
    d = canvas(image)
    bob = _bob(t)
    d.rounded_rectangle((55, 393+bob, 324, 622+bob), radius=18,
                        fill=(252, 240, 215, 255), outline=(*INK, 255), width=7)
    text(image, 'KODE OTP', 189, 450+bob, 37, INK, 230)
    d = canvas(image)
    for x in (112, 143, 174, 205, 236, 267):
        d.ellipse((x-6, 514+bob-6, x+6, 514+bob+6), fill=(*INK, 255))
    slash = ease(t / .45)
    if slash > 0:
        d.line((96, 586+bob, 96+188*slash, 586-116*slash+bob), fill=(*RED, 255), width=15)
    plate(image, 'JANGAN BAGIKAN', 189, 680, 266, 59, RED, CREAM, 30)
    text(image, 'KODE OTP', 189, 737, 29, CREAM, 260)
    bank_x = _sway(t)
    sprite(image, 'bank', 527+bank_x, 505-bob, 278)
    bank_slash = ease((t - cue_start(scene, 'dan jangan transfer', 1.9)) / .45)
    if bank_slash > 0:
        d = canvas(image)
        d.line((430+bank_x, 600-bob, 430+bank_x+195*bank_slash, 600-187*bank_slash-bob),
               fill=(*RED, 255), width=15)
    plate(image, 'JANGAN TRANSFER', 527, 680, 275, 59, RED, CREAM, 30)
    text(image, 'KE REKENING TAK JELAS', 527, 737, 26, CREAM, 290)
    share_pop = ease((t - cue_start(scene, 'Bagikan faktanya,', 5.4) + .2) / .55)
    sprite(image, 'share', 360, 855, 180 + 55*share_pop)
    if share_pop > .25:
        plate(image, 'BAGIKAN FAKTANYA', 360, 1012, 365, 67, MINT, INK, 40)
    source(image)


VISUALS = {
    'claim': claim,
    'verdict': verdict,
    'validity': validity,
    'phishing': phishing,
    'verify': verify,
    'protect': protect,
}


def scene_image(scene: TimedScene, time: float) -> Image.Image:
    image = background(scene.scene.visual).copy()
    VISUALS[scene.scene.visual](image, time, scene)
    return image
