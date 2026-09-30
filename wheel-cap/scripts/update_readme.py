"""Copy verification/verification.md into the results section of README.md."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
readme = root / "README.md"
body = (root / "verification" / "verification.md").read_text().strip()
start, end = "<!-- results:start -->", "<!-- results:end -->"
text = readme.read_text()
a, b = text.index(start) + len(start), text.index(end)
readme.write_text(text[:a] + "\n" + body + "\n\n"
                  "![cross sections](verification/cross_sections.png)\n\n"
                  "![deviation map](verification/deviation_map.png)\n\n"
                  "![scan symmetry](verification/symmetry.png)\n" + text[b:])
