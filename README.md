# Leica Project Days

A small static website for Leica Geosystems Project Days: one tab per student project, a
Previous Projects page, and a Student Programmer job page. It also includes printable A4
posters with a QR code that opens each project's tab.

## Layout

| Path | What it is |
|---|---|
| `site/` | The website: plain HTML/CSS/JS, no build step. All links are relative, so it works on any domain. |
| `site/index.html` | All page content. The project texts are in the `PROJECTS` array near the bottom. |
| `site/img/` | Images. `<poster-id>.jpg` is also used as that poster's picture. |
| `print/build.py` | Generates the posters and QR codes for a given domain. |
| `deploy/nginx.conf` | Example nginx server block. |

## Deploy the site

Copy `site/` to the server and point a web server at it, for example with nginx:

```bash
rsync -a --delete site/ root@<server>:/var/www/projectdays/
ssh root@<server> 'chown -R www-data:www-data /var/www/projectdays'
```

Then install `deploy/nginx.conf` (set `server_name` and `root`) and run
`certbot --nginx -d <your-domain> --redirect` for HTTPS.

Links to individual pages:

- Home: `https://<domain>/`
- A project: `https://<domain>/#projects/<id>` (e.g. `surface-mapping`, `blade-pose`, `ins-sensor-fusion`,
  `tool-recognition`, `radar-camera`, `vr-teleoperation`)
- Job: `https://<domain>/#job`

## Posters and QR codes

QR codes contain the full URL, including the domain, so each domain needs its own set of posters.

```bash
pip install segno            # Chromium/Chrome and pdfunite (poppler-utils) are used if installed
python print/build.py --base https://<your-domain>/
python print/build.py --base https://<your-domain>/ job    # only rebuild one poster
```

Output goes to `print/out/<domain>/`:

- `pdf/<id>.pdf`: one A4 poster per project, plus `home` and `job`
- `all-posters.pdf`: all posters in one file
- `qr/<id>.png|svg`: just the QR codes

The QR codes for the domains in use are committed in `print/out/<domain>/qr/`
(`sducollab.duckdns.org` and `sducollab.conx.leica-geosystems.com`). The PDFs are not committed; rebuild them.

Poster texts are in `PROJECTS` and `POSTERS` at the top of `print/build.py`. They are shorter
than the website texts on purpose.

**Several domains at the same time:** printed QR codes keep working only while their domain is
online. If a domain is retired, point it at a server that 301-redirects to the new domain. Browsers
keep the `#projects/...` part through the redirect, so old posters still open the right project.
