# Polaris 5439157 clutch outlet duct, repaired model

A printable STL of the Polaris **5439157 REV04 "Duct-Outlet, Clutch"**, rebuilt from a 3D scan of a
broken part (`Mesh_Tressa.stl`, about 20 million triangles). It is item 8 on the Polaris
"Clutch Cover and Ducting" diagram. It fits the 2014–2016 Sportsman 850 and 1000 Touring and SP
models, among others.

Output: [`polaris_5439157_outlet_duct_repaired.stl`](polaris_5439157_outlet_duct_repaired.stl)

- Units are millimeters.
- The STL is in **the same coordinates as the scan**, so you can overlay the two directly.
- It is watertight, one solid body, 800k triangles.

![scan vs repaired model](verification/scan_vs_model.png)

## What was broken

From the scan and the customer's photos:

- The round outlet end that clamps to the clutch cover with a rubber coupler is torn off. What is
  left of it is crushed, folded, and has a torn flap sticking out.
- The J-bend next to it is scorched and abraded, with belt-cord residue melted into the surface
  and a hole worn through the wall. This is typical of a blown drive belt.
- The box, the rectangular mouth, the mounting ear and the rest of the tube are intact.

## What the model keeps and what was rebuilt

| region | how it was made |
|---|---|
| box, rectangular mouth, mounting ear, molded "5439157 REV04" text, upper tube | taken directly from the scan (see Verification) |
| melted and abraded J-bend | scan surface with about 1.2 mm of smoothing, which removes the belt residue and scorch texture but keeps the shape (median 0.12 mm from the scan) |
| outlet cuff | rebuilt as a straight round cuff on the axis measured from the intact tube end, then lofted into the last undamaged tube section |
| outlet-rim keying tab | added from photos of the OEM part: a flat tab on the outer side of the bend, just behind the cuff end (the scan only has a torn remnant) |
| small area between the box and the tube that the scanner could not reach (about 100 cm²) | smooth surface bridged from the surrounding scan |
| wall | 2.5 mm, 3.0 mm in the cuff. Wherever the scanner caught both faces of a wall (mouth collar, box end), the scanned thickness is kept. Two spots on the box that came out thinner than 1.4 mm (where the scanner missed the outside face) are brought up to 2.2 mm. |
| scan noise | about 120 tiny specks of stray scan points stuck to the outside surface are removed |

## Measurements

| feature | value |
|---|---|
| overall size (aligned) | 394 × 169 × 154 mm |
| outlet cuff outside diameter | **66.8 mm** |
| outlet cuff inside diameter | 60.8 mm (3.0 mm wall) |
| straight round cuff length | 50 mm, after a 22 mm loft from the oval tube |
| outlet-rim keying tab | 7 mm tall (radial), 10 mm long, 3 mm thick, ending 4 mm before the cuff end, on the outer side of the bend |
| tube section before the cuff | oval, about 78 × 56 mm, 225 mm outside perimeter |
| wall thickness elsewhere | 2.5 mm (scan shows about 2 mm at the box end and 3 mm at the outlet) |
| volume | 315 cm³, about 340 g in ASA, 360 g in PA6-CF, 400 g in PETG at full density |

[`reconstruction.json`](reconstruction.json) holds the cuff axis, center and the full set of build parameters.

## Please check before printing

These are the numbers I could not measure exactly, because that part of the original is missing or crushed:

1. **Cuff outside diameter, 66.8 mm.** This comes from circle fits to the surviving bottom and side
   wall of the cuff (R = 33.2–33.4 mm). If you have the rubber coupler or the clutch cover outlet,
   check the coupler's inside diameter. To change the diameter, edit `Ro` in `scripts/params_in.json`
   and re-run `build.py`, `final_mesh.py` and `export.py`.
2. **Cuff length.** The cuff ends 36 mm past the measured outlet section, where the furthest
   surviving piece of the original wall ends. The original might have been slightly longer, but not
   shorter.
3. **Rim tab.** Modeled from photos of the OEM part, not measured: the scan only has a torn
   remnant at that spot. Its size and its position around the rim should be checked against the
   slot in the rubber coupler (or a photo of an undamaged duct). Its settings are in
   `scripts/addtab.py`.
4. **Hidden area between the box and the tube.** This area is bridged smoothly, not measured.
   It doesn't touch a mating part.

## Verification

Distances from the scan points to the repaired model (`verification/verification.json`):

| region | median | 95th percentile | within 0.25 mm | within 0.5 mm |
|---|---|---|---|---|
| untouched (more than 160 mm from the outlet) | 0.10 mm | 0.20 mm | 98.6 % | 99.65 % |
| smoothed melted bend | 0.12 mm | 0.25 mm | 94.8 % | 99.3 % |
| rebuilt outlet (vs the broken scan) | 0.37 mm | 11 mm | 45 % | 53 % |

The first two rows show the model follows the scan to within scan noise. The few untouched-area points
further than 0.5 mm away are the removed noise specks and the inside face of the two thickened spots. The last row is large on purpose: there the model differs
from the broken scan by design (crushed, torn and missing material).

![deviation map](verification/deviation_map.png)

## Revised version (fire damage and contaminants removed)

[`polaris_5439157_outlet_duct_revised.stl`](polaris_5439157_outlet_duct_revised.stl) is a second,
cleaner model. The first STL above is kept unchanged. The revised one aims for the part as
originally molded, before the fire: no scorch crust, no heat dents, no seams where the scanner
couldn't see.

- **Tube rebuilt as a design-intent sweep.** The original is blow-molded, so its tube is a smooth
  sweep. I fit one to the scan: a smoothed centerline with smooth cross-sections (14 angular
  harmonics, a cubic B-spline every 18 mm along the length). The fit is robust, so outward crust
  and inward dents count as outliers and don't pull the surface. About 4% of the tube scan was
  crust above the surface and 1% dents below it (see `verification/revised_tube_crust_and_dents.png`).
  The crushed last stretch before the outlet is left out of the fit and bridged by the sweep.
- **Box faces: smart smoothing.** A robust local surface fit (bilateral moving least squares)
  uses only neighbors on the same face, rejects outliers and caps each move at 1.5–2 mm. That
  removes the seam and waviness where the scanner missed the inside corner between the tube and
  the box, without rounding edges or shrinking the part.
- **Left untouched:** the mounting ear, the molded "5439157 REV04" text and recycling mark, the
  mouth lip, the rebuilt outlet cuff and the rim tab.
- **Tube wall** is a uniform 2.5 mm. The scanner couldn't see inside the tube, so this is an
  assumption, not a measurement.

| region (revised vs scan) | median | 95th pct | within 0.5 mm |
|---|---|---|---|
| box and upper tube | 0.12 mm | 0.29 mm | 97.6 % |
| fire-damaged tube | 0.13 mm | 0.48 mm | 95.3 % |

The remaining differences are the crust and dents that were deliberately removed. Volume is 303 cm³.

**Shrinkage.** Heat can make molded plastic shrink a little. The scan alone can't tell overall
shrinkage apart from the original design, so the revised model keeps the scanned size. The
customer's measurement of the rubber boot settles the one dimension that matters for fit (the
cuff diameter).

Pipeline: `scripts/rebuild_rev.sh` (the sweep fit, sweep application, rebuild, then `mls.py`
twice and `foldfix.py`). The before/after of the inside corner is
`verification/revised_circled_area_before_after.png`. Screenshots for the customer are in `customer/revised/`.

### Revised v2: warping on the box side removed

[`polaris_5439157_outlet_duct_revised_v2.stl`](polaris_5439157_outlet_duct_revised_v2.stl) is the
revised model with the irregular ridges removed from the side of the box next to the tube joint.
The two earlier STLs are kept unchanged. About 85% of that face had no scan data (the scanner
couldn't see into that corner).

- **Outer face:** smoothed with a bending-energy fill that also has a "stay close" term
  (smoothing scale 9 mm). That removes short irregular ripples but keeps the face's natural
  curve. The surface moved at most 2.6 mm (95% of points under 1.4 mm).
- **Inside wall:** moved to sit exactly 2.5 mm from the new outer face (measured 2.48–2.51 mm).
- **Accuracy and size:** everywhere else matches the scan as in the revised model. Volume is
  300 cm³, because the wall in that corner had come out thicker than 2.5 mm.

Before/after: `verification/revised_v2_warp_before_after.png`. Customer screenshots are in
`customer/revised_v2/`. Scripts: `scripts/bifair.py` (run with `--whole --grow=10 --ell=9`), then
`scripts/offset_inner.py`.

## Customer check

`customer/` holds annotated screenshots and `customer/message.md` holds a message asking the customer to
confirm the model and measure the coupler, the cuff length and the tab.

## Printing notes

The duct carries hot air out of the CVT. Use **ASA, ABS, or nylon (PA6/PA12, plain or CF)**. PLA and
PETG soften at CVT outlet temperatures. Print the 2.5–3 mm walls solid (4 or more perimeters).

## Pipeline

All scripts are in `scripts/`, and `scripts/run_all.sh` lists the order they were run in. It needs
about 16 GB of RAM. The steps were run individually, not as a single `run_all.sh` call.

1. **Align and voxelize.** Load the scan, compute normals, move it to a principal-axis frame, and
   build a 0.35 mm grid.
2. **Fill the outer skin.** A ray-parity vote from 12 random directions marks the inside of the
   part. This tolerates holes and open ends. A distance field is then fitted to the outer scan
   points: k-nearest-neighbor plane fits, light smoothing, and heavier smoothing only where there
   is no scan data.
3. **Close the mouth and fill gaps.** The surface the fill puts across the rectangular mouth is fed
   back in so the box reads as closed, then the fill is run again. Unscanned patches get smooth
   fill points.
4. **Wall field.** A signed distance is taken from every scanned face, using each face's own normal
   and only neighbors on the same side. It is thickened inward by the wall thickness. Two-sided
   scanned walls keep their true thickness, and the mouth stays open.
5. **Outlet.** Measure the tube centerline (skeleton), find minimum-area cross-sections near the
   end to get the outlet axis, and fit the cuff circle to the surviving wall. Then loft from the last
   intact section to the round cuff, open the bore, and trim the torn flap.
6. **Mesh and verify.** Marching cubes, decimation to 800k faces, repair to a watertight solid, map
   back to scan coordinates, and compare with the scan.
