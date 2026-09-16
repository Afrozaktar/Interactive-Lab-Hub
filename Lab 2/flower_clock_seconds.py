#!/usr/bin/env python3
"""
flower_clock_seconds.py

Seconds portion of a Flower Clock, built for display on a Raspberry Pi.
Ported (best-effort, from the described logic) from the p5.js sketch at
https://github.com/khanlamiah019/the_flower_clock

Behavior:
    - A flower blooms (petals grow from the center outward) over the course
      of each 60-second minute.
    - At :00 the flower is fully closed (petal length ~ 0).
    - At :59 the flower is at full bloom (petal length = max).
    - The instant the minute rolls over (:00 again), the flower resets and
      starts blooming from scratch.

NOTE: This is a best-effort port. I could not fetch the actual contents of
your sketch.js (small/private repos aren't crawlable), so the exact petal
shape, count, colors, and easing curve here are my own interpretation of
"flower blooms over each second, restarts at 60". If you paste your real
sketch.js code, I can make this an exact 1:1 port.

Setup on the Raspberry Pi:
    sudo apt update
    sudo apt install python3-pip
    pip3 install pygame

Run:
    python3 flower_clock_seconds.py            # windowed
    python3 flower_clock_seconds.py --fullscreen   # fullscreen on the Pi display

Press ESC or close the window to quit.
"""

import sys
import math
import time
import argparse
import pygame


# ---------------------------------------------------------------- settings
NUM_PETALS = 12            # number of petals around the center
MAX_PETAL_LEN = 180        # px, length of a fully bloomed petal
PETAL_WIDTH = 40           # px, widest part of a fully bloomed petal
STEM_LEN = 160             # px
BG_COLOR = (15, 15, 20)
STEM_COLOR = (60, 140, 70)
CENTER_COLOR = (235, 180, 40)
PETAL_COLOR = (230, 90, 140)
TEXT_COLOR = (230, 230, 230)
FPS = 30


def bloom_progress(now=None):
    """
    Returns (seconds_elapsed_float, progress) for the CURRENT minute.
    seconds_elapsed_float includes the fractional second so the bloom grows
    smoothly instead of jumping once per second. progress is 0.0 at :00 and
    approaches 1.0 near :59.999.
    """
    now = now if now is not None else time.time()
    local = time.localtime(now)
    frac = now - math.floor(now)
    seconds_elapsed = local.tm_sec + frac
    progress = seconds_elapsed / 60.0
    return seconds_elapsed, progress


def eased(progress):
    """
    Ease linear 0..1 progress into a smooth blooming curve (quick growth
    early, settling into full bloom by the end of the minute) -- similar
    in spirit to the sin-based growth typical of these p5.js flower sketches.
    """
    return math.sin(progress * math.pi / 2)


def draw_flower(surface, cx, cy, progress):
    p = eased(progress)
    petal_len = MAX_PETAL_LEN * p

    # stem
    pygame.draw.line(surface, STEM_COLOR, (cx, cy), (cx, cy + STEM_LEN), 8)

    # petals, arranged radially around the center
    for i in range(NUM_PETALS):
        angle = (2 * math.pi / NUM_PETALS) * i - math.pi / 2
        tip_x = cx + math.cos(angle) * petal_len
        tip_y = cy + math.sin(angle) * petal_len

        perp = angle + math.pi / 2
        half_w = (PETAL_WIDTH / 2) * p  # petals widen as they bloom too

        base1 = (cx + math.cos(perp) * half_w, cy + math.sin(perp) * half_w)
        base2 = (cx - math.cos(perp) * half_w, cy - math.sin(perp) * half_w)

        mid_x = cx + math.cos(angle) * (petal_len * 0.6)
        mid_y = cy + math.sin(angle) * (petal_len * 0.6)
        mid1 = (mid_x + math.cos(perp) * half_w * 0.6,
                mid_y + math.sin(perp) * half_w * 0.6)
        mid2 = (mid_x - math.cos(perp) * half_w * 0.6,
                mid_y - math.sin(perp) * half_w * 0.6)

        if petal_len > 1:
            pygame.draw.polygon(
                surface, PETAL_COLOR,
                [base1, mid1, (tip_x, tip_y), mid2, base2],
            )

    # flower center
    center_r = 20 + 10 * p
    pygame.draw.circle(surface, CENTER_COLOR, (cx, cy), int(center_r))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fullscreen", action="store_true",
                         help="run fullscreen on the Pi's display")
    parser.add_argument("--width", type=int, default=480)
    parser.add_argument("--height", type=int, default=640)
    args = parser.parse_args()

    pygame.init()
    pygame.display.set_caption("Flower Clock - Seconds")
    flags = pygame.FULLSCREEN if args.fullscreen else 0
    screen = pygame.display.set_mode((args.width, args.height), flags)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)

    w, h = screen.get_size()
    cx, cy = w // 2, h // 2 - 40

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        seconds_elapsed, progress = bloom_progress()

        screen.fill(BG_COLOR)
        draw_flower(screen, cx, cy, progress)

        label = font.render(f"{int(seconds_elapsed):02d} / 60 sec", True, TEXT_COLOR)
        screen.blit(label, label.get_rect(center=(w // 2, h - 40)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
