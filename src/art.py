from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import geometry
from .audio import TimedScene, caption_cues

WIDTH, HEIGHT = 720, 1280
SCALE = 1.5
OUTPUT_WIDTH, OUTPUT_HEIGHT = 1080, 1920
ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / 'assets' / 'fonts'
WHITE = (247, 249, 242)
MUTED = (186, 200, 198)
YELLOW = (255, 213, 89)
ORANGE = (239, 151, 67)
BLUE = (68, 182, 220)
GREEN = (86, 193, 144)
RED = (235, 89, 75)
INK = (17, 31, 36)


class DesignDraw:
    def __init__(self, image: Image.Image):
        self.draw = ImageDraw.Draw(image, 'RGBA')

    @staticmethod
    def _points(points):
        if len(points) and isinstance(points[0], (tuple, list)):
            return [(x*SCALE, y*SCALE) for x,y in points]
        return tuple(value*SCALE for value in points)

    @staticmethod
    def _width(value):
        return max(1, round(value*SCALE))

    def ellipse(self, xy, fill=None, outline=None, width=1):
        self.draw.ellipse(self._points(xy), fill=fill, outline=outline, width=self._width(width))

    def rectangle(self, xy, fill=None, outline=None, width=1):
        self.draw.rectangle(self._points(xy), fill=fill, outline=outline, width=self._width(width))

    def line(self, xy, fill=None, width=0, joint=None):
        self.draw.line(self._points(xy), fill=fill, width=self._width(width), joint=joint)

    def polygon(self, xy, fill=None, outline=None, width=1):
        self.draw.polygon(self._points(xy), fill=fill, outline=outline, width=self._width(width))

    def rounded_rectangle(self, xy, radius=0, fill=None, outline=None, width=1):
        self.draw.rounded_rectangle(self._points(xy), radius=round(radius*SCALE), fill=fill,
                                    outline=outline, width=self._width(width))

    def text(self, xy, text, font=None, fill=None, anchor=None, stroke_width=0, stroke_fill=None):
        self.draw.text(self._points(xy), text, font=font, fill=fill, anchor=anchor,
                       stroke_width=round(stroke_width*SCALE), stroke_fill=stroke_fill)

    def textlength(self, text, font=None):
        return self.draw.textlength(text, font=font)/SCALE


def canvas(image):
    return DesignDraw(image)


def clamp(value, low=0, high=1):
    return max(low, min(high, value))


def ease(value):
    value = clamp(value)
    return value*value*(3-2*value)


@lru_cache(maxsize=None)
def font(name, size):
    names={'display':'BarlowCondensed-ExtraBold.ttf', 'bold':'Barlow-Bold.ttf',
           'body':'Barlow-SemiBold.ttf'}
    return ImageFont.truetype(str(FONT_DIR/names[name]), size=round(size*SCALE))


def fitted_font(draw, text, name, size, max_width):
    while size>16 and draw.textlength(text,font=font(name,size))>max_width:
        size-=1
    return font(name,size)


def centered(draw, xy, text, size=30, color=WHITE, name='bold', max_width=620):
    face=fitted_font(draw,text,name,size,max_width)
    x,y=xy
    draw.text((x+1,y+3),text,font=face,fill=(5,13,18,210),anchor='mt',
              stroke_width=2,stroke_fill=(5,13,18,210))
    draw.text((x,y),text,font=face,fill=(*color,255),anchor='mt')


def label(draw, x, y, text, color=WHITE, secondary=None):
    centered(draw,(x,y),text,34,color,'display',250)
    if secondary:
        centered(draw,(x,y+42),secondary,21,MUTED,'body',260)


@lru_cache(maxsize=8)
def background(kind):
    palettes={
        'city': ((19,27,45),(55,73,84)),
        'studio': ((26,37,43),(78,92,92)),
        'parts': ((25,38,42),(76,94,89)),
        'fluid': ((16,37,50),(44,76,87)),
        'idle': ((28,35,41),(76,79,77)),
        'stator': ((24,42,42),(71,92,83)),
        'clutch': ((31,35,43),(82,83,84)),
    }
    top,bottom=palettes[kind]
    yy=np.linspace(0,1,OUTPUT_HEIGHT,dtype=np.float32)[:,None]
    xx=np.linspace(-1,1,OUTPUT_WIDTH,dtype=np.float32)[None,:]
    vignette=np.clip(1-0.14*xx*xx,0.8,1)
    data=np.empty((OUTPUT_HEIGHT,OUTPUT_WIDTH,3),dtype=np.uint8)
    for ch in range(3):
        data[:,:,ch]=np.clip((top[ch]*(1-yy)+bottom[ch]*yy)*vignette,0,255)
    result=Image.fromarray(data,'RGB')
    draw=canvas(result)
    if kind!='city':
        draw.polygon(((0,952),(720,952),(720,1280),(0,1280)),fill=(19,28,31,115))
        draw.line((0,952,720,952),fill=(214,225,217,40),width=2)
    return result


def city(image, time, moving):
    draw=canvas(image)
    shift=time*28 if moving else 0
    for n in range(-2,10):
        x=n*105-(shift%105)
        h=115+(n*37)%130
        draw.rectangle((x,760-h,x+87,760),fill=(24,36,51,230))
        for row in range(2,6):
            for col in range(1,3):
                if (n+row+col)%4==0:
                    draw.rectangle((x+col*23,760-h+row*19,x+col*23+5,760-h+row*19+9),
                                   fill=(233,208,155,110))
    draw.rectangle((0,760,720,854),fill=(41,52,58,255))
    draw.rectangle((0,854,720,1280),fill=(30,38,44,255))
    draw.line((0,854,720,854),fill=(190,204,199,135),width=4)
    for n in range(-1,8):
        x=n*132-(time*112%132 if moving else 0)
        draw.line((x,910,x+55,910),fill=(205,213,200,160),width=5)


def car(image, x, y, width, wheel_angle, braking):
    draw=canvas(image)
    s=width/500
    def xy(a,b): return (x+a*s,y+b*s)
    def rr(a): return a*s
    draw.ellipse((*xy(22,167),*xy(488,204)),fill=(3,11,17,110))
    body=[xy(8,116),xy(19,88),xy(75,73),xy(114,32),xy(157,14),xy(292,14),
          xy(345,32),xy(392,73),xy(458,86),xy(489,109),xy(488,150),
          xy(467,165),xy(33,165),xy(12,151)]
    draw.polygon(body,fill=(91,139,150,255),outline=(205,224,218,255),width=max(3,int(rr(4))))
    draw.polygon([xy(20,90),xy(76,74),xy(391,74),xy(457,87),xy(480,104),xy(24,104)],
                 fill=(153,190,188,255))
    draw.polygon([xy(20,124),xy(483,124),xy(482,147),xy(459,151),xy(39,151),xy(20,145)],
                 fill=(64,105,116,255))
    draw.polygon([xy(87,72),xy(124,39),xy(159,26),xy(224,26),xy(224,72)],
                 fill=(24,49,58,255),outline=(206,226,219,255),width=max(2,int(rr(2))))
    draw.polygon([xy(238,26),xy(289,26),xy(335,41),xy(367,72),xy(238,72)],
                 fill=(26,52,62,255),outline=(206,226,219,255),width=max(2,int(rr(2))))
    draw.line([xy(102,65),xy(134,40),xy(191,30)],fill=(171,208,207,150),width=max(2,int(rr(3))))
    draw.line([xy(232,79),xy(232,145)],fill=(48,81,90,255),width=max(2,int(rr(3))))
    draw.line([xy(150,95),xy(173,95)],fill=(239,246,235,255),width=max(2,int(rr(4))))
    draw.line([xy(260,95),xy(283,95)],fill=(239,246,235,255),width=max(2,int(rr(4))))
    draw.rounded_rectangle((*xy(465,104),*xy(487,118)),radius=max(1,int(rr(4))),fill=(255,222,154,255))
    taillight=(255,65,51,255) if braking else (155,63,55,255)
    draw.rounded_rectangle((*xy(10,104),*xy(31,118)),radius=max(1,int(rr(4))),fill=taillight)
    for wx in (105,389):
        cx,cy=xy(wx,155)
        draw.ellipse((cx-rr(43),cy-rr(43),cx+rr(43),cy+rr(43)),fill=(10,20,24,255),
                     outline=(196,213,206,255),width=max(2,int(rr(4))))
        draw.ellipse((cx-rr(28),cy-rr(28),cx+rr(28),cy+rr(28)),fill=(165,180,176,255))
        draw.ellipse((cx-rr(8),cy-rr(8),cx+rr(8),cy+rr(8)),fill=(49,70,75,255))
        for k in range(5):
            angle=wheel_angle+k*math.tau/5
            draw.line(((cx+rr(10)*math.cos(angle),cy+rr(10)*math.sin(angle)),
                       (cx+rr(24)*math.cos(angle),cy+rr(24)*math.sin(angle))),
                      fill=(63,82,85,255),width=max(2,int(rr(4))))


def mesh(image, obj, x, y, size, spin=0, yaw=0.65, pitch=-0.16):
    geometry.render(image,obj,x,y,size,spin=spin,yaw=yaw,pitch=pitch,scale=SCALE)


@lru_cache(maxsize=1)
def shell_master():
    result=Image.new('RGBA',(960,960),(0,0,0,0))
    mesh(result,geometry.converter(),320,320,260,yaw=0.68)
    return result


@lru_cache(maxsize=96)
def shell_size(size):
    return shell_master().resize((size,size),Image.Resampling.LANCZOS)


def shell(image,x,y,radius):
    size=max(8,round(960*radius/260/4)*4)
    sprite=shell_size(size)
    image.paste(sprite,(round(x*SCALE-size/2),round(y*SCALE-size/2)),sprite)


def shadow(draw,x,y,width=190):
    draw.ellipse((x-width,y-20,x+width,y+20),fill=(2,9,12,100))


def bezier(a,b,c,d,count=48):
    result=[]
    for n in range(count):
        t=n/(count-1);u=1-t
        result.append((u**3*a[0]+3*u*u*t*b[0]+3*u*t*t*c[0]+t**3*d[0],
                       u**3*a[1]+3*u*u*t*b[1]+3*u*t*t*c[1]+t**3*d[1]))
    return result


def fluid(draw,points,time,color=BLUE,speed=0.20):
    draw.line(points,fill=(*color,135),width=14,joint='curve')
    start=int(((time*speed)%1)*(len(points)-1))
    length=12
    segment=[points[(start+i)%(len(points)-1)] for i in range(length)]
    # A discontinuous wrap is split rather than drawn across the diagram.
    if start+length<len(points):
        draw.line(segment,fill=(204,242,244,240),width=7,joint='curve')
    else:
        first=points[start:]
        second=points[:(start+length)%(len(points)-1)]
        if len(first)>1: draw.line(first,fill=(204,242,244,240),width=7,joint='curve')
        if len(second)>1: draw.line(second,fill=(204,242,244,240),width=7,joint='curve')
    ex,ey=points[-1]; px,py=points[-2]
    angle=math.atan2(ey-py,ex-px)
    p1=(ex-19*math.cos(angle-0.5),ey-19*math.sin(angle-0.5))
    p2=(ex-19*math.cos(angle+0.5),ey-19*math.sin(angle+0.5))
    draw.polygon(((ex,ey),p1,p2),fill=(*color,255))


@lru_cache(maxsize=64)
def cue_start(scene: TimedScene, needle: str, default: float):
    for start,_,phrase in caption_cues(scene):
        if needle.casefold() in phrase.casefold():
            return start-scene.start
    return default


def scene_style(scene,time):
    visual=scene.scene.visual
    if visual=='intro':
        return 'city' if time<cue_start(scene,'Rahasianya',scene.duration*0.55) else 'studio'
    if visual=='outro':
        return 'city' if time>=cue_start(scene,'yang bikin mobil matik',scene.duration*0.55) else 'studio'
    return {'connection':'studio','parts':'parts','flow':'fluid','idle':'idle',
            'stator':'stator','lockup':'clutch'}[visual]


def visual_intro(image,time,scene):
    draw=canvas(image)
    reveal=cue_start(scene,'Rahasianya',scene.duration*0.55)
    if time<reveal:
        start=cue_start(scene,'bisa berhenti',1)
        gas=cue_start(scene,'Tapi, begitu gas diinjak,',scene.duration*0.28)
        braking=start<=time<gas
        moving=time<start or time>=gas
        city(image,time,moving)
        advance=100*ease((time-gas)/2) if time>=gas else -45*(1-ease(time/max(start,0.4)))
        wheel=time*2 if moving else start*2
        car(image,72+advance,615,570,wheel,braking)
    else:
        appear=ease((time-reveal)/0.55)
        shadow(draw,360,927,205)
        shell(image,360,602,220*(0.86+0.14*appear))
        label(draw,360,905,'TORQUE CONVERTER',YELLOW)


def visual_connection(image,time,scene):
    draw=canvas(image)
    focus=ease((time-cue_start(scene,'Uniknya, tenaga dikirim',scene.duration*0.5))/0.7)
    if focus<0.96:
        shift=280*focus
        left=115-shift;right=605+shift
        draw.line((left+62,635,right-62,635),fill=(146,170,169,220),width=16)
        draw.line((left+62,630,right-62,630),fill=(219,228,218,180),width=3)
        if left>-130:
            mesh(image,geometry.engine(),left,610,104,yaw=0.42,pitch=-0.28)
            label(draw,left,810,'MESIN')
        if right<850:
            mesh(image,geometry.transmission(),right,610,102,yaw=0.50,pitch=-0.25)
            label(draw,right,810,'TRANSMISI')
        shell(image,360,610,144+50*focus)
        label(draw,360,847,'TORCON',YELLOW)
    else:
        upper=bezier((168,492),(200,345),(520,345),(552,492))
        lower=bezier((552,742),(520,875),(200,875),(168,742))
        fluid(draw,upper,time,BLUE)
        fluid(draw,lower,time+0.6,BLUE,0.16)
        mesh(image,geometry.rotor('impeller'),195,614,133,spin=time*0.9)
        mesh(image,geometry.rotor('turbine'),525,614,133,spin=time*0.65)
        label(draw,195,840,'IMPELER',ORANGE)
        label(draw,525,840,'TURBIN',BLUE)
        centered(draw,(360,938),'ALIRAN OLI',27,WHITE,'bold')


def visual_parts(image,time,scene):
    draw=canvas(image)
    keys=[('impeller','Impeler berputar','IMPELER',ORANGE,'DIPUTAR MESIN'),
          ('turbine','turbin tersambung','TURBIN',BLUE,'KE TRANSMISI'),
          ('stator','stator mengatur','STATOR',GREEN,'MENGARAHKAN OLI')]
    starts=[cue_start(scene,k[1],1+n*2) for n,k in enumerate(keys)]
    if time<starts[0]-0.28:
        shadow(draw,360,932,200)
        shell(image,360,602,215)
        return
    active=max(0,min(2,sum(time>=t for t in starts)-1))
    transition=ease((time-starts[active])/0.38)
    if transition<1:
        old_x=360-540*transition
        if old_x>-260:
            if active==0:
                shell(image,old_x,590,215)
            else:
                old=keys[active-1]
                mesh(image,geometry.rotor(old[0]),old_x,590,225,spin=time*0.65)
    name,_,text,color,role=keys[active]
    new_x=360+540*(1-transition)
    mesh(image,geometry.rotor(name),new_x,590,225,spin=time*(0 if name=='stator' else 0.65))
    if transition>0.55:
        label(draw,360,916,text,color,role)


def visual_flow(image,time,scene):
    draw=canvas(image)
    upper=bezier((159,500),(190,350),(530,350),(561,500))
    lower=bezier((561,714),(530,870),(190,870),(159,714))
    fluid(draw,upper,time,BLUE,0.17)
    fluid(draw,lower,time+0.8,BLUE,0.14)
    mesh(image,geometry.rotor('impeller'),191,610,143,spin=time*1.05)
    mesh(image,geometry.rotor('turbine'),529,610,143,spin=time*0.78)
    label(draw,191,858,'IMPELER',ORANGE)
    label(draw,529,858,'TURBIN',BLUE)
    centered(draw,(360,946),'ALIRAN OLI',23,WHITE,'bold')


def visual_idle(image,time,scene):
    draw=canvas(image)
    mesh(image,geometry.rotor('impeller'),191,590,145,spin=time*1.05)
    mesh(image,geometry.rotor('turbine'),529,590,145,spin=0.25)
    label(draw,191,838,'IMPELER',ORANGE,'BERPUTAR')
    label(draw,529,838,'TURBIN',BLUE,'DIAM')
    draw.rounded_rectangle((246,954,474,1005),radius=10,fill=(*RED,255))
    centered(draw,(360,965),'REM DIINJAK',22,WHITE,'bold')


def visual_stator(image,time,scene):
    draw=canvas(image)
    boost=ease((time-cue_start(scene,'sehingga tarikan awal',scene.duration*0.7)+0.2)/0.65)
    y=598-125*boost
    radius=210-55*boost
    top=bezier((126,y-25),(160,y-290),(560,y-290),(594,y-25))
    bottom=bezier((594,y+25),(560,y+290),(160,y+290),(126,y+25))
    fluid(draw,top,time,ORANGE,0.17)
    fluid(draw,bottom,time+0.4,BLUE,0.15)
    mesh(image,geometry.rotor('stator'),360,y,radius,spin=0.20)
    if boost<0.5:
        label(draw,360,907,'STATOR',GREEN,'MENGARAHKAN OLI')
    else:
        draw.line((58,980,662,890),fill=(203,211,197,180),width=5)
        car(image,176,768,380,time*2,False)
        centered(draw,(360,1005),'TARIKAN AWAL LEBIH KUAT',26,WHITE,'bold')


def visual_lockup(image,time,scene):
    draw=canvas(image)
    start=cue_start(scene,'kopling pengunci',scene.duration*0.3)
    close=ease((time-start+0.25)/1.2)
    left=190+75*close;right=530-75*close
    impeller_spin=time*0.85
    turbine_spin=time*(0.55+0.30*close)
    mesh(image,geometry.rotor('impeller'),left,604,150,spin=impeller_spin)
    mesh(image,geometry.rotor('turbine'),right,604,150,spin=turbine_spin)
    if close>0.03:
        size=76+18*close
        mesh(image,geometry.clutch(),360,604,size,spin=impeller_spin)
        label(draw,360,864,'KOPLING PENGUNCI',YELLOW)
    if close>0.9:
        centered(draw,(360,952),'SELIP BERKURANG',25,WHITE,'bold')


def visual_outro(image,time,scene):
    draw=canvas(image)
    move=cue_start(scene,'yang bikin mobil matik',scene.duration*0.55)
    if time<move:
        shadow(draw,360,927,205)
        shell(image,360,602,220)
        label(draw,360,905,'TORQUE CONVERTER',YELLOW)
    else:
        city(image,time,True)
        x=45+120*ease((time-move)/3)
        car(image,x,615,570,time*2,False)


VISUALS={'intro':visual_intro,'connection':visual_connection,'parts':visual_parts,
         'flow':visual_flow,'idle':visual_idle,'stator':visual_stator,
         'lockup':visual_lockup,'outro':visual_outro}


def scene_image(scene: TimedScene,time: float):
    image=background(scene_style(scene,time)).copy()
    VISUALS[scene.scene.visual](image,time,scene)
    return image


@lru_cache(maxsize=32)
def cached_cues(scene: TimedScene):
    return caption_cues(scene)


def caption(image: Image.Image,scene: TimedScene,absolute_time: float):
    current=None
    for start,end,text in cached_cues(scene):
        if start<=absolute_time<end:
            current=(start,end,text)
            break
    if not current:
        return
    start,end,phrase=current
    draw=canvas(image)
    face=fitted_font(draw,phrase,'body',42,620)
    width=draw.textlength(phrase,font=face)
    left=(WIDTH-width)/2
    words=phrase.split(' ')
    weights=[max(1,len(word.strip(',.!?'))) for word in words]
    position=clamp((absolute_time-start)/max(0.01,end-start))*sum(weights)
    active=len(words)-1;total=0
    for i,weight in enumerate(weights):
        total+=weight
        if position<=total:
            active=i
            break
    space=draw.textlength(' ',font=face)
    for i,word in enumerate(words):
        color=WHITE if i==active else (184,196,195)
        draw.text((left,129),word,font=face,fill=(*color,255),stroke_width=2,
                  stroke_fill=(9,18,23,230))
        left+=draw.textlength(word,font=face)+space
