from __future__ import annotations

from functools import lru_cache

import mitsuba as mi
import numpy as np
from PIL import Image, ImageFilter


@lru_cache(maxsize=1)
def studio_reflection() -> np.ndarray:
    # A ray-traced aluminum sphere provides a stable studio-light lookup for
    # every animated frame. This works headlessly on the CPU, without a GPU.
    mi.set_variant('scalar_rgb')
    transform = mi.ScalarTransform4f

    def light(origin, size, color):
        return {
            'type': 'rectangle',
            'to_world': transform.look_at(origin=origin, target=[0,0,0], up=[0,1,0])
                        @ transform.scale(size),
            'emitter': {'type': 'area', 'radiance': {'type': 'rgb', 'value': color}},
        }

    scene = mi.load_dict({
        'type': 'scene',
        'integrator': {'type': 'direct'},
        'sensor': {
            'type': 'orthographic',
            'to_world': transform.look_at(origin=[0,0,4], target=[0,0,0], up=[0,1,0])
                        @ transform.scale([1.02,1.02,1]),
            'sampler': {'type': 'independent', 'sample_count': 64},
            'film': {'type': 'hdrfilm', 'width': 384, 'height': 384,
                     'pixel_format': 'rgb', 'rfilter': {'type': 'gaussian'}},
        },
        'environment': {'type': 'constant', 'radiance': {'type': 'rgb', 'value': [.10,.13,.15]}},
        'key': light([-2.4,3.1,3.8], [1.5,.7,1], [5.4,5.1,4.7]),
        'fill': light([2.6,1.0,3.3], [.65,1.6,1], [1.9,2.7,3.6]),
        'rim': light([-.4,-2.6,2.6], [1.8,.35,1], [1.1,1.5,1.8]),
        'sphere': {'type': 'sphere', 'bsdf': {'type': 'roughconductor', 'material': 'Al', 'alpha': .19}},
    })
    result = mi.render(scene, seed=31, spp=64)
    bitmap = mi.Bitmap(result).convert(mi.Bitmap.PixelFormat.RGB, mi.Struct.Type.UInt8, srgb_gamma=True)
    smooth = Image.fromarray(np.asarray(bitmap)).filter(ImageFilter.GaussianBlur(1.5))
    return np.asarray(smooth, dtype=np.uint8).copy()
