from __future__ import annotations

from pathlib import Path

print("Loading CadQuery...", flush=True)
import cadquery as cq

print(f"CadQuery loaded: {cq.__version__}", flush=True)


HERE = Path(__file__).resolve().parent
OUTPUT_STEP = HERE / "male_24-410_thread.step"
OUTPUT_STL = HERE / "male_24-410_thread.stl"


# Dimensions from the supplied 24-410 bottle-neck drawing, in millimeters.
LENGTH = 25.00
MAJOR_DIAMETER = 24.20
INNER_DIAMETER = 17.20
WALL_THICKNESS_AT_THREAD_ROOT = 2.50

# OD 24.20 and ID 17.20 imply 3.50 mm at the thread crest.  The drawing also
# calls out 2.50 mm wall thickness, so the unthreaded/root body diameter is:
ROOT_DIAMETER = INNER_DIAMETER + 2.0 * WALL_THICKNESS_AT_THREAD_ROOT

# The drawing does not list pitch.  2.50 mm gives ten full turns over 25 mm and
# matches the visual spacing shown for the all-threaded 24-410 reference part.
PITCH = 2.50


def make_male_24_410_thread() -> cq.Workplane:
    """Build a real external helical-thread 24-410 male neck sample."""

    inner_radius = INNER_DIAMETER / 2.0
    root_radius = ROOT_DIAMETER / 2.0
    major_radius = MAJOR_DIAMETER / 2.0
    pitch = PITCH

    # Hollow cylindrical body at the thread root diameter.
    body = (
        cq.Workplane("XY")
        .circle(root_radius)
        .circle(inner_radius)
        .extrude(LENGTH)
    )

    # Sweep an external 60-degree triangular thread crest around the body.
    # The swept ridge is slightly over-length and then clipped to leave clean,
    # flat, exactly 25.00 mm end faces.
    overrun = pitch
    sweep_height = LENGTH + 2.0 * overrun
    path_radius = (root_radius + major_radius) / 2.0
    half_pitch_width = 0.36 * pitch

    helix = cq.Wire.makeHelix(
        pitch=pitch,
        height=sweep_height,
        radius=path_radius,
        center=(0, 0, -overrun),
        dir=(0, 0, 1),
        lefthand=False,
    )

    thread_profile = (
        cq.Workplane("XZ")
        .polyline(
            [
                (root_radius - 0.02, -half_pitch_width),
                (major_radius, 0.0),
                (root_radius - 0.02, half_pitch_width),
            ]
        )
        .close()
    )
    thread = thread_profile.sweep(helix, isFrenet=True, combine=False)

    threaded = body.union(thread)

    # Keep the exported part exactly within OD 24.20 and length 25.00.
    envelope = cq.Workplane("XY").circle(major_radius).extrude(LENGTH)
    threaded = threaded.intersect(envelope)

    # Reopen the center bore after clipping, ensuring the inner diameter remains
    # exactly 17.20 mm through the full threaded length.
    bore = cq.Workplane("XY").circle(inner_radius).extrude(LENGTH)
    return threaded.cut(bore).clean()


def main() -> None:
    print("Building 24-410 male threaded neck...", flush=True)
    part = make_male_24_410_thread()

    print(f"Exporting {OUTPUT_STEP.name}...", flush=True)
    cq.exporters.export(part, str(OUTPUT_STEP))

    print(f"Exporting {OUTPUT_STL.name}...", flush=True)
    cq.exporters.export(part, str(OUTPUT_STL), tolerance=0.05, angularTolerance=0.08)

    print(f"Wrote {OUTPUT_STEP}", flush=True)
    print(f"Wrote {OUTPUT_STL}", flush=True)


if __name__ == "__main__":
    main()
