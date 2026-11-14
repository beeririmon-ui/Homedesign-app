#!/usr/bin/env python3
"""
arrival_timeline.py: the kinematics of the arrival from the front door (storyboard S1), as numbers only:
where the door, the camera and the turn are at every moment, for each play version. No images, 0 var2 tokens.

  0 .. door_s            the door leaf swings open (an object: eases in and out, TR2 does not apply to it)
  cam_start ..           the camera leaves rest (a speed ramp of ramp_s) and walks D0 -> HD at one constant speed v
  then turn_s            the turn at HD, 65 degrees, without a stop: its angular speed starts at the image speed the
                         walk ends with and ends at the image speed the dolly starts with (ratio 1.0, QA window
                         0.85-1.15), and is smooth in between
  then                   the dolly HDx -> M0 at the same v, landing over the last land_m (the only slowing, TR2)
  hold_s                 stillness on M0 before the swap to the live layers

TR2 as recorded: one speed along the route, no slowing in mid-route; leaving rest at the start and the landing at the
end are the two ramps. The versions differ only in v and in the three durations; the frames come from the same clips.

  python3 arrival_timeline.py            # the table of the versions
  python3 arrival_timeline.py --fps 60 --version 7.3 --json out.json    # the state at every frame
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict

L1 = 4.938          # D0 -> HD, metres (7.40 - 2.462)
L2 = 3.872          # HDx -> M0, metres
TURN_DEG = 65.0
LAND_M = 0.36

# image speed per unit of camera speed, mean over the 16:9 frame, in frame widths:
#   K_WALK_END  per m/s, at the end of the walk (HD: the wall 1.662 m ahead fills the frame)
#   K_DOLLY_0   per m/s, at the start of the dolly (HDx)
#   K_TURN_0/1  per rad/s of yaw, at the start / end of the turn (the shift change included)
# Measured on the proxy house depth (proxy_house.py) by `measure_k`; to be re-measured on the clay depth of HD / HDx.
K = dict(walk_end=0.1954, dolly_0=0.1576, turn_0=0.7274, turn_1=0.6992)


def S(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ramp_dist(x: float) -> float:
    """Integral of S from 0 to x."""
    x = min(1.0, max(0.0, x))
    return x ** 3 - x ** 4 / 2


def smoother(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


@dataclass
class Version:
    name: str
    play_s: float
    door_s: float = 0.90
    cam_start: float = 0.35
    ramp_s: float = 0.50
    turn_s: float = 1.00
    hold_s: float = 0.20
    cut: bool = False                 # the version inside U5: a cut HD -> HDx in place of the turn
    v: float = 0.0                    # walking speed, m/s (solved from play_s)

    def __post_init__(self):
        turn = 0.0 if self.cut else self.turn_s
        # play_s = cam_start + ramp_s + (L1 - v ramp_s / 2) / v + turn + (L2 - LAND_M) / v + 2 LAND_M / v
        self.v = (L1 + L2 + LAND_M) / (self.play_s - self.cam_start - self.ramp_s / 2 - turn)
        self.t_walk_const = self.cam_start + self.ramp_s
        self.t_walk_end = self.t_walk_const + (L1 - self.v * self.ramp_s / 2) / self.v
        self.t_turn_end = self.t_walk_end + turn
        self.t_land = self.t_turn_end + (L2 - LAND_M) / self.v
        self.land_s = 2 * LAND_M / self.v
        self.t_end = self.t_land + self.land_s
        # the turn: w(x) = w0 + (w1 - w0) S(x) + A B(x), B = 16 x^2 (1-x)^2 (integral 8/15), degrees per second
        self.w0 = math.degrees(self.v * K["walk_end"] / K["turn_0"])
        self.w1 = math.degrees(self.v * K["dolly_0"] / K["turn_1"])
        self.A = 0.0 if self.cut else (TURN_DEG / self.turn_s - self.w0 - (self.w1 - self.w0) / 2) / (8 / 15)

    # -- pieces ----------------------------------------------------------------------------------------------
    def door_angle(self, t: float) -> float:
        return 90.0 * smoother(t / self.door_s)

    def s1(self, t: float) -> float:
        if t <= self.cam_start:
            return 0.0
        if t < self.t_walk_const:
            return self.v * self.ramp_s * ramp_dist((t - self.cam_start) / self.ramp_s)
        return min(L1, self.v * self.ramp_s / 2 + self.v * (t - self.t_walk_const))

    def turn_deg(self, t: float) -> float:
        if self.cut:
            return 0.0 if t < self.t_walk_end else TURN_DEG
        x = min(1.0, max(0.0, (t - self.t_walk_end) / self.turn_s))
        return self.turn_s * (self.w0 * x + (self.w1 - self.w0) * ramp_dist(x) + self.A * 16 * (x ** 3 / 3 - x ** 4 / 2 + x ** 5 / 5))

    def turn_speed(self, t: float) -> float:
        x = min(1.0, max(0.0, (t - self.t_walk_end) / self.turn_s))
        return self.w0 + (self.w1 - self.w0) * S(x) + self.A * 16 * x * x * (1 - x) ** 2

    def s2(self, t: float) -> float:
        if t <= self.t_turn_end:
            return 0.0
        if t < self.t_land:
            return self.v * (t - self.t_turn_end)
        y = 1 - min(1.0, (t - self.t_land) / self.land_s)
        return L2 - self.v * self.land_s * ramp_dist(y)

    def state(self, t: float) -> dict:
        """phase, door angle (deg), s1 (m along D0 -> HD), turn progress 0..1, s2 (m along HDx -> M0)."""
        if t < self.t_walk_end:
            ph = "door" if t < self.cam_start else ("door+walk" if t < self.door_s else "walk")
        elif t < self.t_turn_end:
            ph = "turn"
        elif t < self.t_end:
            ph = "dolly" if t < self.t_land else "landing"
        else:
            ph = "hold"
        return dict(t=round(t, 5), phase=ph, door=self.door_angle(t), s1=self.s1(t), turn=self.turn_deg(t) / TURN_DEG, s2=self.s2(min(t, self.t_end)))

    def frames(self, fps: float) -> list[dict]:
        n = int(round((self.t_end + self.hold_s) * fps)) + 1
        return [self.state(i / fps) for i in range(n)]

    def summary(self) -> dict:
        peak = max(self.turn_speed(self.t_walk_end + self.turn_s * i / 200) for i in range(201)) if not self.cut else 0.0
        return dict(name=self.name, play_s=round(self.t_end, 3), v_m_s=round(self.v, 3), door=[0.0, self.door_s],
                    camera_leaves_rest=[self.cam_start, round(self.t_walk_const, 3)], door_angle_when_camera_starts=round(self.door_angle(self.cam_start), 1),
                    walk_const=[round(self.t_walk_const, 3), round(self.t_walk_end, 3)],
                    turn=None if self.cut else [round(self.t_walk_end, 3), round(self.t_turn_end, 3)],
                    turn_speed_deg_s=None if self.cut else dict(start=round(self.w0, 1), peak=round(peak, 1), end=round(self.w1, 1)),
                    dolly_const=[round(self.t_turn_end, 3), round(self.t_land, 3)], landing=[round(self.t_land, 3), round(self.t_end, 3)],
                    hold_s=self.hold_s, cut=self.cut)


VERSIONS = {
    "7.3": Version("7.3", 7.3),
    "5.5": Version("5.5", 5.5, door_s=0.75, cam_start=0.25, ramp_s=0.40, turn_s=0.85),
    "7.3-cut": Version("7.3-cut", 6.3, cut=True),
    "5.5-cut": Version("5.5-cut", 4.65, door_s=0.75, cam_start=0.25, ramp_s=0.40, cut=True),
}


def measure_k(depth_hd, depth_hdx, grid=(192, 108)) -> dict:
    """The K table from the planar depth of the HD and HDx frames (arrays on the 16:9 frame, metres)."""
    import numpy as np
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    import camgeo as cg
    import cv2
    fr = cg.Canvas.frame(*grid)
    u, v = fr.uv()

    def walk(depth, cam):
        d = cv2.resize(np.where(np.isfinite(depth), depth, 50.0).astype(np.float32), grid, interpolation=cv2.INTER_NEAREST)
        r = np.hypot(u - cam.u0, (v - cam.v0) * 9 / 16)             # distance from the vanishing point, frame widths
        return float((r / d).mean())

    def turn(p):
        eps = 1e-3
        a = cg.lerp_cam(cg.HD, cg.HDX, p - eps if p > 0.5 else p)
        b = cg.lerp_cam(cg.HD, cg.HDX, p if p > 0.5 else p + eps)
        D = cg.rays(a, fr)
        dd, x = D @ b.f, D @ b.r
        ub = b.u0 + cg.KU * x / dd
        vb = b.v0 - cg.KV * D[..., 2] / dd
        dyaw = math.radians(abs(a.yaw - b.yaw))
        return float(np.hypot(ub - u, (vb - v) * 9 / 16).mean() / dyaw)

    return dict(walk_end=round(walk(depth_hd, cg.HD), 4), dolly_0=round(walk(depth_hdx, cg.HDX), 4), turn_0=round(turn(0.0), 4), turn_1=round(turn(1.0), 4))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", choices=sorted(VERSIONS))
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    if a.version and a.json:
        V = VERSIONS[a.version]
        with open(a.json, "w") as fh:
            json.dump(dict(version=V.summary(), fps=a.fps, frames=V.frames(a.fps)), fh)
        return 0
    print(json.dumps([V.summary() for V in VERSIONS.values()], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
