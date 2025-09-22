import os, sys, time
from dotenv import load_dotenv
from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from jellyfin_apiclient_python.client import JellyfinClient

load_dotenv()

JELLYFIN_URL = os.getenv("JELLYFIN_URL")
JELLYFIN_FALLBACK_URL = os.getenv("JELLYFIN_FALLBACK_URL")
USER = os.getenv("JELLYFIN_USER")
PASSWORD = os.getenv("JELLYFIN_PASSWORD")

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
        raise RuntimeError("No session playing")
    album_id = sessions[0]["NowPlayingItem"].get("AlbumId")
    if not album_id:
        raise RuntimeError("No album info in current session")
    images = client.jellyfin.get_images(album_id)
    if not images:
        raise RuntimeError("No images for album")
    return images[0]["Path"]


def open_and_fit(path):
    img = Image.open(path.replace("\\", "/")).convert("RGB")
    img = img.resize((128, 128))
    return img


def main():
    url = login(client)
    print(f"Connected to Jellyfin at {url}")
    path = current_album_image_path()
    print(f"Album image: {path}")

    img = open_and_fit(path)
    matrix = RGBMatrix(options=opts)

    try:
        img.thumbnail((matrix.width, matrix.height))
        matrix.SetImage(img)
        time.sleep(60)
    finally:
        matrix.Clear()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("Error:", e)
        sys.exit(1)