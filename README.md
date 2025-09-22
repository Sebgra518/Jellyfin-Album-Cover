# LED Album Display (128×128 RGB Matrix on Raspberry Pi 4B)

Show the currently playing album art from Jellyfin on a 128×128 LED matrix (4× 64×64 panels) driven by a Raspberry Pi 4B and a Raspberry Pi RGB matrix HAT.

> ⚠️ **Security note**: Do **not** commit real server addresses, usernames, or passwords. This README uses environment variables and an `.env` file. Rotate any credentials you’ve previously committed.

---

## Demo

*Add a short GIF or video here (5–10s). A crisp demo does more than paragraphs.*

---

## Features

* Fetches the currently playing track from Jellyfin and retrieves the album art
* Resizes/converts the art and displays it on a 128×128 panel (4× 64×64)
* Runs automatically on boot as a service
* Uses the battle‑tested [`hzeller/rpi-rgb-led-matrix`](https://github.com/hzeller/rpi-rgb-led-matrix) library

---

## Hardware

* **Controller:** Raspberry Pi 4B (2–8 GB)
* **HAT:** RGB Matrix Panel Drive Board for Raspberry Pi (Electrodragon V2)
* **Panels:** 4× 64×64 HUB75 RGB LED matrix panels
* **Power:** Sufficient 5V supply for Pi + 5V supply for panels (size per panel spec)
* **Cables:** IDC ribbon + power leads for HUB75

> **Panel topology:** 2×2 grid. Configured as `chain_length=2`, `parallel=2` for the hzeller library.

---

## System Diagram

```
Jellyfin Server ──(HTTP API)──> Raspberry Pi 4B ──HUB75──> Electrodragon HAT ──> 4×64×64 Panels (2×2)
```

---

## Prerequisites

* Raspberry Pi OS (Bookworm or Bullseye) with Python 3
* Build tools for `rpi-rgb-led-matrix` (see their README)
* Python packages: `Pillow`, `jellyfin-apiclient-python`, `python-dotenv`

---

## Setup

### 1) Clone and install matrix library

Follow the official instructions from `hzeller/rpi-rgb-led-matrix` to build and enable GPIO access for your Pi. Make sure examples can run before continuing.

### 2) Project install

```bash
# inside your projects dir
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

*Example `requirements.txt`*

```
jellyfin-apiclient-python
Pillow
python-dotenv
rpi-rgb-led-matrix
```

### 3) Configure environment

Create a `.env` in the project root (do not commit it):

```
JELLYFIN_URL=http://192.168.x.y:8096
JELLYFIN_USER=your-user
JELLYFIN_PASSWORD=your-password
# Optional: alternate URL if first fails (e.g., Tailscale)
JELLYFIN_FALLBACK_URL=http://100.xx.xx.xx:8096
# Matrix options
MATRIX_ROWS=64
MATRIX_COLS=64
MATRIX_CHAIN=2
MATRIX_PARALLEL=2
MATRIX_BRIGHTNESS=40
MATRIX_LIMIT_HZ=60
MATRIX_GPIO_SLOWDOWN=2
MATRIX_MULTIPLEXING=0
```

### 4) Wiring & layout

* Arrange panels in a 2×2 grid
* Match orientation consistently (all HUB75 connectors aligned)
* If images appear mirrored/rotated, adjust `--led-panel-type`, `--led-scan-mode` or rotation in code

---

## Running

### One‑off run

```bash
source .venv/bin/activate
python album_display.py
```

### Run on boot (systemd)

Create `/etc/systemd/system/album-display.service`:

```
[Unit]
Description=LED Album Display
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/led-album-display
Environment=PYTHONUNBUFFERED=1
Environment=DOTENV_CONFIG_PATH=/home/pi/led-album-display/.env
ExecStart=/home/pi/led-album-display/.venv/bin/python /home/pi/led-album-display/album_display.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable + start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable album-display
sudo systemctl start album-display
journalctl -u album-display -f
```

---

## Configuration

You can tune the matrix behavior via env vars:

* `MATRIX_BRIGHTNESS` (0–100)
* `MATRIX_LIMIT_HZ` (refresh rate)
* `MATRIX_GPIO_SLOWDOWN`, `MATRIX_MULTIPLEXING`
* Panel type flags if you use a non‑default panel

For Jellyfin, the app logs the active URL (primary or fallback). If no session is playing, the app exits gracefully (systemd will restart if configured).

---

## How it works

1. Authenticate to Jellyfin via `jellyfin-apiclient-python`
2. Fetch active session and current track
3. Request the album image path
4. Open the image (local/NAS path or via URL), resize to 128×128
5. Display the image on the matrix using `RGBMatrix.SetImage`
6. Keep it visible for a timeout, then clear

---

## Troubleshooting

* **Black screen / flicker:** lower `MATRIX_BRIGHTNESS`, increase `MATRIX_GPIO_SLOWDOWN`, confirm power budget
* **Wrong orientation:** try panel type flags or rotate image before display
* **No image found:** confirm Jellyfin session is active and `AlbumId` exists; check permissions/paths
* **Service starts before network:** ensure `After=network-online.target` and `Wants=network-online.target`

---

## Performance & Power

* High brightness dramatically increases current draw—size PSU accordingly
* Limit refresh rate to reduce ghosting and CPU usage
* Consider double‑buffering & `FrameCanvas` for future animations

---

## Roadmap

* Show artist/title text overlay
* Add fallback art when nothing is playing
* Support multiple sessions or a session picker
* Add web UI for configuration

---

## License
This project is licensed under the [MIT License](./LICENSE).

---

## Acknowledgements

* [`hzeller/rpi-rgb-led-matrix`](https://github.com/hzeller/rpi-rgb-led-matrix)
* Electrodragon RGB Matrix Panel Drive Board for Raspberry Pi V2
