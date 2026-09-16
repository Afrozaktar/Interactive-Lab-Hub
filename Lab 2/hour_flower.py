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

The flower's look has also been redesigned from the original rounded
ellipse petals: petals and leaves are now pointed, marquise/almond
shapes (base near the stem, tapering to a point), drawn in two layered
rows like a double-petaled blossom, with a small ring of "stamen" dots
around the center for texture.

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
STEM_COLOR = hsb(120, 60, 40)
LEAF_COLOR = hsb(120, 70, 55)
LEAF_STROKE = hsb(120, 80, 30)
CENTER_COLOR = hsb(45, 90, 80)
STAMEN_COLOR = hsb(30, 85, 60)

# Outer petal row (main blossom color).
PETAL_FILL = hsb(330, 55, 90)
PETAL_STROKE = hsb(330, 80, 45)
PETAL_HIGHLIGHT = hsb(330, 25, 97)

# Inner petal row -- a second, smaller layer offset between the outer
# petals, in a warmer accent shade, to give the blossom more depth than
# a single ring of petals.
INNER_PETAL_FILL = hsb(20, 70, 95)
INNER_PETAL_STROKE = hsb(20, 85, 55)

BUD_COLOR = hsb(120, 40, 50)
BUD_TIP_COLOR = hsb(120, 60, 30)
TEXT_COLOR = (230, 230, 230)


# ------------------------------------------------------------ geometry
def transform(lx, ly, angle, ox, oy):
    """Rotate local point (lx, ly) by angle (p5-style, y-down screen
    coords) then translate to (ox, oy) -- mirrors p5.js's rotate()+
    translate() matrix composition."""
    gx = lx * math.cos(angle) - ly * math.sin(angle)
    gy = lx * math.sin(angle) + ly * math.cos(angle)
    return (ox + gx, oy + gy)


def marquise_points(base_dist, length, width, angle, ox, oy, n=16):
    """Points for a pointed, almond/marquise-shaped leaf-or-petal: a
    base at distance `base_dist` from (ox, oy), tapering to a point
    `length` further out, `width` wide at its middle. Traced with
    x = (width/2) * sin(pi * t) so it pinches to zero width at both the
    base and the tip, then rotated by `angle` and placed at (ox, oy).
    Replaces the plain ellipse petals/leaves from the original sketch
    with a more traditional pointed petal silhouette."""
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
PETAL_COUNT = 8

HOURS_IN_CYCLE = 12.0   # 12-hour clock face cycle


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
    alternating sides, growing slightly with each one. Leaves are now
    pointed marquise shapes anchored on the stem instead of ellipses."""
    num_leaves = int(hour_value // 3) + 2
    for i in range(num_leaves):
        leaf_y = (80 * SCALE) + i * (15 * SCALE)
        side = -1 if i % 2 == 0 else 1
        anchor_x = cx + side * (4 * SCALE)
        anchor_y = cy + leaf_y
        leaf_angle = side * (1.0 + i * 0.08)   # tilts leaf away from stem
        leaf_len = (24 + i * 2.5) * SCALE
        leaf_w = (13 + i * 1.2) * SCALE

        stroke_pts = marquise_points(0, leaf_len * 1.08, leaf_w * 1.2,
                                      leaf_angle, anchor_x, anchor_y)
        draw.polygon(stroke_pts, fill=LEAF_STROKE)
        fill_pts = marquise_points(0, leaf_len, leaf_w,
                                    leaf_angle, anchor_x, anchor_y)
        draw.polygon(fill_pts, fill=LEAF_COLOR)


def draw_petal(draw, cx, cy, angle, petal_dist, cur_w, cur_h):
    """Outer petal: pointed marquise shape with a darker outline and a
    lighter inner highlight, replacing the original's rounded ellipse
    petal."""
    stroke_pts = marquise_points(petal_dist - cur_h * 0.06, cur_h * 1.12,
                                  cur_w * 1.2, angle, cx, cy)
    draw.polygon(stroke_pts, fill=PETAL_STROKE)

    fill_pts = marquise_points(petal_dist, cur_h, cur_w, angle, cx, cy)
    draw.polygon(fill_pts, fill=PETAL_FILL)

    hi_pts = marquise_points(petal_dist + cur_h * 0.18, cur_h * 0.5,
                              cur_w * 0.45, angle, cx, cy)
    draw.polygon(hi_pts, fill=PETAL_HIGHLIGHT)


def draw_inner_petal(draw, cx, cy, angle, petal_dist, cur_w, cur_h):
    """Inner petal row: smaller, offset between the outer petals, in a
    warmer accent color, for a layered double-blossom look."""
    stroke_pts = marquise_points(petal_dist - cur_h * 0.05, cur_h * 1.05,
                                  cur_w * 1.15, angle, cx, cy)
    draw.polygon(stroke_pts, fill=INNER_PETAL_STROKE)

    fill_pts = marquise_points(petal_dist, cur_h, cur_w, angle, cx, cy)
    draw.polygon(fill_pts, fill=INNER_PETAL_FILL)


def draw_center(draw, cx, cy, center_r, bloom):
    """Flower center: base disc plus a small ring of stamen dots for
    texture, instead of a single plain circle."""
    draw.ellipse((cx - center_r, cy - center_r, cx + center_r, cy + center_r),
                 fill=CENTER_COLOR)
    if bloom > 0.15:
        num_stamens = 6
        stamen_r = max(0.6, center_r * 0.22)
        ring_r = center_r * 1.35
        for i in range(num_stamens):
            t = 2 * math.pi * i / num_stamens + bloom * 0.6
            sx = cx + ring_r * math.cos(t)
            sy = cy + ring_r * math.sin(t)
            draw.ellipse((sx - stamen_r, sy - stamen_r,
                          sx + stamen_r, sy + stamen_r), fill=STAMEN_COLOR)


def draw_hours_flower(draw, cx, cy, hour_value):
    bloom = min(1.0, max(0.0, hour_value / (HOURS_IN_CYCLE - 1)))

    # Stem
    draw.line((cx, cy + STEM_TOP, cx, cy + STEM_BOTTOM),
              fill=STEM_COLOR, width=max(2, round(8 * SCALE)))

    # Leaves -- a new one every 3 hours
    draw_leaves(draw, cx, cy, hour_value)

    # Petal sizing, shared by both rows
    base_radius = FLOWER_SIZE * 0.3
    bloom_radius = FLOWER_SIZE * (0.3 + bloom * 0.4)
    petal_w = (20 + bloom * 15) * SCALE
    petal_h = (40 + bloom * 30) * SCALE
    petal_dist = base_radius + (bloom_radius - base_radius) * bloom
    cur_w = petal_w * (0.3 + 0.7 * bloom)
    cur_h = petal_h * (0.4 + 0.6 * bloom)

    # Inner row first (sits behind/between the outer petals), offset by
    # half a step so it peeks out between the outer petals.
    for i in range(PETAL_COUNT):
        angle = 2 * math.pi * (i + 0.5) / PETAL_COUNT
        draw_inner_petal(draw, cx, cy, angle,
                          petal_dist * 0.78, cur_w * 0.6, cur_h * 0.65)

    # Outer row
    for i in range(PETAL_COUNT):
        angle = 2 * math.pi * i / PETAL_COUNT
        draw_petal(draw, cx, cy, angle, petal_dist, cur_w, cur_h)

    # Flower center, drawn on top of the petal bases
    center_r = (6 + bloom * 15) * SCALE / 2
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
