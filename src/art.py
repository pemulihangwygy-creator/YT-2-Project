from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import aggdraw
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import vector
from .audio import TimedScene, caption_cues

WIDTH, HEIGHT = 720, 1280
SCALE = 1.5
OUTPUT_WIDTH, OUTPUT_HEIGHT = 1080, 1920
ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / 'assets' / 'fonts'
INK = (20, 48, 62)
WHITE = (250, 250, 230)
MUTED = (212, 228, 218)
YELLOW = (255, 205, 106)
ORANGE = (255, 176, 77)
BLUE = (109, 221, 234)
GREEN = (161, 234, 166)
RED = (245, 111, 87)


class DesignDraw:
    def __init__(self, image: Image.Image):
        self.image = image
        self.draw = ImageDraw.Draw(image, 'RGBA')

    @staticmethod
    def points(points):
        if len(points) and isinstance(points[0], (tuple, list)):
            return [(x*SCALE, y*SCALE) for x,y in points]
        return tuple(value*SCALE for value in points)

    def ellipse(self, xy, fill=None, outline=None, width=1):
        self.draw.ellipse(self.points(xy), fill=fill, outline=outline,
                          width=max(1,round(width*SCALE)))

    def rectangle(self, xy, fill=None, outline=None, width=1):
        self.draw.rectangle(self.points(xy), fill=fill, outline=outline,
                            width=max(1,round(width*SCALE)))

    def polygon(self, xy, fill=None, outline=None, width=1):
        self.draw.polygon(self.points(xy), fill=fill, outline=outline,
                          width=max(1,round(width*SCALE)))

    def line(self, xy, fill=None, width=1, joint='curve'):
        self.draw.line(self.points(xy), fill=fill, width=max(1,round(width*SCALE)), joint=joint)

    def rounded_rectangle(self, xy, radius=0, fill=None, outline=None, width=1):
        self.draw.rounded_rectangle(self.points(xy), radius=round(radius*SCALE), fill=fill,
                                    outline=outline, width=max(1,round(width*SCALE)))

    def text(self, xy, text, font, fill, anchor=None, stroke_width=0, stroke_fill=None):
        self.draw.text(self.points(xy), text, font=font, fill=fill, anchor=anchor,
                       stroke_width=round(stroke_width*SCALE), stroke_fill=stroke_fill)

    def textlength(self, text, font):
        return self.draw.textlength(text,font=font)/SCALE


def canvas(image):
    return DesignDraw(image)


def clamp(value, low=0, high=1):
    return max(low, min(high, value))


def ease(value):
    value=clamp(value)
    return value*value*(3-2*value)


@lru_cache(maxsize=None)
def font(name, size):
    names={'display':'BarlowCondensed-ExtraBold.ttf', 'bold':'Barlow-Bold.ttf',
           'body':'Barlow-SemiBold.ttf'}
    return ImageFont.truetype(str(FONT_DIR/names[name]), size=round(size*SCALE))


def fitted_font(draw,text,name,size,max_width):
    while size>16 and draw.textlength(text,font(name,size))>max_width:
        size-=1
    return font(name,size)


def centered(draw,xy,text,size=30,color=WHITE,name='bold',max_width=630):
    face=fitted_font(draw,text,name,size,max_width)
    x,y=xy
    draw.text((x+1,y+2),text,face,(12,31,38,165),anchor='mt',
              stroke_width=2,stroke_fill=(12,31,38,165))
    draw.text((x,y),text,face,(*color,255),anchor='mt')


@lru_cache(maxsize=128)
def _label_image(text,color,secondary,width):
    bitmap=Image.new('RGBA',(round((width+50)*SCALE),round(110*SCALE)),(0,0,0,0))
    draw=canvas(bitmap)
    x=(width+50)/2
    face=fitted_font(draw,text,'display',34,width-20)
    text_width=draw.textlength(text,face)
    box_width=min(width,max(105,text_width+34))
    draw.rounded_rectangle((x-box_width/2,0,x+box_width/2,43),radius=7,
                           fill=(*color,255))
    draw.text((x,3),text,face,(*INK,255),anchor='mt')
    if secondary:
        centered(draw,(x,55),secondary,22,WHITE,'bold',width+25)
    return bitmap


def label(draw,x,y,text,color=WHITE,secondary=None,width=270):
    bitmap=_label_image(text,color,secondary,width)
    draw.image.paste(bitmap,(round((x-(width+50)/2)*SCALE),round(y*SCALE)),bitmap)


@lru_cache(maxsize=10)
def background(kind):
    palettes={
        'city': ((34,33,68),(98,80,111)),
        'workshop': ((33,48,67),(96,113,110)),
        'parts': ((38,67,72),(92,142,126)),
        'fluid': ((23,54,76),(39,132,145)),
        'idle': ((55,44,67),(152,103,97)),
        'stator': ((33,79,75),(97,166,135)),
        'clutch': ((47,45,79),(120,97,121)),
    }
    top,bottom=palettes[kind]
    yy=np.linspace(0,1,OUTPUT_HEIGHT,dtype=np.float32)[:,None]
    xx=np.linspace(-1,1,OUTPUT_WIDTH,dtype=np.float32)[None,:]
    vignette=np.clip(1-.12*xx*xx, .82, 1)
    focus=np.exp(-((xx+.05)/.8)**2-((yy-.43)/.38)**2)*8
    data=np.empty((OUTPUT_HEIGHT,OUTPUT_WIDTH,3),dtype=np.uint8)
    for ch in range(3):
        data[:,:,ch]=np.clip((top[ch]*(1-yy)+bottom[ch]*yy)*vignette+focus,0,255)
    image=Image.fromarray(data,'RGB')
    d=canvas(image)
    if kind not in ('city','idle'):
        # Wall panels and a floor situate the diagrams in a simple 2D workshop.
        d.rectangle((0,250,65,1015),fill=(15,41,50,32))
        d.rectangle((655,250,720,1015),fill=(15,41,50,32))
        d.line((65,250,65,1015),fill=(218,238,213,35),width=3)
        d.line((655,250,655,1015),fill=(218,238,213,35),width=3)
        d.rectangle((0,1030,720,1280),fill=(14,41,49,55))
        d.line((0,1030,720,1030),fill=(227,236,204,38),width=3)
    return image


@lru_cache(maxsize=96)
def resized_asset(name,width,height):
    sources={'housing':vector.housing,'car':vector.car_body,'wheel':vector.car_wheel,
             'engine':vector.engine,'gearbox':vector.gearbox,'lock':vector.lock,
             'impeller':lambda:vector.rotor('impeller'),
             'turbine':lambda:vector.rotor('turbine'),
             'stator':lambda:vector.rotor('stator')}
    return sources[name]().resize((width,height),Image.Resampling.LANCZOS)


def sprite(image,name,x,y,width,height=None,angle=0):
    if height is None:
        height=width
    w=max(1,round(width*SCALE)); h=max(1,round(height*SCALE))
    source=resized_asset(name,w,h)
    if angle:
        source=source.rotate(-math.degrees(angle),Image.Resampling.BILINEAR,expand=False)
    image.paste(source,(round(x*SCALE-w/2),round(y*SCALE-h/2)),source)


def wheel(image,name,x,y,radius,spin=0):
    sprite(image,name,x,y,2*radius,angle=spin)


@lru_cache(maxsize=16)
def _half_mask(size):
    mask=Image.new('L',(size,size),0)
    ImageDraw.Draw(mask).rectangle((0,0,size//2,size),fill=255)
    return mask


def cutaway(image,x,y,radius,time):
    # A flat split-view diagram; the colored halves turn independently.
    size=round(radius*2*SCALE)
    pump=resized_asset('impeller',size,size).rotate(-math.degrees(time*.85),Image.Resampling.BILINEAR)
    turbine=resized_asset('turbine',size,size).rotate(-math.degrees(time*.60),Image.Resampling.BILINEAR)
    pair=Image.composite(pump,turbine,_half_mask(size))
    image.paste(pair,(round(x*SCALE-size/2),round(y*SCALE-size/2)),pair)
    wheel(image,'stator',x,y,radius*.25)


def city(image,travel):
    d=canvas(image)
    # Flat building silhouettes, curb and road give the moving car context.
    d.rectangle((0,733,720,876),fill=(41,57,73,255))
    for n in range(-2,9):
        x=n*118-(travel*22%118)
        h=100+(n*43)%155
        d.rectangle((x,760-h,x+88,760),fill=(37,53,71,255))
        d.rectangle((x+7,767-h,x+81,760),fill=(43,65,80,255))
        for row in range(2,5):
            for col in range(2):
                if (n+row+col)%3==0:
                    d.rectangle((x+19+col*31,760-h+row*23,x+25+col*31,760-h+row*23+10),
                                fill=(255,219,145,120))
    d.rectangle((0,860,720,1280),fill=(28,47,56,255))
    d.line((0,859,720,859),fill=(200,212,201,180),width=5)
    for n in range(-1,9):
        x=n*126-(travel*105%126)
        d.rounded_rectangle((x,963,x+60,970),radius=3,fill=(213,225,212,170))


def car(image,x,y,width,spin):
    factor=width/620
    sprite(image,'car',x+width/2,y+130*factor,width,260*factor)
    for cx in (150,490):
        sprite(image,'wheel',x+cx*factor,y+205*factor,110*factor,angle=spin)


def signal(draw,x,y,green=False):
    draw.rounded_rectangle((x-32,y-10,x+32,y+158),radius=17,fill=(*INK,255))
    for i,c in enumerate(((241,102,81),(255,205,106),(126,221,164))):
        active=(i==2 if green else i==0)
        fill=(*c,255 if active else 60)
        draw.ellipse((x-19,y+4+i*48,x+19,y+42+i*48),fill=fill)
    draw.line((x,y+158,x,850),fill=(*INK,255),width=10)


def bezier(a,b,c,d,count=48):
    result=[]
    for n in range(count):
        t=n/(count-1);u=1-t
        result.append((u**3*a[0]+3*u*u*t*b[0]+3*u*t*t*c[0]+t**3*d[0],
                       u**3*a[1]+3*u*u*t*b[1]+3*u*t*t*c[1]+t**3*d[1]))
    return result


def fluid(image,points,time,color=BLUE,speed=.20):
    # Render only the curve's bounding region; it remains a continuous ribbon.
    pad=36
    left=max(0,math.floor((min(x for x,_ in points)-pad)*SCALE))
    top=max(0,math.floor((min(y for _,y in points)-pad)*SCALE))
    right=min(image.width,math.ceil((max(x for x,_ in points)+pad)*SCALE))
    bottom=min(image.height,math.ceil((max(y for _,y in points)+pad)*SCALE))
    if left>=right or top>=bottom:
        return
    crop=image.crop((left,top,right,bottom))
    context=aggdraw.Draw(crop)
    def curve(path_points,tint,width):
        path=aggdraw.Path()
        path.moveto(path_points[0][0]*SCALE-left,path_points[0][1]*SCALE-top)
        for x,y in path_points[1:]:
            path.lineto(x*SCALE-left,y*SCALE-top)
        context.path(path,None,aggdraw.Pen(tint,width*SCALE))
    curve(points,INK,25)
    curve(points,color,17)
    curve(points,(224,255,245),3)
    span=len(points)-1
    start=(time*speed%1)*span
    length=min(10.,span*.23)
    def point_at(position):
        i=min(span-1,int(position));f=position-i
        a,b=points[i],points[i+1]
        return (a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f)
    def highlight(first,last):
        middle=points[math.floor(first)+1:math.ceil(last)]
        curve([point_at(first),*middle,point_at(last)],(244,255,238),7)
    if start+length<=span:
        highlight(start,start+length)
    else:
        highlight(start,float(span))
        highlight(0.,start+length-span)
    context.flush()
    image.paste(crop,(left,top))
    ex,ey=points[-1];px,py=points[-2]
    angle=math.atan2(ey-py,ex-px)
    d=canvas(image)
    d.polygon(((ex+4*math.cos(angle),ey+4*math.sin(angle)),
               (ex-29*math.cos(angle-.55),ey-29*math.sin(angle-.55)),
               (ex-29*math.cos(angle+.55),ey-29*math.sin(angle+.55))),
              fill=(*color,255),outline=(*INK,255),width=3)


def straight_arrow(draw,x0,y0,x1,y1,color=YELLOW,width=17):
    draw.line((x0,y0,x1,y1),fill=(*INK,255),width=width+8)
    draw.line((x0,y0,x1,y1),fill=(*color,255),width=width)
    a=math.atan2(y1-y0,x1-x0)
    draw.polygon(((x1+2*math.cos(a),y1+2*math.sin(a)),
                  (x1-31*math.cos(a-.54),y1-31*math.sin(a-.54)),
                  (x1-31*math.cos(a+.54),y1-31*math.sin(a+.54))),
                 fill=(*color,255),outline=(*INK,255),width=3)


@lru_cache(maxsize=64)
def cue_start(scene: TimedScene,needle: str,default: float):
    for start,_,phrase in caption_cues(scene):
        if needle.casefold() in phrase.casefold():
            return start-scene.start
    return default


def scene_style(scene,time):
    visual=scene.scene.visual
    if visual=='intro':
        return 'city' if time<cue_start(scene,'Rahasianya',scene.duration*.55) else 'workshop'
    if visual=='outro':
        return 'city' if time>=cue_start(scene,'yang bikin mobil matik',scene.duration*.55) else 'workshop'
    return {'connection':'workshop','parts':'parts','flow':'fluid','idle':'idle',
            'stator':'stator','lockup':'clutch'}[visual]


def visual_intro(image,time,scene):
    draw=canvas(image)
    reveal=cue_start(scene,'Rahasianya',scene.duration*.55)
    if time<reveal:
        stop=cue_start(scene,'bisa berhenti',1)
        gas=cue_start(scene,'Tapi, begitu gas diinjak,',scene.duration*.28)
        braking=stop<=time<gas
        travel=min(time,stop)+max(0,time-gas)*1.5
        city(image,travel)
        signal(draw,630,370,green=time>=gas)
        x=35-40*(1-ease(time/max(.5,stop)))+95*ease((time-gas)/2)
        car(image,x,665,610,travel*1.65)
        if braking:
            sprite(image,'engine',132,507,150,126)
            label(draw,132,590,'MESIN HIDUP',YELLOW,width=215)
    else:
        sprite(image,'housing',360,585,470,angle=.12*time)
        label(draw,360,880,'TORQUE CONVERTER',YELLOW,width=360)


def _flow_diagram(image,time,turbine_angle,center_y=600):
    # Two separated arrow paths show oil travelling outward and returning.
    top=bezier((195,center_y-126),(240,center_y-245),(462,center_y-245),(525,center_y-126))
    bottom=bezier((525,center_y+126),(468,center_y+245),(250,center_y+245),(195,center_y+126))
    wheel(image,'impeller',180,center_y,135,time*.92)
    wheel(image,'turbine',540,center_y,135,turbine_angle)
    fluid(image,top,time,BLUE,.18)
    fluid(image,bottom,time+.55,BLUE,.16)
    draw=canvas(image)
    label(draw,180,840,'IMPELER',YELLOW,width=240)
    label(draw,540,840,'TURBIN',BLUE,width=240)
    label(draw,360,925,'ALIRAN OLI',WHITE,width=210)


def visual_connection(image,time,scene):
    link=cue_start(scene,'adalah penghubung',scene.duration*.25)
    enter=ease((time-link+.1)/.8)
    focus=ease((time-cue_start(scene,'Uniknya, tenaga dikirim',scene.duration*.5))/.65)
    if focus<1:
        previous=image.copy(); d=canvas(previous)
        size=round((470-220*enter)/6)*6
        sprite(previous,'housing',360,595,size,angle=time*.15)
        if enter>.01:
            left=126-300*(1-enter); right=593+300*(1-enter)
            sprite(previous,'engine',left,595,205,172)
            sprite(previous,'gearbox',right,595,205,167)
            if enter>.8:
                straight_arrow(d,226,590,262,590,YELLOW,12)
                straight_arrow(d,460,590,496,590,BLUE,12)
                label(d,126,768,'MESIN',YELLOW,width=185)
                label(d,360,768,'TORCON',WHITE,width=185)
                label(d,593,768,'TRANSMISI',BLUE,width=210)
        if enter<.1:
            label(d,360,880,'TORQUE CONVERTER',YELLOW,width=360)
        if focus<=.02:
            image.paste(previous)
            return
    coming=image.copy()
    cutaway(coming,360,585,220,time)
    d=canvas(coming)
    label(d,360,875,'ALIRAN OLI',BLUE,'MEMINDAHKAN TENAGA',320)
    if focus>=1:
        image.paste(coming)
    else:
        image.paste(Image.blend(previous,coming,focus))


def visual_parts(image,time,scene):
    d=canvas(image)
    keys=[('impeller','Impeler berputar','IMPELER',YELLOW,'DIPUTAR MESIN'),
          ('turbine','turbin tersambung','TURBIN',BLUE,'KE TRANSMISI'),
          ('stator','stator mengatur','STATOR',GREEN,'MENGARAHKAN OLI')]
    starts=[cue_start(scene,k[1],1+n*2) for n,k in enumerate(keys)]
    reveal=cue_start(scene,'tiga pemain utama.',1.5)
    if time<reveal-.25:
        sprite(image,'housing',360,585,470,angle=time*.12)
        return
    spread=ease((time-reveal+.25)/.65)
    if time<starts[0]:
        if spread<1:
            cover=image.copy();parts=image.copy()
            sprite(cover,'housing',360,585,470,angle=time*.12)
            for i,(kind,_,name,color,_) in enumerate(keys):
                x=140+i*220
                wheel(parts,kind,x,590,95,time*.45 if kind!='stator' else 0)
                label(canvas(parts),x,760,name,color,width=200)
            image.paste(Image.blend(cover,parts,spread))
        else:
            for i,(kind,_,name,color,_) in enumerate(keys):
                x=140+i*220
                wheel(image,kind,x,590,95,time*.45 if kind!='stator' else 0)
                label(d,x,760,name,color,width=200)
        return
    active=max(0,min(2,sum(time>=start for start in starts)-1))
    slide=ease((time-starts[active])/.45)
    if slide<1:
        if active==0:
            for i,(kind,_,_,_,_) in enumerate(keys):
                wheel(image,kind,140+i*220-700*slide,590,95,
                      time*.45 if kind!='stator' else 0)
        else:
            previous=keys[active-1]
            wheel(image,previous[0],360-700*slide,585,220,
                  time*.65 if previous[0]!='stator' else .15)
    kind,_,name,color,role=keys[active]
    wheel(image,kind,360+700*(1-slide),585,220,
          time*.65 if kind!='stator' else .15)
    if slide>.6:
        label(d,360,875,name,color,role,width=300)


def ramp_rotation(time,start,duration,rate):
    elapsed=max(0,time-start)
    if elapsed<duration:
        return rate*elapsed*elapsed/(2*duration)
    return rate*(elapsed-duration/2)


def visual_flow(image,time,scene):
    turbine=ramp_rotation(time,cue_start(scene,'Dorongan oli membuat',scene.duration*.35),1.1,.78)
    _flow_diagram(image,time,turbine)
    onward=cue_start(scene,'lalu tenaga diteruskan',scene.duration*.7)
    if time>=onward:
        amount=ease((time-onward)/.45)
        d=canvas(image)
        sprite(image,'gearbox',220,1080+45*(1-amount),145,118)
        sprite(image,'wheel',500,1080+45*(1-amount),100,angle=turbine)
        if amount>.8:
            straight_arrow(d,320,1080,400,1080,BLUE,11)
            centered(d,(220,1155),'TRANSMISI',21,WHITE,'bold',195)
            centered(d,(500,1155),'RODA',21,WHITE,'bold',195)


def visual_idle(image,time,scene):
    draw=canvas(image)
    wheel(image,'impeller',180,575,135,time*1.05)
    wheel(image,'turbine',540,575,135)
    label(draw,180,782,'IMPELER',YELLOW,'BERPUTAR',245)
    label(draw,540,782,'TURBIN',BLUE,'DIAM',245)
    # A parked car and brake pedal make the operating condition explicit.
    draw.line((58,1035,402,1035),fill=(230,224,205,150),width=4)
    car(image,60,904,345,0)
    draw.line((550,949,550,887),fill=(*INK,255),width=14)
    draw.rounded_rectangle((490,935,610,988),radius=10,fill=(*RED,255),outline=(*INK,255),width=5)
    for x in (515,535,555,575,595):
        draw.line((x,946,x,976),fill=(255,221,186,190),width=3)
    centered(draw,(550,1010),'REM DIINJAK',26,WHITE,'bold',220)



def visual_stator(image,time,scene):
    draw=canvas(image)
    boost=ease((time-cue_start(scene,'sehingga tarikan awal',scene.duration*.7)+.2)/.65)
    y=575-115*boost
    radius=205-45*boost
    wheel(image,'stator',360,y,radius)
    incoming=bezier((55,y+165),(72,y+75),(125,y+28),(205,y+22))
    outgoing=bezier((505,y-22),(580,y-28),(635,y-75),(660,y-155))
    fluid(image,incoming,time,BLUE,.17)
    fluid(image,outgoing,time+.4,ORANGE,.15)
    if boost<.5:
        label(draw,360,865,'STATOR',GREEN,'MENGARAHKAN OLI',300)
    else:
        straight_arrow(draw,95,923,624,923,YELLOW,18)
        car(image,120,750,480,time*2)
        centered(draw,(360,1010),'TARIKAN AWAL LEBIH KUAT',28,WHITE,'bold')


def visual_lockup(image,time,scene):
    draw=canvas(image)
    start=cue_start(scene,'kopling pengunci',scene.duration*.3)
    close=ease((time-start+.25)/1.2)
    pump=time*.85
    turbine=time*.55+ramp_rotation(time,start-.25,1.2,.30)
    wheel(image,'impeller',190+105*close,590,154,pump)
    wheel(image,'turbine',530-105*close,590,154,turbine)
    if close>.06:
        sprite(image,'lock',360,590,112,122)
        label(draw,360,855,'KOPLING PENGUNCI',YELLOW,width=355)
    if close>.9:
        centered(draw,(360,945),'SELIP BERKURANG',28,WHITE,'bold')
        centered(draw,(145,1015),'MESIN',23,WHITE,'bold',170)
        straight_arrow(draw,255,1031,465,1031,BLUE,11)
        centered(draw,(575,1015),'TRANSMISI',23,WHITE,'bold',190)


def visual_outro(image,time,scene):
    draw=canvas(image)
    move=cue_start(scene,'yang bikin mobil matik',scene.duration*.55)
    if time<move:
        # A flat concentric diagram recaps the three parts working together.
        wheel(image,'impeller',360,585,220,time*.65)
        wheel(image,'turbine',360,585,142,time*.50)
        wheel(image,'stator',360,585,63)
        label(draw,360,885,'TORQUE CONVERTER',YELLOW,width=360)
    else:
        city(image,time-move)
        signal(draw,630,370,green=True)
        car(image,35+90*ease((time-move)/2),665,610,time*1.8)
        label(draw,360,425,'GERAK LEBIH HALUS',GREEN,width=360)


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


@lru_cache(maxsize=256)
def _caption_image(phrase,active):
    bitmap=Image.new('RGBA',(OUTPUT_WIDTH,round(100*SCALE)),(0,0,0,0))
    draw=canvas(bitmap)
    face=fitted_font(draw,phrase,'body',42,620)
    width=draw.textlength(phrase,face)
    left=(WIDTH-width)/2
    space=draw.textlength(' ',face)
    for i,word in enumerate(phrase.split(' ')):
        color=WHITE if i==active else (200,215,209)
        draw.text((left,0),word,face,(*color,255),stroke_width=2,
                  stroke_fill=(14,31,42,225))
        left+=draw.textlength(word,face)+space
    return bitmap


def caption(image: Image.Image,scene: TimedScene,absolute_time: float):
    current=None
    for start,end,text in cached_cues(scene):
        if start<=absolute_time<end:
            current=(start,end,text)
            break
    if not current:
        return
    start,end,phrase=current
    words=phrase.split(' ')
    weights=[max(1,len(word.strip(',.!?'))) for word in words]
    position=clamp((absolute_time-start)/max(.01,end-start))*sum(weights)
    active=len(words)-1;total=0
    for i,weight in enumerate(weights):
        total+=weight
        if position<=total:
            active=i
            break
    overlay=_caption_image(phrase,active)
    image.paste(overlay,(0,round(128*SCALE)),overlay)
