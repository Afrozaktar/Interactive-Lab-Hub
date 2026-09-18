#!/usr/bin/env python3
"""
flower_clock_hours.py

Hour flower from Lamiah Khan's "Flower Clock"
(https://github.com/khanlamiah019/the_flower_clock), ported from p5.js to
run on the Adafruit Mini PiTFT - 135x240 Color TFT Add-on for Raspberry Pi
(ST7789, SPI): https://www.adafruit.com/product/4393

Adapted from the seconds-flower version: instead of blooming over a
60-second cycle, this flower blooms over a 12-hour cycle (like the hour
hand of a clock face). The bloom fraction is driven by
(hour % 12) + minutes/60 + seconds/3600, so the animation still moves
smoothly second-to-second instead of only updating once an hour. The
"new leaf" logic is scaled the same way: the original spawned a leaf
every 15 seconds (a quarter of 60); this spawns one every 3 hours (a
quarter of 12).

The flower is now styled as a sunflower: a single ring of narrow,
pointed yellow-orange ray petals around a large dark brown disc center,
with seed dots arranged in a Vogel/Fibonacci spiral (the same packing
pattern real sunflower seed heads use), and broad, dark-green
heart-shaped leaves.

--------------------------------------------------------------------------
ONE-TIME SETUP ON THE PI  (skip anything you've already done)
--------------------------------------------------------------------------
    sudo raspi-config          # Interface Options -> SPI -> Enable
    pip3 install adafruit-circuitpython-rgb-display pillow adafruit-blinka

    # If you hit "lgpio.error: 'GPIO busy'" on board.CE0, add this line to
    # /boot/firmware/config.txt under the [all] section, then reboot:
    #     dtoverlay=spi0-0cs

Run:
    python flower_clock_hours.py

    Use Ctrl+C to quit -- NOT Ctrl+Z. Ctrl+Z only suspends the process
    (it keeps holding the GPIO pins), which causes "GPIO busy" errors on
    the next run. Ctrl+C actually terminates it and releases the pins.
--------------------------------------------------------------------------
"""

import math
import time

import board
import digitalio
from PIL import Image, ImageDraw
import adafruit_rgb_display.st7789 as st7789


# ------------------------------------------------------- display setup
# CS/DC/RST pins and the width/height/offset values are Adafruit's own
# documented defaults for the Mini PiTFT 1.14" (135x240):
# https://learn.adafruit.com/adafruit-mini-pitft-135x240-color-tft-add-on-for-raspberry-pi/python-usage
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)
BAUDRATE = 24000000

spi = board.SPI()

disp = st7789.ST7789(
    spi,
    rotation=90,        # landscape
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
)

if disp.rotation % 180 == 90:
    WIDTH = disp.height   # 240
    HEIGHT = disp.width   # 135
else:
    WIDTH = disp.width
    HEIGHT = disp.height


# ---------------------------------------------------------------- colors
def hsb(h, s, b):
    """HSB/HSV (h: 0-360, s/b: 0-100) -> RGB (0-255). Same color model as
    p5.js's colorMode(HSB, 360, 100, 100), so the hue/sat/bright values
    below match the ones used in sketch.js directly."""
    h = (h % 360) / 60.0
    s /= 100.0
    b /= 100.0
    c = b * s
    x = c * (1 - abs(h % 2 - 1))
    m = b - c
    if 0 <= h < 1:
        r, g, bl = c, x, 0
    elif 1 <= h < 2:
        r, g, bl = x, c, 0
    elif 2 <= h < 3:
        r, g, bl = 0, c, x
    elif 3 <= h < 4:
        r, g, bl = 0, x, c
    elif 4 <= h < 5:
        r, g, bl = x, 0, c
    else:
        r, g, bl = c, 0, x
    return (round((r + m) * 255), round((g + m) * 255), round((bl + m) * 255))


def blend(fg, bg, alpha_pct):
    """Blend fg over bg at alpha_pct (0-100). Approximates p5.js's
    fill(..., alpha) transparency for the bud overlay, since Pillow's
    ImageDraw doesn't alpha-composite onto a plain RGB image."""
    a = max(0.0, min(1.0, alpha_pct / 100.0))
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3))


BG_COLOR = hsb(220, 20, 15)          # same dark background as sketch.js
STEM_COLOR = hsb(100, 55, 40)
LEAF_COLOR = hsb(100, 70, 40)
LEAF_STROKE = hsb(100, 80, 22)

# Sunflower disc center: dark brown, with slightly darker seed dots
# arranged in a spiral.
CENTER_COLOR = hsb(30, 65, 35)
CENTER_EDGE_COLOR = hsb(35, 75, 55)
SEED_COLOR = hsb(25, 75, 18)

# Ray petals: warm yellow-orange, narrow and pointed.
PETAL_FILL = hsb(46, 90, 98)
PETAL_STROKE = hsb(38, 95, 65)
PETAL_HIGHLIGHT = hsb(52, 45, 100)

BUD_COLOR = hsb(100, 45, 45)
BUD_TIP_COLOR = hsb(100, 60, 28)
TEXT_COLOR = (230, 230, 230)


# ------------------------------------------------------------ geometry
def transform(lx, ly, angle, ox, oy):
    """Rotate local point (lx, ly) by angle (p5-style, y-down screen
    coords) then translate to (ox, oy) -- mirrors p5.js's rotate()+
    translate() matrix composition."""
    gx = lx * math.cos(angle) - ly * math.sin(angle)
    gy = lx * math.sin(angle) + ly * math.cos(angle)
    return (ox + gx, oy + gy)


def marquise_points(base_dist, length, width, angle, ox, oy, n=10):
    """Points for a pointed, almond/marquise-shaped leaf-or-petal: a
    base at distance `base_dist` from (ox, oy), tapering to a point
    `length` further out, `width` wide at its middle. Traced with
    x = (width/2) * sin(pi * t) so it pinches to zero width at both the
    base and the tip, then rotated by `angle` and placed at (ox, oy)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        lx = (width / 2) * math.sin(math.pi * t)
        ly = -(base_dist + length * t)
        pts.append(transform(lx, ly, angle, ox, oy))
    for i in range(n + 1):
        t = 1 - i / n
        lx = -(width / 2) * math.sin(math.pi * t)
        ly = -(base_dist + length * t)
        pts.append(transform(lx, ly, angle, ox, oy))
    return pts


# ---------------------------------------------------------------- scale
# sketch.js's hour flower was drawn at size=60 with a ~130px stem on
# an 800x600 canvas. Scaled down to fit this display's 240x135 area.
SCALE = 0.42
FLOWER_SIZE = 60 * SCALE
STEM_TOP = 20 * SCALE
STEM_BOTTOM = 150 * SCALE
PETAL_COUNT = 16   # sunflowers read best with a dense single ring

HOURS_IN_CYCLE = 12.0   # 12-hour clock face cycle
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))   # ~137.5 degrees, seed spiral


def bloom_progress(now=None):
    """Returns hours elapsed in the current 12-hour cycle, as a float
    (e.g. 7.5 = half past 7), so the bloom advances smoothly instead of
    jumping once per hour."""
    now = now if now is not None else time.time()
    local = time.localtime(now)
    frac_of_hour = (local.tm_min * 60 + local.tm_sec) / 3600.0
    hour_12 = local.tm_hour % 12
    return hour_12 + frac_of_hour


def percent_left_to_next_hour(now=None):
    """Returns 0-100: how much of the current hour is still remaining
    (100 = the hour just started, 0 = about to roll over)."""
    now = now if now is not None else time.time()
    local = time.localtime(now)
    frac_of_hour_elapsed = (local.tm_min * 60 + local.tm_sec) / 3600.0
    return (1.0 - frac_of_hour_elapsed) * 100.0


def draw_leaves(draw, cx, cy, hour_value):
    """A new leaf every 3 hours (a quarter of the 12-hour cycle, scaled
    from the original's "every 15 seconds" -- a quarter of 60),
    alternating sides, growing slightly with each one. Leaves are broad
    and heart-shaped, like a real sunflower's foliage."""
    num_leaves = int(hour_value // 3) + 2
    for i in range(num_leaves):
        leaf_y = (78 * SCALE) + i * (16 * SCALE)
        side = -1 if i % 2 == 0 else 1
        anchor_x = cx + side * (4 * SCALE)
        anchor_y = cy + leaf_y
        leaf_angle = side * (0.85 + i * 0.06)
        leaf_len = (30 + i * 3) * SCALE
        leaf_w = (22 + i * 2) * SCALE   # wide relative to length = broad leaf

        stroke_pts = marquise_points(0, leaf_len * 1.06, leaf_w * 1.15,
                                      leaf_angle, anchor_x, anchor_y)
        draw.polygon(stroke_pts, fill=LEAF_STROKE)
        fill_pts = marquise_points(0, leaf_len, leaf_w,
                                    leaf_angle, anchor_x, anchor_y)
        draw.polygon(fill_pts, fill=LEAF_COLOR)


def draw_petal(draw, cx, cy, angle, petal_dist, cur_w, cur_h):
    """Ray petal: long, narrow, pointed, with a darker outline and a
    lighter streak near the base -- like a sunflower's ray florets."""
    stroke_pts = marquise_points(petal_dist - cur_h * 0.04, cur_h * 1.08,
                                  cur_w * 1.15, angle, cx, cy)
    draw.polygon(stroke_pts, fill=PETAL_STROKE)

    fill_pts = marquise_points(petal_dist, cur_h, cur_w, angle, cx, cy)
    draw.polygon(fill_pts, fill=PETAL_FILL)

    hi_pts = marquise_points(petal_dist + cur_h * 0.05, cur_h * 0.45,
                              cur_w * 0.35, angle, cx, cy)
    draw.polygon(hi_pts, fill=PETAL_HIGHLIGHT)


def draw_center(draw, cx, cy, center_r, bloom):
    """Large sunflower disc: a dark brown center with a slightly lighter
    rim, and seeds packed in a Vogel/Fibonacci spiral (the same
    arrangement real sunflower heads use) that fills in as it blooms."""
    draw.ellipse((cx - center_r, cy - center_r, cx + center_r, cy + center_r),
                 fill=CENTER_EDGE_COLOR)
    inner_r = center_r * 0.9
    draw.ellipse((cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
                 fill=CENTER_COLOR)

    num_seeds = int(bloom * 55) + 4
    seed_r = max(0.5, center_r * 0.11)
    for i in range(num_seeds):
        frac = i / max(1, num_seeds - 1)
        r = inner_r * 0.92 * math.sqrt(frac)
        theta = i * GOLDEN_ANGLE
        sx = cx + r * math.cos(theta)
        sy = cy + r * math.sin(theta)
        draw.ellipse((sx - seed_r, sy - seed_r, sx + seed_r, sy + seed_r),
                     fill=SEED_COLOR)


def draw_hours_flower(draw, cx, cy, hour_value):
    bloom = min(1.0, max(0.0, hour_value / (HOURS_IN_CYCLE - 1)))

    # Stem
    draw.line((cx, cy + STEM_TOP, cx, cy + STEM_BOTTOM),
              fill=STEM_COLOR, width=max(2, round(9 * SCALE)))

    # Leaves -- a new one every 3 hours
    draw_leaves(draw, cx, cy, hour_value)

    # Ray petals -- long and narrow, single ring
    base_radius = FLOWER_SIZE * 0.32
    bloom_radius = FLOWER_SIZE * (0.32 + bloom * 0.32)
    petal_w = (10 + bloom * 7) * SCALE
    petal_h = (46 + bloom * 34) * SCALE
    petal_dist = base_radius + (bloom_radius - base_radius) * bloom
    cur_w = petal_w * (0.35 + 0.65 * bloom)
    cur_h = petal_h * (0.4 + 0.6 * bloom)

    for i in range(PETAL_COUNT):
        angle = 2 * math.pi * i / PETAL_COUNT
        draw_petal(draw, cx, cy, angle, petal_dist, cur_w, cur_h)

    # Sunflower disc, large relative to the whole flower
    center_r = (14 + bloom * 20) * SCALE
    draw_center(draw, cx, cy, center_r, bloom)

    # Bud overlay while mostly closed -- fades out as it blooms
    if bloom < 0.3:
        alpha = (1 - bloom * 3) * 80
        rx, ry = (25 * SCALE) / 2, (45 * SCALE) / 2
        by = cy - 10 * SCALE
        draw.ellipse((cx - rx, by - ry, cx + rx, by + ry),
                     fill=blend(BUD_COLOR, BG_COLOR, alpha))

        alpha_tip = (1 - bloom * 3) * 90
        rx2, ry2 = (15 * SCALE) / 2, (20 * SCALE) / 2
        by2 = cy - 25 * SCALE
        draw.ellipse((cx - rx2, by2 - ry2, cx + rx2, by2 + ry2),
                     fill=blend(BUD_TIP_COLOR, BG_COLOR, alpha_tip))


def main():
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    cx = WIDTH // 2
    cy = 40   # flower head near the top; stem + leaves hang below it

    while True:
        hours_elapsed = bloom_progress()
        pct_left = percent_left_to_next_hour()
        local = time.localtime()

        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=BG_COLOR)
        draw_hours_flower(draw, cx, cy, hours_elapsed)
        draw.text((4, HEIGHT - 22),
                   time.strftime("%I:%M:%S", local), fill=TEXT_COLOR)
        draw.text((4, HEIGHT - 12),
                   f"{pct_left:.0f}% to next hour", fill=TEXT_COLOR)

        disp.image(image)
        time.sleep(1 / 15)   # Adafruit measured ~15 FPS max on this display


if __name__ == "__main__":
    main()
