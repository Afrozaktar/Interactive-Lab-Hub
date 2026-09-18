#!/usr/bin/env python3
"""
flower_clock_hours.py

Blossom Hour Flower

A 12-petal flower clock. The flower has 12 petals representing
a 12-hour half-day cycle, and is in full bloom (all 12 petals)
at 00:00 (midnight) and again at 12:00:00 (noon).

00:00  -> 12 petals (full bloom)
01:00  -> first petal falls
02:00  -> second petal falls
...
11:00  -> 11th petal falls
12:00  -> resets to 12 petals (full bloom)
13:00  -> first petal falls again
...
23:00  -> 11th petal falls
00:00  -> resets to 12 petals (full bloom)

HOW THE CURRENT-HOUR PETAL FALLS
-------------------------------------------------------------
Every STEP_SECONDS (4s), one big, clearly-visible chunk breaks
off the tip of the petal still attached to the flower:

  - The chunk starts BIG while it's in the air, so it's
    unmistakable that something just fell.
  - As it flies down toward the ground, it shrinks, ending up
    exactly the (much smaller) size the growing floor petal
    will be at that moment - so it visually "merges" into the
    pile instead of just popping into place.
  - After a full hour, the flower-side petal has completely
    eroded away and the ground-side petal has grown to its
    full, final size - joining the pile of already-fallen
    petals from earlier hours.

SUN / MOON
-------------------------------------------------------------
A small sun arcs across the top of the screen from sunrise
(5am) to sunset (8pm), sinking lower as evening approaches. By
night (8pm - 5am) the sun is gone and a crescent moon arcs
across the same path instead.

THE FLOWER ITSELF
-------------------------------------------------------------
A sunflower with big, rounded oval petals (not sharp points)
in a warm yellow-orange gradient, and a classic brown seeded
center with a Fibonacci packing pattern. Leaves are two-tone
green with a simple center vein.

Background color by time of day: black at night, white in the
morning/daytime, grey in the evening.
"""

import math
import time

import board
import digitalio
from PIL import Image, ImageDraw
import adafruit_rgb_display.st7789 as st7789


# -------------------------------------------------------
# DISPLAY SETUP
# -------------------------------------------------------

cs_pin = digitalio.DigitalInOut(board.D5)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)

BAUDRATE = 24000000

spi = board.SPI()

disp = st7789.ST7789(
    spi,
    rotation=90,
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
    WIDTH = disp.height
    HEIGHT = disp.width
else:
    WIDTH = disp.width
    HEIGHT = disp.height


# -------------------------------------------------------
# COLOR HELPERS
# -------------------------------------------------------

def hsb(h, s, b):
    """Convert HSB/HSV to RGB."""

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

    return (
        round((r + m) * 255),
        round((g + m) * 255),
        round((bl + m) * 255),
    )


def lerp_color(c1, c2, t):
    """Linearly interpolate between two (r, g, b) colors."""

    t = max(0.0, min(1.0, t))

    return tuple(
        round(c1[i] + (c2[i] - c1[i]) * t)
        for i in range(3)
    )


def lerp(a, b, t):
    return a + (b - a) * t


def hex_to_rgb(hex_str):
    """Convert a '#RRGGBB' string to an (r, g, b) tuple."""

    hex_str = hex_str.lstrip("#")

    return tuple(
        int(hex_str[i:i + 2], 16)
        for i in (0, 2, 4)
    )


# -------------------------------------------------------
# SKY / BACKGROUND COLORS
# -------------------------------------------------------
#
#  8:00 PM - 4:59:59 AM  -> black   (night, moon is out)
#  5:00 AM - 5:59:59 PM  -> white   (morning / daytime, sun is out)
#  6:00 PM - 7:59:59 PM  -> grey    (evening, sun is setting)

NIGHT_SKY_COLOR   = hex_to_rgb("#000000")
MORNING_SKY_COLOR = hex_to_rgb("#FFFFFF")
EVENING_SKY_COLOR = hex_to_rgb("#808080")


def get_sky_color(hour_value):
    """
    Return the sky/background color for the given hour_value
    (hours elapsed since midnight, 0.0 - 24.0).
    """

    h = hour_value % 24

    if h >= 20 or h < 5:
        return NIGHT_SKY_COLOR
    elif h < 18:
        return MORNING_SKY_COLOR
    else:
        return EVENING_SKY_COLOR


def get_text_color(bg_rgb):
    """
    Pick readable text color (light or dark) based on the
    brightness of the current background color.
    """

    luminance = (
        0.299 * bg_rgb[0]
        + 0.587 * bg_rgb[1]
        + 0.114 * bg_rgb[2]
    )

    if luminance > 140:
        return (25, 25, 25)
    else:
        return (230, 230, 230)


# -------------------------------------------------------
# SUN / MOON
# -------------------------------------------------------
#
# The sun is up from 5am to 8pm, arcing across the top of the
# screen and sinking toward the horizon as it nears 8pm. The
# moon takes over for the rest of the night, following the same
# arc shape.

SUN_START_HOUR = 5.0
SUN_END_HOUR = 20.0
SUN_SPAN_HOURS = SUN_END_HOUR - SUN_START_HOUR

NIGHT_SPAN_HOURS = 24.0 - SUN_SPAN_HOURS

SKY_BODY_Y_HIGH = 10.0   # near the top of the screen (midday/midnight)
SKY_BODY_Y_LOW = 30.0    # near the horizon (sunrise/sunset)
SKY_BODY_MARGIN = 16.0   # keep the sun/moon off the very edges

SUN_COLOR = hsb(45, 85, 100)
SUN_GLOW_COLOR = hsb(45, 60, 100)
MOON_COLOR = hex_to_rgb("#E7E8F5")
MOON_CRATER_COLOR = hex_to_rgb("#C7C9DE")


def _sky_body_position(t):
    """
    Shared arc for both the sun and the moon: t=0 is "just
    risen" (low, on the left), t=1 is "about to set" (low, on
    the right), t=0.5 is the highest point of the arc.
    """

    t = max(0.0, min(1.0, t))

    x = SKY_BODY_MARGIN + t * (WIDTH - 2 * SKY_BODY_MARGIN)

    y = (
        SKY_BODY_Y_LOW
        - (SKY_BODY_Y_LOW - SKY_BODY_Y_HIGH) * math.sin(math.pi * t)
    )

    return x, y


def draw_sun(draw, hours_elapsed, sky_color):
    """Draw the sun somewhere along its daytime arc."""

    t = (hours_elapsed - SUN_START_HOUR) / SUN_SPAN_HOURS
    x, y = _sky_body_position(t)

    r = 8.0

    # Soft glow, blended toward the sky so it doesn't look like
    # a flat colored square on white or grey backgrounds.
    glow_r = r * 2.0
    glow_color = lerp_color(SUN_GLOW_COLOR, sky_color, 0.55)

    draw.ellipse(
        (x - glow_r, y - glow_r, x + glow_r, y + glow_r),
        fill=glow_color
    )

    draw.ellipse(
        (x - r, y - r, x + r, y + r),
        fill=SUN_COLOR
    )

    # A handful of simple rays for a classic sun look.
    for i in range(8):

        ray_angle = i * (math.pi / 4)

        rx1 = x + math.cos(ray_angle) * (r + 2)
        ry1 = y + math.sin(ray_angle) * (r + 2)
        rx2 = x + math.cos(ray_angle) * (r + 6)
        ry2 = y + math.sin(ray_angle) * (r + 6)

        draw.line((rx1, ry1, rx2, ry2), fill=SUN_COLOR, width=1)


def draw_moon(draw, hours_elapsed, sky_color):
    """Draw a crescent moon somewhere along its nighttime arc."""

    # Hours since the sun set (8pm), wrapping past midnight.
    night_hours = (hours_elapsed - SUN_END_HOUR) % 24.0
    t = night_hours / NIGHT_SPAN_HOURS
    x, y = _sky_body_position(t)

    r = 7.0

    draw.ellipse(
        (x - r, y - r, x + r, y + r),
        fill=MOON_COLOR
    )

    # Crescent "bite" - an overlapping circle painted in the
    # sky color, offset to one side.
    bite_r = r * 0.88
    bite_offset = r * 0.62

    draw.ellipse(
        (
            x - bite_r + bite_offset,
            y - bite_r,
            x + bite_r + bite_offset,
            y + bite_r
        ),
        fill=sky_color
    )

    # A couple of small craters for a bit of texture.
    draw.ellipse(
        (x - r * 0.55, y - r * 0.2, x - r * 0.25, y + r * 0.1),
        fill=MOON_CRATER_COLOR
    )

    draw.ellipse(
        (x - r * 0.15, y - r * 0.6, x + r * 0.05, y - r * 0.35),
        fill=MOON_CRATER_COLOR
    )


# -------------------------------------------------------
# FLOWER COLORS (blush-pink blossom)
# -------------------------------------------------------

STEM_COLOR = hsb(100, 55, 40)

LEAF_BASE_COLOR = hsb(98, 78, 30)
LEAF_TIP_COLOR = hsb(104, 60, 50)
LEAF_STROKE = hsb(98, 85, 17)
LEAF_VEIN_COLOR = hsb(100, 35, 62)

# Petals - classic sunflower yellow-orange gradient
PETAL_BASE_COLOR = hsb(28, 85, 90)
PETAL_FILL = hsb(45, 88, 99)
PETAL_TIP_COLOR = hsb(52, 30, 100)
PETAL_STROKE = hsb(32, 90, 52)

FALLEN_PETAL_BASE = PETAL_BASE_COLOR
FALLEN_PETAL_FILL = PETAL_FILL
FALLEN_PETAL_STROKE = PETAL_STROKE

# Falling chunk (reuses the petal palette so it reads as "part
# of the flower")
SHARD_FILL = PETAL_FILL
SHARD_STROKE = PETAL_STROKE

# Center - classic sunflower brown disc with a Fibonacci seed
# pattern, 3-ring gradient for a bit of depth
CENTER_OUTER_RING = hsb(34, 78, 58)
CENTER_MID_RING = hsb(30, 70, 40)
CENTER_INNER_RING = hsb(26, 62, 28)
CENTER_SHADOW = hsb(20, 40, 12)
SEED_COLOR_A = hsb(22, 78, 19)
SEED_COLOR_B = hsb(27, 68, 25)
SEED_SPARKLE = hsb(38, 35, 58)


# -------------------------------------------------------
# GEOMETRY
# -------------------------------------------------------

def transform(lx, ly, angle, ox, oy):
    """Rotate and translate a point."""

    gx = lx * math.cos(angle) - ly * math.sin(angle)
    gy = lx * math.sin(angle) + ly * math.cos(angle)

    return (ox + gx, oy + gy)


def petal_ellipse_points(rx, ry, base_dist, angle, ox, oy, n=16):
    """
    A rounded (ellipse) petal shape. The near edge of the
    ellipse always sits exactly at base_dist from (ox, oy), no
    matter how big or small rx/ry are - so a petal always stays
    visually attached at the same point as it grows or shrinks.
    """

    center_local_y = -(base_dist + ry)

    pts = []

    for i in range(n):

        theta = 2 * math.pi * i / n

        lx = rx * math.cos(theta)
        ly = center_local_y + ry * math.sin(theta)

        pts.append(transform(lx, ly, angle, ox, oy))

    return pts


def rotated_ellipse_points(rx, ry, angle, ox, oy, n=14):
    """A simple rotated ellipse centered exactly at (ox, oy)."""

    pts = []

    for i in range(n):

        theta = 2 * math.pi * i / n

        lx = rx * math.cos(theta)
        ly = ry * math.sin(theta)

        pts.append(transform(lx, ly, angle, ox, oy))

    return pts


def marquise_points(base_dist, length, width, angle, ox, oy, n=14):
    """
    A pointed almond/marquise shape - used for the leaves,
    which still look good with a pointed profile.
    """

    pts = []

    for i in range(n + 1):

        t = i / n

        lx = width / 2 * math.sin(math.pi * t)
        ly = -(base_dist + length * t)

        pts.append(transform(lx, ly, angle, ox, oy))

    for i in range(n + 1):

        t = 1 - i / n

        lx = -(width / 2 * math.sin(math.pi * t))
        ly = -(base_dist + length * t)

        pts.append(transform(lx, ly, angle, ox, oy))

    return pts


def petal_jitter(index):
    """
    A small, deterministic per-petal variation in width/tilt
    so the flower doesn't look like a perfectly robotic
    12-gon. Same index always gives the same jitter, so the
    flower doesn't "wobble" between frames.
    """

    width_jitter = 1.0 + 0.07 * math.sin(index * 2.399963)
    tilt_jitter = 0.05 * math.sin(index * 1.713 + 1.1)

    return width_jitter, tilt_jitter


# -------------------------------------------------------
# SCALE
# -------------------------------------------------------

SCALE = 0.42

STEM_TOP = 20 * SCALE
STEM_BOTTOM = 150 * SCALE

# 12 petals: full bloom at midnight (0:00) and noon (12:00),
# one petal falls per hour through each 12-hour half of the day.
PETAL_COUNT = 12

GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))

# -------------------------------------------------------
# STEPPED-EROSION SETTINGS
# -------------------------------------------------------
#
# The currently-falling petal loses one big, visible chunk
# every STEP_SECONDS. The chunk itself is drawn BIG while in
# flight and shrinks down to the (tiny) size the floor pile
# actually grows by, so it visually "merges" on landing rather
# than just popping into place.

STEP_SECONDS = 4
STEPS_PER_HOUR = 3600 // STEP_SECONDS

SHARD_FLIGHT_SECONDS = 1.0

# The on-flower petal's SIZE (both width and height, shrinking
# together so it reads as "getting smaller" rather than just
# "getting shorter") updates in bigger, clearly-visible notches
# instead of the same fine 4-second grain as the chunk falls -
# a single 1/900th shrink is too small to notice on a small
# petal, but a 1/10th jump every few minutes is obvious.
FLOWER_NOTCHES_PER_HOUR = 10
FLOWER_NOTCH_SECONDS = 3600 // FLOWER_NOTCHES_PER_HOUR


# -------------------------------------------------------
# TIME
# -------------------------------------------------------

def day_progress(now=None):
    """
    Return hours elapsed since midnight.

    00:00 -> 0.0
    06:30 -> 6.5
    12:00 -> 12.0
    23:59 -> ~24.0
    """

    if now is None:
        now = time.time()

    local = time.localtime(now)

    seconds_today = (
        local.tm_hour * 3600
        + local.tm_min * 60
        + local.tm_sec
    )

    return seconds_today / 3600.0


def half_day_progress(hour_value):
    """
    Return hours elapsed since the most recent 12-hour mark
    (midnight or noon).
    """

    return hour_value % 12


# -------------------------------------------------------
# LEAVES
# -------------------------------------------------------

def draw_leaves(draw, cx, cy, hour_value):
    """
    Draw leaves. Count is kept low (max 4) so the flower
    silhouette stays clear. Each leaf is two-tone with a simple
    center vein.
    """

    num_leaves = min(int(hour_value // 4) + 1, 4)

    for i in range(num_leaves):

        leaf_y = 78 * SCALE + i * (16 * SCALE)
        side = -1 if i % 2 == 0 else 1

        anchor_x = cx + side * (4 * SCALE)
        anchor_y = cy + leaf_y

        leaf_angle = side * (0.85 + i * 0.06)
        leaf_len = (30 + i * 3) * SCALE
        leaf_w = (22 + i * 2) * SCALE

        stroke_pts = marquise_points(
            0, leaf_len * 1.06, leaf_w * 1.15,
            leaf_angle, anchor_x, anchor_y
        )
        draw.polygon(stroke_pts, fill=LEAF_STROKE)

        base_pts = marquise_points(
            0, leaf_len, leaf_w,
            leaf_angle, anchor_x, anchor_y
        )
        draw.polygon(base_pts, fill=LEAF_BASE_COLOR)

        tip_pts = marquise_points(
            leaf_len * 0.35, leaf_len * 0.65, leaf_w * 0.85,
            leaf_angle, anchor_x, anchor_y
        )
        draw.polygon(tip_pts, fill=LEAF_TIP_COLOR)

        vein_start = transform(0, -leaf_len * 0.08, leaf_angle, anchor_x, anchor_y)
        vein_end = transform(0, -leaf_len * 0.92, leaf_angle, anchor_x, anchor_y)
        draw.line((vein_start, vein_end), fill=LEAF_VEIN_COLOR, width=1)


# -------------------------------------------------------
# PETALS (rounded / blossom style)
# -------------------------------------------------------

def draw_petal(
    draw,
    cx,
    cy,
    angle,
    petal_dist,
    cur_w,
    cur_h,
    jitter=(1.0, 0.0)
):
    """
    Draw one rounded blossom petal, still attached to the
    flower. Layered as: deeper pink outline -> blush base ->
    light pink mid fill -> near-white tip highlight.
    """

    if cur_h <= 0.5:
        return

    width_jitter, tilt_jitter = jitter
    angle = angle + tilt_jitter
    cur_w = cur_w * width_jitter

    outline_pts = petal_ellipse_points(
        cur_w * 0.58, cur_h * 0.54,
        petal_dist - cur_h * 0.02, angle, cx, cy
    )
    draw.polygon(outline_pts, fill=PETAL_STROKE)

    base_pts = petal_ellipse_points(
        cur_w * 0.5, cur_h * 0.5,
        petal_dist, angle, cx, cy
    )
    draw.polygon(base_pts, fill=PETAL_BASE_COLOR)

    fill_pts = petal_ellipse_points(
        cur_w * 0.42, cur_h * 0.42,
        petal_dist + cur_h * 0.1, angle, cx, cy
    )
    draw.polygon(fill_pts, fill=PETAL_FILL)

    hi_pts = petal_ellipse_points(
        cur_w * 0.22, cur_h * 0.16,
        petal_dist + cur_h * 0.72, angle, cx, cy, n=12
    )
    draw.polygon(hi_pts, fill=PETAL_TIP_COLOR)


def draw_fallen_petal(draw, x, y, angle, size):
    """
    Draw a small rounded petal resting on the ground. 'size' is
    0.0 - 1.0: a fully-fallen petal from an earlier hour is
    size=1.0, while the petal currently forming grows toward
    1.0 as chunks land on it.
    """

    if size <= 0.02:
        return

    width = 18 * SCALE * size
    height = 21 * SCALE * size

    outline_pts = petal_ellipse_points(
        width * 0.58, height * 0.54, 0, angle, x, y
    )
    draw.polygon(outline_pts, fill=FALLEN_PETAL_STROKE)

    base_pts = petal_ellipse_points(
        width * 0.5, height * 0.5, 0, angle, x, y
    )
    draw.polygon(base_pts, fill=FALLEN_PETAL_BASE)

    fill_pts = petal_ellipse_points(
        width * 0.42, height * 0.42, height * 0.1, angle, x, y
    )
    draw.polygon(fill_pts, fill=FALLEN_PETAL_FILL)


# -------------------------------------------------------
# FALLING CHUNK (big while flying, shrinks to merge on landing)
# -------------------------------------------------------

def spawn_shard(
    shards,
    start_pos,
    end_pos,
    base_angle,
    start_w,
    start_h,
    end_w,
    end_h,
    now
):
    """
    Add a new chunk that flies from start_pos to end_pos over
    SHARD_FLIGHT_SECONDS, shrinking from (start_w, start_h) down
    to (end_w, end_h) as it goes - so it lands already matching
    the size the floor petal needs, and visually merges into it.
    """

    shards.append({
        "start": start_pos,
        "end": end_pos,
        "base_angle": base_angle,
        "start_w": start_w,
        "start_h": start_h,
        "end_w": end_w,
        "end_h": end_h,
        "start_time": now,
        "duration": SHARD_FLIGHT_SECONDS,
    })


def draw_shard_shape(draw, x, y, angle, width, height):
    """A simple two-layer rounded chunk (outline + fill)."""

    outline_pts = rotated_ellipse_points(
        width * 0.58, height * 0.58, angle, x, y, n=12
    )
    draw.polygon(outline_pts, fill=SHARD_STROKE)

    fill_pts = rotated_ellipse_points(
        width * 0.5, height * 0.5, angle, x, y, n=12
    )
    draw.polygon(fill_pts, fill=SHARD_FILL)


def update_and_draw_shards(draw, shards, now):
    """
    Draw every chunk currently in flight (shrinking from big to
    small as it travels), and return the list of chunks that
    haven't landed yet.
    """

    still_flying = []

    for shard in shards:

        elapsed = now - shard["start_time"]
        t = elapsed / shard["duration"]

        if t >= 1.0:
            # Landed - it has already shrunk to match the floor
            # petal's size, so it simply merges in and vanishes.
            continue

        t_smooth = t * t * (3 - 2 * t)

        x = lerp(shard["start"][0], shard["end"][0], t_smooth)
        y = lerp(shard["start"][1], shard["end"][1], t_smooth)

        w = lerp(shard["start_w"], shard["end_w"], t_smooth)
        h = lerp(shard["start_h"], shard["end_h"], t_smooth)

        spin_angle = shard["base_angle"] + t * math.pi * 1.3

        draw_shard_shape(draw, x, y, spin_angle, w, h)

        still_flying.append(shard)

    return still_flying


# -------------------------------------------------------
# FLOWER CENTER
# -------------------------------------------------------

def draw_center(draw, cx, cy, center_r):
    """
    Draw a classic sunflower center: a soft shadow, a 3-ring
    brown gradient disc, and a Fibonacci seed pattern with
    alternating tones plus a few sparkle highlights.
    """

    shadow_r = center_r * 1.08

    draw.ellipse(
        (
            cx - shadow_r + 1, cy - shadow_r + 2,
            cx + shadow_r + 1, cy + shadow_r + 2
        ),
        fill=CENTER_SHADOW
    )

    draw.ellipse(
        (cx - center_r, cy - center_r, cx + center_r, cy + center_r),
        fill=CENTER_OUTER_RING
    )

    mid_r = center_r * 0.82

    draw.ellipse(
        (cx - mid_r, cy - mid_r, cx + mid_r, cy + mid_r),
        fill=CENTER_MID_RING
    )

    inner_r = center_r * 0.62

    draw.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        fill=CENTER_INNER_RING
    )

    num_seeds = 55
    seed_r = max(0.5, center_r * 0.11)

    for i in range(num_seeds):

        frac = i / max(1, num_seeds - 1)
        r = center_r * 0.92 * math.sqrt(frac)
        theta = i * GOLDEN_ANGLE

        sx = cx + r * math.cos(theta)
        sy = cy + r * math.sin(theta)

        seed_color = SEED_COLOR_A if i % 2 == 0 else SEED_COLOR_B

        draw.ellipse(
            (sx - seed_r, sy - seed_r, sx + seed_r, sy + seed_r),
            fill=seed_color
        )

        if i % 7 == 0:

            sparkle_r = seed_r * 0.4

            draw.ellipse(
                (
                    sx - sparkle_r * 1.4, sy - sparkle_r * 1.4,
                    sx - sparkle_r * 0.4, sy - sparkle_r * 0.4
                ),
                fill=SEED_SPARKLE
            )


# -------------------------------------------------------
# STATIC PETALS: untouched (still full) + already fallen
# -------------------------------------------------------

def draw_static_petals_and_center(
    draw,
    cx,
    cy,
    completed_hours,
    petal_dist,
    petal_w,
    petal_h,
    center_r
):
    """
    Draw:
      - petals with index > completed_hours: still full size,
        untouched, attached to the flower
      - petals with index < completed_hours: already fully
        fallen, resting on the ground at full size
      - the flower center

    The petal at index == completed_hours (the one currently
    eroding/forming) is handled separately by the caller.
    """

    for i in range(PETAL_COUNT):

        if i <= completed_hours:
            continue

        angle = 2 * math.pi * i / PETAL_COUNT

        draw_petal(
            draw, cx, cy, angle, petal_dist, petal_w, petal_h,
            jitter=petal_jitter(i)
        )

    for i in range(completed_hours):

        spacing = WIDTH / (PETAL_COUNT + 1)
        fallen_x = spacing * (i + 1)
        fallen_y = HEIGHT - 7
        fallen_rotation = -0.45 + (i % 5 * 0.22)

        draw_fallen_petal(draw, fallen_x, fallen_y, fallen_rotation, 1.0)

    draw_center(draw, cx, cy, center_r)


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

def main():

    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    cx = WIDTH // 2
    cy = 40

    base_radius = (60 * SCALE) * 0.42

    petal_w = 36 * SCALE
    petal_h = 46 * SCALE
    petal_dist = base_radius
    center_r = 24 * SCALE

    # Animation state carried between frames.
    flying_shards = []
    prev_step_index = -1

    while True:

        now_ts = time.time()

        hours_elapsed = day_progress(now_ts)
        petal_hour_value = half_day_progress(hours_elapsed)

        completed_hours = int(petal_hour_value)
        hour_fraction = petal_hour_value - completed_hours

        seconds_into_hour = hour_fraction * 3600
        step_index = min(
            int(seconds_into_hour // STEP_SECONDS),
            STEPS_PER_HOUR - 1
        )
        step_frac = step_index / STEPS_PER_HOUR

        local = time.localtime(now_ts)

        sky_color = get_sky_color(hours_elapsed)
        text_color = get_text_color(sky_color)

        # -----------------------------------------------
        # CLEAR SCREEN
        # -----------------------------------------------

        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=sky_color)

        # -----------------------------------------------
        # SUN OR MOON
        # -----------------------------------------------

        h24 = hours_elapsed % 24

        if SUN_START_HOUR <= h24 < SUN_END_HOUR:
            draw_sun(draw, hours_elapsed, sky_color)
        else:
            draw_moon(draw, hours_elapsed, sky_color)

        # -----------------------------------------------
        # STATIC PETALS (untouched + already fully fallen)
        # AND CENTER
        # -----------------------------------------------

        draw_static_petals_and_center(
            draw, cx, cy, completed_hours,
            petal_dist, petal_w, petal_h, center_r
        )

        # -----------------------------------------------
        # CURRENTLY ERODING PETAL (flower side) AND
        # CURRENTLY GROWING PETAL (ground side)
        # -----------------------------------------------

        if completed_hours < PETAL_COUNT:

            falling_index = completed_hours
            falling_angle = 2 * math.pi * falling_index / PETAL_COUNT

            # Coarser, clearly-visible shrink: the whole petal
            # (width AND height together, so it reads as
            # shrinking rather than just getting shorter) steps
            # down once every few minutes instead of every 4
            # seconds - a jump big enough to actually notice.
            flower_notch_index = min(
                int(seconds_into_hour // FLOWER_NOTCH_SECONDS),
                FLOWER_NOTCHES_PER_HOUR - 1
            )
            flower_remaining_frac = (
                1.0 - flower_notch_index / FLOWER_NOTCHES_PER_HOUR
            )

            cur_w_remaining = petal_w * flower_remaining_frac
            cur_h_remaining = petal_h * flower_remaining_frac

            draw_petal(
                draw, cx, cy, falling_angle, petal_dist,
                cur_w_remaining, cur_h_remaining,
                jitter=petal_jitter(falling_index)
            )

            spacing = WIDTH / (PETAL_COUNT + 1)
            target_x = spacing * (falling_index + 1)
            target_y = HEIGHT - 7
            growing_rotation = -0.45 + (falling_index % 5 * 0.22)

            draw_fallen_petal(
                draw, target_x, target_y, growing_rotation, step_frac
            )

            # Once every STEP_SECONDS, spawn a big chunk that
            # shrinks down to the floor petal's new size as it
            # flies - so it visually merges in when it lands.
            if step_index != prev_step_index:

                tip_x, tip_y = transform(
                    0, -(petal_dist + cur_h_remaining),
                    falling_angle, cx, cy
                )

                end_w = 18 * SCALE * step_frac
                end_h = 21 * SCALE * step_frac

                start_w = petal_w * 1.15
                start_h = petal_h * 1.0

                spawn_shard(
                    flying_shards,
                    (tip_x, tip_y),
                    (target_x, target_y),
                    falling_angle,
                    start_w, start_h,
                    end_w, end_h,
                    now_ts
                )

                prev_step_index = step_index

        # -----------------------------------------------
        # FLYING CHUNKS IN TRANSIT
        # -----------------------------------------------

        flying_shards = update_and_draw_shards(draw, flying_shards, now_ts)

        # -----------------------------------------------
        # DRAW STEM
        # -----------------------------------------------

        draw.line(
            (cx, cy + STEM_TOP, cx, cy + STEM_BOTTOM),
            fill=STEM_COLOR,
            width=max(2, round(9 * SCALE))
        )

        # -----------------------------------------------
        # DRAW LEAVES
        # -----------------------------------------------

        draw_leaves(draw, cx, cy, hours_elapsed)

        # -----------------------------------------------
        # TEXT READOUTS
        # -----------------------------------------------

        hour_pct = int(step_frac * 100)

        draw.text(
            (4, HEIGHT - 32),
            f"{hour_pct}% to next petal",
            fill=text_color
        )

        draw.text(
            (4, HEIGHT - 22),
            time.strftime("%H:%M:%S", local),
            fill=text_color
        )

        petals_remaining = max(0, PETAL_COUNT - completed_hours)

        draw.text(
            (4, HEIGHT - 12),
            f"{petals_remaining} petals",
            fill=text_color
        )

        # -----------------------------------------------
        # SEND TO DISPLAY
        # -----------------------------------------------

        disp.image(image)

        time.sleep(1 / 15)


if __name__ == "__main__":
    main()
