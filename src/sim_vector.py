from __future__ import annotations

from functools import lru_cache

from PIL import Image

from .vector import raster_svg


def _asset(body: str, width: int, height: int) -> Image.Image:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
           f'{body}</svg>')
    return raster_svg(svg, width * 2, height * 2)


@lru_cache(maxsize=None)
def phone() -> Image.Image:
    return _asset('''
      <rect x="11" y="7" width="398" height="686" rx="52" fill="#17253b"/>
      <rect x="21" y="17" width="378" height="666" rx="43" fill="#41516c"/>
      <rect x="28" y="22" width="364" height="655" rx="37" fill="#fbf5e9"/>
      <path d="M147 22 h126 l-8 20 q-3 8-13 8 h-84 q-10 0-13-8z" fill="#17253b"/>
      <circle cx="238" cy="32" r="4" fill="#637795"/>
      <rect x="160" y="653" width="100" height="8" rx="4" fill="#17253b" opacity=".55"/>
    ''', 420, 700)


@lru_cache(maxsize=None)
def shield() -> Image.Image:
    return _asset('''
      <path d="M230 16 C302 56 366 63 419 68 v132 c0 131-69 223-189 289
               C110 423 41 331 41 200 V68 C94 63 158 56 230 16z"
            fill="#172a3c"/>
      <path d="M230 37 C295 73 352 80 398 84 v116 c0 119-61 204-168 264
               C123 404 62 319 62 200 V84 C108 80 165 73 230 37z"
            fill="#69ddbc"/>
      <path d="M230 55 C288 87 338 94 379 98 v102 c0 108-54 182-149 238
               C135 382 81 308 81 200 V98 C122 94 172 87 230 55z"
            fill="#39a996"/>
      <path d="M138 225 l62 61 125-136" fill="none" stroke="#183b45"
            stroke-width="42" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M138 215 l62 61 125-136" fill="none" stroke="#fff5db"
            stroke-width="28" stroke-linecap="round" stroke-linejoin="round"/>
    ''', 460, 500)


@lru_cache(maxsize=None)
def sim_card() -> Image.Image:
    return _asset('''
      <rect x="7" y="9" width="606" height="362" rx="27" fill="#1a3041"/>
      <rect x="18" y="18" width="584" height="342" rx="20" fill="#fcf0d7"/>
      <path d="M18 38 q0-20 20-20 h544 q20 0 20 20 v77 H18z" fill="#64cfc3"/>
      <path d="M18 115 h584" stroke="#173b46" stroke-width="7"/>
      <rect x="45" y="141" width="150" height="162" rx="11" fill="#d0e5d8" stroke="#25525b" stroke-width="6"/>
      <circle cx="120" cy="191" r="31" fill="#4f8685"/>
      <path d="M67 278 q6-55 53-55 t53 55" fill="#4f8685"/>
      <rect x="227" y="149" width="230" height="14" rx="7" fill="#456d70"/>
      <rect x="227" y="183" width="278" height="12" rx="6" fill="#9fbcb0"/>
      <rect x="227" y="212" width="200" height="12" rx="6" fill="#9fbcb0"/>
      <rect x="227" y="241" width="252" height="12" rx="6" fill="#9fbcb0"/>
      <rect x="227" y="274" width="139" height="21" rx="10" fill="#efc66a"/>
      <path d="M49 329 h522" stroke="#bed2c0" stroke-width="6"/>
    ''', 620, 380)


@lru_cache(maxsize=None)
def calendar() -> Image.Image:
    return _asset('''
      <rect x="12" y="30" width="276" height="255" rx="23" fill="#173443"/>
      <rect x="22" y="40" width="256" height="235" rx="15" fill="#fbf0d5"/>
      <path d="M22 55 q0-15 15-15 h226 q15 0 15 15 v65 H22z" fill="#f3bc54"/>
      <path d="M22 120 h256" stroke="#173443" stroke-width="7"/>
      <path d="M79 19 v51 M221 19 v51" stroke="#173443" stroke-width="18" stroke-linecap="round"/>
      <path d="M79 22 v43 M221 22 v43" stroke="#fff5d7" stroke-width="8" stroke-linecap="round"/>
      <path d="M55 246 h190" stroke="#d2dac6" stroke-width="6"/>
    ''', 300, 300)


@lru_cache(maxsize=None)
def warning() -> Image.Image:
    return _asset('''
      <path d="M150 14 L292 259 Q303 279 279 279 H21 Q-3 279 8 259 L133 14 Q141-2 150 14z"
            fill="#273044"/>
      <path d="M142 35 L271 255 H29z" fill="#ffd36d"/>
      <path d="M150 102 v70" stroke="#9d3d35" stroke-width="21" stroke-linecap="round"/>
      <circle cx="150" cy="207" r="12" fill="#9d3d35"/>
    ''', 300, 290)


@lru_cache(maxsize=None)
def building() -> Image.Image:
    return _asset('''
      <path d="M42 174 L300 28 558 174 v226 H42z" fill="#1b3948" stroke="#1b3948" stroke-width="14" stroke-linejoin="round"/>
      <path d="M62 180 L300 48 538 180 v203 H62z" fill="#f9eac9"/>
      <path d="M47 175 L300 29 553 175" fill="none" stroke="#1b3948" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M68 175 L300 59 532 175" fill="#68c3bb" stroke="#1b3948" stroke-width="8" stroke-linejoin="round"/>
      <rect x="155" y="158" width="290" height="59" rx="8" fill="#fff4d7" stroke="#1b3948" stroke-width="7"/>
      <rect x="99" y="239" width="94" height="91" rx="5" fill="#87cfc8" stroke="#1b3948" stroke-width="7"/>
      <rect x="407" y="239" width="94" height="91" rx="5" fill="#87cfc8" stroke="#1b3948" stroke-width="7"/>
      <path d="M146 240 v90 M100 284 h92 M454 240 v90 M408 284 h92" stroke="#1b3948" stroke-width="6"/>
      <path d="M236 383 v-113 q0-15 15-15 h98 q15 0 15 15 v113z" fill="#335b65" stroke="#1b3948" stroke-width="8"/>
      <path d="M300 258 v125" stroke="#b9e1d7" stroke-width="5"/>
      <circle cx="285" cy="326" r="5" fill="#f7d17d"/><circle cx="315" cy="326" r="5" fill="#f7d17d"/>
      <path d="M39 391 h522 M23 409 h554" stroke="#1b3948" stroke-width="13" stroke-linecap="round"/>
    ''', 600, 430)


@lru_cache(maxsize=None)
def bank_card() -> Image.Image:
    return _asset('''
      <rect x="8" y="10" width="384" height="240" rx="26" fill="#1d3044"/>
      <rect x="18" y="20" width="364" height="220" rx="18" fill="#6488af"/>
      <path d="M18 76 h364 v45 H18z" fill="#355776"/>
      <rect x="48" y="151" width="62" height="44" rx="8" fill="#f5d285"/>
      <path d="M78 151 v44 M48 173 h62" stroke="#8c7749" stroke-width="4"/>
      <rect x="138" y="160" width="167" height="10" rx="5" fill="#d7e7da"/>
      <rect x="138" y="182" width="124" height="10" rx="5" fill="#d7e7da"/>
    ''', 400, 260)


@lru_cache(maxsize=None)
def share() -> Image.Image:
    return _asset('''
      <path d="M24 32 h254 q29 0 29 29 v103 q0 29-29 29 H145 l-54 51 v-51 H53 q-29 0-29-29 V61 q0-29 29-29z"
            fill="#173d4a"/>
      <path d="M35 43 h243 q18 0 18 18 v103 q0 18-18 18 H141 l-39 37 v-37 H53 q-18 0-18-18 V61 q0-18 18-18z"
            fill="#9be2ce"/>
      <path d="M84 104 h158 M84 133 h111" stroke="#285966" stroke-width="12" stroke-linecap="round"/>
      <circle cx="306" cy="195" r="64" fill="#1b3f4a"/>
      <circle cx="306" cy="195" r="52" fill="#f8d27b"/>
      <path d="M279 194 l19 19 35-39" fill="none" stroke="#265c58" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/>
    ''', 380, 280)
