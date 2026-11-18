"""
End-to-end test: a real Chromium browser uses the app like a person would.

Requires the backend (port 8000), PostgreSQL and the Vite dev server (port 5173)
to be running. Run from the project root:

    .\\e2e\\.venv\\Scripts\\python.exe e2e\\run_e2e.py            # headless
    .\\e2e\\.venv\\Scripts\\python.exe e2e\\run_e2e.py --headed   # watch it happen

The LIVE CAMERA is tested with Chromium's fake camera, which plays a video file
we build from a held-out CAT test photo - so the camera path must answer "Cat".
Screenshots are saved to e2e/screenshots/.
"""

import base64
import os
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import httpx
from PIL import Image, ImageOps
from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("E2E_BASE_URL", "http://localhost:5173")
TEST_IMAGES = ROOT / "training" / "dataset" / "test"
SHOTS = Path(__file__).parent / "screenshots"
WORK = Path(__file__).parent / ".work"
PASSWORD = "secret123"
EMAIL = f"e2e-{uuid.uuid4().hex[:6]}@example.com"

expect.set_options(timeout=15_000)
passed: list[str] = []


def photo(label: str, i: int) -> Path:
    return sorted((TEST_IMAGES / label).glob("*.jpg"))[i]


def make_big_photo(image: Path, out: Path) -> Path:
    """A >5 MB JPEG like a modern phone photo: 4000x3000 px, with sensor-like noise."""
    img = ImageOps.fit(Image.open(image).convert("RGB"), (4000, 3000))
    noise = Image.effect_noise((4000, 3000), 40).convert("RGB")
    Image.blend(img, noise, 0.12).save(out, "JPEG", quality=100)
    assert out.stat().st_size > 5 * 1024 * 1024, out.stat().st_size
    return out


def make_fake_camera_video(image: Path, out: Path, w: int = 640, h: int = 480) -> None:
    """Y4M = raw video format Chromium's fake camera can play (YUV 4:2:0 frames)."""
    img = ImageOps.fit(Image.open(image).convert("RGB"), (w, h))
    y, cb, cr = img.convert("YCbCr").split()
    frame = b"FRAME\n" + y.tobytes() + cb.resize((w // 2, h // 2)).tobytes() + cr.resize((w // 2, h // 2)).tobytes()
    out.write_bytes(f"YUV4MPEG2 W{w} H{h} F15:1 Ip A1:1 C420jpeg\n".encode() + frame * 15)


@contextmanager
def step(name: str, page: Page):
    start = time.time()
    try:
        yield
    except Exception:
        page.screenshot(path=SHOTS / "FAILED.png", full_page=True)
        print(f"  FAIL  {name}  (screenshot: e2e/screenshots/FAILED.png)")
        raise
    passed.append(name)
    print(f"  PASS  {name}  ({time.time() - start:.1f}s)")


def result_label(page: Page):
    return page.locator(".result-label")


def main(headed: bool) -> None:
    SHOTS.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    fake_video = WORK / "fake_camera_cat.y4m"
    make_fake_camera_video(photo("cat", 20), fake_video)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, args=[
            "--use-fake-ui-for-media-stream",        # auto-accept the permission prompt
            "--use-fake-device-for-media-stream",    # use a fake webcam...
            f"--use-file-for-fake-video-capture={fake_video}",  # ...that shows our cat video
        ])
        # ignore_https_errors: Caddy's LOCAL certificate isn't trusted by the test browser.
        ctx = browser.new_context(viewport={"width": 1280, "height": 860}, ignore_https_errors=True)
        ctx.grant_permissions(["camera"], origin=BASE)
        page = ctx.new_page()
        console_errors: list[str] = []
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and console_errors.append(m.text))

        print(f"E2E against {BASE} as {EMAIL}\n")

        # ---------------------------------------------------------------- auth
        with step("protected page redirects to /login when logged out", page):
            page.goto(f"{BASE}/dashboard")
            expect(page).to_have_url(f"{BASE}/login")
            page.screenshot(path=SHOTS / "01-login.png")

        with step("register: mismatched passwords show an error", page):
            page.get_by_role("link", name="Create one").click()
            expect(page).to_have_url(f"{BASE}/register")
            page.get_by_label("Email").fill(EMAIL)
            page.get_by_label("Password", exact=True).fill(PASSWORD)
            page.get_by_label("Confirm password").fill("different1")
            page.get_by_role("button", name="Create account").click()
            expect(page.get_by_role("alert")).to_have_text("Passwords do not match.")

        with step("register succeeds and lands on the dashboard (auto-login)", page):
            page.get_by_label("Confirm password").fill(PASSWORD)
            page.get_by_role("button", name="Create account").click()
            expect(page).to_have_url(f"{BASE}/dashboard")
            expect(page.get_by_role("heading", level=1)).to_have_text(f"Hello, {EMAIL.split('@')[0]}")
            expect(page.get_by_text("No predictions yet")).to_be_visible()
            page.screenshot(path=SHOTS / "02-dashboard-empty.png")

        # ----------------------------------------------------------- predictions
        with step("upload via file picker: cat photo -> 'Cat'", page):
            page.locator("input[type=file]").first.set_input_files(photo("cat", 0))
            expect(page.locator(".preview img")).to_be_visible()
            page.get_by_role("button", name="Predict").click()
            expect(result_label(page)).to_have_text("Cat")
            expect(page.locator(".prob-bar")).to_have_count(3)
            page.screenshot(path=SHOTS / "03-result-cat.png", full_page=True)

        with step("drag & drop: dog photo -> 'Dog'", page):
            page.get_by_role("button", name="Try another image").click()
            data = base64.b64encode(photo("dog", 0).read_bytes()).decode()
            dt = page.evaluate_handle("""([b64, name]) => {
                const bin = atob(b64); const bytes = new Uint8Array(bin.length);
                for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
                const dt = new DataTransfer();
                dt.items.add(new File([bytes], name, { type: 'image/jpeg' }));
                return dt; }""", [data, "dog.jpg"])
            page.dispatch_event(".dropzone", "dragover", {"dataTransfer": dt})
            page.dispatch_event(".dropzone", "drop", {"dataTransfer": dt})
            page.get_by_role("button", name="Predict").click()
            expect(result_label(page)).to_have_text("Dog")

        with step("non-image file is rejected in the browser with a clear message", page):
            page.get_by_role("button", name="Try another image").click()
            page.locator("input[type=file]").first.set_input_files(
                {"name": "notes.txt", "mimeType": "text/plain", "buffer": b"not an image"})
            expect(page.get_by_role("alert")).to_have_text("Please choose a JPEG, PNG or WEBP image.")

        with step("'other' photo -> 'Neither / Unknown'", page):
            page.locator("input[type=file]").first.set_input_files(photo("other", 0))
            page.get_by_role("button", name="Predict").click()
            expect(result_label(page)).to_have_text("Neither / Unknown")
            page.screenshot(path=SHOTS / "04-result-other.png", full_page=True)

        with step("photo larger than 5 MB is resized in the browser, then predicted 'Cat'", page):
            big = make_big_photo(photo("cat", 30), WORK / "big_phone_photo.jpg")
            page.get_by_role("button", name="Try another image").click()
            page.locator("input[type=file]").first.set_input_files(big)
            expect(page.locator(".alert-info")).to_contain_text("was resized to")
            print(f"        ({page.locator('.alert-info').inner_text()})")
            page.get_by_role("button", name="Predict").click()
            expect(result_label(page)).to_have_text("Cat")

        with step("live camera: start -> video streams -> capture -> predict 'Cat'", page):
            page.get_by_role("button", name="Try another image").click()
            page.get_by_role("tab", name="Live camera").click()
            page.get_by_role("button", name="Start camera").click()
            page.wait_for_function("document.querySelector('.camera-view video')?.videoWidth > 0")
            expect(page.get_by_role("button", name="Stop camera")).to_be_visible()
            page.wait_for_timeout(500)  # let a few frames render for the screenshot
            page.screenshot(path=SHOTS / "05-camera-live.png")
            page.get_by_role("button", name="Capture photo").click()
            expect(page.locator(".preview img")).to_be_visible()
            page.get_by_role("button", name="Predict").click()
            expect(result_label(page)).to_have_text("Cat")
            page.screenshot(path=SHOTS / "06-camera-result.png", full_page=True)

        with step("dashboard shows 4 recent predictions and the counter", page):
            expect(page.locator(".recent-list .history-card")).to_have_count(4)
            expect(page.locator(".stat-value")).to_have_text("5")

        # ---------------------------------------------------- history/pagination
        with step("seed 10 more predictions through the API (for pagination)", page):
            with httpx.Client(base_url=f"{BASE}/api", timeout=30, verify=False) as api:
                token = api.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
                for i in range(10):
                    img = photo(("cat", "dog")[i % 2], i + 1)
                    r = api.post("/predict", headers={"Authorization": f"Bearer {token}"},
                                 files={"file": (img.name, img.read_bytes(), "image/jpeg")})
                    assert r.status_code == 200, r.text

        with step("history page 1: 15 total, 12 cards, thumbnails load", page):
            page.get_by_role("link", name="History", exact=True).click()
            expect(page).to_have_url(f"{BASE}/history")
            expect(page.get_by_text("15 predictions in total")).to_be_visible()
            expect(page.locator(".history-grid .history-card")).to_have_count(12)
            expect(page.locator(".history-grid img.thumb[src^='blob:']")).to_have_count(12)
            page.screenshot(path=SHOTS / "07-history.png", full_page=True)

        with step("history page 2 via Next: 3 cards, ?page=2 in URL", page):
            page.get_by_role("button", name="Next →").click()
            expect(page).to_have_url(f"{BASE}/history?page=2")
            expect(page.locator(".history-grid .history-card")).to_have_count(3)
            expect(page.get_by_text("Page 2 of 2")).to_be_visible()

        with step("full page reload keeps the user logged in (silent refresh)", page):
            page.reload()
            expect(page).to_have_url(f"{BASE}/history?page=2")
            expect(page.locator(".history-grid .history-card")).to_have_count(3)

        with step("profile page shows email and total", page):
            page.get_by_role("link", name="Profile").click()
            expect(page.locator(".profile-list")).to_contain_text(EMAIL)
            expect(page.locator(".profile-list")).to_contain_text("15")
            page.screenshot(path=SHOTS / "08-profile.png")

        # ------------------------------------------------------------- mobile
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                     has_touch=True, device_scale_factor=2, ignore_https_errors=True)
        m = mobile.new_page()
        with step("mobile: login, hamburger menu, phone-camera button", m):
            m.goto(f"{BASE}/login")
            m.get_by_label("Email").fill(EMAIL)
            m.get_by_label("Password").fill(PASSWORD)
            m.get_by_role("button", name="Log in").click()
            expect(m).to_have_url(f"{BASE}/dashboard")
            expect(m.get_by_role("button", name="Take a photo with your phone camera")).to_be_visible()
            expect(m.get_by_role("link", name="History", exact=True)).to_be_hidden()
            m.screenshot(path=SHOTS / "09-mobile-dashboard.png")
            m.get_by_role("button", name="Toggle menu").click()
            expect(m.get_by_role("link", name="History", exact=True)).to_be_visible()
            m.screenshot(path=SHOTS / "10-mobile-menu.png")
            no_overflow = m.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            assert no_overflow, "page is wider than the phone screen"
        mobile.close()

        # ------------------------------------------------------------- logout
        with step("logout -> /login, protected pages blocked, refresh cookie revoked", page):
            page.get_by_role("link", name="Log out").first.click()
            expect(page).to_have_url(f"{BASE}/login")
            page.goto(f"{BASE}/dashboard")
            expect(page).to_have_url(f"{BASE}/login")
            assert page.request.post(f"{BASE}/api/auth/refresh").status == 401

        with step("wrong password shows 'Invalid email or password.'", page):
            page.get_by_label("Email").fill(EMAIL)
            page.get_by_label("Password").fill("wrongpass1")
            page.get_by_role("button", name="Log in").click()
            expect(page.get_by_role("alert")).to_have_text("Invalid email or password.")

        browser.close()

    # 401s on startup refresh / after logout are expected; anything else is a bug.
    unexpected = [e for e in console_errors if "401" not in e]
    print(f"\n{len(passed)} steps passed.")
    print(f"Browser console errors (excluding expected 401s): {unexpected or 'none'}")
    if unexpected:
        sys.exit(1)


if __name__ == "__main__":
    main(headed="--headed" in sys.argv)
