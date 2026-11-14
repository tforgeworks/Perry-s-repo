---
name: AR-handguards-modeling
description: Design and build printable sculpted sleeves (snakes, dragons, vines, any organic art) for AR-15 handguards from a customer's 3D scan, photos and concept art, plus a printable copy of the handguard, assembly guides and customer/commercial manuals. Covers scan alignment and measurement, slide-on fit, Meshy image-to-3D sculpture, double-helix bodies, joints, bolting into keymod holes, sight and bipod clearance, printability checks, renders and manuals. Learns from the user's feedback every run (LEARNINGS.md). Trigger on '/AR-handguards-modeling', 'model a handguard', 'snake handguard', 'add a snake / dragon / sculpture to this handguard', 'reverse engineer this handguard from the scan', 'make a handguard sleeve', or follow-up edits to such a job (fangs, nose, loops, bipod cut, sight clearance, manual).
---

# AR handguard sleeve modeling (Titan Forgeworks)

Turn a customer's handguard scan and concept picture into print files: an optional CAD copy of the
handguard, and a sculpted sleeve that slides over it in two pieces and bolts into its own holes.
Then the illustrations and manuals to sell it.

The first job built with this skill is in `handguard/` of this repository (two-bodied double-helix
viper on a Trinity Force KMX-15 keymod 15 in handguard, 2026-10/11). Its scripts are the reference
implementation: reuse and adapt them rather than starting over. `handguard/README.md` documents them.

## 0. Every run starts here (self-learning)

1. Read `LEARNINGS.md` in this skill's folder, all of it, before doing anything else. Apply every
   rule in it. Where it conflicts with this file, the newer, more specific entry wins.
2. Read the "Known-good parameters" table below and start from those values, not from defaults.
3. Follow section 9 (self-learning protocol) for the whole run: log every correction the moment it
   happens, and update this skill before the run ends.

## 1. Gather the inputs

- **Customer context**: the conversation is usually in the shop's Google Voice texts, which arrive in
  the Titan Forgeworks Gmail. Search Gmail by the customer's phone digits (both `"931"`-style area
  code and the rest, quoted) and by name. Read every text and every picture: the concept art is the
  artistic spec.
- **Scan and photos**: usually a shared Google Drive folder. Download the scan STL and the photos.
  Scans can exceed 500 MB: keep them out of git (`work/` is gitignored) and do not re-send them in
  chat (chat upload limit 500 MiB); point the user to the Drive copy instead.
- **What is bolted on the scan**: the scan often includes the customer's accessories (front sight,
  bottom accessory rail, bipod adapter). They are measurement data: extract them (section 5.5).
- **Meshy**: the API key comes from the user. Keep it only in the scratchpad, pass it as the
  `MESHY_API_KEY` environment variable, never commit it, never print it, and tell the user to rotate a
  key they pasted in chat.

## 2. Reverse-engineer the handguard (when a printed copy is wanted)

Scripts: `align_scan.py`, `measure_templates.py`, `build_handguard.py`, `verify.py`, `strength_check.py`.

- Align the scan: PCA for the long axis, bore axis from circle fits of the plain rear tube, roll
  from the rail-top normals. Work in mm with X along the bore (receiver end X = 0, muzzle +X), Z up
  (rail), +Y = the rifle's left.
- Measure what touches the gun directly (rear tube OD, barrel-nut bore, rail top height, lugs,
  clamp). Average repeated features (rail slots, keymod holes, lightening cuts) over every copy by
  unrolling the skin into (X, theta), so scan noise cancels.
- Picatinny dovetail: follow MIL-STD-1913, not the scan (scanners round the undercut).
- Model as CSG (manifold3d). Add print clearance where it must slide on the gun (+0.1 mm per side
  on the barrel-nut bore).
- Verify scan-to-model distances (median about 0.1 to 0.2 mm on fit surfaces is good) and render a
  deviation map. Red spots at hole edges and screw pockets are scanner artifacts, not model errors.
- Printed plastic is weaker than aluminium: close lightening slots into shallow recesses, thicken
  under the rail slots, use steel nuts in hex pockets instead of plastic threads, radius slit ends.
  Run the beam check (`strength_check.py`) and report safety factors honestly.
- Always provide a short fit-test print of the clamp end before the long print.

## 3. The sculpture: artistic rules (customer feedback, binding)

The concept picture is the art direction. Be faithful to it first, then make the engineering work
inside that look. "This is an artistic work; the engineering must be right, but it must resemble
the original idea."

- **Use Meshy (image-to-3D) for organic sculpture.** Hand-built SDF heads and bodies looked
  "too simplistic". Use Meshy's head; build bodies procedurally so they fit the handguard.
- **Bodies are continuous smooth curves.** No abrupt stops, no straight runs, no flat segments, no
  kinks or sudden bends anywhere on the exterior. Smooth the centreline in (X, theta) with a
  Gaussian (a helix is a straight line there, so spirals keep their shape) and check the minimum
  bend radius is at least 1.5 times the body radius. Flat surfaces are allowed only where hidden
  against the handguard (the belly cut).
- **Double helix, as drawn.** Two bodies crossing over and under each other like the concept, not a
  single spiral. Mirror-symmetric seen from above: two bodies leave the head, spiral back in
  opposite directions, and end in two tails on the top shoulders at the rear.
- **Density**: not too tight, not too sparse. Accepted: each body turns 4.5 deg per mm (a crossing
  every 40 mm, 8 crossings over 387 mm). 6 deg/mm was "too close together"; 2 to 3 deg/mm was "too
  much space".
- **Proportions**: the body must look connected to the head in full. Necks slightly thinner than
  the mid-body (accepted: 23 mm neck, 29 mm mid-body, tapering to a fine tail tip), flaring into the
  head with a wide fillet. No concavities where the neck meets the head.
- **Necks rise toward the head**: from the last crossing under the handguard, each neck angles
  diagonally up and forward into the back of the head.
- **Head**:
  - back of the head rounded; nothing in nature is square-cut;
  - nose pointed but not needle-sharp: a short, gentle taper to a rounded tip; never flat;
  - no fangs on the lower jaw; remove Meshy's own fang stubs;
  - two long upper fangs that grow from the roof of the mouth (not the nostril, not the outer
    skin), curve only forward/back (never sideways), and taper smoothly to a point with no kink;
  - fill any slit between the internal stop ring and the lower jaw with a smooth taper.
- **Symmetry**: every edit to one side is mirrored to the other unless the user says otherwise.

## 4. Fit, joints and fastening: engineering rules

- **Slide-on envelope**: subtract the handguard's outer profile with every hole, slot and flat
  filled, grown by 0.35 mm running clearance, extruded along X. The sleeve slides on from the muzzle;
  the keymod flats and the rail stop it turning. Stop the rear piece at the step where the flats
  begin if one is used.
- **Belly**: sink the body about 35 to 40 % of its height into the handguard and cut it off: the
  belly then hugs the surface. Do not sink thin parts (tails, radius under about 9 mm): put them on
  the real surface, or the cut eats through them.
- **Barrel passage**: keep a 31 mm passage straight through the head (A2 flash hider and 7/8 in
  brakes pass). Add a solid stop ring inside the head that rests on the handguard's muzzle end.
- **Two pieces, each under 256 mm** (common bed size). Split where the bodies are on the sides, and
  turn the cut plane halfway between square-to-the-body (no feather edges) and square-to-the-bore
  (pieces slide together).
- **Alignment tabs**: four tabs on the front piece, pockets in the rear piece. The user asked for
  "2 top and 2 bottom"; with the bodies on the sides at the joint they ended up two per body, left
  and right; confirm the placement with the user. Accepted tab: tapered trapezoid, 7.5 mm long,
  4.5 x 5 mm at the tip, 5 x 6.5 mm at the root, chamfered lead-in; pockets with 0.5 mm clearance
  all round and at least 1.2 mm wall.
- **Bolting**: bolt where the handguard already has holes, never where it has none. Accepted: one
  M5 socket head cap screw on the left and one on the right of each piece, at the same X, into
  brass heat-set inserts (M5 x 5.8, 7.0 OD, 6.4 mm hole), through the side keymod holes. The rear
  piece's screws bear on the rear end of their holes (stops it moving back), the front piece's on
  the front end (stops recoil pushing it forward). The screw tip ends inside the handguard wall,
  never at the barrel (free float). Pick lengths so the head seats in a counterbore with material
  all round (accepted: M5 x 12 rear, M5 x 16 front).
- **Easy on, easy off**: nothing needs more than a hex key. The handguard stays on the rifle.

## 5. Accessories: always check them in their real positions

- **Measure accessories from the scan.** If the scan shows a sight, rail or bipod adapter, slice it
  out and use its real size. Do not guess with a stand-in when the scan has the part.
- **Front sight**: keep the top rail clear behind the head. When the customer moves the sight, trim
  only where the clash is (the location the customer validated), sized from the scanned sight with
  at least 2 mm clearance all round, ends ramped at 45 deg, both sides. Accepted: trim 40 mm wide,
  from 9.6 mm below the rail top, over the 2nd and 3rd rail slots from the muzzle.
- **Bipod (standard)**: keep the bottom clear around the keymod hole it uses.
- **Bipod rail version**: when asked to "crop / delete" the bottom, make one clean, straight, level
  cut, exactly as asked, along the length asked. Place it 3 to 4 mm above the handguard's bottom face
  (a cut level with the face leaves feather-thin edges). If the cut detaches a loop, add a small
  bridge strip just above the cut so each piece stays one part.
- **Check every accessory change** by intersecting the final pieces with the accessory volume,
  grown by 0.5, 1, 2 mm; report the clearance found.

## 6. Printability and verification (run before every delivery)

- 0.4 mm nozzle, 0.2 mm layers. Features thinner than 1.2 mm are removed (morphological opening at
  build time); `thin_check.py` reports what is left under 2 mm and 1.2 mm.
- `fragment_check.py` must report 0 fragments joined by bridges under 0.8 mm.
- Each piece one part, watertight, no zero-area slivers (`strip_slivers`), zero overlap with the
  handguard, with each other, and with any accessory volume; pieces slide into place without
  collision (sweep test).
- Voxel build at 0.5 mm for drafts and previews, 0.25 mm for final files. Cache the voxel mesh
  (`--cache`) so joint/bolt/trim changes rebuild in under 2 minutes. Run long builds detached
  (`setsid nohup`) with thin slabs to stay under the memory limit.
- Material: the shop prints the sleeve in **polycarbonate (PC)**: insert iron about 280 C, keep
  anaerobic threadlockers and solvents off it (plastic-safe threadlocker, or blue on the tip only).

## 7. Showing the work

- The user is often on a phone: put pictures in the chat (SendUserFile, display render) or an
  artifact page, not just file paths. Send files they ask to download directly.
- For each edit, show before/after views from the angle the user's screenshot used, with removed
  material in red and accessories (from the scan) in black.
- Renders: orthographic, sampled-surface renderer (`render_util.py`, `assembly_guide.Scene`).

## 8. Manuals and documents

- Style: plain, black and white, Times New Roman, no colour. Word (.docx via the `docx` npm package)
  plus a PDF export. Pull every number from the build outputs (`data/*.json`, measured meshes),
  never type dimensions by hand.
- **Customer manual**: no customer names. Assume the buyer owns the handguard and its hardware.
  The kit is the two pieces, four pre-installed heat-set inserts and four screws; still list
  replacement specs for inserts and screws.
- **Commercial manual**: cover, contents, safety notices (WARNING/CAUTION/NOTE panels), overview and
  versions, kit contents, specifications table, material specifications and chemical compatibility,
  dimensioned drawings, cross-sections with width/height tables, detail views, tools, how each
  movement is locked, installation, accessories, torque, inspection schedule, insert replacement,
  care and storage, troubleshooting, removal, replacement parts, disclaimer. Keep a document number
  and bump the revision on every change.
- Use the user's own wording when they supply a sentence (light copy-editing only, and say so).
- Keep one manual set unless the user wants a quick-start sheet as well; ask.
- Assembly guide image: parts and hardware, inserts, each fitting step with arrows, close-ups of the
  joint and a bolt cross-section, and an end view showing why it cannot spin or come off.

## 9. Self-learning protocol

The skill improves from every run. `LEARNINGS.md` (same folder) is its memory.

**During the run**
- Every time the user corrects, rejects, re-annotates or repeats a request, append an entry to
  `LEARNINGS.md` at once (do not wait for the end), in this form:
  `- YYYY-MM-DD [area] What I did -> what the user wanted. Rule: <general rule>. (seen N times)`
  Areas: art, head, body, fit, joint, bolts, accessories, print, manual, process, communication.
- Every time the user approves a result ("looks great", "done", "right"), record the parameter values
  that produced it in the Known-good parameters table below, with the job name and date.
- If the same correction already exists, increase its count instead of adding a duplicate.

**Before ending the run**
1. Re-read the entries added this run. Promote any entry seen twice or more, or stated by the user as
   a rule ("always", "never", "nothing in nature..."), into the matching section of this SKILL.md,
   then mark the entry `[promoted]`.
2. If a newer instruction contradicts a rule here, update the rule and mark the old one superseded
   in `LEARNINGS.md` with the date (never silently delete history).
3. Update the Known-good parameters table.
4. Commit `SKILL.md` and `LEARNINGS.md` with the job's other changes.

**Never record** API keys, passwords, customer phone numbers or addresses. Refer to customers by
job name, not personal details.

## Known-good parameters

| Parameter | Value | Job / status |
|---|---|---|
| Fit clearance, sleeve to handguard | 0.35 mm per side | KMX-15 snake, 2026-10, test-fitted |
| Helix rate | 4.5 deg/mm (crossing every 40 mm) | KMX-15 snake, approved |
| Body radius neck / mid / tail tip | 11.5 / 14.5 / 1.4 mm (+3.5 mm flare into head) | approved |
| Body height / width (flattened ellipse) | 0.82 | approved |
| Belly sink | 35 % of body height | approved |
| Centreline smoothing | 10 mm Gaussian, min bend radius >= 1.5 x body radius | approved |
| Head blend fillet | 9 mm | approved |
| Barrel passage | 31 mm | approved |
| Pieces | 218.6 mm and 237.1 mm, joint at 227.8 mm | approved |
| Tabs | 7.5 long, tip 4.5 x 5, root 5 x 6.5, 0.5 clearance, 1.2 wall | approved |
| Screws | M5 x 12 rear, M5 x 16 front, 1.5 N m (max 2.0), inserts M5 x 5.8 | approved |
| Sight trim (2nd slot from muzzle) | 40 mm wide, Z > 21.5 (9.6 below rail top), X 338 to 384 | 2 mm clearance, approved location |
| Bipod rail cut | level, 3.6 mm above bottom face, full length; bridges X 77 to 97 | approved |
| Insert iron, PC | 280 C | |
| Min feature / fragment bridge | 1.2 mm / 0.8 mm | |
| Voxel size draft / final | 0.5 / 0.25 mm | |
