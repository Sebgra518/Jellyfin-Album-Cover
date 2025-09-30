#!/usr/bin/env python3
import os, sys, time, io, hashlib, random, string, requests
from typing import Optional, Tuple
from dotenv import load_dotenv
from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions

load_dotenv()

# --- Navidrome/Subsonic config ---
ND_URL   = os.getenv("NAVIDROME_URL", "").rstrip("/")
ND_USER  = os.getenv("NAVIDROME_USER")
ND_PASS  = os.getenv("NAVIDROME_PASSWORD")
ND_CLIENT= os.getenv("NAVIDROME_CLIENT", "led-matrix")
API_VER  = "1.16.1"   # Subsonic compatible
POLL     = int(os.getenv("POLL_SECONDS", 5))

# --- Matrix config ---
opts = RGBMatrixOptions()
opts.rows              = int(os.getenv("MATRIX_ROWS", 64))
opts.cols              = int(os.getenv("MATRIX_COLS", 64))
opts.chain_length      = int(os.getenv("MATRIX_CHAIN", 2))
opts.parallel          = int(os.getenv("MATRIX_PARALLEL", 2))
opts.brightness        = int(os.getenv("MATRIX_BRIGHTNESS", 40))
opts.limit_refresh_rate_hz = int(os.getenv("MATRIX_LIMIT_HZ", 60))
opts.gpio_slowdown     = int(os.getenv("MATRIX_GPIO_SLOWDOWN", 2))
opts.multiplexing      = int(os.getenv("MATRIX_MULTIPLEXING", 0))
opts.hardware_mapping  = "regular"
opts.drop_privileges   = False

# --- auth helper (Subsonic token auth) ---
def _salt(n=8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))

def _token(password: str, salt: str) -> str:
    # token = md5(password + salt)
    h = hashlib.md5()
    h.update((password + salt).encode("utf-8"))
    return h.hexdigest()

def _auth_params() -> dict:
    if not (ND_URL and ND_USER and ND_PASS):
        raise RuntimeError("Missing NAVIDROME_URL / NAVIDROME_USER / NAVIDROME_PASSWORD")
    s = _salt()
    return {
        "u": ND_USER,
        "t": _token(ND_PASS, s),
        "s": s,
        "v": API_VER,
        "c": ND_CLIENT,
        "f": "json"
    }

# --- API calls ---
def get_now_playing_for_user(username: str) -> Optional[dict]:
    """
    Returns the first now-playing entry for the given user, or None if nothing is playing.
    """
    params = _auth_params()
    url = f"{ND_URL}/rest/getNowPlaying.view"
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    entries = data.get("subsonic-response", {}).get("nowPlaying", {}).get("entry", [])
    if not entries:
        return None
    # Navidrome may report multiple users; pick this user
    for e in entries:
        if e.get("username") == username:
            return e
    # If nothing matched, return first (optional) or None
    return None

def get_cover_image(cover_id: str, size: Tuple[int,int]=(128,128)) -> Image.Image:
    params = _auth_params()
    # size is optional; many servers accept 'size' to scale
    params["id"] = cover_id
    params["size"] = max(size)  # Subsonic expects a single edge size
    url = f"{ND_URL}/rest/getCoverArt.view"
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    if img.size != size:
        img = img.resize(size)
    return img

# --- main loop ---
def main():
    matrix = RGBMatrix(options=opts)
    last_track_id = None

    try:
        while True:
            try:
                entry = get_now_playing_for_user(ND_USER)
                if not entry:
                    # nothing playing; clear once and wait
                    matrix.Clear()
                    print("No track playing", flush=True)
                    time.sleep(POLL)
                    continue

                track_id = entry.get("id") or entry.get("streamId") or entry.get("title")
                cover_id = entry.get("coverArt") or entry.get("albumId")

                if not cover_id:
                    print("No coverArt for current track; clearing.", flush=True)
                    matrix.Clear()
                    time.sleep(POLL)
                    continue

                if track_id != last_track_id:
                    # fetch and display new art
                    img = get_cover_image(cover_id, (128,128))
                    img.thumbnail((matrix.width, matrix.height))
                    matrix.SetImage(img)
                    last_track_id = track_id
                    print(f"Updated art: {entry.get('artist','')} — {entry.get('album','')} — {entry.get('title','')}", flush=True)
                else:
                    # unchanged; no update
                    pass

            except requests.HTTPError as e:
                print("HTTP error:", e, flush=True)
                matrix.Clear()
                last_track_id = None
            except Exception as e:
                print("Error:", e, flush=True)
                matrix.Clear()
                last_track_id = None

            time.sleep(POLL)
    except KeyboardInterrupt:
        print("Interrupted", flush=True)
    finally:
        try:
            matrix.Clear()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Fatal:", e)
        sys.exit(1)
