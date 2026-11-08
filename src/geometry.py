from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from numba import njit
from PIL import Image

from .lighting import studio_reflection


@dataclass(frozen=True)
class Mesh:
    vertices: np.ndarray
    normals: np.ndarray
    triangles: np.ndarray
    colors: np.ndarray


class MeshBuilder:
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.triangles = []
        self.colors = []

    def patch(self, points, color, *, periodic=False, flip=False):
        grid = np.asarray(points, dtype=np.float32)
        rows, columns, _ = grid.shape
        normals = np.zeros_like(grid)
        for row in range(rows):
            before = (row - 1) % rows if periodic else max(0, row - 1)
            after = (row + 1) % rows if periodic else min(rows - 1, row + 1)
            for column in range(columns):
                left, right = max(0, column - 1), min(columns - 1, column + 1)
                normal = np.cross(grid[after, column] - grid[before, column],
                                  grid[row, right] - grid[row, left])
                normal /= np.linalg.norm(normal) + 1e-9
                normals[row, column] = -normal if flip else normal
        base = len(self.vertices)
        self.vertices.extend(grid.reshape(-1, 3))
        self.normals.extend(normals.reshape(-1, 3))
        for row in range(rows if periodic else rows - 1):
            next_row = (row + 1) % rows
            for column in range(columns - 1):
                a = base + row * columns + column
                b = base + next_row * columns + column
                c = base + next_row * columns + column + 1
                d = base + row * columns + column + 1
                self.triangles.extend(((a, b, c), (a, c, d)))
                self.colors.extend((color, color))

    def lathe(self, profile, color, *, sides=80, center=(0, 0), axis='z'):
        grid = []
        for i in range(sides):
            angle = math.tau * i / sides
            ca, sa = math.cos(angle), math.sin(angle)
            if axis == 'z':
                grid.append([(center[0] + r * ca, center[1] + r * sa, z)
                             for r, z in profile])
            else:
                grid.append([(z, center[0] + r * ca, center[1] + r * sa)
                             for r, z in profile])
        self.patch(grid, color, periodic=True)

    def box(self, center, extent, color):
        x, y, z = center
        a, b, c = (n / 2 for n in extent)
        p = [(x-a,y-b,z-c), (x+a,y-b,z-c), (x+a,y+b,z-c), (x-a,y+b,z-c),
             (x-a,y-b,z+c), (x+a,y-b,z+c), (x+a,y+b,z+c), (x-a,y+b,z+c)]
        for i, j, k, l in ((0,1,2,3), (4,7,6,5), (0,4,5,1),
                           (1,5,6,2), (2,6,7,3), (3,7,4,0)):
            self.patch(((p[i], p[l]), (p[j], p[k])), color)

    def finish(self):
        return Mesh(np.asarray(self.vertices, dtype=np.float32),
                    np.asarray(self.normals, dtype=np.float32),
                    np.asarray(self.triangles, dtype=np.int32),
                    np.asarray(self.colors, dtype=np.float32))


def bolt(builder, x, y, z, radius=0.035):
    builder.lathe([(0.0,z), (radius*0.8,z), (radius,z-0.008),
                   (radius,z-0.024)], (171, 184, 178), sides=8, center=(x,y))


@lru_cache(maxsize=3)
def rotor(kind: str) -> Mesh:
    palette = {'impeller': (208, 141, 82), 'turbine': (101, 173, 196),
               'stator': (103, 174, 143)}
    color = palette[kind]
    count = 12 if kind == 'stator' else 16
    b = MeshBuilder()
    # A rounded steel rim and the bowl behind the curved vanes.
    b.lathe([(.88,-.21), (.94,-.20), (.985,-.17), (1.,-.12),
             (1.,.10), (.985,.14), (.95,.155), (.92,.155), (.89,.14)],
            (158, 177, 178), sides=96)
    b.lathe([(.18,-.07), (.38,-.06), (.70,-.07), (.90,-.10)],
            tuple(int(v * .43) for v in color), sides=96)
    for blade in range(count):
        angle = math.tau * blade / count
        for side in (0, 1):
            surface = []
            for step in range(13):
                t = step / 12
                radius = .235 + .665 * t
                row = []
                for height_step in range(5):
                    h = height_step / 4
                    curve = .36 * t**1.2 + (.14 if kind != 'stator' else -.12) * (h - .5)
                    a = angle + curve + (.024 if side else 0)
                    z = -.075 + .24 * h + .055 * (1 - t*t)
                    row.append((radius * math.cos(a), radius * math.sin(a), z))
                surface.append(row)
            b.patch(surface, color, flip=bool(side))
        top = []
        for step in range(13):
            t = step / 12
            radius = .235 + .665 * t
            z = -.075 + .24 + .055 * (1 - t*t)
            a = angle + .36 * t**1.2 + (.14 if kind != 'stator' else -.12) * .5
            top.append(((radius*math.cos(a), radius*math.sin(a), z),
                        (radius*math.cos(a+.024), radius*math.sin(a+.024), z)))
        b.patch(top, tuple(min(255, int(v * 1.1)) for v in color))
    b.lathe([(.15,-.07), (.235,-.07), (.245,-.01), (.245,.19), (.23,.23),
             (.155,.23), (.135,.21), (.135,.10)], (176, 191, 186), sides=64)
    b.lathe([(.10,.10), (.13,.10), (.13,.215), (.10,.215)], (43, 64, 68), sides=64)
    return b.finish()


@lru_cache(maxsize=1)
def converter() -> Mesh:
    b = MeshBuilder()
    profile = [(.10,.43), (.16,.43), (.18,.39), (.19,.28), (.27,.26),
               (.38,.245), (.53,.22), (.68,.18), (.80,.13), (.92,.065),
               (.985,-.02), (1.,-.09), (.98,-.16), (.90,-.23),
               (.75,-.27), (.55,-.31), (.32,-.33), (.17,-.33)]
    b.lathe(profile, (160, 179, 180), sides=112)
    b.lathe([(.975,-.055), (1.006,-.055), (1.01,-.105), (.98,-.105)],
            (79, 99, 101), sides=112)
    b.lathe([(.075,.43), (.075,.49), (.16,.49), (.165,.43)], (189, 204, 200), sides=72)
    b.lathe([(.048,.43), (.075,.43), (.075,.49), (.048,.49)], (45, 62, 65), sides=72)
    for index in range(6):
        angle = index * math.tau / 6
        bolt(b, .61*math.cos(angle), .61*math.sin(angle), .208, .026)
    return b.finish()


@lru_cache(maxsize=1)
def clutch() -> Mesh:
    b = MeshBuilder()
    b.lathe([(.17,-.13), (.72,-.13), (.88,-.10), (.92,-.06), (.92,.07),
             (.86,.11), (.69,.11), (.68,.15), (.25,.15)], (153, 170, 169))
    b.lathe([(.70,.145), (.86,.145), (.86,.105), (.70,.105)], (165, 113, 70))
    b.lathe([(.12,.14), (.24,.14), (.27,.18), (.27,.24), (.14,.24), (.12,.21)],
            (189, 203, 197), sides=64)
    for index in range(6):
        angle = index*math.tau/6
        bolt(b, .47*math.cos(angle), .47*math.sin(angle), .166, .025)
    return b.finish()


def _oil_position(angle, sign):
    return np.asarray((-.55, sign*(.60 + .39*math.cos(angle)), .90*math.sin(angle)), dtype=np.float32)


def _oil_frame(angle, sign):
    tangent = np.asarray((0, -sign*.39*math.sin(angle), .90*math.cos(angle)), dtype=np.float32)
    tangent /= np.linalg.norm(tangent) + 1e-8
    across = np.asarray((1,0,0), dtype=np.float32)
    normal = np.cross(tangent, across)
    normal /= np.linalg.norm(normal) + 1e-8
    return tangent, across, normal


@lru_cache(maxsize=1)
def oil_loop() -> Mesh:
    # Two continuous closed cross-section paths show the recirculating oil.
    # These are solid flow ribbons, not detached decorative particles.
    b = MeshBuilder()
    segments, sides = 72, 8
    for sign in (1, -1):
        grid = []
        for segment in range(segments):
            a = math.tau*segment/segments
            point = _oil_position(a, sign)
            _, across, normal = _oil_frame(a, sign)
            row = []
            for side in range(sides+1):
                theta = math.tau*side/sides
                xyz = point + .038*(math.cos(theta)*across + math.sin(theta)*normal)
                row.append(tuple(xyz))
            grid.append(row)
        b.patch(grid, (44,167,197), periodic=True)
    for sign in (1, -1):
        for fraction in (.18,.68):
            angle = math.tau*fraction
            point = _oil_position(angle, sign)
            tangent, across, normal = _oil_frame(angle, sign)
            cone = []
            for side in range(sides):
                theta = math.tau*side/sides
                radial = math.cos(theta)*across + math.sin(theta)*normal
                cone.append((tuple(point - tangent*.045 + radial*.080),
                             tuple(point + tangent*.070 + radial*.001)))
            b.patch(cone, (90,211,226), periodic=True)
    return b.finish()


def animated_oil(time: float) -> Mesh:
    source = oil_loop()
    colors = source.colors.copy()
    sides, segments = 8, 72
    faces_per_loop = sides*2*segments
    fractions = np.repeat(np.arange(segments, dtype=np.float32)/segments, sides*2)
    for loop in range(2):
        wave = (.5 + .5*np.cos(math.tau*(fractions-time*.24)))**6
        factor = .75 + .55*wave
        start = loop*faces_per_loop
        colors[start:start+faces_per_loop] *= factor[:,None]
    np.clip(colors, 0, 255, out=colors)
    return Mesh(source.vertices, source.normals, source.triangles, colors)


@lru_cache(maxsize=1)
def engine() -> Mesh:
    b = MeshBuilder()
    b.box((0,-.08,0), (1.76,.82,.82), (117, 138, 138))
    b.box((0,.46,0), (1.48,.27,.73), (163, 179, 175))
    b.box((0,.68,-.05), (1.18,.18,.60), (58, 76, 78))
    b.box((0,-.59,0), (1.36,.20,.70), (58, 75, 78))
    b.lathe([(.08,-.76), (.10,-.76), (.10,.76), (.08,.76)],
            (168, 184, 180), center=(.28,.47), axis='x', sides=32)
    for x in (-.64,-.21,.21,.64):
        b.box((x,-.04,.44), (.25,.50,.14), (68, 89, 92))
        b.box((x,.45,.42), (.17,.12,.11), (211, 219, 207))
        b.box((x,.24,.51), (.13,.20,.11), (135, 156, 151))
    return b.finish()


@lru_cache(maxsize=1)
def transmission() -> Mesh:
    b = MeshBuilder()
    b.lathe([(.52,-.96), (.60,-.90), (.60,-.57), (.49,-.39), (.39,.12),
             (.34,.45), (.29,.69), (.22,.91), (.15,.95)],
            (126, 147, 148), axis='x', sides=72)
    for x, radius in ((-.57,.61), (.12,.40), (.67,.31)):
        b.lathe([(radius-.02,x-.035), (radius,x-.035), (radius,x+.035),
                 (radius-.02,x+.035)], (176, 192, 188), axis='x', sides=72)
    b.lathe([(.15,.94), (.12,.94), (.12,1.18), (.15,1.18)],
            (160, 175, 172), axis='x', sides=48)
    return b.finish()


@njit(cache=True, fastmath=True)
def _raster(points, normals, triangles, colors, out, depth, reflection):
    height, width = depth.shape
    map_h, map_w, _ = reflection.shape
    for i in range(triangles.shape[0]):
        i0, i1, i2 = triangles[i,0], triangles[i,1], triangles[i,2]
        x0,y0,z0 = points[i0]
        x1,y1,z1 = points[i1]
        x2,y2,z2 = points[i2]
        area = (x1-x0)*(y2-y0) - (y1-y0)*(x2-x0)
        if abs(area) < .00001:
            continue
        min_x, max_x = max(0,int(min(x0,x1,x2))), min(width-1,int(max(x0,x1,x2))+1)
        min_y, max_y = max(0,int(min(y0,y1,y2))), min(height-1,int(max(y0,y1,y2))+1)
        if min_x > max_x or min_y > max_y:
            continue
        reciprocal = 1. / area
        for y in range(min_y, max_y+1):
            for x in range(min_x, max_x+1):
                u = ((x1-x0)*(y+.5-y0) - (y1-y0)*(x+.5-x0)) * reciprocal
                v = ((x+.5-x0)*(y2-y0) - (y+.5-y0)*(x2-x0)) * reciprocal
                w = 1. - u - v
                if u < 0 or v < 0 or w < 0:
                    continue
                z = w*z0 + v*z1 + u*z2
                if z <= depth[y,x]:
                    continue
                nx = w*normals[i0,0] + v*normals[i1,0] + u*normals[i2,0]
                ny = w*normals[i0,1] + v*normals[i1,1] + u*normals[i2,1]
                nz = w*normals[i0,2] + v*normals[i1,2] + u*normals[i2,2]
                inv = 1. / math.sqrt(nx*nx + ny*ny + nz*nz + 1e-8)
                nx, ny, nz = nx*inv, ny*inv, nz*inv
                if nz < 0:
                    nx, ny, nz = -nx, -ny, -nz
                key = max(0., -.35*nx + .55*ny + .76*nz)
                fill = max(0., .65*nx - .10*ny + .75*nz)
                strength = .29 + .45*key + .16*fill
                map_x = (nx*.49 + .5) * (map_w-1)
                map_y = (.5 - ny*.49) * (map_h-1)
                ix = max(0, min(map_w-2, int(map_x)))
                iy = max(0, min(map_h-2, int(map_y)))
                fx, fy = map_x-ix, map_y-iy
                for channel in range(3):
                    top = (1-fx)*reflection[iy,ix,channel] + fx*reflection[iy,ix+1,channel]
                    bottom = (1-fx)*reflection[iy+1,ix,channel] + fx*reflection[iy+1,ix+1,channel]
                    reflected = top*(1-fy) + bottom*fy
                    value = colors[i,channel]*strength + max(0., reflected-75)*.70
                    out[y,x,channel] = min(255, int(value))
                out[y,x,3] = 255
                depth[y,x] = z


def _camera(yaw, pitch):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    return np.asarray(((cy,0,sy), (sp*sy,cp,-sp*cy), (-cp*sy,sp,cp*cy)), dtype=np.float32)


def _spin(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(((c,-s,0), (s,c,0), (0,0,1)), dtype=np.float32)


def _project(points, radius, center):
    projected = points.copy()
    perspective = 4.4 / (4.4 - points[:,2] * .42)
    projected[:,0] = center + points[:,0] * radius * perspective
    projected[:,1] = center - points[:,1] * radius * perspective
    return projected


def _draw_parts(image, parts, x, y, radius, yaw, pitch, scale):
    radius_px = radius * scale
    extent = max(8, int(math.ceil(radius_px * 2.7)))
    if extent > 2200:
        raise ValueError('Model exceeds the render budget')
    origin_x = round(x*scale - extent/2)
    origin_y = round(y*scale - extent/2)
    if origin_x >= image.width or origin_y >= image.height or origin_x+extent <= 0 or origin_y+extent <= 0:
        return
    out = np.zeros((extent,extent,4), dtype=np.uint8)
    depth = np.full((extent,extent), -100, dtype=np.float32)
    camera = _camera(yaw, pitch)
    for model, angle, center in parts:
        spin = _spin(angle)
        points = ((model.vertices - center) @ spin.T + center) @ camera.T
        normals = model.normals @ spin.T @ camera.T
        screen = _project(points, radius_px, extent/2)
        _raster(screen.astype(np.float32), normals.astype(np.float32), model.triangles,
                model.colors, out, depth, studio_reflection())
    sprite = Image.fromarray(out)
    image.paste(sprite, (origin_x,origin_y), sprite)


def render(image: Image.Image, model: Mesh, x: float, y: float, radius: float,
           spin: float = 0, yaw: float = .65, pitch: float = -.16, scale: float = 1.5):
    _draw_parts(image, [(model, spin, np.zeros(3, dtype=np.float32))],
                x, y, radius, yaw, pitch, scale)


def render_assembly(image: Image.Image, parts, x: float, y: float, radius: float,
                    yaw: float = 1.14, pitch: float = .12, scale: float = 1.5):
    """Render independently animated coaxial parts into one 3D depth buffer."""
    radius_px = radius * scale
    height = max(8, int(math.ceil(radius_px * 2.9)))
    origin_y = round(y*scale - height/2)
    if origin_y >= image.height or origin_y + height <= 0:
        return
    out = np.zeros((height,image.width,4), dtype=np.uint8)
    depth = np.full((height,image.width), -100, dtype=np.float32)
    camera = _camera(yaw, pitch)
    reflection = studio_reflection()
    for model, angle, z_offset, dimensions in parts:
        dimensions = np.asarray(dimensions, dtype=np.float32)
        spin = _spin(angle)
        points = (model.vertices * dimensions) @ spin.T
        points[:,2] += z_offset
        points = points @ camera.T
        normals = (model.normals / dimensions) @ spin.T @ camera.T
        perspective = 4.4 / (4.4 - points[:,2] * .42)
        screen = points.copy()
        screen[:,0] = x*scale + points[:,0] * radius_px * perspective
        screen[:,1] = height/2 - points[:,1] * radius_px * perspective
        _raster(screen.astype(np.float32), normals.astype(np.float32), model.triangles,
                model.colors, out, depth, reflection)
    sprite = Image.fromarray(out)
    image.paste(sprite, (0,origin_y), sprite)


@lru_cache(maxsize=2)
def car_model(braking: bool):
    path = Path(__file__).resolve().parent.parent / 'assets' / 'models' / 'car-concept.npz'
    models = []
    with np.load(path, allow_pickle=False) as data:
        for name in ('body', 'wheel0', 'wheel1', 'wheel2', 'wheel3'):
            colors = data[name+'_c'].copy()
            if braking and name == 'body':
                mask = data[name+'_brake']
                colors[mask] = np.minimum(colors[mask] * np.array((1.4, .7, .7)), 255)
            model = Mesh(data[name+'_v'], data[name+'_n'], data[name+'_f'], colors)
            models.append((model, data[name+'_center']))
    return tuple(models)


def render_car(image: Image.Image, x: float, y: float, radius: float,
               spin: float, braking: bool, yaw: float = -.45, pitch: float = .18, scale: float = 1.5):
    parts = []
    for index, (model, center) in enumerate(car_model(braking)):
        parts.append((model, spin if index else 0, center))
    _draw_parts(image, parts, x, y, radius, yaw, pitch, scale)
