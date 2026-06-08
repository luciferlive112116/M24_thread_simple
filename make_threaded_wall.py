from __future__ import annotations

import math
from pathlib import Path

print("Loading CadQuery...", flush=True)
import cadquery as cq
print(f"CadQuery loaded: {cq.__version__}", flush=True)


HERE = Path(__file__).resolve().parent
INPUT_STEP = HERE / "Wall project.step"
OUTPUT_STEP = HERE / "Wall project_M24_threaded.step"
OUTPUT_STL = HERE / "Wall project_M24_threaded.stl"


# Existing STEP bounds read from the AP242 file:
# X: -25..25, Y: 0..70, Z: -95..25.
# The requested front face is the upper block face at Y=70.
FACE_CENTER = cq.Vector(0, 70, 0)


def make_m24_thread_cutter(
    major_diameter: float = 24.0,
    pitch: float = 3.0,
    thread_depth: float = 28.0,
    front_overcut: float = 1.5,
    radial_clearance: float = 0.05,
) -> cq.Workplane:
    """Return a male M24x3 cutter aligned on +Z, to be subtracted from the wall.

    Subtracting this cutter creates a real helical internal thread.  The cutter
    includes the ISO internal-thread minor diameter core plus a swept 60-degree
    helical ridge out to the nominal major diameter.
    """

    # ISO metric basic minor diameter for internal thread, D1 = D - 1.082532P.
    minor_diameter = major_diameter - 1.082532 * pitch
    root_radius = minor_diameter / 2.0
    crest_radius = major_diameter / 2.0 + radial_clearance
    path_radius = (root_radius + crest_radius) / 2.0

    total_length = thread_depth + front_overcut

    core = cq.Workplane("XY").circle(root_radius).extrude(total_length)

    helix = cq.Wire.makeHelix(
        pitch=pitch,
        height=total_length,
        radius=path_radius,
        lefthand=False,
    )

    # 60-degree-ish thread tooth, deliberately extended a little at the face so
    # the boolean leaves a clean fully-open thread start.
    half_width = 0.36 * pitch
    profile = (
        cq.Workplane("XZ")
        .polyline(
            [
                (root_radius - 0.05, -half_width),
                (crest_radius, 0.0),
                (root_radius - 0.05, half_width),
            ]
        )
        .close()
    )
    ridge = profile.sweep(helix, isFrenet=True, combine=False)

    cutter = core.union(ridge)

    # Add a very small entrance clearance cylinder at the thread major diameter
    # to prevent a fragile zero-thickness lip on the front face.
    entry = cq.Workplane("XY").circle(crest_radius).extrude(front_overcut)
    cutter = cutter.union(entry)

    return cutter


def main() -> None:
    if not INPUT_STEP.exists():
        raise FileNotFoundError(f"Missing input STEP: {INPUT_STEP}")

    print(f"Importing {INPUT_STEP.name}...", flush=True)
    wall = cq.importers.importStep(str(INPUT_STEP))
    print("Building M24x3 threaded cutter...", flush=True)
    cutter = make_m24_thread_cutter()

    # Cutter is modeled along +Z starting at Z=0. Rotate +90 degrees around X so
    # +Z becomes -Y, then translate the opening to the face center at Y=70.
    cutter = cutter.rotate((0, 0, 0), (1, 0, 0), 90)
    cutter = cutter.translate((FACE_CENTER.x, FACE_CENTER.y + 1.5, FACE_CENTER.z))

    print("Cutting threaded feature...", flush=True)
    result = wall.cut(cutter).clean()

    print(f"Exporting {OUTPUT_STEP.name}...", flush=True)
    cq.exporters.export(result, str(OUTPUT_STEP))
    print(f"Exporting {OUTPUT_STL.name}...", flush=True)
    cq.exporters.export(result, str(OUTPUT_STL), tolerance=0.08, angularTolerance=0.1)

    print(f"Wrote {OUTPUT_STEP}")
    print(f"Wrote {OUTPUT_STL}")


if __name__ == "__main__":
    main()
