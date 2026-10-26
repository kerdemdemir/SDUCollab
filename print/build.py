"""Build printable A4 posters (title, short description, picture, big QR code) for one domain.

Usage: python build.py [--base https://your.domain/] [poster-id ...]
Needs `segno` (pip install segno). PDFs are rendered with Chromium/Chrome and merged with pdfunite if installed.
Output goes to print/out/<domain>/ : html/, pdf/, qr/ and all-posters.pdf.
Put a picture at site/img/<poster-id>.jpg and it is added to that poster automatically.
"""
import argparse
import base64
import io
import pathlib
import shutil
import subprocess
import urllib.parse

import segno

HERE = pathlib.Path(__file__).parent
args = argparse.ArgumentParser()
args.add_argument("--base", default="https://sducollab.duckdns.org/", help="site URL the QR codes point to")
args.add_argument("ids", nargs="*", help="only build these posters")
args = args.parse_args()
BASE = args.base.rstrip("/") + "/"
SITE = BASE + "#projects/"
LOGO = base64.b64encode((HERE.parent / "site/img/leica-logo.png").read_bytes()).decode()

PROJECTS = [
    ("surface-mapping", "Real-Time Mapping of the Construction Site Surface",
     "Put cameras around an excavator and turn what they see into a live 3D map of the ground. "
     "While the machine digs, the operator always sees the current surface: what has been dug, what is left, and what has changed."),
    ("blade-pose", "Real-Time Pose Estimation for Construction Machines",
     "Use a camera to see where the excavator's arm or the dozer's blade is and how it is angled, live. "
     "Combined with inclination sensors and GNSS, the pose stays reliable even when the view is blocked."),
    ("ins-sensor-fusion", "Positioning Heavy Machines with IMU + GNSS",
     "GPS tells a machine where it is, but drops out near buildings or in deep pits. A motion sensor (IMU) is fast but drifts. "
     "Combine the two so an excavator always knows its position and heading, tested on a simulated construction site."),
    ("tool-recognition", "Recognizing Excavator Buckets with a Camera",
     "Excavators swap buckets all the time. Train a camera to recognize which bucket is attached, "
     "so the machine picks the right settings automatically."),
    ("radar-camera", "Detecting People and Obstacles with Radar + Camera",
     "A camera sees what an object is; a radar sees how far away it is, even through dust and fog. "
     "Fuse the two so an excavator can warn its operator about people and obstacles around it."),
    ("vr-teleoperation", "Operating Construction Machines Remotely in VR",
     "Put on a VR headset and step into a live 3D copy of an excavator and its worksite, built from real survey data. "
     "As a final step: drive it remotely from a safe place."),
]

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; }}
  body {{ font-family: "Noto Sans", "Segoe UI", Helvetica, Arial, sans-serif; color: #11161d; background: #fff; }}
  .page {{ width: 210mm; height: 297mm; padding: 18mm 20mm 16mm; display: flex; flex-direction: column; position: relative; overflow: hidden; }}
  .page::before {{ content: ""; position: absolute; left: 0; top: 0; right: 0; height: 6mm; background: #e2001a; }}
  .top {{ display: flex; align-items: center; justify-content: space-between; margin-top: 2mm; }}
  .top img {{ height: 18mm; }}
  .kicker {{ color: #e2001a; text-transform: uppercase; letter-spacing: .12em; font-weight: 700; font-size: 11pt; }}
  h1 {{ font-size: 26pt; line-height: 1.15; margin: 14mm 0 6mm; }}
  h1::before {{ content: ""; display: block; width: 18mm; height: 2mm; background: #e2001a; margin-bottom: 6mm; }}
  .desc {{ font-size: 14pt; line-height: 1.5; color: #3a4350; margin: 0; }}
  .list {{ margin: 5mm 0 0; padding-left: 6mm; font-size: 12.5pt; line-height: 1.55; color: #11161d; }}
  .list li::marker {{ color: #e2001a; }}
  .list .hl {{ color: #e2001a; font-weight: 700; }}
  .poster-home .qr {{ padding-top: 6mm; }}
  .poster-home .qr img {{ width: 100mm; height: 100mm; }}
  .qr {{ margin: auto 0 0; text-align: center; }}
  .qr .cta {{ font-size: 22pt; font-weight: 800; margin-bottom: 4mm; }}
  .qr .cta span {{ color: #e2001a; }}
  .photo {{ margin: 6mm auto 0; flex: 1 1 0; min-height: 40mm; max-height: 70mm; width: 100%; object-fit: contain; display: block; }}
  .has-photo {{ padding-top: 14mm; padding-bottom: 12mm; }}
  .has-photo h1 {{ margin: 8mm 0 4mm; font-size: 24pt; }}
  .has-photo .qr {{ margin-top: 6mm; }}
  .has-photo .qr .cta {{ font-size: 20pt; margin-bottom: 2mm; }}
  .has-photo .qr img {{ width: 85mm; height: 85mm; }}
  .has-photo .foot {{ margin-top: 5mm; }}
  .qr img {{ width: 120mm; height: 120mm; display: block; margin: 0 auto; image-rendering: pixelated; }}
  .qr .url {{ font-size: 10pt; color: #6b7480; margin-top: 2mm; }}
  .foot {{ margin-top: 8mm; padding-top: 4mm; border-top: 1px solid #d9dde2; display: flex; justify-content: space-between; font-size: 10pt; color: #6b7480; }}
  .foot b {{ color: #11161d; }}
</style></head>
<body><div class="page{page_class}">
  <div class="top"><span class="kicker">{kicker}</span><img src="data:image/png;base64,{logo}" alt="Leica Geosystems"></div>
  <h1>{title}</h1>
  <div class="desc">{desc}</div>
  {photo}
  <div class="qr">
    <div class="cta">For more info, <span>scan here</span></div>
    <img src="data:image/svg+xml;base64,{qr}" alt="QR code">
    <div class="url">{url}</div>
  </div>
  <div class="foot"><span><b>{contact_name}</b> · {contact_email}</span><span>Leica Geosystems · Odense</span></div>
</div></body></html>
"""

MADS = ("Mads Tilgaard Jensen", "mads.jensen@leica-geosystems.com")
POSTERS = [
    dict(id=pid, title=title, desc=desc, url=SITE + pid, kicker="Student project · Project Days", contact=MADS)
    for pid, title, desc in PROJECTS
] + [
    dict(id="home", title="Build cool stuff with real machines",
         desc="Student projects and a student job at Leica Geosystems Machine Control, Odense."
              '<ul class="list">' + "".join(f"<li>{t}</li>" for _, t, _ in PROJECTS) +
              '<li class="hl">We\'re hiring: Student Programmer</li></ul>',
         url=BASE, kicker="Project Days · Leica Geosystems", contact=MADS),
    dict(id="job", title="We're hiring: Student Programmer",
         desc="Join our On Machine Software team in Odense. Write, test and improve the software that runs on real "
              "excavators and dozers, with access to our T-Site test area.",
         url=BASE + "#job", kicker="Student job · Machine Control",
         contact=("Martin Reich", "martin.reich@leica-geosystems.com")),
]

ORDER = ["home"] + [pid for pid, _, _ in PROJECTS] + ["job"]
POSTERS.sort(key=lambda p: ORDER.index(p["id"]))

out = HERE / "out" / urllib.parse.urlparse(BASE).netloc
for d in ("html", "pdf", "qr"):
    (out / d).mkdir(parents=True, exist_ok=True)
browser = next((b for b in ("chromium", "chromium-browser", "google-chrome") if shutil.which(b)), None)

for p in POSTERS:
    pid = p["id"]
    if args.ids and pid not in args.ids:
        continue
    code = segno.make(p["url"], error="q")
    code.save(str(out / "qr" / f"{pid}.png"), scale=20, border=4)
    code.save(str(out / "qr" / f"{pid}.svg"), scale=10, border=4)
    buf = io.BytesIO()
    code.save(buf, kind="svg", scale=10, border=2)
    qr = base64.b64encode(buf.getvalue()).decode()
    img = HERE.parent / f"site/img/{pid}.jpg"
    photo = f'<img class="photo" src="data:image/jpeg;base64,{base64.b64encode(img.read_bytes()).decode()}" alt="">' if img.exists() else ""
    title = "\u00a0".join(p["title"].replace(" + ", "\u00a0+\u00a0").rsplit(" ", 1))
    html = out / "html" / f"{pid}.html"
    html.write_text(TEMPLATE.format(
        title=title, desc=p["desc"], qr=qr, url=p["url"], logo=LOGO, photo=photo,
        page_class=f" poster-{pid}" + (" has-photo" if photo else ""), kicker=p["kicker"],
        contact_name=p["contact"][0], contact_email=p["contact"][1]))
    if browser:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={(out / 'pdf' / f'{pid}.pdf').resolve()}", html.resolve().as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(pid, "->", p["url"])

pdfs = [out / "pdf" / f"{pid}.pdf" for pid in ORDER]
if shutil.which("pdfunite") and all(f.exists() for f in pdfs):
    subprocess.run(["pdfunite", *pdfs, out / "all-posters.pdf"], check=True)
if not browser:
    print("No Chromium/Chrome found: open the html/ files and print them to PDF (A4, no margins).")
