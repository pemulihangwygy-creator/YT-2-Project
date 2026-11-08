from __future__ import annotations

import io
import math
from functools import lru_cache

import resvg_py
from PIL import Image


@lru_cache(maxsize=32)
def raster_svg(markup: str, width: int, height: int) -> Image.Image:
    data = resvg_py.svg_to_bytes(svg_string=markup, width=width, height=height,
                                 skip_system_fonts=True)
    return Image.open(io.BytesIO(data)).convert('RGBA')


def _svg(body: str, w: int = 512, h: int = 512) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">{body}</svg>'


def _polar(radius: float, angle: float) -> str:
    return f'{256+radius*math.cos(angle):.2f},{256+radius*math.sin(angle):.2f}'


@lru_cache(maxsize=4)
def rotor(kind: str) -> Image.Image:
    colors = {
        'impeller': ('#ffc65b', '#e9973f', '#ffdf91'),
        'turbine': ('#6bdaed', '#3a9fb8', '#b5f3ef'),
        'stator': ('#9ce4a2', '#52b987', '#c9f5bf'),
    }
    main, dark, light = colors[kind]
    count = 11 if kind == 'stator' else 14
    blades = []
    for i in range(count):
        a = math.tau*i/count
        path = (f'M {_polar(62,a)} '
                f'C {_polar(92,a+.015)} {_polar(156,a+.19)} {_polar(187,a+.31)} '
                f'L {_polar(187,a+.57*math.tau/count+.31)} '
                f'C {_polar(151,a+.45*math.tau/count+.16)} '
                f'{_polar(94,a+.55*math.tau/count+.08)} {_polar(62,a+.55*math.tau/count)} Z')
        blades.append(f'<path d="{path}" fill="{main if i%2==0 else dark}" '
                      f'stroke="#173845" stroke-width="4" stroke-linejoin="round"/>')
        inner_a = a+.47*math.tau/count
        blades.append(f'<path d="M {_polar(83,inner_a)} Q {_polar(138,inner_a+.08)} '
                      f'{_polar(169,inner_a+.20)}" fill="none" stroke="{light}" '
                      'stroke-width="3" stroke-linecap="round" opacity=".55"/>')
    bolts = ''.join(f'<circle cx="{256+211*math.cos(math.tau*i/8):.2f}" '
                    f'cy="{256+211*math.sin(math.tau*i/8):.2f}" r="5" fill="#193a48"/>'
                    for i in range(8))
    blade_group=''.join(blades)
    if kind == 'turbine':
        blade_group=f'<g transform="translate(512 0) scale(-1 1)">{blade_group}</g>'
    body = f'''
      <circle cx="256" cy="256" r="238" fill="#152e3e"/>
      <circle cx="256" cy="256" r="224" fill="{light}" stroke="#173845" stroke-width="7"/>
      <circle cx="256" cy="256" r="196" fill="#214554" stroke="#173845" stroke-width="7"/>
      {blade_group}
      <circle cx="256" cy="256" r="66" fill="#173845"/>
      <circle cx="256" cy="256" r="54" fill="{main}" stroke="#173845" stroke-width="7"/>
      <circle cx="256" cy="256" r="26" fill="#203d49" stroke="{light}" stroke-width="6"/>
      <circle cx="256" cy="256" r="10" fill="{light}"/>
      {bolts}
    '''
    return raster_svg(_svg(body), 768, 768)


@lru_cache(maxsize=1)
def housing() -> Image.Image:
    bolts = ''.join(f'<circle cx="{256+177*math.cos(math.tau*i/8):.2f}" '
                    f'cy="{256+177*math.sin(math.tau*i/8):.2f}" r="7" '
                    'fill="#285260" stroke="#173845" stroke-width="3"/>'
                    for i in range(8))
    body = f'''
      <circle cx="256" cy="256" r="232" fill="#173341"/>
      <circle cx="256" cy="256" r="218" fill="#f3d28d" stroke="#173845" stroke-width="7"/>
      <circle cx="256" cy="256" r="195" fill="#f6e4b3" stroke="#d2aa65" stroke-width="7"/>
      <circle cx="256" cy="256" r="145" fill="#e9bc6b" stroke="#284b51" stroke-width="8"/>
      <path d="M 110 256 A 146 146 0 0 1 256 110" fill="none" stroke="#fff0c8" stroke-width="11" stroke-linecap="round"/>
      <circle cx="256" cy="256" r="60" fill="#285260" stroke="#173845" stroke-width="7"/>
      <circle cx="256" cy="256" r="38" fill="#fbe5aa" stroke="#173845" stroke-width="7"/>
      <circle cx="256" cy="256" r="17" fill="#173845"/>
      {bolts}
    '''
    return raster_svg(_svg(body), 768, 768)


@lru_cache(maxsize=1)
def car_body() -> Image.Image:
    body = '''
      <path d="M48 166 Q52 145 86 136 L150 116 195 68 Q211 51 243 51 H347
               Q381 51 411 75 L469 117 548 131 Q585 138 591 161 L596 190
               Q597 208 578 211 H45 Q25 211 26 193 L28 178 Q30 170 48 166Z"
            fill="#69c6cb" stroke="#173845" stroke-width="8" stroke-linejoin="round"/>
      <path d="M49 161 Q60 149 91 142 L155 127 H466 L548 140 Q566 143 578 155
               L578 175 H42Z" fill="#8ae2dd"/>
      <path d="M162 119 L205 75 Q216 64 241 64 H345 Q372 64 394 81 L440 118Z"
            fill="#173b4c" stroke="#173845" stroke-width="7" stroke-linejoin="round"/>
      <path d="M178 112 L208 80 Q220 70 242 70 H277 V112Z" fill="#a4e7e0"/>
      <path d="M288 70 H343 Q369 70 388 84 L420 112 H288Z" fill="#a4e7e0"/>
      <path d="M245 72 L214 112 M331 72 L302 111" stroke="#d4f7e7" stroke-width="6" opacity=".65"/>
      <path d="M280 120 V181 M442 122 L452 170 M51 180 H581" fill="none" stroke="#287c86" stroke-width="5"/>
      <path d="M305 135 h28" stroke="#173845" stroke-width="5" stroke-linecap="round"/>
      <path d="M548 145 L575 150 Q584 153 586 163 H548Z" fill="#fff1b0" stroke="#173845" stroke-width="4"/>
      <path d="M31 159 H61 V177 H29Z" fill="#ff8c6c" stroke="#173845" stroke-width="4"/>
      <path d="M28 191 H596 M50 205 H573" stroke="#173845" stroke-width="6"/>
    '''
    return raster_svg(_svg(body, 620, 260), 930, 390)


@lru_cache(maxsize=1)
def car_wheel() -> Image.Image:
    spokes=''.join(f'<path d="M 60 60 L {60+26*math.cos(math.tau*i/6):.2f} '
                   f'{60+26*math.sin(math.tau*i/6):.2f}" stroke="#e5f7dc" '
                   'stroke-width="7" stroke-linecap="round"/>' for i in range(6))
    body=f'''<circle cx="60" cy="60" r="55" fill="#173845"/>
       <circle cx="60" cy="60" r="43" fill="#305460" stroke="#e4f1d7" stroke-width="5"/>
       <circle cx="60" cy="60" r="31" fill="#7aadb0"/>{spokes}
       <circle cx="60" cy="60" r="10" fill="#f8de96" stroke="#173845" stroke-width="4"/>'''
    return raster_svg(_svg(body,120,120), 240, 240)


@lru_cache(maxsize=1)
def engine() -> Image.Image:
    body = '''
      <path d="M35 83 H67 L76 50 H186 L200 80 H241 V111 H257 V171 H242 V218
               H48 V201 H22 V128 H35Z" fill="#f8c85f" stroke="#173845" stroke-width="9" stroke-linejoin="round"/>
      <path d="M78 53 H184 L190 81 H70Z" fill="#f7dfa0" stroke="#173845" stroke-width="8"/>
      <path d="M79 53 V34 H119 V53 M144 53 V34 H176 V53" fill="none" stroke="#173845" stroke-width="8"/>
      <path d="M48 105 H223 V189 H48Z" fill="#e89a42" stroke="#173845" stroke-width="7"/>
      <rect x="71" y="121" width="36" height="51" rx="6" fill="#ffdf98" stroke="#173845" stroke-width="6"/>
      <rect x="120" y="121" width="36" height="51" rx="6" fill="#ffdf98" stroke="#173845" stroke-width="6"/>
      <rect x="169" y="121" width="36" height="51" rx="6" fill="#ffdf98" stroke="#173845" stroke-width="6"/>
      <circle cx="51" cy="194" r="26" fill="#173845"/><circle cx="51" cy="194" r="12" fill="#f8d994"/>
      <circle cx="222" cy="194" r="26" fill="#173845"/><circle cx="222" cy="194" r="12" fill="#f8d994"/>
      <path d="M257 126 H287 V158 H257" fill="#e89a42" stroke="#173845" stroke-width="8"/>
    '''
    return raster_svg(_svg(body, 310, 260), 620, 520)


@lru_cache(maxsize=1)
def gearbox() -> Image.Image:
    body = '''
      <path d="M30 66 H75 L92 41 H189 L207 66 H247 V103 H277 V159 H247 V196
               H207 L190 220 H92 L75 196 H30Z" fill="#7ccee0" stroke="#173845" stroke-width="9" stroke-linejoin="round"/>
      <path d="M51 83 H226 V178 H51Z" fill="#c2f1ec" stroke="#173845" stroke-width="7"/>
      <circle cx="138" cy="130" r="49" fill="#278ca7" stroke="#173845" stroke-width="7"/>
      <circle cx="138" cy="130" r="23" fill="#e2f8e9" stroke="#173845" stroke-width="7"/>
      <path d="M138 70 V91 M138 169 V190 M78 130 H99 M177 130 H198
               M96 88 L111 103 M165 157 L180 172 M180 88 L165 103 M111 157 L96 172"
            stroke="#173845" stroke-width="9" stroke-linecap="round"/>
      <path d="M277 119 H300 V143 H277" fill="#c2f1ec" stroke="#173845" stroke-width="8"/>
      <circle cx="54" cy="67" r="7" fill="#173845"/><circle cx="220" cy="67" r="7" fill="#173845"/>
      <circle cx="54" cy="195" r="7" fill="#173845"/><circle cx="220" cy="195" r="7" fill="#173845"/>
    '''
    return raster_svg(_svg(body, 320, 260), 640, 520)


@lru_cache(maxsize=1)
def lock() -> Image.Image:
    body = '''<path d="M 63 106 V 75 A 46 46 0 0 1 155 75 V 106" fill="none" stroke="#163745" stroke-width="23" stroke-linecap="round"/>
      <path d="M 63 103 V 75 A 46 46 0 0 1 155 75 V 103" fill="none" stroke="#ffe5a3" stroke-width="12" stroke-linecap="round"/>
      <rect x="31" y="100" width="156" height="122" rx="20" fill="#ffc45a" stroke="#173845" stroke-width="9"/>
      <circle cx="109" cy="148" r="13" fill="#173845"/><path d="M 109 151 V 180" stroke="#173845" stroke-width="11" stroke-linecap="round"/>'''
    return raster_svg(_svg(body, 220, 240), 440, 480)
