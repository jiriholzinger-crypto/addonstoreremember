"""Build addonStoreSortMemory-<version>.nvda-addon.

Usage: python build.py
Compiles locale/*/LC_MESSAGES/nvda.po to .mo, converts readme(.cs).md to doc/<lang>/readme.html
and zips the addon folder. Needs only the Python standard library.
"""

import ast
import html
import re
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADDON = ROOT / "addon"


def parsePo(path):
	entries = {}
	key = val = None
	cur = None
	for line in path.read_text(encoding="utf-8").splitlines() + [""]:
		line = line.strip()
		if line.startswith("msgid "):
			if key is not None:
				entries[key] = val
			key, val, cur = ast.literal_eval(line[6:]), "", "id"
		elif line.startswith("msgstr "):
			val, cur = ast.literal_eval(line[7:]), "str"
		elif line.startswith('"'):
			if cur == "id":
				key += ast.literal_eval(line)
			elif cur == "str":
				val += ast.literal_eval(line)
	if key is not None:
		entries[key] = val
	return {k: v for k, v in entries.items() if v or k == ""}


def writeMo(entries, path):
	keys = sorted(entries)
	ids = [k.encode("utf-8") for k in keys]
	strs = [entries[k].encode("utf-8") for k in keys]
	n = len(keys)
	keyStart = 7 * 4 + 16 * n
	valStart = keyStart + sum(len(i) + 1 for i in ids)
	offsets, idData, strData = [], b"", b""
	for i, s in zip(ids, strs):
		offsets.append((len(i), keyStart + len(idData), len(s), valStart + len(strData)))
		idData += i + b"\0"
		strData += s + b"\0"
	out = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + 8 * n, 0, 0)
	out += b"".join(struct.pack("ii", l, o) for l, o, _, _ in offsets)
	out += b"".join(struct.pack("ii", l, o) for _, _, l, o in offsets)
	path.write_bytes(out + idData + strData)


def inline(text):
	text = html.escape(text, quote=False)
	text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
	return re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)


def mdToHtml(md, lang, title):
	out, stack = [], []  # stack of list indent levels
	para = []

	def flushPara():
		if para:
			out.append("<p>" + inline(" ".join(para)) + "</p>")
			para.clear()

	def closeLists(level):
		while stack and stack[-1] >= level:
			out.append("</li></ul>")
			stack.pop()

	for raw in md.splitlines():
		m = re.match(r"^( *)\* (.*)$", raw)
		if raw.startswith("#"):
			flushPara()
			closeLists(0)
			lvl = len(raw) - len(raw.lstrip("#"))
			out.append(f"<h{lvl}>{inline(raw.lstrip('#').strip())}</h{lvl}>")
		elif m:
			flushPara()
			level = len(m.group(1))
			if stack and stack[-1] == level:
				out.append("</li><li>" + inline(m.group(2)))
			elif stack and stack[-1] > level:
				closeLists(level + 1)
				out.append("</li><li>" + inline(m.group(2)))
			else:
				out.append("<ul><li>" + inline(m.group(2)))
				stack.append(level)
		elif not raw.strip():
			flushPara()
		else:
			closeLists(0)
			para.append(raw.strip())
	flushPara()
	closeLists(0)
	body = "\n".join(out)
	return (
		f'<!DOCTYPE html>\n<html lang="{lang}"><head><meta charset="utf-8">'
		f"<title>{html.escape(title)}</title></head><body>\n{body}\n</body></html>\n"
	)


def main():
	for po in ADDON.glob("locale/*/LC_MESSAGES/nvda.po"):
		writeMo(parsePo(po), po.with_suffix(".mo"))
	for src, lang in ((ROOT / "readme.md", "en"), (ROOT / "readme.cs.md", "cs")):
		md = src.read_text(encoding="utf-8")
		title = md.splitlines()[0].lstrip("# ").strip()
		dest = ADDON / "doc" / lang / "readme.html"
		dest.parent.mkdir(parents=True, exist_ok=True)
		dest.write_text(mdToHtml(md, lang, title), encoding="utf-8")
	manifest = (ADDON / "manifest.ini").read_text(encoding="utf-8")
	version = re.search(r"^version\s*=\s*(\S+)", manifest, re.M).group(1)
	target = ROOT / f"addonStoreSortMemory-{version}.nvda-addon"
	with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
		for f in sorted(ADDON.rglob("*")):
			if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
				z.write(f, f.relative_to(ADDON).as_posix())
	print("Built", target.name)


if __name__ == "__main__":
	main()
