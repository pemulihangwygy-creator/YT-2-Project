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
    vignette=np.clip(1-.20*xx*xx,0.74,1)
    # Broad studio illumination, without decorative particles or overlays.
    key=np.exp(-((xx+.25)/.70)**2-((yy-.38)/.36)**2)*12
    fill=np.exp(-((xx-.60)/.85)**2-((yy-.60)/.48)**2)*5
    data=np.empty((OUTPUT_HEIGHT,OUTPUT_WIDTH,3),dtype=np.uint8)
    for ch in range(3):
        light=key*(.85 if ch==2 else 1)+fill*(1.15 if ch==2 else 1)
        data[:,:,ch]=np.clip((top[ch]*(1-yy)+bottom[ch]*yy)*vignette+light,0,255)
    result=Image.fromarray(data,'RGB')
    draw=canvas(result)
    if kind!='city':
        draw.polygon(((0,1048),(720,1048),(720,1280),(0,1280)),fill=(19,28,31,75))
    return result


def city(image, time):
    draw=canvas(image)
    shift=time*28
    for n in range(-2,10):
        x=n*105-(shift%105)
        h=115+(n*37)%130
        draw.rectangle((x,760-h,x+69,760),fill=(23,36,50,235))
        draw.polygon(((x+69,760-h),(x+87,760-h-12),(x+87,748),(x+69,760)),
                     fill=(30,46,59,240))
        draw.polygon(((x,760-h),(x+69,760-h),(x+87,760-h-12),(x+18,760-h-12)),
                     fill=(35,51,63,240))
        for row in range(2,6):
            for col in range(1,3):
                if (n+row+col)%4==0:
                    draw.rectangle((x+col*23,760-h+row*19,x+col*23+5,760-h+row*19+9),
                                   fill=(233,208,155,110))
    draw.rectangle((0,760,720,854),fill=(41,52,58,255))
    draw.rectangle((0,854,720,1280),fill=(30,38,44,255))
    draw.line((0,854,720,854),fill=(190,204,199,135),width=4)
    for n in range(-1,8):
        x=n*132-(time*112%132)
        draw.line((x,910,x+55,910),fill=(205,213,200,160),width=5)


def car(image, x, y, width, wheel_angle, braking):
    # The wheel spins independently; its ground shadow anchors the 3D car.
    draw=canvas(image)
    center_x=x+width/2
    ground=y+width*.42
    for spread in range(6,0,-1):
        draw.ellipse((center_x-width*.46-spread*2,ground-9-spread,
                      center_x+width*.46+spread*2,ground+9+spread),
                     fill=(2,8,12,12))
    geometry.render_car(image,center_x,y+width*.35,width*.46,
                        spin=-wheel_angle,braking=braking,yaw=-.46,pitch=.18,scale=SCALE)


def mesh(image, obj, x, y, size, spin=0, yaw=0.65, pitch=0.12):
    geometry.render(image,obj,x,y,size,spin=spin,yaw=yaw,pitch=pitch,scale=SCALE)


def shell(image,x,y,radius,time=0):
    # A slow camera move reveals the depth of the stamped housing.
    mesh(image,geometry.converter(),x,y,radius,spin=.12*time,
         yaw=.57+.10*math.sin(time*.45),pitch=.10+.04*math.sin(time*.31))


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
    # Continuous ribbons represent oil flow rather than decorative particles.
    deep=tuple(int(c*.42) for c in color)
    draw.line(points,fill=(*deep,230),width=22,joint='curve')
    draw.line(points,fill=(*color,220),width=14,joint='curve')
    draw.line(points,fill=(170,227,235,120),width=3,joint='curve')
    span=len(points)-1
    start=((time*speed)%1)*span
    length=min(10.,span*.23)
    def point_at(position):
        index=min(span-1,int(position))
        fraction=position-index
        a,b=points[index],points[index+1]
        return (a[0]+(b[0]-a[0])*fraction,a[1]+(b[1]-a[1])*fraction)
    def ribbon(first,last):
        between=points[math.floor(first)+1:math.ceil(last)]
        segment=[point_at(first),*between,point_at(last)]
        if len(segment)>1:
            draw.line(segment,fill=(204,242,244,240),width=7,joint='curve')
    if start+length<=span:
        ribbon(start,start+length)
    else:
        ribbon(start,float(span))
        ribbon(0.,start+length-span)
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
        travel=min(time,start)+max(0,time-gas)
        city(image,travel)
        advance=100*ease((time-gas)/2) if time>=gas else -45*(1-ease(time/max(start,0.4)))
        wheel=travel*2
        car(image,72+advance,615,570,wheel,braking)
    else:
        appear=ease((time-reveal)/0.55)
        shadow(draw,360,865,205)
        shell(image,360,602,220*(0.86+0.14*appear),time)
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
        shell(image,360,610,144+50*focus,time)
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
    spread=ease((time-cue_start(scene,'tiga pemain utama.',1))/0.9)

    def assembly(offset=0):
        # An exploded axial view shows the three parts inside the housing.
        shell(image,360-235*spread+offset,590,215-108*spread,time)
        if spread>.025:
            camera=.70
            mesh(image,geometry.rotor('impeller'),360-83*spread+offset,590,
                 110*spread,spin=time*.65,yaw=camera,pitch=.10)
            mesh(image,geometry.rotor('stator'),360+34*spread+offset,590,
                 78*spread,spin=.2,yaw=camera,pitch=.10)
            mesh(image,geometry.rotor('turbine'),360+169*spread+offset,590,
                 110*spread,spin=time*.5,yaw=camera,pitch=.10)

    if time<starts[0]:
        assembly()
        return
    active=max(0,min(2,sum(time>=t for t in starts)-1))
    transition=ease((time-starts[active])/.45)
    if transition<1:
        old_x=360-540*transition
        if active==0:
            assembly(-540*transition)
        elif old_x>-260:
            old=keys[active-1]
            mesh(image,geometry.rotor(old[0]),old_x,590,225,spin=time*.65,
                 yaw=.58+.18*math.sin(time*.40),pitch=.10+.04*math.sin(time*.25))
    name,_,text,color,role=keys[active]
    new_x=360+540*(1-transition)
    mesh(image,geometry.rotor(name),new_x,590,225,spin=time*(0 if name=='stator' else .65),
         yaw=.58+.18*math.sin(time*.40),pitch=.10+.04*math.sin(time*.25))
    if transition>.55:
        label(draw,360,916,text,color,role)


def ramp_rotation(time,start,duration,rate):
    elapsed=max(0.,time-start)
    if elapsed>=duration:
        return rate*(elapsed-duration/2)
    t=elapsed/duration
    return rate*duration*(t**3-.5*t**4)


def visual_flow(image,time,scene):
    draw=canvas(image)
    upper=bezier((159,500),(190,350),(530,350),(561,500))
    lower=bezier((561,714),(530,870),(190,870),(159,714))
    fluid(draw,upper,time,BLUE,0.17)
    fluid(draw,lower,time+0.8,BLUE,0.14)
    mesh(image,geometry.rotor('impeller'),191,610,143,spin=time*1.05)
    spin=ramp_rotation(time,cue_start(scene,'Dorongan oli membuat',scene.duration*.35),1.1,.78)
    mesh(image,geometry.rotor('turbine'),529,610,143,spin=spin)
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
    mesh(image,geometry.rotor('stator'),360,y,radius,spin=.20,
         yaw=.59+.12*math.sin(time*.40),pitch=.12)
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
    turbine_spin=time*.55+ramp_rotation(time,start-.25,1.2,.30)
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
        shadow(draw,360,865,205)
        shell(image,360,602,220,time)
        label(draw,360,905,'TORQUE CONVERTER',YELLOW)
    else:
        city(image,time)
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
