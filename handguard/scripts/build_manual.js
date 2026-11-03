// Customer user manual for the snake kit (manual/Snake_Handguard_Kit_User_Manual.docx): plain, black and white,
// Times New Roman. Numbers that depend on the build (bolt lengths and positions, the joint, the
// tabs) come from data/snake_lock.json.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  BorderStyle, ImageRun, AlignmentType, LevelFormat, PageBreak, Footer, PageNumber,
} = require("docx");

const ROOT = process.env.GUIDE_ROOT || path.join(__dirname, "..");
// SNAKE_VARIANT=bipod_rail: the version whose head piece is cut away under the front for the bottom accessory rail
const RAIL = process.env.SNAKE_VARIANT === "bipod_rail";
const OUT = RAIL ? path.join(ROOT, "manual", "bipod_rail") : path.join(ROOT, "manual");
const RL = RAIL ? JSON.parse(fs.readFileSync(path.join(ROOT, "data", "bipod_rail.json"))) : null;
const X_END = 387.4;                                   // front end of the handguard, from its rear face
const fromFront = (x) => Math.round(X_END - x);
const cutNear = RAIL ? fromFront(RL.cut_x[1]) : 0;
const TAIL = RAIL && RL.pieces.includes("tail");   // bottom cut leaves the tails as a separate piece
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
const [ROOT_W, ROOT_H] = LOCK.tab_root_mm;
const CLEAR = LOCK.tab_clearance_mm;
const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [t("Titan Forgeworks", { size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [t("Snake Handguard Kit", { bold: true, size: 40 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [t(RAIL ? "User Manual: Bipod Rail Version" : "User Manual", { size: 30 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [t("Two-piece snake sleeve for the Trinity Force KMX-15 keymod free-float handguard (15 in) on an AR-15", { size: 22 })] }),

  h1("1. Safety"),
  bullet([b("Unload the rifle before you start. "), t("Remove the magazine, lock the bolt open, and check the chamber and magazine well by sight and by touch. Keep ammunition out of the room.")]),
  bullet("Read this manual once before you start."),
  bullet([t("The handguard is "), b("free floating"), t(": nothing in this kit touches the barrel. Do the free-float check in section 8 after every installation.")]),
  bullet("Threadlocker needs time to cure (typically 24 hours). Do not fire the rifle until it has cured."),
  bullet("Do not fire the rifle with a snake piece loose, cracked, or missing a bolt."),

  h1("2. What this kit fits"),
  bullet([b("Handguard: "), t("Trinity Force KMX-15 keymod free-float handguard, 15 in (KM-34812-15), installed on the rifle as its maker instructs. The snake slides over the outside of the handguard; the handguard itself, its barrel nut and its own screws are not changed.")]),
  bullet([b("Muzzle device: "), t("the snake's head slides over the barrel through its open mouth (31 mm passage). A muzzle device up to 31 mm in diameter (for example an A2 flash hider or a 7/8 in brake) can stay on; a larger one must come off while the snake is fitted or removed.")]),
  ...(RAIL ? [
    bullet([b("Bottom accessory rail: "), t(`in this version the snake is cut away along the whole bottom of the handguard, in one straight line from ${cutNear} mm behind its front end all the way back. Nothing of the snake is below the handguard, so a Picatinny accessory rail on the bottom keymod holes, and a bipod on that rail, go on and come off with the snake in place.`)]),
    bullet([b("Accessories: "), t("a front sight on the top rail right behind the head, and the bottom accessory rail and bipod (section 9). Everything else mounted on the handguard comes off while the snake is fitted or removed.")]),
  ] : [
    bullet([b("Accessories: "), t("a front sight on the top rail right behind the head, and a bipod on a bottom keymod hole (section 9). Everything mounted on the handguard comes off while the snake is fitted or removed.")]),
  ]),

  h1("3. What is in the kit"),
  table([3000, 800, 5560], [
    ["Item", "Qty", "Description and replacement specification"],
    ["A  Snake rear piece", "1", (TAIL ? "The rear half of the two bodies. Four pockets at its front end." : "The two tails and the rear half of the two bodies. Four pockets at its front end.")],
    ["B  Snake head piece", "1", "The head and the front half of the two bodies. Four tabs at its rear end."],
    ...(TAIL ? [["C  Snake tail piece", "1", "The two tails and the last loop over the top, at the rear end of the handguard. No screws: it is held by the handguard and by piece A (section 5)."]] : []),
    ["M5 heat-set threaded inserts", "4", "Already pressed in, two in each piece (one on each side). Replacement: M5 x 0.8 internal thread, brass, knurled, for plastics, 5.8 mm long, 7.0 mm outside diameter, for a 6.4 mm hole (for example ruthex RX-M5x5.8 or CNC Kitchen M5 standard)."],
    [`${screwLen(rb).replace("x", " x ")} socket head cap screws`, "2", `For the rear piece A. Replacement: M5 x 0.8 thread, ${screwLen(rb).split("x")[1]} mm long, ISO 4762 (DIN 912), alloy steel class 12.9, black oxide; 8.5 mm head, 4 mm hex socket.`],
    [`${screwLen(fb).replace("x", " x ")} socket head cap screws`, "2", `For the head piece B. Replacement: M5 x 0.8 thread, ${screwLen(fb).split("x")[1]} mm long, ISO 4762 (DIN 912), alloy steel class 12.9, black oxide; 8.5 mm head, 4 mm hex socket.`],
  ]),
  p(""),
  p([b("Use only the screw lengths above, in the piece they belong to. "), t("A longer screw can reach the barrel; a shorter one does not reach the keymod hole and does not lock the piece.")]),
  ...figure("fig_parts.png", TAIL ? "Figure 1. The kit's three pieces (A rear, B head, C tail) and the handguard they fit (not included)." : "Figure 1. The kit's two pieces (A rear, B head) and the handguard they fit (not included)."),

  h1("4. What you need"),
  bullet("4 mm hex key or hex bit."),
  bullet("Torque screwdriver covering 1 to 3 N m (recommended), with a 4 mm hex bit."),
  bullet([t("Medium-strength removable threadlocker that is "), b("safe on plastics"), t(", for example Vibra-TITE VC-3 Threadmate. If you use an anaerobic blue threadlocker such as Loctite 243 instead, use only a very small amount on the screw tip and never let it touch the snake: anaerobic threadlockers can crack polycarbonate.")]),
  bullet("Isopropyl alcohol and a cotton swab, to degrease the screws."),
  bullet("A paint marker, for witness marks (recommended)."),
  bullet("A strip of printer paper, for the free-float check."),

  h1("5. How the snake stays put"),
  p("Every movement is stopped by a part, and every screw is held by threadlocker and torque:"),
  table([3600, 5760], [
    ["Movement", "What stops it"],
    ["Turning around the handguard", "The inside of each piece is shaped to the handguard's flats and rail (with 0.35 mm clearance), so it cannot rotate."],
    RAIL ? ["Coming off sideways or downward", "Each piece wraps more than halfway around the handguard: the opening along the bottom is about 27 mm wide and the handguard about 36 mm, so it cannot come off except by sliding along the handguard."]
         : ["Coming off sideways", "Each piece is a closed tube that goes all the way around the handguard."],
    ...(TAIL ? [
      ["Tail piece C moving back", "The step where the round rear part of the handguard begins."],
      ["Tail piece C moving forward", "The rear piece A in front of it, which is screwed in place."],
    ] : []),
    ["Rear piece A moving back", `Its two screws, whose tips sit at the rear end of the ${ord(rearHole)} side keymod hole (counted from the rear of the handguard) on each side.`],
    ["Rear piece A moving forward", "The head piece B in front of it."],
    ["Head piece B moving forward (recoil pushes the snake forward)", `Its two screws, whose tips sit at the front end of the ${ord(frontHole)} side keymod hole (counted from the rear) on each side. Piece A pushes on B, so these two screws hold both pieces under recoil.`],
    ["Head piece B moving back", "The solid ring inside the head rests on the front end of the handguard."],
    ["A and B shifting against each other", `Four tapered tabs on B (${TAB_W} x ${TAB_H} mm at the tip, ${ROOT_W} x ${ROOT_H} mm at the root, ${TAB_L} mm long) fit four matching pockets in A with ${CLEAR} mm clearance all round: two on the left body, two on the right body.`],
    ["Screws working loose", "Threadlocker on every screw, the torque in section 11, brass inserts (no plastic threads), and witness marks checked after firing."],
  ]),

  h1("6. Before you install"),
  ...steps([
    ["Unload the rifle (section 1)."],
    ["Check that the handguard is installed and tight as its maker instructs. Nothing on the handguard itself changes for the snake."],
    ...(RAIL ? [
      ["Remove everything mounted on the handguard: front sight, bipod, the bottom accessory rail, lights, rail covers and keymod accessories."],
    ] : [
      ["Remove everything mounted on the handguard: front sight, bipod or bipod mount, lights, rail covers and keymod accessories."],
    ]),
    ["Remove the muzzle device if it is wider than 31 mm."],
    [TAIL ? "Check the inside of the three snake pieces, the screw holes and the four pockets for dust or loose bits, and blow them clean."
          : "Check the inside of both snake pieces, the screw holes and the four pockets for dust or loose bits, and blow them clean."],
  ]),

  h1("7. Installing the snake"),
  ...(TAIL ? [
    h2("Tail piece C (first)"),
    ...steps([
      ["Slide piece C over the muzzle, tails first, and all the way back along the handguard until it stops at the step where the round rear part of the handguard begins (about 18 mm from the rear end). It needs no screws."],
    ]),
  ] : []),
  h2("Rear piece A"),
  ...steps([
    [TAIL ? "Slide piece A over the muzzle and along the handguard until its rear end meets piece C. It slides like a sleeve; do not force it."
          : "Slide piece A over the muzzle, tails first, and along the handguard. It slides like a sleeve; do not force it."],
    [`Slide it back until a side keymod hole of the handguard shows through the round screw hole on each side (the ${ord(rearHole)} keymod hole counted from the rear).`],
    [`Degrease the two ${screwLen(rb)} screws, put a small amount of threadlocker on the last 3 to 4 threads at the tip (keep it off the snake), and screw one in on each side by hand until the tips enter the keymod holes.`],
    ["Push piece A back (toward the receiver) and hold it there, so the screw tips rest against the rear ends of their keymod holes."],
    ["Tighten both screws to 1.5 N m. Do not exceed 2.0 N m: more can pull the insert out of the plastic."],
  ]),
  h2("Head piece B"),
  ...steps([
    ["Slide piece B over the muzzle (the barrel and muzzle device pass through the open mouth) and back along the handguard."],
    ["As it reaches piece A, line up its four tabs with the four pockets in A (two on the left body, two on the right body) and push it home. The tapered tabs find the pockets and slide in with light hand pressure."],
    ["Push piece B back until the inside of the head rests on the front end of the handguard and the faces of A and B meet with an even, hairline gap."],
    [`Degrease the two ${screwLen(fb)} screws, put a small amount of threadlocker on the last 3 to 4 threads at the tip (keep it off the snake), and screw one in on each side (the ${ord(frontHole)} keymod hole counted from the rear).`],
    ["Push piece B back and hold it while tightening both screws to 1.5 N m (maximum 2.0 N m)."],
  ]),
  ...figure("fig_joint.png", "Figure 2. The joint between A (left) and B (right), pulled apart: the four tapered tabs on B (black) and their pockets in A."),
  ...figure("fig_bolt_section.png", "Figure 3. Cut across the head piece's screws, seen from the muzzle: each screw goes through a heat-set insert and its tip ends in a keymod hole in the handguard wall, clear of the barrel."),

  h1("8. Final checks"),
  ...steps([
    ["Grip the snake at the head and at the tails and try to twist it, push it and pull it. Nothing may move or click."],
    ["Free float: slide the paper strip all the way around the barrel inside the head and at the front end of the handguard. It must pass freely everywhere. Nothing may touch the barrel."],
    ["Make a paint witness mark across each of the four screw heads and the snake next to it."],
    ["Let the threadlocker cure as its maker states (typically 24 hours) before firing."],
    ["After the first 50 rounds, and after any hard knock, check the witness marks. If a mark has moved, remove that screw, clean the threads, re-apply threadlocker and tighten it again."],
  ]),
  ...figure("fig_assembled.png", "Figure 4. Installed, rifle's left side, with the screw positions (one screw on each side of each piece)."),

  h1("9. Accessories"),
  bullet([b("Front sight: "), t("mounts on the top rail right behind the head, with its recoil lug in the 2nd or 3rd rail slot counted from the muzzle end. The snake leaves the rail clear there, and the necks beside the rail are trimmed for the sight's clamp and clamp knob (up to 34 mm wide). Install the sight after the snake.")]),
  ...(RAIL ? [
    bullet([b("Bottom accessory rail: "), t("with the snake installed, bolt the rail to the bottom keymod holes as its maker instructs. The snake is cut away along the whole bottom, so the rail can go anywhere along it and its screws are open to reach.")]),
    bullet([b("Bipod: "), t("clamps onto the bottom accessory rail anywhere along it, as its maker instructs. Rail and bipod come off again without touching the snake.")]),
  ] : [
    bullet([b("Bipod: "), t("mounts on the 4th bottom keymod hole counted from the muzzle end, with a standard keymod bipod adapter. The snake leaves this hole clear.")]),
  ]),
  bullet("The rest of the rail and keymod holes are partly covered by the snake. Install accessories after the snake, with their own hardware and instructions, and remove them before taking the snake off."),
  ...(RAIL ? figure("fig_rail.png", "Figure 5. From below: the snake is cut away along the whole bottom of the handguard, leaving the bottom accessory rail (black) fully open.") : []),

  h1("10. Removal"),
  ...steps([
    [RAIL ? "Unload the rifle (section 1). Remove the front sight, the bipod, the bottom accessory rail and, if needed, the muzzle device."
          : "Unload the rifle (section 1). Remove the front sight, the bipod mount and, if needed, the muzzle device."],
    ["Remove the two screws of head piece B (if tight, a short, sharp turn of the hex key breaks the threadlocker). Pull B forward off the muzzle."],
    ["Remove the two screws of rear piece A and pull A forward off the muzzle."],
    ...(TAIL ? [["Pull tail piece C forward off the muzzle."]] : []),
    ["Before re-installing, clean old threadlocker off the screws and the inserts with a brush and isopropyl alcohol, and use fresh threadlocker."],
  ]),

  h1("11. Torque values"),
  table([4200, 2200, 2960], [
    ["Screw", "Torque", "Notes"],
    [`${screwLen(rb)}, rear piece A (2)`, "1.5 N m (max 2.0)", "Piece pushed back while tightening; threadlocker"],
    [`${screwLen(fb)}, head piece B (2)`, "1.5 N m (max 2.0)", "Piece pushed back while tightening; threadlocker"],
  ]),

  h1("12. Care"),
  bullet("The snake is printed in polycarbonate (PC). It takes the handguard's normal heat, but let the rifle cool between long strings of rapid fire."),
  bullet("Clean it with a soft brush and a cloth dampened with mild soap and water, then dry it."),
  bullet([b("Keep chemicals off the snake. "), t("Polycarbonate can crack when it touches many solvents: keep bore cleaners, gun solvents, brake and parts cleaners, aerosol lubricants, acetone, paint strippers and anaerobic threadlockers off it, and wipe off any oil that gets on it straight away. Clean the rifle with the snake removed, or cover the snake while you clean.")]),
  bullet("Check the witness marks and look the snake over for cracks before each range trip. Do not use a cracked piece."),

  h1("13. Replacing a heat-set insert"),
  p("The inserts come installed. If one ever comes loose or is damaged, replace it as follows (spare: section 3):"),
  ...steps([
    ["Remove the snake piece from the rifle. Heat the old insert with a soldering iron and pull it out with pliers while it is hot; let the hole cool."],
    ["Set the soldering iron to 280 C (for polycarbonate). Put the new insert on the 6.4 mm hole at the bottom of the wide screw hole, small end down, straight and square."],
    ["Press it in slowly with the iron, keeping it straight, until its top is flush with the floor of the wide hole. Do not push it below the floor. Lift the iron straight off."],
    ["While still soft, press the top of the insert flat with a cool flat tool for 10 seconds, then let it cool for 5 minutes."],
    ["Check it: the screw for that piece must turn in freely by hand and its head must sit down on the insert."],
  ]),
  ...figure("fig_insert.png", `Figure ${RAIL ? 6 : 5}. A heat-set insert at the bottom of a screw hole (rear piece, left side).`),
];

const doc = new Document({
  creator: "Titan Forgeworks",
  title: RAIL ? "Snake Handguard Kit: User Manual, Bipod Rail Version" : "Snake Handguard Kit: User Manual",
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
      children: [t(RAIL ? "Snake Handguard Kit (Bipod Rail Version), User Manual, page " : "Snake Handguard Kit, User Manual, page ", { size: 18 }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "000000" })] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const f = path.join(OUT, RAIL ? "Snake_Handguard_Kit_Bipod_Rail_User_Manual.docx" : "Snake_Handguard_Kit_User_Manual.docx");
  fs.writeFileSync(f, buf);
  console.log(f);
});
