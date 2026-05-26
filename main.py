import os
import asyncio
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


async def click_in_all_frames(page, selectors, label):
    """Try clicking selectors on main page and all iframes."""
    # Try main page first
    for sel in selectors:
        try:
            await page.click(sel, timeout=4000)
            print(f"[INFO] Clicked {label} on main page via: {sel}")
            return True
        except Exception:
            pass
    # Try every iframe
    for i, frame in enumerate(page.frames):
        for sel in selectors:
            try:
                await frame.click(sel, timeout=3000)
                print(f"[INFO] Clicked {label} in frame[{i}] via: {sel}")
                return True
            except Exception:
                pass
    return False


async def fill_in_all_frames(page, selectors, value, label):
    """Try filling a field on main page and all iframes."""
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


async def dump_all_frames(page):
    """Print all clickable elements across all frames for debugging."""
    for i, frame in enumerate(page.frames):
        try:
            items = await frame.eval_on_selector_all(
                "a, button, input[type=button], input[type=submit], [role=button], [role=link]",
                "els => els.map(e => (e.innerText || e.value || e.getAttribute('aria-label') || '').trim()).filter(Boolean)"
            )
            if items:
                print(f"[DEBUG] Frame[{i}] url={frame.url[:80]} items={items[:30]}")
        except Exception as ex:
            print(f"[DEBUG] Frame[{i}] error: {ex}")


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

        # ── 1. Open login page ────────────────────────────────────────────
        print(f"[INFO] Navigating to login page ...")
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"[INFO] Login page title: {await page.title()}")

        # ── 2. Fill User ID ───────────────────────────────────────────────
        print("[INFO] Filling User ID ...")
        user_selectors = [
            "#USER", "input[name='USER']", "input[id='USER']",
            "input[autocomplete='username']",
            "input[id*='user' i][type='text']",
            "input[name*='user' i][type='text']",
            "input[placeholder*='user' i]",
            "input[type='text']",
        ]
        if not await fill_in_all_frames(page, user_selectors, USERNAME, "User ID"):
            raise RuntimeError("User ID field not found")

        # ── 3. Click Next after username ──────────────────────────────────
        print("[INFO] Clicking Next after username ...")
        submit_selectors = [
            "input[type='submit']", "button[type='submit']",
            "#submit-button", "button:has-text('Next')",
            "button:has-text('Continue')", "button:has-text('Sign In')",
            "input[value='Next']", "input[value='Submit']",
            "input[value='Sign In']",
        ]
        if not await click_in_all_frames(page, submit_selectors, "Next button"):
            await page.keyboard.press("Enter")
            print("[INFO] Pressed Enter as fallback")

        await page.wait_for_timeout(4000)
        print(f"[INFO] After username submit — title: {await page.title()}")

        # ── 4. Fill Password ──────────────────────────────────────────────
        print("[INFO] Filling Password ...")
        pass_selectors = [
            "#PASSWORD", "input[name='PASSWORD']", "input[id='PASSWORD']",
            "input[type='password']", "input[autocomplete='current-password']",
            "input[id*='pass' i]", "input[name*='pass' i]",
        ]
        if not await fill_in_all_frames(page, pass_selectors, PASSWORD, "Password"):
            raise RuntimeError("Password field not found")

        # ── 5. Submit password ────────────────────────────────────────────
        print("[INFO] Submitting password ...")
        if not await click_in_all_frames(page, submit_selectors, "Submit button"):
            await page.keyboard.press("Enter")
            print("[INFO] Pressed Enter as fallback")

        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeout:
            print("[WARN] Timeout after login - continuing")

        await page.wait_for_timeout(3000)
        print(f"[INFO] Logged in — title: {await page.title()}")
        print(f"[INFO] Logged in — URL  : {page.url}")

        # ── 6. Dismiss popup with ESC ─────────────────────────────────────
        print("[INFO] Pressing ESC to dismiss popup ...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(2000)

        # ── 7. Click 'Me' — search all frames ────────────────────────────
        print("[INFO] Clicking 'Me' in sidebar ...")
        me_selectors = [
            "text=Me",
            "a:has-text('Me')",
            "[aria-label='Me']",
            "[title='Me']",
            "span:has-text('Me')",
            "li:has-text('Me') > a",
            "nav >> text=Me",
        ]
        if not await click_in_all_frames(page, me_selectors, "'Me'"):
            print("[DEBUG] Could not click Me — dumping all frames:")
            await dump_all_frames(page)
            raise RuntimeError("'Me' sidebar item not found in any frame")

        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            pass
        await page.wait_for_timeout(2000)
        print(f"[INFO] After Me click — title: {await page.title()}")

        # ── 8. Click 'Time & Attendance' — search all frames ─────────────
        print("[INFO] Clicking 'Time & Attendance' ...")
        ta_selectors = [
            "text=Time & Attendance",
            "text=Time and Attendance",
            "a:has-text('Time & Attendance')",
            "a:has-text('Time and Attendance')",
            "a:has-text('Attendance')",
            "[title*='Time']",
            "span:has-text('Time & Attendance')",
        ]
        if not await click_in_all_frames(page, ta_selectors, "'Time & Attendance'"):
            print("[DEBUG] Could not find Time & Attendance — dumping all frames:")
            await dump_all_frames(page)
            raise RuntimeError("'Time & Attendance' not found in any frame")

        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeout:
            pass
        await page.wait_for_timeout(3000)
        print(f"[INFO] T&A page title: {await page.title()}")

        # ── 9. Click 'Punch Out' — search all frames ──────────────────────
        print("[INFO] Clicking 'Punch Out' ...")
        punch_selectors = [
            "text=Punch Out",
            "button:has-text('Punch Out')",
            "input[value='Punch Out']",
            "a:has-text('Punch Out')",
            "[aria-label='Punch Out']",
            "[title='Punch Out']",
        ]
        if not await click_in_all_frames(page, punch_selectors, "'Punch Out'"):
            print("[DEBUG] Punch Out not found — dumping all frames:")
            await dump_all_frames(page)
            raise RuntimeError("'Punch Out' button not found in any frame")

        await page.wait_for_timeout(3000)
        print("[SUCCESS] Punch Out completed successfully!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
