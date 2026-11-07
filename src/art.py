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
WHITE = (247, 250, 244)
MUTED = (166, 194, 197)
YELLOW = (255, 210, 70)
ORANGE = (250, 145, 52)
BLUE = (57, 190, 229)
GREEN = (78, 211, 151)
RED = (255, 97, 86)
INK = (8, 25, 35)


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


def fitted_font(draw, text: str, name: str, size: int, max_width: int):
    while size > 16 and draw.textlength(text, font=font(name, size)) > max_width:
        size -= 2
    return font(name, size)


def centered(draw, xy, text, name='bold', size=30, fill=WHITE, shadow=True, max_width=640):
    x, y = xy
    face = fitted_font(draw, text, name, size, max_width)
    if shadow:
        draw.text((x + 2, y + 4), text, font=face, fill=(3, 15, 22, 220), anchor='mt',
                  stroke_width=2, stroke_fill=(3, 15, 22, 220))
    draw.text((x, y), text, font=face, fill=fill, anchor='mt')


def disc(draw, x, y, r, fill, outline=None, width=1):
    draw.ellipse((x-r, y-r, x+r, y+r), fill=fill, outline=outline, width=width)


def ellipse(draw, x, y, rx, ry, fill=None, outline=None, width=1):
    draw.ellipse((x-rx, y-ry, x+rx, y+ry), fill=fill, outline=outline, width=width)


def polar(x, y, radius, angle):
    return (x + radius * math.cos(angle), y + radius * math.sin(angle))


def polar_ellipse(x, y, rx, ry, fraction, angle):
    return (x + rx * fraction * math.cos(angle), y + ry * fraction * math.sin(angle))


@lru_cache(maxsize=1)
def background() -> Image.Image:
    x = np.linspace(-1, 1, WIDTH, dtype=np.float32)[None, :]
    y = np.linspace(0, 1, HEIGHT, dtype=np.float32)[:, None]
    cool = np.exp(-((x / 0.85) ** 2 + ((y - 0.53) / 0.39) ** 2) * 1.3)
    warm = np.exp(-(((x + 0.82) / 0.60) ** 2 + ((y - 0.24) / 0.33) ** 2) * 1.8)
    vignette = np.clip(1 - 0.23 * x * x - 0.24 * (y - 0.48) ** 2, 0.60, 1)
    grain = np.random.default_rng(19).normal(0, 0.8, (HEIGHT, WIDTH))
    data = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for channel, (base, blue, amber) in enumerate(((9, 14, 9), (22, 27, 5), (31, 32, 1))):
        data[:, :, channel] = np.clip((base + blue * cool + amber * warm) * vignette + grain, 0, 255)
    result = Image.fromarray(data, 'RGB')
    draw = ImageDraw.Draw(result, 'RGBA')
    for x0 in range(-140, WIDTH + 160, 76):
        draw.line((x0, 345, x0 + 230, 1045), fill=(180, 215, 214, 8), width=1)
    for y0 in range(385, 1060, 76):
        draw.line((0, y0, WIDTH, y0), fill=(180, 215, 214, 8), width=1)
    return result


def ambience(image: Image.Image, time: float):
    draw = ImageDraw.Draw(image, 'RGBA')
    cx, cy = 360, 640
    for r, phase, alpha in ((272, 0, 36), (310, 70, 27), (358, 150, 18)):
        box = (cx-r, cy-r*0.82, cx+r, cy+r*0.82)
        draw.arc(box, phase + time * 4, phase + 84 + time * 4,
                 fill=(150, 213, 219, alpha), width=2)
        draw.arc(box, phase + 180 + time * 4, phase + 240 + time * 4,
                 fill=(255, 202, 101, alpha), width=2)
    for i in range(21):
        x = 32 + (i * 173 + time * (6 + i % 4)) % 657
        y = 342 + ((i * 131 - time * (3 + i % 3)) % 660)
        size = 1.3 + (i % 3) * 0.7
        disc(draw, x, y, size, (229, 245, 232, 30 + i % 3 * 10))


def header(image: Image.Image, scene: TimedScene, time: float):
    draw = ImageDraw.Draw(image, 'RGBA')
    start_y = 82 if len(scene.scene.title) == 3 else 105
    for index, line in enumerate(scene.scene.title):
        appear = ease((time - index * 0.08) / 0.48)
        offset = 22 * (1 - appear)
        centered(draw, (360, start_y + index * 87 + offset), line,
                 name='display', size=88 if len(scene.scene.title) == 2 else 84,
                 fill=YELLOW if index == scene.scene.highlight else WHITE, max_width=644)
    # A pair of small bolts frames the title without suggesting playback controls.
    for x in (56, 664):
        disc(draw, x, 126, 4, (*YELLOW, 200))
        disc(draw, x, 126, 1.5, (*INK, 255))


def capsule(draw, center, text, color=YELLOW, text_color=INK, size=23, pad=20, height=42):
    x, y = center
    face = fitted_font(draw, text, 'bold', size, 565)
    width = draw.textlength(text, font=face) + pad * 2
    box = (x-width/2, y-height/2, x+width/2, y+height/2)
    draw.rounded_rectangle((box[0] + 2, box[1] + 4, box[2] + 2, box[3] + 4),
                           radius=height//2, fill=(2, 14, 21, 130))
    draw.rounded_rectangle(box, radius=height//2, fill=(*color, 255))
    draw.text((x, y-size*0.49), text, font=face, fill=(*text_color, 255), anchor='mt')


def outlined_capsule(draw, center, text, color=WHITE, size=22, pad=18, height=42):
    x, y = center
    face = fitted_font(draw, text, 'bold', size, 560)
    width = draw.textlength(text, font=face) + pad*2
    draw.rounded_rectangle((x-width/2, y-height/2, x+width/2, y+height/2),
                           radius=height//2, fill=(11, 31, 41, 230), outline=(*color, 235), width=2)
    draw.text((x, y-size*0.49), text, font=face, fill=(*color, 255), anchor='mt')


def rotor(image: Image.Image, x: float, y: float, r: float,
          color: tuple[int, int, int], angle: float, blades: int = 15):
    if r < 20:
        return
    draw = ImageDraw.Draw(image, 'RGBA')
    rx, ry = r * 0.86, r
    depth = max(8, r * 0.16)
    ellipse(draw, x + depth + 5, y + depth + 11, rx + 8, ry + 8, (0, 8, 13, 110))
    ellipse(draw, x + depth, y + depth * 0.58, rx + 4, ry + 4,
            (59, 76, 83, 255), (*WHITE, 230), max(2, round(r/80)))
    ellipse(draw, x + depth * 0.65, y + depth * 0.33, rx + 4, ry + 4,
            (100, 121, 126, 255), (28, 50, 58, 255), max(2, round(r/70)))
    ellipse(draw, x, y, rx + 5, ry + 5, (234, 243, 239, 255))
    ellipse(draw, x, y, rx + 1, ry + 1, (30, 52, 61, 255))
    ellipse(draw, x, y, rx - 5, ry - 5, (149, 171, 172, 255))
    ellipse(draw, x, y, rx - 11, ry - 11, (62, 83, 91, 255))
    ellipse(draw, x, y, rx * 0.87, ry * 0.87, (*mix(color, 0.43), 255))
    ellipse(draw, x, y, rx * 0.80, ry * 0.80, (*mix(color, 0.72), 255))

    for n in range(blades):
        theta = angle + n * math.tau / blades
        points = [
            polar_ellipse(x, y, rx, ry, 0.24, theta - 0.07),
            polar_ellipse(x, y, rx, ry, 0.42, theta - 0.015),
            polar_ellipse(x, y, rx, ry, 0.63, theta + 0.08),
            polar_ellipse(x, y, rx, ry, 0.80, theta + 0.18),
            polar_ellipse(x, y, rx, ry, 0.80, theta + 0.32),
            polar_ellipse(x, y, rx, ry, 0.62, theta + 0.22),
            polar_ellipse(x, y, rx, ry, 0.41, theta + 0.11),
            polar_ellipse(x, y, rx, ry, 0.24, theta + 0.04),
        ]
        light = 0.88 + 0.34 * (0.5 + 0.5 * math.cos(theta - 3.4))
        relief = max(2, r * 0.025)
        draw.polygon([(px + relief, py + relief * 0.55) for px, py in points],
                     fill=(*mix(color, 0.35), 255))
        draw.polygon(points, fill=(*mix(color, light), 255),
                     outline=(*mix(color, 0.38), 255), width=max(1, round(r/110)))
        draw.line(points[1:4], fill=(*mix(color, 1.38), 220), width=max(1, round(r/90)), joint='curve')
        draw.line(points[5:7], fill=(*mix(color, 0.58), 160), width=max(1, round(r/110)), joint='curve')

    for scale, fill, outline in ((0.295, (27, 45, 52, 255), (*WHITE, 245)),
                                  (0.245, (133, 157, 160, 255), (55, 78, 87, 255)),
                                  (0.175, (47, 69, 76, 255), (194, 214, 209, 235)),
                                  (0.102, (13, 31, 40, 255), (76, 103, 109, 255))):
        ellipse(draw, x, y, rx * scale, ry * scale, fill, outline, max(1, round(r/110)))
    ring = (x-rx*0.96, y-ry*0.96, x+rx*0.96, y+ry*0.96)
    draw.arc(ring, 205, 305, fill=(248, 255, 246, 210), width=max(2, round(r/40)))
    draw.arc(ring, 20, 105, fill=(19, 40, 48, 200), width=max(2, round(r/48)))
    for n in range(8):
        bx, by = polar_ellipse(x, y, rx, ry, 0.925, angle + n * math.tau / 8)
        disc(draw, bx, by, max(2, r*0.017), (28, 44, 49, 255))
        disc(draw, bx-r*0.004, by-r*0.004, max(1, r*0.006), (197, 210, 205, 230))


def arrow(draw, points, color=BLUE, width=8, tip=20):
    draw.line(points, fill=(*INK, 190), width=width+9, joint='curve')
    draw.line(points, fill=(*mix(color, 0.70), 255), width=width+3, joint='curve')
    draw.line(points, fill=(*color, 255), width=width, joint='curve')
    ex, ey = points[-1]
    px, py = points[-2]
    angle = math.atan2(ey-py, ex-px)
    left = (ex-tip*math.cos(angle-0.55), ey-tip*math.sin(angle-0.55))
    right = (ex-tip*math.cos(angle+0.55), ey-tip*math.sin(angle+0.55))
    draw.polygon(((ex, ey), left, right), fill=(*color, 255))


def bezier(a, b, c, d, count=45):
    points = []
    for n in range(count):
        t = n / (count - 1)
        u = 1 - t
        points.append((u**3*a[0] + 3*u*u*t*b[0] + 3*u*t*t*c[0] + t**3*d[0],
                       u**3*a[1] + 3*u*u*t*b[1] + 3*u*t*t*c[1] + t**3*d[1]))
    return points


def particles(draw, points, time, color=BLUE, count=5, speed=0.20):
    for i in range(count):
        p = (time*speed + i/count) % 1
        index = min(len(points)-1, int(p*(len(points)-1)))
        old = max(0, index-2)
        draw.line((points[old], points[index]), fill=(*color, 105), width=8)
        x, y = points[index]
        disc(draw, x, y, 5, (*color, 200))
        disc(draw, x-1, y-1, 2, (*WHITE, 235))


def spark(draw, x, y, size, color=YELLOW):
    draw.polygon(((x, y-size), (x+size*0.22, y-size*0.22), (x+size, y),
                  (x+size*0.22, y+size*0.22), (x, y+size),
                  (x-size*0.22, y+size*0.22), (x-size, y),
                  (x-size*0.22, y-size*0.22)), fill=(*color, 210))


def orbit(draw, x, y, rx, ry, time, color=BLUE):
    box = (x-rx, y-ry, x+rx, y+ry)
    start = time*28
    draw.arc(box, start, start+78, fill=(*color, 145), width=3)
    draw.arc(box, start+166, start+218, fill=(*WHITE, 95), width=2)
    a = math.radians(start+78)
    px, py = x+rx*math.cos(a), y+ry*math.sin(a)
    disc(draw, px, py, 4, (*color, 230))


def engine(image, x, y, size, time):
    draw = ImageDraw.Draw(image, 'RGBA')
    s = size / 150
    def xy(a, b): return (x+a*s, y+b*s)
    draw.rounded_rectangle((*xy(-65, -29), *xy(64, 58)), radius=int(14*s),
                           fill=(91, 115, 123, 255), outline=(*WHITE, 245), width=max(3, int(4*s)))
    draw.polygon([xy(-54,-29), xy(-43,-58), xy(35,-58), xy(48,-29)],
                 fill=(160, 183, 182, 255), outline=(*WHITE, 245), width=max(3, int(4*s)))
    draw.polygon([xy(-57,-23), xy(58,-23), xy(58,-8), xy(-57,-8)], fill=(142, 168, 169, 255))
    draw.line([xy(-40,-58), xy(-40,-75), xy(15,-75)], fill=(*WHITE, 255), width=max(3,int(5*s)))
    draw.line([xy(63,-4), xy(78,-4), xy(78,32), xy(63,32)], fill=(*WHITE,255), width=max(3,int(5*s)))
    for a in (-39,-13,13):
        draw.rounded_rectangle((*xy(a,-19), *xy(a+14,6)), radius=int(4*s), fill=(35,59,68,255))
    disc(draw, *xy(-31,31), 17*s, (42,65,74,255), (*WHITE,255), max(2,int(3*s)))
    disc(draw, *xy(-31,31), 7*s, (*YELLOW,255))
    for n in range(4):
        a=time*2+n*math.pi/2
        p=polar(*xy(-31,31), 13*s, a)
        disc(draw, *p, 2*s, (*WHITE,230))
    draw.line([xy(4,27),xy(44,27)], fill=(*WHITE,255), width=max(2,int(4*s)))
    draw.line([xy(4,42),xy(35,42)], fill=(183,209,205,255), width=max(2,int(4*s)))


def gearbox(image, x, y, size):
    draw = ImageDraw.Draw(image, 'RGBA')
    s = size / 150
    def xy(a,b): return (x+a*s, y+b*s)
    points=[xy(-70,-44),xy(-30,-56),xy(35,-45),xy(62,-25),
            xy(68,27),xy(35,49),xy(-30,56),xy(-70,44)]
    draw.polygon(points, fill=(99,128,135,255), outline=(*WHITE,255), width=max(3,int(4*s)))
    draw.polygon([xy(-20,-44),xy(34,-37),xy(58,-19),xy(58,-4),xy(-20,-9)], fill=(144,172,172,255))
    disc(draw,*xy(-42,0),34*s,(54,78,87,255),(*WHITE,255),max(2,int(4*s)))
    disc(draw,*xy(-42,0),19*s,(165,190,186,255))
    disc(draw,*xy(-42,0),9*s,(36,59,69,255))
    for a in (-5,11,27,43):
        draw.line([xy(a,-30),xy(a,30)], fill=(44,71,79,255), width=max(2,int(4*s)))


def car(image, x, y, width, time, braking=False):
    draw = ImageDraw.Draw(image, 'RGBA')
    s = width/500
    def xy(a,b): return (x+a*s, y+b*s)
    def r(a): return a*s
    draw.ellipse((*xy(15,165),*xy(490,205)),fill=(1,12,19,120))
    body=[xy(7,116),xy(18,89),xy(72,74),xy(114,32),xy(158,15),xy(290,15),
          xy(344,32),xy(391,73),xy(457,87),xy(489,109),xy(488,151),xy(468,165),
          xy(32,165),xy(12,151)]
    draw.polygon(body,fill=(87,133,146,255),outline=(*WHITE,255),width=max(4,int(r(5))))
    draw.polygon([xy(17,91),xy(72,75),xy(389,75),xy(454,88),xy(477,105),xy(24,105)],
                 fill=(147,187,191,255))
    draw.polygon([xy(20,126),xy(482,126),xy(483,146),xy(457,151),xy(37,151),xy(20,145)],
                 fill=(69,111,123,255))
    draw.polygon([xy(84,73),xy(123,39),xy(159,27),xy(225,27),xy(225,73)],
                 fill=(24,52,65,255),outline=(220,239,233,255),width=max(2,int(r(3))))
    draw.polygon([xy(238,27),xy(288,27),xy(333,42),xy(367,73),xy(238,73)],
                 fill=(26,55,67,255),outline=(220,239,233,255),width=max(2,int(r(3))))
    draw.line([xy(105,65),xy(138,38),xy(190,32)],fill=(155,199,205,130),width=max(2,int(r(3))))
    draw.line([xy(233,81),xy(233,145)],fill=(45,83,96,255),width=max(2,int(r(3))))
    draw.line([xy(150,96),xy(173,96)],fill=(*WHITE,255),width=max(2,int(r(4))))
    draw.line([xy(260,96),xy(283,96)],fill=(*WHITE,255),width=max(2,int(r(4))))
    draw.rounded_rectangle((*xy(463,104),*xy(489,119)),radius=max(1,int(r(4))),fill=(*YELLOW,255))
    draw.rounded_rectangle((*xy(9,104),*xy(31,119)),radius=max(1,int(r(4))),fill=(*RED,255))
    if braking:
        for i in range(3):
            draw.line([xy(-12-i*9,107+i*8),xy(1,107+i*8)],fill=(*RED,175-i*30),width=max(2,int(r(4))))
    for cx in (105,389):
        wx,wy=xy(cx,155)
        disc(draw,wx,wy,r(43),(8,23,30,255),(*WHITE,255),max(3,int(r(4))))
        disc(draw,wx,wy,r(32),(57,81,89,255),(17,38,46,255),max(2,int(r(3))))
        disc(draw,wx,wy,r(24),(168,188,187,255))
        disc(draw,wx,wy,r(8),(42,65,73,255))
        for n in range(5):
            a=time*2+n*math.tau/5
            draw.line((polar(wx,wy,r(9),a),polar(wx,wy,r(22),a)),
                      fill=(48,77,86,255),width=max(2,int(r(4))))


def road(draw, y, time, speed=110):
    draw.line((40,y,680,y),fill=(185,224,220,105),width=3)
    for n in range(-1,8):
        x=42+n*110-(time*speed)%110
        draw.line((x,y+23,x+48,y+23),fill=(218,239,232,85),width=4)


@lru_cache(maxsize=64)
def cue_start(scene: TimedScene, needle: str, default: float) -> float:
    for start, _, phrase in caption_cues(scene):
        if needle.casefold() in phrase.casefold():
            return start-scene.start
    return default


def visual_intro(image, time, scene):
    draw=ImageDraw.Draw(image,'RGBA')
    reveal_start=cue_start(scene,'Rahasianya',scene.duration*0.55)
    reveal=ease((time-reveal_start)/0.65)
    if reveal < 0.98:
        road(draw, 838+reveal*70, 0)
        shift=70*(1-ease(time/1.3))
        car(image, 100-shift, 636+reveal*190, 520*(1-reveal*0.16), min(time,1.3), braking=time>1.3)
        if time>1.1 and reveal<0.45:
            capsule(draw,(360,475),'REM DIINJAK',RED,WHITE,23,22,44)
            outlined_capsule(draw,(360,929),'MESIN TETAP MENYALA',YELLOW,22)
    if reveal>0:
        r=205*reveal
        orbit(draw,360,630,r+34,(r+34)*0.91,time,YELLOW)
        rotor(image,360,630,r,(161,181,184),time*0.65,18)
        if reveal>0.55:
            capsule(draw,(360,914),'TORQUE CONVERTER',YELLOW,INK,25,25,48)
            spark(draw,155,481,9,YELLOW)
            spark(draw,572,757,7,BLUE)


def visual_connection(image, time, scene):
    draw=ImageDraw.Draw(image,'RGBA')
    enter=ease(time/0.75)
    focus=ease((time-cue_start(scene,'Uniknya, tenaga dikirim',scene.duration*0.5))/0.8)
    left=118-55*(1-enter)-260*focus
    right=602+55*(1-enter)+260*focus
    y=615
    draw.line((left+40,y,right-40,y),fill=(115,175,184,100),width=13)
    draw.line((left+40,y,right-40,y),fill=(211,234,226,135),width=3)
    top=bezier((max(38,left+45),580),(220,495-40*focus),(500,495-40*focus),
               (min(682,right-45),580))
    arrow(draw,top,BLUE,5,15)
    particles(draw,top,time,BLUE,7,0.15)
    if left > -100:
        engine(image,left,y,145,time)
    if right < WIDTH+100:
        gearbox(image,right,y,145)
    radius=(139+40*focus)*(0.88+0.12*enter)
    orbit(draw,360,y,radius+23,(radius+23)*1.09,time,YELLOW)
    if focus>0.1:
        oil=arc_points(360,y,radius+45,radius+55,math.radians(35+time*22),
                       math.radians(135+time*22))
        arrow(draw,oil,BLUE,6,17)
        particles(draw,oil,time,WHITE,3,0.22)
    rotor(image,360,y,radius,(157,180,183),time*0.85,18)
    for x,text in ((left,'MESIN'),(360,'TORCON'),(right,'TRANSMISI')):
        if 50<x<670:
            centered(draw,(x,818+28*focus),text,'display',36,WHITE,max_width=190)
    outlined_capsule(draw,(360,938),'TENAGA MENGALIR MELALUI OLI',BLUE,21,20,42)


def visual_parts(image, time, scene):
    draw=ImageDraw.Draw(image,'RGBA')
    reveal_start=cue_start(scene,'Impeler berputar',scene.duration*0.25)
    unfold=ease((time-reveal_start+0.35)/0.75)
    if unfold<0.95:
        rotor(image,360,580,160*(1-0.6*unfold),(150,173,177),time*0.6,18)
        if unfold<0.35:
            outlined_capsule(draw,(360,815),'TIGA BAGIAN UTAMA',YELLOW,22)
    if unfold<=0.05:
        return
    specs=[(150,ORANGE,'IMPELER','Impeler berputar',96),
           (570,BLUE,'TURBIN','turbin tersambung',96),
           (360,GREEN,'STATOR','stator mengatur',78)]
    draw.line((90,565,630,565),fill=(181,214,211,75),width=4)
    for target_x,color,label,needle,radius in specs:
        start=cue_start(scene,needle,reveal_start)
        pop=ease((time-start+0.20)/0.55)
        x=360+(target_x-360)*unfold
        y=565+(1-unfold)*50
        if pop>0.02:
            rotor(image,x,y,radius*(0.66+0.34*pop),color,time*(0.45 if label!='STATOR' else 0)+0.2,15 if label!='STATOR' else 11)
        elif unfold>0.80:
            ellipse(draw,x,y,radius*0.75,radius*0.88,outline=(*color,70),width=3)
        if pop>0.45 and unfold>0.80:
            capsule(draw,(target_x,710),label,color,INK,20,15,38)
    rows=[(ORANGE,'IMPELER','DIPUTAR MESIN','Impeler berputar'),
          (BLUE,'TURBIN','KE TRANSMISI','turbin tersambung'),
          (GREEN,'STATOR','ARAHKAN OLI','stator mengatur')]
    for n,(color,label,desc,needle) in enumerate(rows):
        active=ease((time-cue_start(scene,needle,reveal_start))/0.35)
        if active<=0.01:
            continue
        yy=770+n*61
        draw.rounded_rectangle((73,yy,647,yy+49),radius=14,
                               fill=(7,27,37,190),outline=(*color,100),width=2)
        disc(draw,98,yy+24,6,(*color,255))
        draw.text((118,yy+8),label,font=font('bold',24),fill=(*WHITE,255))
        draw.text((318,yy+10),desc,font=font('body',21),fill=(*MUTED,255))


def visual_flow(image, time, scene):
    draw=ImageDraw.Draw(image,'RGBA')
    delivery=ease((time-cue_start(scene,'lalu tenaga diteruskan',scene.duration*0.7)+0.3)/1.0)
    left=185-60*delivery
    right=535-120*delivery
    radius=136-22*delivery
    upper=bezier((left-48,522),(left-32,370),(right+32,370),(right+48,522))
    lower=bezier((right+48,722),(right+32,870),(left-32,870),(left-48,722))
    arrow(draw,upper,BLUE,8,21)
    arrow(draw,lower,(112,211,225),7,19)
    particles(draw,upper,time,WHITE,7,0.18)
    particles(draw,lower,time+0.8,BLUE,6,0.13)
    rotor(image,left,620,radius,ORANGE,time*1.15,16)
    rotor(image,right,620,radius,BLUE,time*0.87,16)
    orbit(draw,left,620,radius+6,radius+22,time,ORANGE)
    orbit(draw,right,620,radius+6,radius+22,time*0.85,BLUE)
    if delivery>0.08:
        path=bezier((right+radius*0.86+14,620),(right+radius+35,620),
                    (588,620),(600,620))
        arrow(draw,path,YELLOW,6,16)
        particles(draw,path,time,YELLOW,3,0.25)
        gearbox(image,630+(1-delivery)*90,620,125)
    capsule(draw,((left+right)/2,432),'ALIRAN OLI',BLUE,INK,23,22,44)
    outlined_capsule(draw,(left,884),'IMPELER',ORANGE,20)
    outlined_capsule(draw,(right,884),'TURBIN',BLUE,20)
    if delivery>0.6:
        outlined_capsule(draw,(630,884),'TRANSMISI',WHITE,18,12,38)
    centered(draw,(360,950),'TENAGA DITERUSKAN', 'display',38, WHITE)


def visual_idle(image, time, scene):
    draw=ImageDraw.Draw(image,'RGBA')
    pulse=0.5+0.5*math.sin(time*3)
    ellipse(draw,360,401,142+5*pulse,32+3*pulse,fill=(*RED,30))
    capsule(draw,(360,401),'REM DIINJAK',RED,WHITE,23,24,44)
    rotor(image,185,620,132,ORANGE,time*1.2,16)
    rotor(image,535,620,132,BLUE,0.15,16)
    orbit(draw,185,620,139,154,time,ORANGE)
    centered(draw,(185,785),'IMPELER', 'display',39, ORANGE, max_width=260)
    centered(draw,(185,831),'TETAP BERPUTAR','bold',22,WHITE,max_width=260)
    centered(draw,(535,785),'TURBIN', 'display',39, BLUE, max_width=260)
    centered(draw,(535,831),'BISA DIAM','bold',22,WHITE,max_width=260)
    for n in range(3):
        xx=325+n*35
        yy=619+7*math.sin(time*3+n)
        disc(draw,xx,yy,5,(*BLUE,180))
    outlined_capsule(draw,(360,938),'MESIN TETAP MENYALA',YELLOW,23,20,46)


def arc_points(x,y,rx,ry,start,end,count=35):
    return [(x+rx*math.cos(start+(end-start)*n/(count-1)),
             y+ry*math.sin(start+(end-start)*n/(count-1))) for n in range(count)]


def visual_stator(image, time, scene):
    draw=ImageDraw.Draw(image,'RGBA')
    boost=ease((time-cue_start(scene,'sehingga tarikan awal',scene.duration*0.7)+0.2)/0.9)
    cy=590-85*boost
    r=164-48*boost+4*math.sin(time*0.9)
    rotor(image,360,cy,r,GREEN,0.12,11)
    rx,ry=r+60,r+65
    upper=arc_points(360,cy,rx,ry,math.radians(200),math.radians(322))
    lower=arc_points(360,cy,rx,ry,math.radians(22),math.radians(142))
    arrow(draw,upper,ORANGE,9,22)
    arrow(draw,lower,BLUE,9,22)
    particles(draw,upper,time,WHITE,4,0.14)
    particles(draw,lower,time+1.0,BLUE,4,0.14)
    capsule(draw,(360,cy),'STATOR',GREEN,INK,22,18,42)
    if boost<0.5:
        for side in (-1,1):
            for n in range(3):
                x=360+side*(145+n*24)
                y=891-(time*28+n*26)%75
                draw.line((x-10,y+9,x,y-2,x+10,y+9),fill=(*YELLOW,145),width=4,joint='curve')
        centered(draw,(360,842),'TARIKAN AWAL','bold',24,MUTED)
        centered(draw,(360,894),'TORSI LEBIH KUAT','display',45,YELLOW)
        centered(draw,(360,957),'PADA KONDISI TERTENTU','body',21,WHITE)
    else:
        centered(draw,(360,731),'TARIKAN AWAL LEBIH KUAT','display',41,YELLOW)
        road(draw,976,time)
        car(image,157+12*math.sin(time),810,405,time)


def visual_lockup(image, time, scene):
    draw=ImageDraw.Draw(image,'RGBA')
    lock_start=cue_start(scene,'kopling pengunci',scene.duration*0.3)
    close=ease((time-lock_start+0.35)/1.2)
    left=195+close*45
    right=525-close*45
    draw.line((55,612,665,612),fill=(200,229,222,90),width=7)
    rotor(image,left,612,134,ORANGE,time*0.86,16)
    rotor(image,right,612,134,BLUE,time*(0.50+0.36*close),16)
    if close>0.05:
        pulse=1+0.08*math.sin(time*4)
        ellipse(draw,360,612,57*pulse,48*pulse,fill=(*YELLOW,30))
        draw.rounded_rectangle((311,570,409,654),radius=22,fill=(10,30,39,245),
                               outline=(*WHITE,255),width=4)
        draw.rounded_rectangle((325,587,370,622),radius=17,outline=(*YELLOW,255),width=7)
        draw.rounded_rectangle((350,601,395,636),radius=17,outline=(*YELLOW,255),width=7)
    capsule(draw,(360,405),'KOPLING PENGUNCI',YELLOW,INK,23,22,44)
    if close>0.65:
        centered(draw,(360,822),'TERHUBUNG LEBIH LANGSUNG','display',39,WHITE)
        outlined_capsule(draw,(360,918),'SELIP BERKURANG',BLUE,22,20,43)


def visual_outro(image,time,scene):
    draw=ImageDraw.Draw(image,'RGBA')
    orbit(draw,360,495,134,139,time,YELLOW)
    rotor(image,360,495,105,(154,181,183),time*0.8,17)
    capsule(draw,(360,670),'MESIN  >  TORCON  >  TRANSMISI',YELLOW,INK,20,19,42)
    road(draw,935,time)
    for n in range(5):
        x=(120+n*103-time*130)%600
        y=774+n*23
        draw.line((x-70,y,x,y),fill=(169,218,218,36+n*6),width=3)
    car(image,102+8*math.sin(time*0.8),735,515,time)
    ending=cue_start(scene,'Menarik, kan?',scene.duration*0.8)
    text='MENARIK, KAN?' if time>=ending else 'MELAJU LEBIH HALUS'
    centered(draw,(360,985),text,'display',37,YELLOW if time>=ending else WHITE)


VISUALS={
    'intro':visual_intro,
    'connection':visual_connection,
    'parts':visual_parts,
    'flow':visual_flow,
    'idle':visual_idle,
    'stator':visual_stator,
    'lockup':visual_lockup,
    'outro':visual_outro,
}


def scene_image(scene: TimedScene, time: float) -> Image.Image:
    image=background().copy()
    ambience(image,time)
    VISUALS[scene.scene.visual](image,time,scene)
    header(image,scene,time)
    return image


@lru_cache(maxsize=32)
def cached_cues(scene: TimedScene):
    return caption_cues(scene)


def caption(image: Image.Image, scene: TimedScene, absolute_time: float):
    current=None
    for start,end,text in cached_cues(scene):
        if start<=absolute_time<end:
            current=(start,end,text)
            break
    if not current:
        return
    start,end,phrase=current
    draw=ImageDraw.Draw(image,'RGBA')
    face=fitted_font(draw,phrase,'bold',38,590)
    width=draw.textlength(phrase,font=face)
    left=(WIDTH-width)/2
    draw.rounded_rectangle((left-23,1086,left+width+23,1156),radius=18,
                           fill=(4,18,26,230),outline=(193,224,214,65),width=2)
    words=phrase.split(' ')
    weights=[max(1,len(word.strip(',.!?'))) for word in words]
    position=clamp((absolute_time-start)/max(0.01,end-start))*sum(weights)
    active=len(words)-1
    total=0
    for i,weight in enumerate(weights):
        total+=weight
        if position<=total:
            active=i
            break
    space=draw.textlength(' ',font=face)
    for i,word in enumerate(words):
        color=YELLOW if i==active else WHITE
        draw.text((left+1,1100),word,font=face,fill=(0,0,0,255),stroke_width=3,
                  stroke_fill=(0,0,0,255))
        draw.text((left,1098),word,font=face,fill=(*color,255))
        left+=draw.textlength(word,font=face)+space
