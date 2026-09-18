#!/usr/bin/env python3
"""
flower_clock_hours.py

Sunflower Hour Flower from Lamiah Khan's "Flower Clock"

The sunflower has 12 petals representing a 12-hour half-day cycle.
The flower is in full bloom (all 12 petals) at 00:00 (midnight)
and again at 12:00:00 (noon).

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

HOW THE CURRENT-HOUR PETAL FALLS (the "is it working?" fix)
-------------------------------------------------------------
The *currently falling* petal erodes in clearly visible,
once-a-minute steps rather than a continuous creep you can't
perceive:

  - Once every MINUTE, a noticeably-sized shard breaks off the
    tip of the petal still attached to the flower.
  - That shard visibly spins as it flies down to the ground,
    where it lands with a brief expanding "poof" flash - an
    unmistakable, easy-to-see event.
  - The instant it lands, the flower-side petal is visibly a
    little shorter and the ground-side petal is visibly a
    little bigger (a real size jump, not a sub-pixel creep),
    since each minute is 1/60th of the hour.
  - After a full hour (60 of these landings), the flower-side
    petal has completely eroded away and the ground-side petal
    has grown to its full, final size - joining the pile of
    already-fallen petals from earlier hours.

Example: at 3:15pm (quarter past the 4th hour of the current
12-hour half), you'd see:
  - 8 full, untouched petals still on the flower
  - 1 partially-eroded petal on the flower (about 3/4 remaining)
  - 3 full petals already resting on the ground
  - 1 partially-formed petal growing on the ground, at the same
    completion fraction as the eroding one above

MAKING IT MORE BEAUTIFUL
-------------------------------------------------------------
  - Petals are layered (dark amber base -> golden mid -> pale
    tip) instead of one flat color, so they read as painted
    rather than clip-art.
  - Each petal gets a tiny deterministic "jitter" in width and
    tilt, based on its index, so the flower doesn't look like
    a perfectly robotic 12-gon - a touch more organic.
  - A soft warm glow halo sits behind the flower, blended
    toward whatever the current sky color is, so it reads well
    on black, white, or grey backgrounds.
  - The center uses a 3-ring gradient with alternating seed
    tones and a few sparkle highlights instead of one flat
    disc.
  - Leaves are two-tone with a simple center vein.
  - The falling shard is a small spinning petal-shape (not a
    plain dot), and its landing gets a brief expanding ring
    flash for extra visual "pop."

The flower keeps its original structure:
- 12 narrow, pointed petals
- Large dark brown disc center
- Fibonacci/Vogel seed pattern
- Background color by time of day: black at night, white in
  the morning/daytime, grey in the evening
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
# COLORS
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


def blend(fg, bg, alpha_pct):
    """Blend fg over bg."""

    a = max(0.0, min(1.0, alpha_pct / 100.0))

    return tuple(
        round(fg[i] * a + bg[i] * (1 - a))
        for i in range(3)
    )


def lerp_color(c1, c2, t):
    """Linearly interpolate between two (r, g, b) colors."""

    t = max(0.0, min(1.0, t))

    return tuple(
        round(c1[i] + (c2[i] - c1[i]) * t)
        for i in range(3)
    )


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
#  8:00 PM - 4:59:59 AM  -> black   (night)
#  5:00 AM - 5:59:59 PM  -> white   (morning / daytime)
#  6:00 PM - 7:59:59 PM  -> grey    (evening)

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
# SUNFLOWER COLORS
# -------------------------------------------------------

# Stem
STEM_COLOR = hsb(100, 55, 40)

# Leaves - two-tone (base darker, tip lighter) + vein
LEAF_BASE_COLOR = hsb(98, 78, 30)
LEAF_TIP_COLOR = hsb(104, 60, 50)
LEAF_STROKE = hsb(98, 85, 17)
LEAF_VEIN_COLOR = hsb(100, 35, 62)

# Sunflower center - 3-ring gradient
CENTER_OUTER_RING = hsb(34, 78, 58)
CENTER_MID_RING = hsb(30, 70, 40)
CENTER_INNER_RING = hsb(26, 62, 28)
CENTER_SHADOW = hsb(20, 40, 12)
SEED_COLOR_A = hsb(22, 78, 19)
SEED_COLOR_B = hsb(27, 68, 25)
SEED_SPARKLE = hsb(38, 35, 58)

# Sunflower petals - layered gradient (base -> mid -> tip)
PETAL_BASE_COLOR = hsb(28, 85, 90)
PETAL_FILL = hsb(45, 88, 99)
PETAL_TIP_COLOR = hsb(52, 30, 100)
PETAL_STROKE = hsb(32, 90, 52)

# Fallen / growing petals on the ground (slightly muted so
# the flower itself stays the visual focus)
FALLEN_PETAL_BASE = PETAL_BASE_COLOR
FALLEN_PETAL_FILL = PETAL_FILL
FALLEN_PETAL_STROKE = PETAL_STROKE

# Falling shard (the piece breaking off each minute)
SHARD_COLOR = PETAL_FILL
SHARD_STROKE = PETAL_STROKE

# Landing flash ring
BURST_COLOR = hsb(48, 70, 100)


# -------------------------------------------------------
# GEOMETRY
# -------------------------------------------------------

def transform(lx, ly, angle, ox, oy):
    """Rotate and translate a point."""

    gx = (
        lx * math.cos(angle)
        - ly * math.sin(angle)
    )

    gy = (
        lx * math.sin(angle)
        + ly * math.cos(angle)
    )

    return (
        ox + gx,
        oy + gy
    )


def marquise_points(
    base_dist,
    length,
    width,
    angle,
    ox,
    oy,
    n=14
):
    """
    Create a pointed almond/marquise shape.
    Used for sunflower petals, leaves, and falling shards.
    """

    pts = []

    for i in range(n + 1):

        t = i / n

        lx = (
            width / 2
            * math.sin(math.pi * t)
        )

        ly = -(
            base_dist
            + length * t
        )

        pts.append(
            transform(
                lx,
                ly,
                angle,
                ox,
                oy
            )
        )

    for i in range(n + 1):

        t = 1 - i / n

        lx = -(
            width / 2
            * math.sin(math.pi * t)
        )

        ly = -(
            base_dist
            + length * t
        )

        pts.append(
            transform(
                lx,
                ly,
                angle,
                ox,
                oy
            )
        )

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

FLOWER_SIZE = 60 * SCALE

STEM_TOP = 20 * SCALE
STEM_BOTTOM = 150 * SCALE

# 12 petals: full bloom at midnight (0:00) and noon (12:00),
# one petal falls per hour through each 12-hour half of the day.
PETAL_COUNT = 12

GOLDEN_ANGLE = (
    math.pi
    * (3 - math.sqrt(5))
)

# -------------------------------------------------------
# STEPPED-EROSION SETTINGS
# -------------------------------------------------------
#
# The currently-falling petal erodes once a MINUTE (not every
# few seconds) so each step is a real, perceivable jump in size
# instead of an invisible sliver. 60 steps take the petal from
# fully attached to fully fallen over the hour.

STEP_SECONDS = 60
STEPS_PER_HOUR = 3600 // STEP_SECONDS

# How long the shard takes to fly from the flower down to the
# ground pile, and how long the landing flash lingers. Both are
# deliberately slow enough to actually notice.
SHARD_FLIGHT_SECONDS = 0.8
BURST_SECONDS = 0.4

# Fixed pixel sizes for the shard/flash - NOT scaled down by
# SCALE, so they stay clearly visible regardless of how big or
# small the flower itself is drawn.
SHARD_WIDTH = 4.5
SHARD_HEIGHT = 10.0
BURST_MIN_RADIUS = 3.0
BURST_MAX_RADIUS = 13.0


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

    00:00 -> 0.0
    06:30 -> 6.5
    12:00 -> 0.0  (resets - full bloom)
    18:30 -> 6.5
    23:59 -> ~11.99
    """

    return hour_value % 12


# -------------------------------------------------------
# LEAVES
# -------------------------------------------------------

def draw_leaves(
    draw,
    cx,
    cy,
    hour_value
):
    """
    Draw sunflower leaves.

    Leaves gradually appear throughout the day. Count is kept
    low (max 4) so the flower silhouette stays clear and
    doesn't get cluttered. Each leaf is two-tone (darker at
    the base, lighter at the tip) with a simple center vein.
    """

    num_leaves = (
        int(hour_value // 4)
        + 1
    )

    num_leaves = min(
        num_leaves,
        4
    )

    for i in range(num_leaves):

        leaf_y = (
            78 * SCALE
            + i * (16 * SCALE)
        )

        side = (
            -1
            if i % 2 == 0
            else 1
        )

        anchor_x = (
            cx
            + side * (4 * SCALE)
        )

        anchor_y = (
            cy
            + leaf_y
        )

        leaf_angle = (
            side
            * (0.85 + i * 0.06)
        )

        leaf_len = (
            (30 + i * 3)
            * SCALE
        )

        leaf_w = (
            (22 + i * 2)
            * SCALE
        )

        # Dark outline
        stroke_pts = marquise_points(
            0,
            leaf_len * 1.06,
            leaf_w * 1.15,
            leaf_angle,
            anchor_x,
            anchor_y
        )

        draw.polygon(
            stroke_pts,
            fill=LEAF_STROKE
        )

        # Darker base tone (full leaf)
        base_pts = marquise_points(
            0,
            leaf_len,
            leaf_w,
            leaf_angle,
            anchor_x,
            anchor_y
        )

        draw.polygon(
            base_pts,
            fill=LEAF_BASE_COLOR
        )

        # Lighter tip tone (upper 60% of the leaf)
        tip_pts = marquise_points(
            leaf_len * 0.35,
            leaf_len * 0.65,
            leaf_w * 0.85,
            leaf_angle,
            anchor_x,
            anchor_y
        )

        draw.polygon(
            tip_pts,
            fill=LEAF_TIP_COLOR
        )

        # Simple center vein
        vein_start = transform(
            0,
            -leaf_len * 0.08,
            leaf_angle,
            anchor_x,
            anchor_y
        )

        vein_end = transform(
            0,
            -leaf_len * 0.92,
            leaf_angle,
            anchor_x,
            anchor_y
        )

        draw.line(
            (vein_start, vein_end),
            fill=LEAF_VEIN_COLOR,
            width=1
        )


# -------------------------------------------------------
# SUNFLOWER PETAL
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
    Draw one sunflower ray petal, still attached to the flower.

    Layered as: dark outline -> warm amber base -> golden mid
    fill (inset so the amber base peeks out near the flower) ->
    pale tip highlight. A small per-petal jitter (width scale,
    tilt) keeps the flower from looking perfectly mechanical.
    """

    if cur_h <= 0.5:
        return

    width_jitter, tilt_jitter = jitter
    angle = angle + tilt_jitter
    cur_w = cur_w * width_jitter

    # Dark outline
    stroke_pts = marquise_points(
        petal_dist - cur_h * 0.04,
        cur_h * 1.08,
        cur_w * 1.18,
        angle,
        cx,
        cy
    )

    draw.polygon(
        stroke_pts,
        fill=PETAL_STROKE
    )

    # Warm amber base - full petal length, sits underneath
    base_pts = marquise_points(
        petal_dist,
        cur_h,
        cur_w,
        angle,
        cx,
        cy
    )

    draw.polygon(
        base_pts,
        fill=PETAL_BASE_COLOR
    )

    # Golden mid fill - inset slightly so a thin amber ring
    # shows through near the attachment point
    fill_pts = marquise_points(
        petal_dist + cur_h * 0.12,
        cur_h * 0.92,
        cur_w * 0.92,
        angle,
        cx,
        cy
    )

    draw.polygon(
        fill_pts,
        fill=PETAL_FILL
    )

    # Pale tip highlight
    hi_pts = marquise_points(
        petal_dist + cur_h * 0.72,
        cur_h * 0.32,
        cur_w * 0.42,
        angle,
        cx,
        cy,
        n=10
    )

    draw.polygon(
        hi_pts,
        fill=PETAL_TIP_COLOR
    )


# -------------------------------------------------------
# FALLEN / GROWING PETAL (on the ground)
# -------------------------------------------------------

def draw_fallen_petal(
    draw,
    x,
    y,
    angle,
    size
):
    """
    Draw a petal resting on the ground.

    'size' is 0.0 - 1.0: a fully-fallen petal from an earlier
    hour is drawn at size=1.0, while the petal currently being
    formed grows from 0.0 to 1.0 over the course of the hour,
    jumping up once a minute as each shard lands.
    """

    if size <= 0.02:
        return

    width = 9 * SCALE * size
    height = 25 * SCALE * size

    stroke_pts = marquise_points(
        0,
        height * 1.06,
        width * 1.15,
        angle,
        x,
        y,
        n=10
    )

    draw.polygon(
        stroke_pts,
        fill=FALLEN_PETAL_STROKE
    )

    base_pts = marquise_points(
        0,
        height,
        width,
        angle,
        x,
        y,
        n=10
    )

    draw.polygon(
        base_pts,
        fill=FALLEN_PETAL_BASE
    )

    fill_pts = marquise_points(
        height * 0.1,
        height * 0.85,
        width * 0.8,
        angle,
        x,
        y,
        n=10
    )

    draw.polygon(
        fill_pts,
        fill=FALLEN_PETAL_FILL
    )


# -------------------------------------------------------
# FALLING SHARDS (the visible "something just happened" cue)
# -------------------------------------------------------

def spawn_shard(shards, start_pos, end_pos, base_angle, now):
    """
    Add a new petal shard that will visibly spin and fly from
    start_pos to end_pos over SHARD_FLIGHT_SECONDS.
    """

    shards.append({
        "start": start_pos,
        "end": end_pos,
        "base_angle": base_angle,
        "start_time": now,
        "duration": SHARD_FLIGHT_SECONDS,
    })


def update_and_draw_shards(draw, shards, bursts, now):
    """
    Draw every shard currently in flight (as a small spinning
    petal shape, not a plain dot, so it's actually easy to
    see). When a shard finishes its flight, remove it and spawn
    a landing flash in its place.

    Returns the list of shards still in flight.
    """

    still_flying = []

    for shard in shards:

        elapsed = now - shard["start_time"]
        t = elapsed / shard["duration"]

        if t >= 1.0:
            # Landed this frame - trigger a flash and drop it.
            bursts.append({
                "pos": shard["end"],
                "start_time": now,
                "duration": BURST_SECONDS,
            })
            continue

        # Ease-in/ease-out motion for the flight path.
        t_smooth = t * t * (3 - 2 * t)

        x = (
            shard["start"][0]
            + (shard["end"][0] - shard["start"][0]) * t_smooth
        )

        y = (
            shard["start"][1]
            + (shard["end"][1] - shard["start"][1]) * t_smooth
        )

        # Spin the shard as it falls - purely cosmetic, but
        # makes it read as a tumbling petal fragment.
        spin_angle = shard["base_angle"] + t * math.pi * 2.5

        shard_pts = marquise_points(
            0,
            SHARD_HEIGHT,
            SHARD_WIDTH,
            spin_angle,
            x,
            y,
            n=8
        )

        draw.polygon(
            shard_pts,
            fill=SHARD_COLOR,
            outline=SHARD_STROKE
        )

        still_flying.append(shard)

    return still_flying


def update_and_draw_bursts(draw, bursts, now, bg_color):
    """
    Draw the brief expanding-ring "poof" flash at each landing
    spot, fading toward the current background color as it
    grows. Returns the list of bursts still active.
    """

    still_active = []

    for burst in bursts:

        elapsed = now - burst["start_time"]
        t = elapsed / burst["duration"]

        if t >= 1.0:
            continue

        radius = (
            BURST_MIN_RADIUS
            + (BURST_MAX_RADIUS - BURST_MIN_RADIUS) * t
        )

        ring_color = lerp_color(BURST_COLOR, bg_color, t)

        x, y = burst["pos"]

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius
            ),
            outline=ring_color,
            width=2
        )

        still_active.append(burst)

    return still_active


# -------------------------------------------------------
# GLOW HALO
# -------------------------------------------------------

def draw_flower_glow(draw, cx, cy, radius, sky_color):
    """
    A soft, two-step warm halo behind the flower, blended
    toward the current sky color so it stays subtle on black,
    white, or grey backgrounds instead of looking like a flat
    colored square.
    """

    outer_color = lerp_color(PETAL_FILL, sky_color, 0.82)
    inner_color = lerp_color(PETAL_FILL, sky_color, 0.6)

    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=outer_color
    )

    inner_r = radius * 0.68

    draw.ellipse(
        (
            cx - inner_r,
            cy - inner_r,
            cx + inner_r,
            cy + inner_r
        ),
        fill=inner_color
    )


# -------------------------------------------------------
# SUNFLOWER CENTER
# -------------------------------------------------------

def draw_center(
    draw,
    cx,
    cy,
    center_r
):
    """
    Draw the sunflower center: a soft shadow, a 3-ring
    gradient disc, and a Fibonacci seed pattern with
    alternating tones plus a few sparkle highlights.
    """

    # Soft shadow, slightly offset, for a touch of depth
    shadow_r = center_r * 1.08

    draw.ellipse(
        (
            cx - shadow_r + 1,
            cy - shadow_r + 2,
            cx + shadow_r + 1,
            cy + shadow_r + 2
        ),
        fill=CENTER_SHADOW
    )

    # Outer ring
    draw.ellipse(
        (
            cx - center_r,
            cy - center_r,
            cx + center_r,
            cy + center_r
        ),
        fill=CENTER_OUTER_RING
    )

    # Mid ring
    mid_r = center_r * 0.82

    draw.ellipse(
        (
            cx - mid_r,
            cy - mid_r,
            cx + mid_r,
            cy + mid_r
        ),
        fill=CENTER_MID_RING
    )

    # Inner disc
    inner_r = center_r * 0.62

    draw.ellipse(
        (
            cx - inner_r,
            cy - inner_r,
            cx + inner_r,
            cy + inner_r
        ),
        fill=CENTER_INNER_RING
    )

    # Seeds, alternating between two tones with occasional
    # sparkle highlights, in the classic Fibonacci packing.
    num_seeds = 55

    seed_r = max(
        0.5,
        center_r * 0.11
    )

    for i in range(num_seeds):

        frac = (
            i
            / max(1, num_seeds - 1)
        )

        r = (
            center_r
            * 0.92
            * math.sqrt(frac)
        )

        theta = (
            i
            * GOLDEN_ANGLE
        )

        sx = (
            cx
            + r * math.cos(theta)
        )

        sy = (
            cy
            + r * math.sin(theta)
        )

        seed_color = (
            SEED_COLOR_A
            if i % 2 == 0
            else SEED_COLOR_B
        )

        draw.ellipse(
            (
                sx - seed_r,
                sy - seed_r,
                sx + seed_r,
                sy + seed_r
            ),
            fill=seed_color
        )

        # A handful of tiny sparkle dots for polish.
        if i % 7 == 0:

            sparkle_r = seed_r * 0.4

            draw.ellipse(
                (
                    sx - sparkle_r * 1.4,
                    sy - sparkle_r * 1.4,
                    sx - sparkle_r * 0.4,
                    sy - sparkle_r * 0.4
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
    eroding/forming) is handled separately by the caller, since
    it needs per-frame animation state.
    """

    # Untouched petals still on the flower.
    for i in range(PETAL_COUNT):

        if i <= completed_hours:
            continue

        angle = (
            2 * math.pi * i / PETAL_COUNT
        )

        draw_petal(
            draw,
            cx,
            cy,
            angle,
            petal_dist,
            petal_w,
            petal_h,
            jitter=petal_jitter(i)
        )

    # Petals that fell during earlier hours - already resting
    # on the ground at full size.
    for i in range(completed_hours):

        spacing = WIDTH / (PETAL_COUNT + 1)

        fallen_x = spacing * (i + 1)
        fallen_y = HEIGHT - 7

        fallen_rotation = (
            -0.45 + (i % 5 * 0.22)
        )

        draw_fallen_petal(
            draw,
            fallen_x,
            fallen_y,
            fallen_rotation,
            1.0
        )

    draw_center(
        draw,
        cx,
        cy,
        center_r
    )


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

def main():

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT)
    )

    draw = ImageDraw.Draw(
        image
    )

    # Center of flower
    cx = WIDTH // 2

    # Flower head near top
    cy = 40

    base_radius = FLOWER_SIZE * 0.32

    # Slightly longer, narrower petals read as more elegant
    # than short, stubby ones.
    petal_w = 15 * SCALE
    petal_h = 92 * SCALE
    petal_dist = base_radius
    center_r = 18 * SCALE

    glow_radius = (petal_dist + petal_h) * 1.15

    # Animation state carried between frames.
    flying_shards = []
    landing_bursts = []
    prev_step_index = -1

    while True:

        now_ts = time.time()

        hours_elapsed = day_progress(now_ts)

        # Petals follow a 12-hour cycle: full bloom at
        # midnight and noon.
        petal_hour_value = half_day_progress(hours_elapsed)

        completed_hours = int(petal_hour_value)
        hour_fraction = petal_hour_value - completed_hours

        # Stepped progress through the current hour - changes
        # once a minute, which is what makes each step visibly
        # "pop" instead of creeping by unnoticeably.
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

        draw.rectangle(
            (0, 0, WIDTH, HEIGHT),
            fill=sky_color
        )

        # -----------------------------------------------
        # SOFT GLOW BEHIND THE FLOWER
        # -----------------------------------------------

        draw_flower_glow(
            draw,
            cx,
            cy,
            glow_radius,
            sky_color
        )

        # -----------------------------------------------
        # STATIC PETALS (untouched + already fully fallen)
        # AND CENTER
        # -----------------------------------------------

        draw_static_petals_and_center(
            draw,
            cx,
            cy,
            completed_hours,
            petal_dist,
            petal_w,
            petal_h,
            center_r
        )

        # -----------------------------------------------
        # CURRENTLY ERODING PETAL (flower side) AND
        # CURRENTLY GROWING PETAL (ground side)
        # -----------------------------------------------

        if completed_hours < PETAL_COUNT:

            falling_index = completed_hours

            falling_angle = (
                2 * math.pi * falling_index / PETAL_COUNT
            )

            remaining_frac = 1.0 - step_frac
            cur_h_remaining = petal_h * remaining_frac

            # The part of this petal still attached to the
            # flower - visibly shorter each minute.
            draw_petal(
                draw,
                cx,
                cy,
                falling_angle,
                petal_dist,
                petal_w,
                cur_h_remaining,
                jitter=petal_jitter(falling_index)
            )

            spacing = WIDTH / (PETAL_COUNT + 1)
            target_x = spacing * (falling_index + 1)
            target_y = HEIGHT - 7

            growing_rotation = (
                -0.45 + (falling_index % 5 * 0.22)
            )

            # The pile on the ground - visibly bigger each
            # minute, in step with the erosion above.
            draw_fallen_petal(
                draw,
                target_x,
                target_y,
                growing_rotation,
                step_frac
            )

            # Once a minute, spawn a shard that spins from the
            # eroding tip down to the growing pile.
            if step_index != prev_step_index:

                tip_x, tip_y = transform(
                    0,
                    -(petal_dist + cur_h_remaining),
                    falling_angle,
                    cx,
                    cy
                )

                spawn_shard(
                    flying_shards,
                    (tip_x, tip_y),
                    (target_x, target_y),
                    falling_angle,
                    now_ts
                )

                prev_step_index = step_index

        # -----------------------------------------------
        # FLYING SHARDS + LANDING FLASHES
        # -----------------------------------------------

        flying_shards = update_and_draw_shards(
            draw,
            flying_shards,
            landing_bursts,
            now_ts
        )

        landing_bursts = update_and_draw_bursts(
            draw,
            landing_bursts,
            now_ts,
            sky_color
        )

        # -----------------------------------------------
        # DRAW STEM
        # -----------------------------------------------

        draw.line(
            (
                cx,
                cy + STEM_TOP,
                cx,
                cy + STEM_BOTTOM
            ),
            fill=STEM_COLOR,
            width=max(
                2,
                round(9 * SCALE)
            )
        )

        # -----------------------------------------------
        # DRAW LEAVES
        # -----------------------------------------------

        draw_leaves(
            draw,
            cx,
            cy,
            hours_elapsed
        )

        # -----------------------------------------------
        # PERCENTAGE READOUT (progress to next petal fall)
        # -----------------------------------------------

        hour_pct = int(step_frac * 100)

        draw.text(
            (4, HEIGHT - 32),
            f"{hour_pct}% to next petal",
            fill=text_color
        )

        # -----------------------------------------------
        # TIME DISPLAY
        # -----------------------------------------------

        draw.text(
            (4, HEIGHT - 22),
            time.strftime("%H:%M:%S", local),
            fill=text_color
        )

        # Number of petals remaining (in the current
        # 12-hour half)
        petals_remaining = max(
            0,
            PETAL_COUNT - completed_hours
        )

        draw.text(
            (4, HEIGHT - 12),
            f"{petals_remaining} petals",
            fill=text_color
        )

        # -----------------------------------------------
        # SEND TO DISPLAY
        # -----------------------------------------------

        disp.image(image)

        # Keep animation smooth.
        time.sleep(1 / 15)


if __name__ == "__main__":
    main()
