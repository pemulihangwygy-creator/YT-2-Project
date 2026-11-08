from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw


@dataclass(frozen=True)
class Mesh:
    vertices: np.ndarray
    normals: np.ndarray
    colors: np.ndarray


class MeshBuilder:
    def __init__(self):
        self.faces: list[list[tuple[float, float, float]]] = []
        self.colors: list[tuple[float, float, float]] = []

    def add(self, face, color):
        self.faces.append(face)
        self.colors.append(color)

    def finish(self) -> Mesh:
        vertices = np.asarray(self.faces, dtype=np.float32)
        normals = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
        normals /= np.linalg.norm(normals, axis=1)[:, None] + 1e-8
        return Mesh(vertices, normals, np.asarray(self.colors, dtype=np.float32))


def radial(radius, angle, z):
    return (radius * math.cos(angle), radius * math.sin(angle), z)


def ring(builder, inner, outer, z, color, sides=48):
    for i in range(sides):
        a = math.tau * i / sides
        b = math.tau * (i + 1) / sides
        builder.add([radial(inner, a, z), radial(outer, a, z),
                     radial(outer, b, z), radial(inner, b, z)], color)


def cylinder(builder, radius, back, front, color, sides=48):
    for i in range(sides):
        a = math.tau * i / sides
        b = math.tau * (i + 1) / sides
        builder.add([radial(radius, a, back), radial(radius, b, back),
                     radial(radius, b, front), radial(radius, a, front)], color)


def box(builder, center, extent, color):
    x, y, z = center
    a, b, c = (n / 2 for n in extent)
    p = [(x-a,y-b,z-c), (x+a,y-b,z-c), (x+a,y+b,z-c), (x-a,y+b,z-c),
         (x-a,y-b,z+c), (x+a,y-b,z+c), (x+a,y+b,z+c), (x-a,y+b,z+c)]
    for indexes in ((0,1,2,3), (4,7,6,5), (0,4,5,1),
                    (1,5,6,2), (2,6,7,3), (3,7,4,0)):
        builder.add([p[i] for i in indexes], color)


def tube_x(builder, x0, x1, radius, y, z, color, sides=18):
    for i in range(sides):
        a,b=math.tau*i/sides,math.tau*(i+1)/sides
        builder.add([(x0,y+radius*math.cos(a),z+radius*math.sin(a)),
                     (x0,y+radius*math.cos(b),z+radius*math.sin(b)),
                     (x1,y+radius*math.cos(b),z+radius*math.sin(b)),
                     (x1,y+radius*math.cos(a),z+radius*math.sin(a))],color)


@lru_cache(maxsize=4)
def rotor(kind: str) -> Mesh:
    palette = {'impeller': (244, 151, 65), 'turbine': (62, 179, 218),
               'stator': (78, 196, 141)}
    color = palette[kind]
    blades = 12 if kind == 'stator' else 15
    mesh = MeshBuilder()
    cylinder(mesh, 1.0, -0.18, 0.12, (117, 136, 139))
    ring(mesh, 0.86, 1.0, 0.12, (191, 208, 207))
    ring(mesh, 0.80, 0.86, 0.14, (44, 66, 74))
    ring(mesh, 0.24, 0.80, 0.02, tuple(c * 0.58 for c in color))
    for blade in range(blades):
        angle = math.tau * blade / blades
        for segment in range(5):
            r0 = 0.25 + segment * 0.108
            r1 = 0.25 + (segment + 1) * 0.108
            a0 = angle + 0.34 * ((r0 - 0.25) / 0.54)
            a1 = angle + 0.34 * ((r1 - 0.25) / 0.54)
            width = 0.085
            mesh.add([radial(r0,a0,0.03), radial(r1,a1,0.03),
                      radial(r1,a1,0.21), radial(r0,a0,0.21)], color)
            mesh.add([radial(r0,a0,0.21), radial(r1,a1,0.21),
                      radial(r1,a1+width,0.21), radial(r0,a0+width,0.21)],
                     tuple(min(255, c * 1.20) for c in color))
            mesh.add([radial(r0,a0+width,0.03), radial(r1,a1+width,0.03),
                      radial(r1,a1+width,0.21), radial(r0,a0+width,0.21)],
                     tuple(c * 0.66 for c in color))
    cylinder(mesh, 0.24, 0.02, 0.28, (151, 172, 173))
    ring(mesh, 0.12, 0.24, 0.28, (218, 228, 224))
    cylinder(mesh, 0.12, 0.20, 0.28, (57, 78, 84))
    ring(mesh, 0.075, 0.12, 0.20, (44, 62, 70))
    return mesh.finish()


@lru_cache(maxsize=1)
def converter() -> Mesh:
    mesh = MeshBuilder()
    outer_segments, cross_segments = 72, 24
    major, minor = 0.57, 0.42
    def point(a, b):
        radius = major + minor * math.cos(b)
        return (radius * math.cos(a), radius * math.sin(a), minor * 0.62 * math.sin(b))
    for i in range(outer_segments):
        a, b = math.tau * i / outer_segments, math.tau * (i + 1) / outer_segments
        for j in range(cross_segments):
            u, v = math.tau * j / cross_segments, math.tau * (j + 1) / cross_segments
            mesh.add([point(a,u), point(b,u), point(b,v), point(a,v)], (169, 185, 188))
    cylinder(mesh, 0.15, 0.0, 0.38, (141, 160, 162), 36)
    ring(mesh, 0.07, 0.15, 0.38, (211, 225, 221), 36)
    cylinder(mesh, 0.07, 0.31, 0.38, (44, 64, 71), 36)
    return mesh.finish()


@lru_cache(maxsize=1)
def engine() -> Mesh:
    m = MeshBuilder()
    box(m, (0, -0.05, 0), (1.70, 0.92, 0.76), (117, 135, 138))
    box(m, (0, 0.52, 0), (1.38, 0.28, 0.70), (170, 185, 183))
    box(m, (0, 0.73, 0), (1.07, 0.14, 0.52), (79, 99, 103))
    box(m, (0, 0.88, -0.05), (0.78, 0.16, 0.43), (57, 76, 80))
    tube_x(m, -0.76, 0.76, 0.09, 0.38, 0.48, (181, 194, 190))
    tube_x(m, -0.64, 0.64, 0.07, -0.38, 0.45, (59, 78, 82))
    for x in (-0.63, -0.21, 0.21, 0.63):
        box(m, (x, -0.03, 0.43), (0.25, 0.49, 0.16), (72, 94, 99))
        box(m, (x, 0.56, 0.37), (0.20, 0.12, 0.12), (213, 220, 212))
        box(m, (x, 0.32, 0.46), (0.13, 0.22, 0.12), (136, 158, 158))
    box(m, (0, -0.60, 0), (1.25, 0.20, 0.65), (67, 87, 92))
    return m.finish()


@lru_cache(maxsize=1)
def transmission() -> Mesh:
    mesh = MeshBuilder()
    sides = 28
    stations = ((-0.92,0.58), (-0.57,0.58), (0.18,0.38), (0.67,0.29), (0.90,0.22))
    for (x0,r0), (x1,r1) in zip(stations, stations[1:]):
        for i in range(sides):
            a, b = math.tau*i/sides, math.tau*(i+1)/sides
            mesh.add([(x0,r0*math.cos(a),r0*math.sin(a)),
                      (x0,r0*math.cos(b),r0*math.sin(b)),
                      (x1,r1*math.cos(b),r1*math.sin(b)),
                      (x1,r1*math.cos(a),r1*math.sin(a))], (129, 149, 151))
    for x,r in ((-0.56,0.60),(0.15,0.40),(0.65,0.31)):
        for i in range(sides):
            a,b=math.tau*i/sides,math.tau*(i+1)/sides
            mesh.add([(x-0.035,r*math.cos(a),r*math.sin(a)),
                      (x-0.035,r*math.cos(b),r*math.sin(b)),
                      (x+0.035,r*math.cos(b),r*math.sin(b)),
                      (x+0.035,r*math.cos(a),r*math.sin(a))], (179, 195, 194))
    return mesh.finish()


def render(image: Image.Image, mesh: Mesh, x: float, y: float, radius: float,
           spin: float = 0, yaw: float = 0.65, pitch: float = -0.16, scale: float = 1.5):
    cz, sz = math.cos(spin), math.sin(spin)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    rz = np.array(((cz,-sz,0), (sz,cz,0), (0,0,1)), dtype=np.float32)
    ry = np.array(((cy,0,sy), (0,1,0), (-sy,0,cy)), dtype=np.float32)
    rx = np.array(((1,0,0), (0,cp,-sp), (0,sp,cp)), dtype=np.float32)
    rotation = rx @ ry @ rz
    vertices = mesh.vertices @ rotation.T
    normals = mesh.normals @ rotation.T
    depth = vertices[:, :, 2].mean(axis=1)
    light = np.array((-0.38, 0.55, 0.74), dtype=np.float32)
    light /= np.linalg.norm(light)
    strength = 0.58 + 0.56 * np.abs(normals @ light)
    colors = np.clip(mesh.colors * strength[:, None], 0, 255).astype(np.uint8)
    projected = np.empty((len(vertices), 4, 2), dtype=np.float32)
    projected[:, :, 0] = (x + vertices[:, :, 0] * radius) * scale
    projected[:, :, 1] = (y - vertices[:, :, 1] * radius) * scale
    draw = ImageDraw.Draw(image, 'RGBA')
    for index in np.argsort(depth):
        draw.polygon([tuple(point) for point in projected[index]],
                     fill=tuple(int(v) for v in colors[index]) + (255,))


@lru_cache(maxsize=1)
def clutch() -> Mesh:
    mesh = MeshBuilder()
    cylinder(mesh, 0.90, -0.10, 0.09, (106, 126, 130), 40)
    ring(mesh, 0.68, 0.90, 0.09, (198, 207, 199), 40)
    ring(mesh, 0.30, 0.68, 0.10, (153, 169, 168), 40)
    cylinder(mesh, 0.30, 0.02, 0.21, (122, 144, 147), 32)
    ring(mesh, 0.13, 0.30, 0.21, (210, 221, 216), 32)
    cylinder(mesh, 0.13, 0.14, 0.21, (53, 75, 82), 32)
    return mesh.finish()
