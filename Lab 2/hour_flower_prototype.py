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
Instead of one whole petal sliding smoothly down over an hour
(which looks frozen from second to second), the *currently
falling* petal now erodes in small visible steps:

  - Every STEP_SECONDS (3s) a small chunk breaks off the tip of
    the petal still attached to the flower.
  - That chunk visibly flies down and lands on the ground,
    where it is absorbed into a petal that is gradually
    "growing" back to full size.
  - After a full hour, the flower-side petal has completely
    eroded away and the ground-side petal has grown to its
    full, final size - joining the pile of already-fallen
    petals from earlier hours.

Example: at 3:15pm (quarter past the 4th hour of the current
12-hour half), you'd see:
  - 8 full, untouched petals still on the flower
  - 1 partially-eroded petal on the flower (about 3/4 remaining)
  - 3 full petals already resting on the ground
  - 1 partially-formed petal growing on the ground, at the same
    completion fraction as the eroding one above

The flower itself remains a sunflower with:
- 12 narrow, pointed yellow-orange petals
- Large dark brown disc center
- Fibonacci/Vogel seed pattern
- Broad dark-green leaves (kept to a small, clear number)
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

# Stem and leaves
STEM_COLOR = hsb(100, 55, 40)
LEAF_COLOR = hsb(100, 70, 40)
LEAF_STROKE = hsb(100, 80, 22)

# Sunflower center
CENTER_COLOR = hsb(30, 65, 35)
CENTER_EDGE_COLOR = hsb(35, 75, 55)
SEED_COLOR = hsb(25, 75, 18)

# Sunflower petals
PETAL_FILL = hsb(46, 90, 98)
PETAL_STROKE = hsb(38, 95, 65)
PETAL_HIGHLIGHT = hsb(52, 45, 100)

# Fallen petals
FALLEN_PETAL_COLOR = PETAL_FILL
FALLEN_PETAL_STROKE = PETAL_STROKE

# Small chunks flying from the flower to the ground
CHUNK_COLOR = PETAL_STROKE


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
    n=10
):
    """
    Create a pointed almond/marquise shape.
    Used for sunflower petals and leaves.
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
# The currently-falling petal erodes in visible steps rather
# than one continuous smooth motion, so it's obvious the clock
# is actively updating.

STEP_SECONDS = 3
STEPS_PER_HOUR = 3600 // STEP_SECONDS

# How long a single flying chunk takes to travel from the
# flower down to the ground pile.
CHUNK_FLIGHT_SECONDS = 0.35


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
    doesn't get cluttered.
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

        # Main leaf
        fill_pts = marquise_points(
            0,
            leaf_len,
            leaf_w,
            leaf_angle,
            anchor_x,
            anchor_y
        )

        draw.polygon(
            fill_pts,
            fill=LEAF_COLOR
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
    cur_h
):
    """
    Draw one sunflower ray petal, still attached to the flower.
    """

    if cur_h <= 0.5:
        return

    # Dark outline
    stroke_pts = marquise_points(
        petal_dist - cur_h * 0.04,
        cur_h * 1.08,
        cur_w * 1.15,
        angle,
        cx,
        cy
    )

    draw.polygon(
        stroke_pts,
        fill=PETAL_STROKE
    )

    # Yellow-orange fill
    fill_pts = marquise_points(
        petal_dist,
        cur_h,
        cur_w,
        angle,
        cx,
        cy
    )

    draw.polygon(
        fill_pts,
        fill=PETAL_FILL
    )

    # Highlight
    hi_pts = marquise_points(
        petal_dist + cur_h * 0.05,
        cur_h * 0.45,
        cur_w * 0.35,
        angle,
        cx,
        cy
    )

    draw.polygon(
        hi_pts,
        fill=PETAL_HIGHLIGHT
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
    formed grows from 0.0 to 1.0 over the course of the hour.
    """

    if size <= 0.02:
        return

    width = 9 * SCALE * size
    height = 25 * SCALE * size

    pts = marquise_points(
        0,
        height,
        width,
        angle,
        x,
        y
    )

    draw.polygon(
        pts,
        fill=FALLEN_PETAL_STROKE
    )

    pts_inner = marquise_points(
        0,
        height * 0.92,
        width * 0.82,
        angle,
        x,
        y
    )

    draw.polygon(
        pts_inner,
        fill=FALLEN_PETAL_COLOR
    )


# -------------------------------------------------------
# FLYING CHUNKS (petal fragments in transit)
# -------------------------------------------------------

def spawn_chunk(chunks, start_pos, end_pos, now):
    """
    Add a new petal fragment that will visibly fly from
    start_pos to end_pos over CHUNK_FLIGHT_SECONDS.
    """

    chunks.append({
        "start": start_pos,
        "end": end_pos,
        "start_time": now,
        "duration": CHUNK_FLIGHT_SECONDS,
    })


def update_and_draw_chunks(draw, chunks, now):
    """
    Draw every chunk currently in flight, and return the list
    of chunks that haven't landed yet (i.e. still need to be
    drawn on future frames).
    """

    still_flying = []
    chunk_r = 2.6 * SCALE

    for chunk in chunks:

        elapsed = now - chunk["start_time"]
        t = elapsed / chunk["duration"]

        if t >= 1.0:
            # Landed - drop it from the list.
            continue

        # Ease-in/ease-out motion, same curve used elsewhere.
        t_smooth = t * t * (3 - 2 * t)

        x = (
            chunk["start"][0]
            + (chunk["end"][0] - chunk["start"][0]) * t_smooth
        )

        y = (
            chunk["start"][1]
            + (chunk["end"][1] - chunk["start"][1]) * t_smooth
        )

        draw.ellipse(
            (
                x - chunk_r,
                y - chunk_r,
                x + chunk_r,
                y + chunk_r
            ),
            fill=CHUNK_COLOR
        )

        still_flying.append(chunk)

    return still_flying


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
    Draw the sunflower center with Fibonacci seed packing.
    """

    # Outer edge
    draw.ellipse(
        (
            cx - center_r,
            cy - center_r,
            cx + center_r,
            cy + center_r
        ),
        fill=CENTER_EDGE_COLOR
    )

    # Inner disc
    inner_r = (
        center_r * 0.9
    )

    draw.ellipse(
        (
            cx - inner_r,
            cy - inner_r,
            cx + inner_r,
            cy + inner_r
        ),
        fill=CENTER_COLOR
    )

    # Seeds
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
            inner_r
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

        draw.ellipse(
            (
                sx - seed_r,
                sy - seed_r,
                sx + seed_r,
                sy + seed_r
            ),
            fill=SEED_COLOR
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
            petal_h
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
    petal_w = 17 * SCALE
    petal_h = 80 * SCALE
    petal_dist = base_radius
    center_r = 20 * SCALE

    # Animation state carried between frames.
    flying_chunks = []
    prev_step_index = -1

    while True:

        now_ts = time.time()

        hours_elapsed = day_progress(now_ts)

        # Petals follow a 12-hour cycle: full bloom at
        # midnight and noon.
        petal_hour_value = half_day_progress(hours_elapsed)

        completed_hours = int(petal_hour_value)
        hour_fraction = petal_hour_value - completed_hours

        # Stepped (not continuous) progress through the
        # current hour - changes every STEP_SECONDS, which is
        # what makes each step visibly "pop" instead of
        # creeping by unnoticeably.
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
            # flower - shrinks a little more every 3 seconds.
            draw_petal(
                draw,
                cx,
                cy,
                falling_angle,
                petal_dist,
                petal_w,
                cur_h_remaining
            )

            spacing = WIDTH / (PETAL_COUNT + 1)
            target_x = spacing * (falling_index + 1)
            target_y = HEIGHT - 7

            growing_rotation = (
                -0.45 + (falling_index % 5 * 0.22)
            )

            # The pile on the ground - grows a little more
            # every 3 seconds, in step with the erosion above.
            draw_fallen_petal(
                draw,
                target_x,
                target_y,
                growing_rotation,
                step_frac
            )

            # Every time the step advances, spawn a visible
            # chunk that flies from the eroding tip down to
            # the growing pile.
            if step_index != prev_step_index:

                tip_x, tip_y = transform(
                    0,
                    -(petal_dist + cur_h_remaining),
                    falling_angle,
                    cx,
                    cy
                )

                spawn_chunk(
                    flying_chunks,
                    (tip_x, tip_y),
                    (target_x, target_y),
                    now_ts
                )

                prev_step_index = step_index

        # -----------------------------------------------
        # FLYING CHUNKS IN TRANSIT
        # -----------------------------------------------

        flying_chunks = update_and_draw_chunks(
            draw,
            flying_chunks,
            now_ts
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
