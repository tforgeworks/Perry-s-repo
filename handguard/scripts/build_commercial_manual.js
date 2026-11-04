// Commercial user manual for the Snake Handguard Kit (both versions):
// manual/commercial/Snake_Handguard_Kit_User_Manual.docx. Plain black and white, Times New Roman.
// Dimensions come from manual/commercial/measurements.json (written by commercial_figures.py) and from
// data/snake_lock.json and data/bipod_rail.json; nothing is typed in by hand that the 3D files define.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  BorderStyle, ImageRun, AlignmentType, LevelFormat, PageBreak, Footer, Header, PageNumber,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const OUT = path.join(ROOT, "manual", "commercial");
const M = JSON.parse(fs.readFileSync(path.join(OUT, "measurements.json")));
const LOCK = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "snake_lock.json")));
const RL = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "bipod_rail.json")));
const FONT = "Times New Roman";
const DOC_NO = "TF-SHK-UM", REV = "Revision B", DATE = "November 2026";
const X_END = 387.4;                                        // front end of the handguard, from its rear face
const f1 = (v) => Number(v).toFixed(1);
const fromFront = (x) => X_END - x;

const rb = LOCK.bolts.rear[0], fb = LOCK.bolts.front[0];
const len = (b) => b.screw.split(" ")[0].split("x")[1];   // "12"
const [TAB_W, TAB_H, TAB_L] = LOCK.tab_size_mm, [ROOT_W, ROOT_H] = LOCK.tab_root_mm, TAB_CLR = LOCK.tab_clearance_mm;
const holeNo = (b) => b.bears_on.startsWith("rear")
  ? Math.round((b.hole_end_x - 70.46) / 20) + 1 : Math.round((b.hole_end_x - 87.95) / 20) + 1;
const ord = (n) => n + (n === 1 ? "st" : n === 2 ? "nd" : n === 3 ? "rd" : "th");

// ---------- helpers
const t = (text, o = {}) => new TextRun({ text, font: FONT, color: "000000", ...o });
const b = (text) => t(text, { bold: true });
const p = (runs, o = {}) => new Paragraph({ children: (Array.isArray(runs) ? runs : [runs]).map((r) => (typeof r === "string" ? t(r) : r)), spacing: { after: 120 }, ...o });
const h1 = (text, brk = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: brk, children: [t(text)] });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(text)] });
const bullet = (runs) => p(runs, { numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 } });
const stepLists = []; let stepRef = 0;
const steps = (items) => { const ref = "steps" + (stepRef++); stepLists.push(ref); return items.map((r) => p(r, { numbering: { reference: ref, level: 0 }, spacing: { after: 90 } })); };
const boxed = (label, text) => new Table({   // WARNING / CAUTION / NOTE panel
  width: { size: 9360, type: WidthType.DXA }, columnWidths: [1500, 7860],
  rows: [new TableRow({ children: [
    new TableCell({ borders, width: { size: 1500, type: WidthType.DXA }, margins: { top: 80, bottom: 80, left: 100, right: 100 }, children: [new Paragraph({ children: [b(label)] })] }),
    new TableCell({ borders, width: { size: 7860, type: WidthType.DXA }, margins: { top: 80, bottom: 80, left: 100, right: 100 }, children: [new Paragraph({ children: [t(text)] })] }),
  ] })],
});
const gap = () => p("", { spacing: { after: 80 } });
const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(widths, rows, header = true) {
  const total = widths.reduce((a, c) => a + c, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((row, i) => new TableRow({
      tableHeader: header && i === 0, cantSplit: true,
      children: row.map((cell, j) => new TableCell({
        borders, width: { size: widths[j], type: WidthType.DXA }, margins: { top: 50, bottom: 50, left: 90, right: 90 },
        children: (Array.isArray(cell) ? cell : [cell]).map((c) => new Paragraph({ children: [typeof c === "string" ? t(c, { bold: header && i === 0, size: 20 }) : c] })),
      })),
    })),
  });
}
function figure(file, caption, widthIn = 6.3, maxH = 7.4) {
  const f = path.join(file.includes("/") ? ROOT : OUT, file);
  const buf = fs.readFileSync(f);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  let W = widthIn * 96, H = (W * h) / w;
  if (H > maxH * 96) { W *= (maxH * 96) / H; H = maxH * 96; }
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: Math.round(W), height: Math.round(H) }, altText: { title: caption, description: caption, name: path.basename(file) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 220 }, children: [t(caption, { italics: true, size: 19 })] }),
  ];
}
let figNo = 0; const fig = (file, cap, w, mh) => figure(file, `Figure ${++figNo}. ${cap}`, w, mh);

// ---------- numbers
const O = M.overall, W_ = M.widest;
const sRear = M.rear, sHead = M.front, bRear = M.rear_bipod_rail, bHead = M.front_bipod_rail;
const bipodHeight = Math.max(bRear.height, bHead.height);
const screwFromRear = (b0) => f1(b0.x - 0.2), screwFromFront = (b0) => f1(fromFront(b0.x));
const sight = M.sight, cutAbove = M.bipod_rail.cut_above_bottom_face;
const secRows = (key) => [["Station (from the handguard's rear face)", "From the front end", "Width", "Height"]]
  .concat(M[key].map((r) => [`${f1(r.x)} mm`, `${f1(r.from_front)} mm`, `${f1(r.width)} mm`, `${f1(r.height)} mm`]));

const body = [
  // ---------------- cover
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 120 }, children: [t("TITAN FORGEWORKS", { size: 26, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [t("Snake Handguard Kit", { size: 56, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [t("User Manual", { size: 36 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [t("Standard version and Bipod Rail version, for the Trinity Force KMX-15 keymod free-float handguard (15 in)", { size: 22 })] }),
  ...figure("cover.png", "", 6.5, 4.5).slice(0, 1),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 }, children: [t(`${DOC_NO}  |  ${REV}  |  ${DATE}`, { size: 20 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [t("Read this manual completely before installing. Keep it with the rifle.", { size: 20, italics: true })] }),

  // ---------------- contents
  h1("Contents"),
  ...["1. Safety information", "2. Product overview", "3. Kit contents", "4. Specifications", "5. Material specifications",
      "6. Dimensions and drawings", "7. Cross-sections", "8. Tools and supplies", "9. How the snake is secured", "10. Installation",
      "11. Accessories: front sight and bipod", "12. Torque values", "13. Inspection and maintenance", "14. Care, cleaning and storage",
      "15. Troubleshooting", "16. Removal", "17. Replacement parts and hardware", "18. Disclaimer and contact"].map((s) => p(s, { spacing: { after: 60 } })),

  // ---------------- 1
  h1("1. Safety information"),
  p("This manual uses the following notices:"),
  boxed("WARNING", "A hazard that could result in serious injury or death if the instruction is not followed."), gap(),
  boxed("CAUTION", "A hazard that could damage the product, the handguard or the rifle."), gap(),
  boxed("NOTE", "Information that makes installation or use easier."), gap(),
  boxed("WARNING", "Unload the rifle before any work. Remove the magazine, lock the bolt open, and check the chamber and magazine well by sight and by touch. Keep ammunition out of the work area."), gap(),
  boxed("WARNING", "Nothing in this kit may touch the barrel. The handguard is free floating. Do the free-float check (section 10.4) after every installation, and do not fire the rifle if anything touches the barrel."), gap(),
  boxed("WARNING", "Do not fire the rifle with a snake piece that is loose, cracked, missing a screw, or with threadlocker that has not cured."), gap(),
  boxed("CAUTION", "Polycarbonate can crack when it touches many solvents, cleaners and anaerobic threadlockers. Read sections 5.2 and 14 before cleaning the rifle with the snake installed."), gap(),
  bullet("The snake is a cosmetic sleeve. It does not change how the rifle, the handguard or the barrel work, and it is not a load-bearing part. Do not use it as a rest, a handle or a carry point."),
  bullet("Follow all laws that apply to modifying and using firearms where you live."),

  // ---------------- 2
  h1("2. Product overview"),
  p("The Snake Handguard Kit is a two-piece sculpted sleeve that slides over the Trinity Force KMX-15 keymod free-float handguard. Two mirror-image snake bodies spiral along the handguard in a double helix, cross each other eight times, and join a single head that sits in front of the handguard with the barrel passing through its open mouth. The two tails end on the top of the handguard near the receiver."),
  p("The sleeve slides on from the muzzle end, is aligned by four tapered tabs at the joint between its two pieces, and is held by four M5 screws that seat in the handguard's own side keymod holes. Nothing on the handguard, the barrel nut or the barrel is changed."),
  h2("2.1 Versions"),
  table([2200, 3580, 3580], [
    ["", "Standard version", "Bipod Rail version"],
    ["Bottom of the handguard", "The snake's bodies pass under the handguard (four loops).", `The snake is cut away along the whole bottom in one straight, level line, ${f1(cutAbove)} mm above the handguard's bottom face.`],
    ["Bipod", "On the 4th bottom keymod hole from the muzzle end, with a keymod bipod adapter.", "On a Picatinny accessory rail on the bottom keymod holes, anywhere along the bottom. Rail and bipod go on and off with the snake installed."],
    ["Pieces", `A rear piece ${f1(sRear.length)} mm, B head piece ${f1(sHead.length)} mm`, `A rear piece ${f1(bRear.length)} mm, B head piece ${f1(bHead.length)} mm`],
    ["Everything else", "Identical: fit, screws, tabs, front sight clearance, materials.", "Identical: fit, screws, tabs, front sight clearance, materials."],
  ]),
  h2("2.2 Compatibility"),
  bullet([b("Handguard: "), t("Trinity Force KMX-15 keymod free-float handguard, 15 in (KM-34812-15), installed as its maker instructs. Other handguards will not fit.")]),
  bullet([b("Muzzle device: "), t("up to 31 mm in diameter can stay on (for example an A2 flash hider or a 7/8 in brake). A larger one must be removed while the snake is fitted or removed.")]),
  bullet([b("Front sight: "), t(`a rail-clamp front sight in the 2nd rail slot from the muzzle end, up to ${sight.trim_width - 6} mm wide over its clamp and knob (see section 11).`)]),
  bullet([b("Bipod: "), t("see the version table above.")]),

  // ---------------- 3
  h1("3. Kit contents"),
  table([2900, 700, 5760], [
    ["Item", "Qty", "Description"],
    ["A  Snake rear piece", "1", "The tails and the rear half of both bodies. Four tab pockets at its front end. One screw hole on each side, each with an M5 heat-set insert installed."],
    ["B  Snake head piece", "1", "The head and the front half of both bodies. Four alignment tabs at its rear end. One screw hole on each side, each with an M5 heat-set insert installed."],
    [`M5 x ${len(rb)} socket head cap screws`, "2", "For the rear piece A."],
    [`M5 x ${len(fb)} socket head cap screws`, "2", "For the head piece B."],
    ["User manual", "1", "This document."],
  ]),
  gap(),
  boxed("CAUTION", `Use the ${len(rb)} mm screws only in piece A and the ${len(fb)} mm screws only in piece B. A longer screw can reach the barrel; a shorter one does not reach the keymod hole and does not lock the piece.`),
  ...fig("exploded.png", "The kit's two pieces and the handguard they fit (handguard not included)."),

  // ---------------- 4
  h1("4. Specifications"),
  p("All dimensions in millimetres. Positions along the handguard are measured from its rear face (the end at the receiver) unless stated otherwise."),
  table([3900, 2730, 2730], [
    ["Property", "Standard version", "Bipod Rail version"],
    ["Overall length of the snake, installed", `${f1(O.length)}`, `${f1(O.length)}`],
    ["Head projection past the handguard's front end", `${f1(O.overhang)}`, `${f1(O.overhang)}`],
    ["Overall width, installed", `${f1(O.width)}`, `${f1(O.width)}`],
    ["Overall height, installed", `${f1(O.height)}`, `${f1(bipodHeight)}`],
    ["Rear piece A (length x width x height)", `${f1(sRear.length)} x ${f1(sRear.width)} x ${f1(sRear.height)}`, `${f1(bRear.length)} x ${f1(bRear.width)} x ${f1(bRear.height)}`],
    ["Head piece B (length x width x height)", `${f1(sHead.length)} x ${f1(sHead.width)} x ${f1(sHead.height)}`, `${f1(bHead.length)} x ${f1(bHead.width)} x ${f1(bHead.height)}`],
    ["Material volume, A / B", `${f1(sRear.volume_cm3)} / ${f1(sHead.volume_cm3)} cm3`, `${f1(bRear.volume_cm3)} / ${f1(bHead.volume_cm3)} cm3`],
    ["Weight, A + B (maximum, at full density)", `${sRear.mass_solid_g + sHead.mass_solid_g} g`, `${bRear.mass_solid_g + bHead.mass_solid_g} g`],
    ["Joint between A and B", `${f1(LOCK.joint_x - 0.2)} from the rear face`, `${f1(LOCK.joint_x - 0.2)} from the rear face`],
  ]),
  gap(),
  table([3900, 5460], [
    ["Fit and fastening", "Value"],
    ["Fit on the handguard", "Inside of each piece = outside of the handguard (keymod flats, rail, round rear section) plus 0.35 mm clearance per side. Slides on from the muzzle end; cannot rotate."],
    ["Barrel passage through the head", `Ø${2 * 15.5} mm`],
    ["Screws", `4 x M5 x 0.8 socket head cap screws in brass heat-set inserts: A ${len(rb)} mm, B ${len(fb)} mm`],
    ["Screw positions, rear piece A", `${screwFromRear(rb)} from the rear face; one each side; tip at the rear end of the ${ord(holeNo(rb))} side keymod hole from the rear`],
    ["Screw positions, head piece B", `${screwFromRear(fb)} from the rear face (${screwFromFront(fb)} from the front end); one each side; tip at the front end of the ${ord(holeNo(fb))} side keymod hole from the rear`],
    ["Screw tip", "Ends inside the handguard's side wall, 16.5 mm from the bore axis; never reaches the barrel"],
    ["Alignment", `4 tapered tabs on B: ${TAB_W} x ${TAB_H} at the tip, ${ROOT_W} x ${ROOT_H} at the root, ${TAB_L} long; matching pockets in A with ${TAB_CLR} clearance all round`],
    ["Front sight clearance", `Necks trimmed ${f1(sight.trim_x[0])} to ${f1(sight.trim_x[1])} from the handguard's front end, ${sight.trim_width} wide, from ${f1(sight.trim_z)} above the bore axis (${f1(31.1 - sight.trim_z)} below the rail top)`],
    ["Bottom (Bipod Rail version)", `Cut away along the whole bottom, ${f1(cutAbove)} above the handguard's bottom face`],
    ["Surface", "Keeled, overlapping snake scales, about 1 mm deep"],
  ]),

  // ---------------- 5
  h1("5. Material specifications"),
  h2("5.1 Material"),
  p("Both pieces are made of polycarbonate (PC) by fused-filament 3D printing at 0.2 mm layer height with a 0.4 mm nozzle. Polycarbonate is tough, impact resistant and keeps its shape at the temperatures a handguard reaches in normal use. Polycarbonate is chosen because it is extremely durable and resilient yet light as a feather, so it does not affect the feel and physics of the gun during each shot."),
  table([4200, 2400, 2760], [
    ["Property (typical for printing-grade polycarbonate)", "Typical value", "Notes"],
    ["Density", "1.20 g/cm3", ""],
    ["Glass transition temperature", "about 145 to 150 C", "The material softens above this."],
    ["Heat deflection temperature (0.45 MPa)", "about 110 to 135 C", "Depends on the filament grade."],
    ["Tensile strength, along the layers", "about 50 to 65 MPa", "Lower across the layers."],
    ["Impact resistance", "High", "Tough; does not shatter."],
    ["Water absorption", "Low (about 0.2 %)", "Not affected by rain or humidity."],
    ["UV resistance", "Moderate", "Can yellow slowly with long sun exposure; does not weaken in normal use."],
  ]),
  p("Values are typical for printing-grade polycarbonate and are given for guidance; they are not guaranteed minimums. Printed parts are strongest along their layers.", { spacing: { before: 100, after: 120 } }),
  h2("5.2 Chemical compatibility"),
  table([3200, 6160], [
    ["Safe", "Water; mild dish soap and water; isopropyl alcohol (brief wipe, then dry); silicone-free plastic-safe protectants; plastic-safe threadlockers (for example Vibra-TITE VC-3 Threadmate)."],
    ["Wipe off promptly", "Gun oil, CLP and lubricants: they are usually harmless in small amounts but can stress-crack the plastic if left on it, especially around the screw holes."],
    ["Avoid", "Acetone and other ketones (MEK), brake and parts cleaners, carburettor cleaner, paint thinners and strippers, aromatic solvents (toluene, xylene), ammonia-based and strong alkaline cleaners, most bore solvents and copper removers, aerosol lubricants and degreasers, anaerobic (methacrylate) threadlockers such as Loctite 243 if they touch the plastic."],
  ], false),
  h2("5.3 Hardware"),
  table([3000, 6360], [
    ["Heat-set inserts (4, installed)", "M5 x 0.8, brass, knurled, 5.8 mm long, 7.0 mm outside diameter, in a 6.4 mm hole."],
    ["Screws (4, supplied)", `M5 x 0.8 socket head cap screws, ISO 4762 (DIN 912), alloy steel class 12.9, black oxide; 8.5 mm head, 4 mm hex socket; ${len(rb)} mm (A) and ${len(fb)} mm (B) long.`],
  ], false),

  // ---------------- 6
  h1("6. Dimensions and drawings"),
  p("The drawings show the snake installed on the handguard (handguard shown light, not included). Dimensions in millimetres."),
  ...fig("dims_side.png", "Installed, rifle's left side: overall length, head projection, joint position and overall height. Circles: screw positions (one screw on each side of each piece)."),
  ...fig("dims_top.png", "Installed, from above: overall width, the front sight in the 2nd rail slot (black, measured from the rifle), and the trimmed zone beside the rail."),
  ...fig("dims_front.png", "From the muzzle: overall width and height of the head and the 31 mm barrel passage.", 4.6),
  h2("6.1 The pieces"),
  ...fig("piece_rear.png", "Rear piece A, standard version.", 6.0, 2.6),
  ...fig("piece_front.png", "Head piece B, standard version.", 6.0, 2.6),
  ...fig("piece_rear_bipod_rail.png", "Rear piece A, Bipod Rail version.", 6.0, 2.6),
  ...fig("piece_front_bipod_rail.png", "Head piece B, Bipod Rail version.", 6.0, 2.6),
  h2("6.2 Details"),
  ...fig("manual/fig_joint.png", "The joint between A (left) and B (right), pulled apart: the four tapered tabs on B (black) and their pockets in A.", 5.0),
  ...fig("manual/fig_bolt_section.png", "Cut across the head piece's screws, seen from the muzzle: each screw passes through an insert and its tip ends in a keymod hole in the handguard wall, clear of the barrel.", 4.6),
  ...fig("sight_detail.png", "The front sight (black, measured from the rifle) in the 2nd rail slot, with the necks trimmed beside the rail for its clamp and knob.", 5.0),
  ...fig("sight_section.png", "Section through the sight clamp: at least 2 mm clearance all round.", 4.8),
  ...fig("bipod_bottom.png", "Bipod Rail version from below: the bottom of the handguard is fully open for an accessory rail and bipod."),

  // ---------------- 7
  h1("7. Cross-sections"),
  p("Sections through the installed snake at six stations along the handguard, seen from the muzzle. Each figure gives the snake's overall width and height at that station."),
  ...fig("sections_standard.png", "Cross-sections, standard version.", 6.5, 6.2),
  table([3300, 2020, 2020, 2020], secRows("sections_standard")),
  ...fig("sections_bipod_rail.png", "Cross-sections, Bipod Rail version.", 6.5, 6.2),
  table([3300, 2020, 2020, 2020], secRows("sections_bipod_rail")),

  // ---------------- 8
  h1("8. Tools and supplies"),
  table([4700, 4660], [
    ["Required", "Recommended"],
    ["4 mm hex key or hex bit", "Torque screwdriver, 1 to 3 N m, with a 4 mm hex bit"],
    ["Medium-strength removable threadlocker safe on plastics (for example Vibra-TITE VC-3 Threadmate)", "Paint marker, for witness marks"],
    ["Isopropyl alcohol and cotton swabs (degreasing the screws)", "Strip of printer paper, for the free-float check"],
    ["The tools your sight, bipod and muzzle device need (not covered here)", "Padded vise block or bench mat"],
  ]),
  gap(),
  boxed("CAUTION", "If you use an anaerobic blue threadlocker (such as Loctite 243) instead of a plastic-safe one, use only a very small amount on the screw tip and never let it touch the snake: it can crack polycarbonate."),

  // ---------------- 9
  h1("9. How the snake is secured"),
  table([3600, 5760], [
    ["Movement", "What stops it"],
    ["Turning around the handguard", "The inside of each piece matches the handguard's keymod flats and rail."],
    ["Coming off sideways", "Standard version: each piece is a closed tube around the handguard. Bipod Rail version: each piece wraps more than halfway around (an opening of about 27 mm along the bottom against a 36 mm handguard), so it can only slide along the handguard."],
    ["Rear piece A moving back", `Its two screws, which rest on the rear ends of the ${ord(holeNo(rb))} side keymod holes from the rear.`],
    ["Rear piece A moving forward", "The head piece B in front of it."],
    ["Head piece B moving forward (recoil)", `Its two screws, which rest on the front ends of the ${ord(holeNo(fb))} side keymod holes from the rear. Piece A pushes on B, so these screws hold both pieces under recoil.`],
    ["Head piece B moving back", "The solid ring inside the head rests on the front end of the handguard."],
    ["A and B shifting against each other", "The four tapered tabs in their pockets."],
    ["Screws working loose", "Threadlocker, the torque in section 12, brass inserts (no plastic threads) and witness marks checked after firing."],
  ]),

  // ---------------- 10
  h1("10. Installation"),
  h2("10.1 Before you install"),
  ...steps([
    ["Unload the rifle (section 1)."],
    ["Check that the handguard is installed and tight as its maker instructs."],
    ["Remove everything mounted on the handguard: front sight, bipod and bipod mount or accessory rail, lights, rail covers and keymod accessories."],
    ["Remove the muzzle device if it is wider than 31 mm."],
    ["Check the inside of both pieces, the screw holes and the tab pockets for dust or debris, and blow them clean."],
  ]),
  h2("10.2 Rear piece A"),
  ...steps([
    ["Slide piece A over the muzzle, tails first, and along the handguard. It slides like a sleeve; do not force it."],
    [`Slide it back until a side keymod hole shows through the screw hole on each side (the ${ord(holeNo(rb))} keymod hole counted from the rear).`],
    [`Degrease the two M5 x ${len(rb)} screws, put a small amount of threadlocker on the last 3 to 4 threads at the tip (keep it off the snake), and screw one in on each side by hand until the tips enter the keymod holes.`],
    ["Push piece A back toward the receiver and hold it there, so the screw tips rest against the rear ends of their keymod holes."],
    ["Tighten both screws to 1.5 N m. Do not exceed 2.0 N m."],
  ]),
  h2("10.3 Head piece B"),
  ...steps([
    ["Slide piece B over the muzzle (the barrel and muzzle device pass through the open mouth) and back along the handguard."],
    ["As it reaches piece A, line up its four tabs with the four pockets in A and push it home. The tapered tabs find the pockets and slide in with light hand pressure."],
    ["Push piece B back until the inside of the head rests on the front end of the handguard and the faces of A and B meet with an even, hairline gap."],
    [`Degrease the two M5 x ${len(fb)} screws, apply threadlocker as above, and screw one in on each side (the ${ord(holeNo(fb))} keymod hole counted from the rear).`],
    ["Push piece B back and hold it while tightening both screws to 1.5 N m (maximum 2.0 N m)."],
  ]),
  h2("10.4 Final checks"),
  ...steps([
    ["Grip the snake at the head and at the tails and try to twist it, push it and pull it. Nothing may move or click."],
    ["Free float: slide the paper strip all the way around the barrel inside the head and at the front end of the handguard. It must pass freely everywhere."],
    ["Make a paint witness mark across each screw head and the snake next to it."],
    ["Let the threadlocker cure as its maker states (typically 24 hours) before firing."],
    ["Install the front sight and the bipod (section 11)."],
  ]),

  // ---------------- 11
  h1("11. Accessories: front sight and bipod"),
  h2("11.1 Front sight"),
  p(`Mount a rail-clamp front sight on the top rail right behind the head, with its clamp in the 2nd rail slot counted from the muzzle end. The necks beside the rail are trimmed for the sight's clamp and clamp knob over ${f1(sight.trim_x[0])} to ${f1(sight.trim_x[1])} mm from the handguard's front end, ${sight.trim_width} mm wide and down to ${f1(31.1 - sight.trim_z)} mm below the rail top. The front sight the kit was designed around (34.2 mm wide over its knob) has at least 2 mm clearance all round. Install the sight after the snake, as its maker instructs.`),
  h2("11.2 Bipod, standard version"),
  p("Mount the bipod on the 4th bottom keymod hole counted from the muzzle end, with a standard keymod bipod adapter. The snake leaves this hole clear. Install it after the snake."),
  h2("11.3 Bipod, Bipod Rail version"),
  p("Bolt a Picatinny accessory rail to the bottom keymod holes as its maker instructs, and clamp the bipod onto it. The snake is cut away along the whole bottom, so the rail can go anywhere along it, its screws are open to reach, and the rail and bipod go on and come off with the snake installed."),

  // ---------------- 12
  h1("12. Torque values"),
  table([4200, 2200, 2960], [
    ["Screw", "Torque", "Notes"],
    [`M5 x ${len(rb)}, rear piece A (2)`, "1.5 N m (max 2.0)", "Piece held back while tightening; threadlocker"],
    [`M5 x ${len(fb)}, head piece B (2)`, "1.5 N m (max 2.0)", "Piece held back while tightening; threadlocker"],
    ["Handguard, sight, bipod, accessory rail", "As their makers instruct", "Not covered by this manual"],
  ]),
  gap(),
  boxed("CAUTION", "More than 2.0 N m can pull a heat-set insert out of the plastic."),

  // ---------------- 13
  h1("13. Inspection and maintenance"),
  table([3000, 6360], [
    ["When", "Check"],
    ["Before each range trip", "Witness marks in line; no cracks, especially around the screw holes, the tabs and the jaw; snake does not move when pushed or twisted."],
    ["After the first 50 rounds", "Witness marks; re-torque any screw whose mark has moved (remove it, clean, fresh threadlocker)."],
    ["Every 500 rounds or 6 months", "Remove the snake (section 16), clean it and the handguard (section 14), inspect for cracks and wear, re-install with fresh threadlocker."],
    ["After a hard knock or drop", "Inspect for cracks; do the free-float check."],
  ]),
  h2("13.1 Replacing a heat-set insert"),
  p("The inserts come installed. If one ever comes loose or is damaged:"),
  ...steps([
    ["Remove the snake piece from the rifle. Heat the old insert with a soldering iron and pull it out with pliers while it is hot; let the hole cool."],
    ["Set the soldering iron to 280 C (for polycarbonate). Put the new insert on the 6.4 mm hole at the bottom of the wide screw hole, small end down, straight and square."],
    ["Press it in slowly, keeping it straight, until its top is flush with the floor of the wide hole. Lift the iron straight off."],
    ["While still soft, press the top of the insert flat with a cool flat tool for 10 seconds, then let it cool for 5 minutes."],
    ["Check that the screw for that piece turns in freely by hand and its head sits down on the insert."],
  ]),
  ...fig("manual/fig_insert.png", "A heat-set insert at the bottom of a screw hole (rear piece, left side).", 3.8),

  // ---------------- 14
  h1("14. Care, cleaning and storage"),
  bullet("Clean the snake with a soft brush and a cloth dampened with mild soap and water, then dry it. A brief wipe with isopropyl alcohol is acceptable."),
  bullet("Clean the rifle with the snake removed, or cover the snake while you use bore cleaners, solvents or aerosol lubricants (section 5.2). Wipe off any oil that gets on the snake straight away."),
  bullet("Let the rifle cool between long strings of rapid fire. Do not let the snake touch heat sources above 100 C."),
  bullet("Store the rifle out of long direct sunlight to slow yellowing. Store spare screws in a dry place."),
  bullet("Do not paint or coat the snake with solvent-based paints. Use only coatings stated to be safe on polycarbonate."),

  // ---------------- 15
  h1("15. Troubleshooting"),
  table([3100, 3100, 3160], [
    ["Problem", "Likely cause", "Remedy"],
    ["A piece will not slide on", "Debris or a burr inside; muzzle device too large", "Clean the inside; remove a muzzle device wider than 31 mm; do not force it."],
    ["The tabs will not enter the pockets", "Pieces rotated slightly; debris in a pocket", "Pull B forward a little, line the tabs up by eye, clean the pockets, push home."],
    ["No keymod hole under a screw hole", "Piece not pushed far enough back", "Slide the piece back until the hole lines up (section 10)."],
    ["A screw turns but does not tighten", "Insert pulled out or stripped", "Replace the insert (section 13.1); do not exceed 2.0 N m."],
    ["The snake moves or clicks", "Screw loose; piece not held back while tightening", "Remove, clean, re-apply threadlocker, hold the piece back, tighten to 1.5 N m."],
    ["The front sight will not seat", "Sight in the wrong slot; sight wider than the trimmed zone", "Use the 2nd rail slot from the muzzle; check the sight's width (section 11.1)."],
    ["Bipod rail will not fit (standard version)", "The standard version covers the bottom", "Use the keymod bipod position (section 11.2) or the Bipod Rail version."],
    ["The paper strip catches on the barrel", "Something is touching the barrel", "Do not fire. Remove the snake and check the handguard installation and the screw lengths."],
    ["A crack in the snake", "Impact or chemical attack", "Do not fire with it installed. Replace the piece."],
  ]),

  // ---------------- 16
  h1("16. Removal"),
  ...steps([
    ["Unload the rifle (section 1). Remove the front sight, the bipod (and, on the standard version, its keymod mount) and, if needed, the muzzle device."],
    ["Remove the two screws of head piece B (if tight, a short, sharp turn of the hex key breaks the threadlocker). Pull B forward off the muzzle."],
    ["Remove the two screws of rear piece A and pull A forward off the muzzle."],
    ["Before re-installing, clean old threadlocker off the screws and inserts with a brush and isopropyl alcohol and use fresh threadlocker."],
  ]),

  // ---------------- 17
  h1("17. Replacement parts and hardware"),
  table([3300, 6060], [
    ["Part", "Specification"],
    ["Heat-set insert", "M5 x 0.8 internal thread, brass, knurled, for plastics, 5.8 mm long, 7.0 mm outside diameter, for a 6.4 mm hole (for example ruthex RX-M5x5.8 or CNC Kitchen M5 standard)."],
    ["Screw, rear piece A", `M5 x 0.8 x ${len(rb)} mm socket head cap screw, ISO 4762 (DIN 912), alloy steel class 12.9, black oxide.`],
    ["Screw, head piece B", `M5 x 0.8 x ${len(fb)} mm socket head cap screw, ISO 4762 (DIN 912), alloy steel class 12.9, black oxide.`],
    ["Snake pieces", "Rear piece A and head piece B are available separately; state the version (standard or Bipod Rail)."],
  ]),

  // ---------------- 18
  h1("18. Disclaimer and contact"),
  p("The Snake Handguard Kit is a cosmetic accessory. It must be installed and used as this manual describes, on a correctly installed Trinity Force KMX-15 handguard, by a person who handles firearms safely. Titan Forgeworks is not responsible for damage or injury caused by incorrect installation, modification of the product, use of the wrong hardware, chemical damage, or use outside the instructions in this manual."),
  p("Trinity Force and KMX-15 are names of their respective owner. This kit is not made, endorsed or supported by the handguard's maker."),
  p([b("Titan Forgeworks"), t("  |  titan-forgeworks.com")], { spacing: { before: 300 } }),
  p(`${DOC_NO}  |  ${REV}  |  ${DATE}`),
];

const doc = new Document({
  creator: "Titan Forgeworks",
  title: "Snake Handguard Kit: User Manual",
  styles: {
    default: { document: { run: { font: FONT, size: 22, color: "000000" } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: "000000" }, paragraph: { spacing: { before: 120, after: 160 }, outlineLevel: 0, keepNext: true,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "000000", space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: "000000" }, paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1, keepNext: true } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 300 } }, run: { font: FONT } } }] },
      ...stepLists.map((ref) => ({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 360 } }, run: { font: FONT } } }] })),
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } }, titlePage: true },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [t("Snake Handguard Kit  |  User Manual", { size: 17, italics: true })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [t(`Titan Forgeworks  |  ${DOC_NO}  |  ${REV}  |  page `, { size: 17 }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 17, color: "000000" })] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const f = path.join(OUT, "Snake_Handguard_Kit_User_Manual.docx");
  fs.writeFileSync(f, buf);
  console.log(f);
});
