"""Convert user's exact PNG/JPEG into a multi-resolution Windows .ico (no AI redraw)."""
from __future__ import annotations
import sys
from pathlib import Path
from PIL import Image

def convert(source: Path, out: Path):
    with Image.open(source) as img:
        im=img.convert('RGBA')
        # Preserve aspect ratio, pad with true transparency.
        side=max(im.size)
        canvas=Image.new('RGBA',(side,side),(0,0,0,0))
        canvas.alpha_composite(im,((side-im.width)//2,(side-im.height)//2))
        canvas.save(out,format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: python tools/make_icon.py input.png output.ico')
    convert(Path(sys.argv[1]),Path(sys.argv[2]))
