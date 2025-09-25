import os, sys, time, io, hashlib, random, string, requests
from dotenv import load_dotenv
from typing import Optional, Tuple
from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from jellyfin_apiclient_python.client import JellyfinClient

load_dotenv()

# --- Navidrome/Subsonic config ---
ND_URL   = os.getenv("NAVIDROME_URL", "").rstrip("/")
ND_USER  = os.getenv("NAVIDROME_USER")
ND_PASS  = os.getenv("NAVIDROME_PASSWORD")
ND_CLIENT= os.getenv("NAVIDROME_CLIENT", "led-matrix")
API_VER  = "1.16.1"   # Subsonic compatible
POLL     = int(os.getenv("POLL_SECONDS", 5))

JELLYFIN_URL = os.getenv("JELLYFIN_URL")
JELLYFIN_FALLBACK_URL = os.getenv("JELLYFIN_FALLBACK_URL")
USER = os.getenv("JELLYFIN_USER")
PASSWORD = os.getenv("JELLYFIN_PASSWORD")
MEDIA_MOUNT_POINT = os.getenv("MEDIA_MOUNT_POINT")

opts = RGBMatrixOptions()
opts.rows = int(os.getenv("MATRIX_ROWS", 64))
opts.cols = int(os.getenv("MATRIX_COLS", 64))
opts.chain_length = int(os.getenv("MATRIX_CHAIN", 2))
opts.parallel = int(os.getenv("MATRIX_PARALLEL", 2))
opts.brightness = int(os.getenv("MATRIX_BRIGHTNESS", 40))
opts.limit_refresh_rate_hz = int(os.getenv("MATRIX_LIMIT_HZ", 60))
opts.gpio_slowdown = int(os.getenv("MATRIX_GPIO_SLOWDOWN", 2))
opts.multiplexing = int(os.getenv("MATRIX_MULTIPLEXING", 0))
opts.hardware_mapping = "regular"
opts.drop_privileges = False

client = JellyfinClient()
client.config.app("LED Album Display", "0.1.0", "RaspberryPi", "1")
client.config.data["auth.ssl"] = True

def login(client):
    for url in filter(None, [JELLYFIN_URL, JELLYFIN_FALLBACK_URL]):
        try:
            client.auth.connect_to_address(url)
            client.auth.login(url, USER, PASSWORD)
            return url
        except Exception:
            continue
    raise RuntimeError("Failed to connect to Jellyfin")

def current_album_image_path():
    sessions = client.jellyfin.get_sessions()

    if not sessions or "NowPlayingItem" not in sessions[0]:
        return None
    
    album_id = sessions[0]["NowPlayingItem"].get("AlbumId")

    if not album_id:
        raise RuntimeError("No album ID")
    
    images = client.jellyfin.get_images(album_id)

    if not images:
        raise RuntimeError("No images for album")
    #print(images[0]["Path"])
    return images[0]["Path"]

def open_and_fit(path):
    img = Image.open(path.replace("\\", "/")).convert("RGB")
    img = img.resize((128, 128))
    return img

def convert_to_mount_path(server_path: str) -> str:
    if not MEDIA_MOUNT_POINT:
        raise RuntimeError("MOUNT_POINT is not set in environment")
    # strip leading backslashes or slashes from Jellyfin path if needed
    return os.path.join(MEDIA_MOUNT_POINT, server_path.lstrip("/\\"))

#--------------------------------------Navidrome--------------------------------------#
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



def main():
    url = login(client)
    print(f"Connected to Jellyfin at {url}")

    matrix = RGBMatrix(options=opts)

    oldpath = None

    while True:

        path = current_album_image_path()

        if(path == None):
            matrix.Clear()
            print("No track playing")

        if(oldpath != path):
            newpath = convert_to_mount_path(path)

            newimg = open_and_fit(newpath)
        
            newimg.thumbnail((matrix.width, matrix.height))
            matrix.SetImage(newimg)

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("Error:", e)
        sys.exit(1)