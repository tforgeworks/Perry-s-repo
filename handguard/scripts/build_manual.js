// Assembly and installation manual (manual/Snake_Handguard_Manual.docx): plain, black and white,
// Times New Roman. Numbers that depend on the build (bolt lengths and positions, the joint, the
// tabs) come from data/snake_lock.json.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  BorderStyle, ImageRun, AlignmentType, LevelFormat, PageBreak, Footer, PageNumber,
} = require("docx");

const ROOT = process.env.GUIDE_ROOT || path.join(__dirname, "..");
const OUT = path.join(ROOT, "manual");
const LOCK = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "snake_lock.json")));
const FONT = "Times New Roman";

const rb = LOCK.bolts.rear[0], fb = LOCK.bolts.front[0];
const screwLen = (b) => b.screw.split(" ")[0];            // "M5x12"
const SIDE_HOLE_REAR0 = 70.46, SIDE_HOLE_FRONT0 = 87.95, PITCH = 20.0, N_SIDE = 15;
const holeFromRear = (b) => b.bears_on.startsWith("rear")
  ? Math.round((b.hole_end_x - SIDE_HOLE_REAR0) / PITCH) + 1
  : Math.round((b.hole_end_x - SIDE_HOLE_FRONT0) / PITCH) + 1;
const ord = (n) => n + (n % 10 === 1 && n !== 11 ? "st" : n % 10 === 2 && n !== 12 ? "nd" : n % 10 === 3 && n !== 13 ? "rd" : "th");
const rearHole = holeFromRear(rb), frontHole = holeFromRear(fb);
const [TAB_W, TAB_H, TAB_L] = LOCK.tab_size_mm;

// ---------- helpers
const t = (text, o = {}) => new TextRun({ text, font: FONT, color: "000000", ...o });
const p = (runs, o = {}) => new Paragraph({ children: (Array.isArray(runs) ? runs : [runs]).map((r) => (typeof r === "string" ? t(r) : r)), spacing: { after: 120 }, ...o });
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(text)] });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(text)] });
const bullet = (runs) => p(runs, { numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 } });
let stepRef = 0;
const steps = (items) => { const ref = "steps" + (stepRef++); stepLists.push(ref); return items.map((runs) => p(runs, { numbering: { reference: ref, level: 0 }, spacing: { after: 90 } })); };
const stepLists = [];
const b = (text) => t(text, { bold: true });

const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(widths, rows, header = true) {
  const total = widths.reduce((a, c) => a + c, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((row, i) => new TableRow({
      tableHeader: header && i === 0,
      children: row.map((cell, j) => new TableCell({
        borders, width: { size: widths[j], type: WidthType.DXA },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: (Array.isArray(cell) ? cell : [cell]).map((c) => new Paragraph({
          children: [typeof c === "string" ? t(c, { bold: header && i === 0, size: 21 }) : c],
        })),
      })),
    })),
  });
}
function figure(file, caption, widthIn = 6.0) {
  const f = path.join(OUT, file);
  const buf = fs.readFileSync(f);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);   // PNG header
  const W = widthIn * 96, H = Math.round((W * h) / w);
  const scale = H > 6.2 * 96 ? (6.2 * 96) / H : 1;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: Math.round(W * scale), height: Math.round(H * scale) },
        altText: { title: caption, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [t(caption, { italics: true, size: 20 })] }),
  ];
}

// ---------- content
const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [t("Snake Handguard", { bold: true, size: 40 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [t("Assembly, Installation and Hardware Manual", { size: 30 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [t("Printed copy of the Trinity Force KMX-15 keymod handguard (15 in) with a two-piece snake sleeve, for a 16 in AR-15", { size: 22 })] }),

  h1("1. Before you start"),
  bullet([b("Unload the rifle. "), t("Remove the magazine, lock the bolt open, and check the chamber and magazine well by sight and by touch. Keep ammunition out of the room.")]),
  bullet("Read the whole manual once before starting. Work on a clean bench with the rifle in a padded vise block or on a mat."),
  bullet("All dimensions are in millimetres. Distances along the handguard are measured from its rear face (the end at the receiver)."),
  bullet([t("The handguard is "), b("free floating"), t(": nothing in this kit may touch the barrel. The checks in section 8 confirm this.")]),
  bullet("Threadlocker needs 24 hours to cure fully. Do not fire the rifle until it has cured."),

  h1("2. Printed parts"),
  table([1100, 3000, 5260], [
    ["Part", "File", "Description"],
    ["A", "handguard_base.stl", "The handguard, 387.2 mm long. Clamps onto the barrel nut like the original."],
    ["B", "snake_rear.3mf", `Snake rear piece: the two tails and the rear half of both bodies. Has two bolt holes (left and right) and four tab pockets at its front end.`],
    ["C", "snake_front.3mf", `Snake head piece: the front half of both bodies and the head. Has two bolt holes (left and right) and four alignment tabs at its rear end.`],
  ]),
  p(""),
  p("Material for all three: PA-CF (carbon-fibre nylon), dried before printing, 0.4 mm hardened nozzle, 0.2 mm layers. Remove all support material, especially from the inside of the snake pieces, the bolt holes and the tab pockets."),
  ...figure("fig_parts.png", "Figure 1. The three printed parts: A handguard, B snake rear piece, C snake head piece."),

  h1("3. Hardware to buy"),
  p("Buy exactly these items (or equivalents with the same specification). The quantity to buy includes spares."),
  table([2200, 3800, 700, 1000, 1660], [
    ["Item", "Specification", "Used", "Buy", "Where"],
    ["Socket head cap screw M4 x 25", "M4 x 0.7 thread, 25 mm long, ISO 4762 (DIN 912), alloy steel class 12.9, black oxide. Head 7.0 mm diameter, 3 mm hex socket.", "2", "4", "Handguard clamp"],
    ["Hex nut M4", "M4 x 0.7, ISO 4032 (DIN 934), steel class 8 or higher, 7.0 mm across flats, 3.2 mm thick. Plain nut: a nylon-insert lock nut (5 mm thick) does not fit the pocket.", "2", "4", "Handguard clamp"],
    ["Centre screw", "Jack's original bottom centre screw from the original handguard (reuse it).", "1", "-", "Handguard clamp"],
    ["Heat-set threaded insert M5", "M5 x 0.8 internal thread, brass, knurled, for plastics, 5.8 mm long, 7.0 mm outside diameter, for a 6.4 mm hole (for example ruthex RX-M5x5.8 or CNC Kitchen M5 standard).", "4", "8", "Snake pieces B and C"],
    [`Socket head cap screw ${screwLen(rb).replace("x", " x ")}`, `M5 x 0.8 thread, ${screwLen(rb).split("x")[1]} mm long, ISO 4762 (DIN 912), alloy steel class 12.9, black oxide. Head 8.5 mm diameter, 4 mm hex socket.`, "2", "4", "Snake rear piece B"],
    [`Socket head cap screw ${screwLen(fb).replace("x", " x ")}`, `M5 x 0.8 thread, ${screwLen(fb).split("x")[1]} mm long, ISO 4762 (DIN 912), alloy steel class 12.9, black oxide. Head 8.5 mm diameter, 4 mm hex socket.`, "2", "4", "Snake head piece C"],
    ["Threadlocker, medium strength", "Removable (blue) anaerobic threadlocker, for example Loctite 243. Works on brass inserts and steel nuts; comes apart with hand tools.", "-", "1 bottle (5 to 10 ml)", "All bolts"],
    ["Paint marker", "Any oil-based paint marker, for witness marks.", "-", "1", "Checks"],
  ]),
  p(""),
  p([b("Do not substitute: "), t("longer M5 screws can reach the barrel; shorter ones do not reach the keymod holes and do not lock. Use the lengths above for each piece.")]),
  h2("Tools"),
  bullet("3 mm and 4 mm hex keys or hex bits."),
  bullet("Torque screwdriver covering 1 to 3 N m (for example a 1 to 5 N m click-type driver with hex bits)."),
  bullet("Soldering iron with an M5 heat-set insert tip (or a conical tip), adjustable temperature."),
  bullet("Isopropyl alcohol and a cotton swab (to degrease threads before threadlocker)."),
  bullet("A straight edge at least 300 mm long (to line up the rails)."),
  bullet("A strip of printer paper (for the free-float check)."),

  h1("4. How everything is locked"),
  p("Every possible movement is stopped by a part, and every bolt is held by threadlocker and torque:"),
  table([3600, 5760], [
    ["Movement", "What stops it"],
    ["Handguard turning or sliding on the barrel nut", "The clamp (two M4 bolts with steel nuts squeeze the bore onto the barrel nut), the centre screw, and the two rear lugs resting against the receiver."],
    ["Snake turning around the handguard", "The inside of each snake piece is the handguard's outer shape (keymod flats and rail) plus 0.35 mm, so it cannot rotate."],
    ["Snake lifting off sideways", "Each snake piece is a closed tube that goes all the way around the handguard."],
    ["Rear piece B moving back", `Its two M5 bolts, whose tips sit at the rear end of the ${ord(rearHole)} side keymod hole (counted from the rear) on each side.`],
    ["Rear piece B moving forward", "The head piece C in front of it."],
    ["Head piece C moving forward (recoil pushes the snake forward)", `Its two M5 bolts, whose tips sit at the front end of the ${ord(frontHole)} side keymod hole (counted from the rear) on each side. Piece B pushes on C, so these two bolts hold both pieces under recoil.`],
    ["Head piece C moving back", "The solid ring inside the head rests on the handguard's muzzle end."],
    ["B and C shifting against each other", `Four rectangular tabs (${TAB_W} x ${TAB_H} mm, ${TAB_L} mm long) on C fit into four pockets in B with 0.2 mm clearance, two on the left body and two on the right body.`],
    ["Bolts working loose", "Medium threadlocker on every bolt, the torque values in section 9, steel nuts and brass inserts (no plastic threads), and paint witness marks checked after firing."],
  ]),

  h1("5. Preparing the snake pieces (once)"),
  p("Each snake piece has two round bolt holes, one on its left side and one on its right side. Each hole is a wide counterbore (9.6 mm, for the screw head) with a narrower hole at its bottom (6.4 mm, for the insert)."),
  ...steps([
    ["Clean the holes of any support material. Check that an insert drops into the 6.4 mm hole by hand only at its tip (it must be pressed in with heat)."],
    ["Set the soldering iron to 260 C for PA-CF (240 C for PC, 230 C for ASA). Put the insert on the 6.4 mm hole, small end down, straight and square to the hole."],
    ["Press it in slowly with the iron, keeping it straight, until its top is flush with the floor of the wide counterbore. Do not push it below the floor. Lift the iron straight off."],
    ["While still soft, press the top of the insert flat with a cool flat tool for 10 seconds. Let it cool fully (5 minutes)."],
    ["Repeat for all four holes (two on B, two on C)."],
    [`Check each insert: screw the matching bolt (${screwLen(rb)} in B, ${screwLen(fb)} in C) in by hand. It must turn freely and the head must sit down on the insert. Remove the bolts again.`],
  ]),
  ...figure("fig_insert.png", "Figure 2. Pressing a heat-set insert into the bottom of a bolt hole (rear piece, left side)."),

  h1("6. Installing the handguard"),
  ...steps([
    ["Remove the original handguard: take out its two clamp bolts and its bottom centre screw (keep the centre screw), and slide it forward off the barrel."],
    ["Remove the muzzle device if it is wider than 31 mm (the head of the snake passes over it later). Remove any front sight and bipod mount."],
    ["Slide the printed handguard A over the barrel onto the barrel nut, rail up, until the two small lugs at its rear end touch the front of the receiver."],
    ["Lay the straight edge along the top of the receiver rail and the handguard rail. Turn the handguard until the two rails are in line."],
    ["Drop the two M4 hex nuts into the hex pockets on the left side of the clamp block."],
    ["Degrease the M4 x 25 bolts. Put one drop of threadlocker on the threads, about 5 mm from the tip. Insert them from the right side and thread them into the nuts."],
    ["Tighten them a little at a time, alternating between the two, to 2.0 N m. Check the rails are still in line."],
    ["Put one drop of threadlocker on the original centre screw and install it from below, snug, as on the original handguard."],
    ["Try to turn and pull the handguard by hand: it must not move at all."],
  ]),
  ...figure("fig_clamp.png", "Figure 3. The clamp from below: two M4 x 25 bolts from the right, nuts on the left, centre screw from below."),

  h1("7. Installing the snake"),
  h2("Rear piece B"),
  ...steps([
    ["Slide piece B over the muzzle, tails first, and along the handguard. It slides like a sleeve: do not force it. If it binds, look for support material inside."],
    [`Slide it back until a side keymod hole of the handguard shows through the bolt hole on each side (the ${ord(rearHole)} keymod hole counted from the rear).`],
    [`Degrease the two ${screwLen(rb)} bolts, put one drop of threadlocker on the threads, and screw one in on each side by hand until the tips enter the keymod holes.`],
    ["Push piece B back (toward the receiver) and hold it there, so the bolt tips rest against the rear ends of their keymod holes."],
    ["Tighten both bolts to 1.5 N m. Do not exceed 2.0 N m (the insert can be pulled out of the plastic)."],
  ]),
  h2("Head piece C"),
  ...steps([
    ["Slide piece C over the muzzle (the barrel and muzzle device pass through the open mouth) and back along the handguard."],
    ["As it reaches piece B, line up its four tabs with the four pockets in B (two on the left body, two on the right body) and push it home. The tabs slide in with light hand pressure."],
    ["Push piece C back until the inside of the head rests on the muzzle end of the handguard, and the faces of B and C meet with an even, hairline gap."],
    [`Degrease the two ${screwLen(fb)} bolts, put one drop of threadlocker on the threads, and screw one in on each side (the ${ord(frontHole)} keymod hole counted from the rear).`],
    ["Push piece C back and hold it while tightening both bolts to 1.5 N m (maximum 2.0 N m)."],
  ]),
  ...figure("fig_joint.png", "Figure 4. The joint between B (left) and C (right), pulled apart: four tabs on C (black) and their pockets in B."),
  ...figure("fig_bolt_section.png", "Figure 5. Cut across the head piece's bolts, seen from the muzzle: each bolt goes through an insert and its tip ends in a keymod hole in the handguard wall, clear of the barrel."),

  h1("8. Final checks"),
  ...steps([
    ["Grip the snake at the head and at the tails and try to twist it, push it and pull it. Nothing may move or click."],
    ["Free float: slide the paper strip all the way around the barrel inside the head and at the muzzle end of the handguard. It must pass freely everywhere. Nothing may touch the barrel."],
    ["Make a paint witness mark across each bolt head and the snake next to it (four snake bolts, two clamp bolts)."],
    ["Let the threadlocker cure for 24 hours before firing."],
    ["After the first 50 rounds, and after any hard knock, check the witness marks. If a mark has moved, remove that bolt, clean the threads, re-apply threadlocker and tighten again."],
  ]),
  ...figure("fig_assembled.png", "Figure 6. Assembled, rifle's left side, with the bolt positions (one bolt on each side of each piece)."),

  h1("9. Torque values"),
  table([4200, 2000, 3160], [
    ["Fastener", "Torque", "Notes"],
    ["M4 x 25 clamp bolts (2)", "2.0 N m", "Alternate between the two; threadlocker"],
    ["Centre screw (original)", "Snug", "As on the original handguard; threadlocker"],
    [`${screwLen(rb)} bolts, rear piece B (2)`, "1.5 N m (max 2.0)", "Piece pushed back while tightening; threadlocker"],
    [`${screwLen(fb)} bolts, head piece C (2)`, "1.5 N m (max 2.0)", "Piece pushed back while tightening; threadlocker"],
  ]),

  h1("10. Accessories"),
  bullet([b("Front sight: "), t("mounts on the top rail right behind the head, on the 3rd to 6th rail slots counted from the muzzle end (312 to 357 mm from the rear face). The snake does not cover this part of the rail.")]),
  bullet([b("Bipod: "), t("mounts on the 4th bottom keymod hole counted from the muzzle end (278.6 to 297.0 mm from the rear face), with a standard keymod bipod adapter. The snake leaves the bottom clear from 272.5 to 303.5 mm.")]),
  bullet("Both must be removed before the snake pieces slide on or off. Install them last, with their own hardware and instructions."),

  h1("11. Removal"),
  ...steps([
    ["Unload the rifle (section 1). Remove the front sight, the bipod mount and, if needed, the muzzle device."],
    ["Remove the two bolts of head piece C (if tight, a short sharp turn of the hex key breaks the threadlocker). Pull C forward off the muzzle."],
    ["Remove the two bolts of rear piece B and pull B forward off the muzzle."],
    ["The handguard stays on the rifle. To remove it, take out the centre screw and the two clamp bolts and slide it forward."],
    ["Before re-installing, clean old threadlocker off the bolts and inserts with a brush and isopropyl alcohol and use fresh threadlocker."],
  ]),
];

const doc = new Document({
  creator: "Titan Forgeworks",
  title: "Snake Handguard: Assembly, Installation and Hardware Manual",
  styles: {
    default: { document: { run: { font: FONT, size: 22, color: "000000" } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 300, after: 140 }, outlineLevel: 0, keepNext: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: "000000" }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1, keepNext: true } },
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
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [t("Snake Handguard Manual, page ", { size: 18 }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "000000" })] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const f = path.join(OUT, "Snake_Handguard_Manual.docx");
  fs.writeFileSync(f, buf);
  console.log(f);
});
