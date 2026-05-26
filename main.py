import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

LOGIN_URL = os.environ.get(
    "LOGIN_URL",
    "https://online.apac.adp.com/signin/v1/?APPID=ADPVISTA-IN"
    "&productId=ff803a24-0ee0-47fc-e053-f282530bfabe"
    "&returnURL=https://www.vista.adp.com/in/"
    "&callingAppId=ADPVISTA"
    "&TARGET=-SM-https://www.vista.adp.com/in/"
)
USERNAME = os.environ.get("USERNAME", "")
PASSWORD = os.environ.get("PASSWORD", "")

SHOTS_DIR = Path("screenshots")
SHOTS_DIR.mkdir(exist_ok=True)
_step = 0


async def shot(page, name):
    """Save a full-page screenshot with an incrementing step number."""
    global _step
    _step += 1
    fname = SHOTS_DIR / f"{_step:02d}_{name}.png"
    try:
        await page.screenshot(path=str(fname), full_page=True)
        print(f"[SCREENSHOT] Saved: {fname}")
    except Exception as e:
        print(f"[SCREENSHOT] Failed for {name}: {e}")


async def click_in_frames(page, selectors, label):
    for sel in selectors:
        try:
            await page.click(sel, timeout=4000)
            print(f"[INFO] Clicked {label} on main page via: {sel}")
            return True
        except Exception:
            pass
    for i, frame in enumerate(page.frames):
        for sel in selectors:
            try:
                await frame.click(sel, timeout=3000)
                print(f"[INFO] Clicked {label} in frame[{i}] ({frame.url[:60]}) via: {sel}")
                return True
            except Exception:
                pass
    return False


async def fill_in_frames(page, selectors, value, label):
    for sel in selectors:
        try:
            await page.wait_for_selector(sel, timeout=4000, state="visible")
            await page.fill(sel, value)
            print(f"[INFO] Filled {label} on main page via: {sel}")
            return True
        except Exception:
            pass
    for i, frame in enumerate(page.frames):
        for sel in selectors:
            try:
                await frame.wait_for_selector(sel, timeout=2000, state="visible")
                await frame.fill(sel, value)
                print(f"[INFO] Filled {label} in frame[{i}] via: {sel}")
                return True
            except Exception:
                pass
    return False


async def dump_frames(page, label=""):
    print(f"[DEBUG] === Frame dump {label} ===")
    for i, frame in enumerate(page.frames):
        try:
            items = await frame.eval_on_selector_all(
                "a, button, input[type=button], input[type=submit], [role=button]",
                "els => els.map(e => (e.innerText || e.value || e.getAttribute('aria-label') || '').trim()).filter(Boolean).slice(0,30)"
            )
            if items:
                print(f"  Frame[{i}] {frame.url[:80]}: {items}")
        except Exception:
            pass


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # ── Step 1: Open login page ───────────────────────────────────────
        print(f"[INFO] Opening login page ...")
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"[INFO] Title: {await page.title()}")
        await shot(page, "01_login_page")

        # ── Step 2: Fill username ─────────────────────────────────────────
        user_selectors = [
            "#USER", "input[name='USER']",
            "input[autocomplete='username']",
            "input[id*='user' i][type='text']",
            "input[name*='user' i][type='text']",
            "input[placeholder*='user' i]",
            "input[type='text']",
        ]
        if not await fill_in_frames(page, user_selectors, USERNAME, "User ID"):
            await shot(page, "02_error_no_username_field")
            raise RuntimeError("User ID field not found")
        await shot(page, "02_username_filled")

        # ── Step 3: Click Next ────────────────────────────────────────────
        submit_selectors = [
            "input[type='submit']", "button[type='submit']",
            "#submit-button", "button:has-text('Next')",
            "button:has-text('Continue')", "button:has-text('Sign In')",
            "input[value='Next']", "input[value='Submit']", "input[value='Sign In']",
        ]
        if not await click_in_frames(page, submit_selectors, "Next button"):
            await page.keyboard.press("Enter")
            print("[INFO] Fallback: pressed Enter")
        await page.wait_for_timeout(4000)
        print(f"[INFO] After Next — title: {await page.title()}")
        await shot(page, "03_after_next_click")

        # ── Step 4: Fill password ─────────────────────────────────────────
        pass_selectors = [
            "#PASSWORD", "input[name='PASSWORD']",
            "input[type='password']",
            "input[autocomplete='current-password']",
            "input[id*='pass' i]", "input[name*='pass' i]",
        ]
        if not await fill_in_frames(page, pass_selectors, PASSWORD, "Password"):
            await shot(page, "04_error_no_password_field")
            raise RuntimeError("Password field not found")
        await shot(page, "04_password_filled")

        # ── Step 5: Submit login ──────────────────────────────────────────
        if not await click_in_frames(page, submit_selectors, "Submit"):
            await page.keyboard.press("Enter")
            print("[INFO] Fallback: pressed Enter")

        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeout:
            print("[WARN] networkidle timeout after login")

        await page.wait_for_timeout(3000)
        print(f"[INFO] Logged in — title: {await page.title()}")
        print(f"[INFO] Logged in — URL  : {page.url}")
        await shot(page, "05_logged_in")

        # ── Step 6: Dismiss popup ─────────────────────────────────────────
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(2000)
        await shot(page, "06_after_esc")

        # ── Step 7: Click Me ──────────────────────────────────────────────
        print("[INFO] Clicking Me ...")
        me_selectors = [
            "text=Me", "a:has-text('Me')", "[aria-label='Me']",
            "[title='Me']", "span:has-text('Me')",
            "li:has-text('Me') > a", "nav >> text=Me",
        ]
        if not await click_in_frames(page, me_selectors, "Me"):
            await shot(page, "07_error_me_not_found")
            await dump_frames(page, "Me not found")
            raise RuntimeError("Me not found in any frame")

        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            pass
        await page.wait_for_timeout(2000)
        print(f"[INFO] After Me — title: {await page.title()}")
        await shot(page, "07_after_me_click")

        # ── Step 8: Click Time & Attendance ──────────────────────────────
        print("[INFO] Clicking Time & Attendance ...")
        ta_selectors = [
            "text=Time & Attendance",
            "text=Time and Attendance",
            "a:has-text('Time & Attendance')",
            "a:has-text('Time and Attendance')",
            "a:has-text('Attendance')",
            "[title*='Time']",
            "span:has-text('Time & Attendance')",
        ]
        if not await click_in_frames(page, ta_selectors, "Time & Attendance"):
            await shot(page, "08_error_ta_not_found")
            await dump_frames(page, "T&A not found")
            raise RuntimeError("Time & Attendance not found in any frame")

        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeout:
            pass
        await page.wait_for_timeout(3000)
        print(f"[INFO] T&A — title: {await page.title()}")
        await shot(page, "08_time_attendance_page")

        # ── Step 9: Click Punch Out ───────────────────────────────────────
        print("[INFO] Clicking Punch Out ...")
        punch_selectors = [
            "text=Punch Out",
            "button:has-text('Punch Out')",
            "input[value='Punch Out']",
            "a:has-text('Punch Out')",
            "[aria-label='Punch Out']",
            "[title='Punch Out']",
        ]
        if not await click_in_frames(page, punch_selectors, "Punch Out"):
            await shot(page, "09_error_punch_out_not_found")
            await dump_frames(page, "Punch Out not found")
            raise RuntimeError("Punch Out button not found in any frame")

        await page.wait_for_timeout(3000)
        await shot(page, "09_punch_out_done")
        print("[SUCCESS] Punch Out completed successfully!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
