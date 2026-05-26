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


async def click_in_frames(page, selectors, label):
    for sel in selectors:
        try:
            await page.click(sel, timeout=4000)
            print(f"[OK] Clicked '{label}' on main page  =>  {sel}")
            return True
        except Exception:
            pass
    for i, frame in enumerate(page.frames):
        for sel in selectors:
            try:
                await frame.click(sel, timeout=3000)
                print(f"[OK] Clicked '{label}' in frame[{i}]  =>  {sel}")
                return True
            except Exception:
                pass
    return False


async def fill_in_frames(page, selectors, value, label):
    for sel in selectors:
        try:
            await page.wait_for_selector(sel, timeout=4000, state="visible")
            await page.fill(sel, value)
            print(f"[OK] Filled '{label}' on main page  =>  {sel}")
            return True
        except Exception:
            pass
    for i, frame in enumerate(page.frames):
        for sel in selectors:
            try:
                await frame.wait_for_selector(sel, timeout=2000, state="visible")
                await frame.fill(sel, value)
                print(f"[OK] Filled '{label}' in frame[{i}]  =>  {sel}")
                return True
            except Exception:
                pass
    return False


async def dump_clickables(page, context=""):
    print(f"[DEBUG] ---- Dump: {context} ----")
    for i, frame in enumerate(page.frames):
        try:
            items = await frame.eval_on_selector_all(
                "a, button, input[type=button], input[type=submit], [role=button], [role=menuitem], [role=tab]",
                "els => els.map(e => (e.innerText || e.value || e.getAttribute('aria-label') || e.getAttribute('title') || '').trim()).filter(Boolean)"
            )
            if items:
                print(f"  Frame[{i}]: {items[:50]}")
        except Exception as ex:
            print(f"  Frame[{i}] error: {ex}")
    print(f"[DEBUG] ---- end ----")


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

        # ── STEP 1: Open login page ───────────────────────────────────────
        print("=" * 60)
        print("[STEP 1] Opening login page ...")
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        print(f"  Title : {await page.title()}")

        # ── STEP 2: Fill username ─────────────────────────────────────────
        print("[STEP 2] Filling username ...")
        user_selectors = [
            "#USER", "input[name='USER']",
            "input[autocomplete='username']",
            "input[id*='user' i][type='text']",
            "input[type='text']",
        ]
        if not await fill_in_frames(page, user_selectors, USERNAME, "Username"):
            raise RuntimeError("FAILED at STEP 2: Username field not found")

        # ── STEP 3: Click Next ────────────────────────────────────────────
        print("[STEP 3] Submitting username ...")
        submit_selectors = [
            "input[type='submit']", "button[type='submit']",
            "button:has-text('Next')", "button:has-text('Sign In')",
            "input[value='Next']", "input[value='Submit']",
        ]
        if not await click_in_frames(page, submit_selectors, "Next"):
            await page.keyboard.press("Enter")
            print("  Fallback: Enter key")
        await page.wait_for_timeout(4000)

        # ── STEP 4: Fill password ─────────────────────────────────────────
        print("[STEP 4] Filling password ...")
        pass_selectors = [
            "#PASSWORD", "input[name='PASSWORD']",
            "input[type='password']",
        ]
        if not await fill_in_frames(page, pass_selectors, PASSWORD, "Password"):
            raise RuntimeError("FAILED at STEP 4: Password field not found")

        # ── STEP 5: Submit login ──────────────────────────────────────────
        print("[STEP 5] Submitting login ...")
        if not await click_in_frames(page, submit_selectors, "Submit"):
            await page.keyboard.press("Enter")
            print("  Fallback: Enter key")

        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeout:
            print("  [WARN] networkidle timeout - continuing")

        await page.wait_for_timeout(3000)
        print(f"  Title after login: {await page.title()}")
        print(f"  URL   after login: {page.url}")

        # ── STEP 6: Dismiss popup with ESC ───────────────────────────────
        print("[STEP 6] ESC to dismiss popup ...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(2000)

        # ── STEP 7: Click 'Me' sidebar item to expand it ─────────────────
        # From logs: 'Expand Me' and 'Me' both exist.
        # 'Expand Me' is the aria-label on the sidebar toggle.
        print("[STEP 7] Clicking 'Me' / 'Expand Me' to open the submenu ...")
        me_selectors = [
            "[aria-label='Expand Me']",
            "text=Expand Me",
            "[aria-label='Me']",
            "text=Me",
            "a:has-text('Me')",
            "span:has-text('Me')",
        ]
        if not await click_in_frames(page, me_selectors, "Me/Expand Me"):
            await dump_clickables(page, "Me not found")
            raise RuntimeError("FAILED at STEP 7: Me sidebar item not found")

        await page.wait_for_timeout(2000)
        print(f"  Title after Me: {await page.title()}")

        # ── STEP 8: Click 'Time & Attendance' ────────────────────────────
        # From logs the available items after Me are:
        # 'View Payslip', 'Pay History', 'Tax Statement', 'Tax Submission' etc.
        # T&A was NOT in the list — maybe we need to scroll or it appears after expand.
        # Try all possible names including abbreviations.
        print("[STEP 8] Clicking 'Time & Attendance' ...")
        ta_selectors = [
            "text=Time & Attendance",
            "text=Time and Attendance",
            "a:has-text('Time & Attendance')",
            "a:has-text('Time and Attendance')",
            "a:has-text('Attendance')",
            "span:has-text('Time & Attendance')",
            "[title*='Attendance']",
            "[aria-label*='Attendance']",
            "text=T&A",
            "a:has-text('T&A')",
        ]
        if not await click_in_frames(page, ta_selectors, "Time & Attendance"):
            # Dump to see what's available after Me expand
            await dump_clickables(page, "T&A not found - after Me click")
            raise RuntimeError("FAILED at STEP 8: Time & Attendance not found")

        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeout:
            pass
        await page.wait_for_timeout(3000)
        print(f"  Title after T&A: {await page.title()}")
        print(f"  URL   after T&A: {page.url}")

        # ── STEP 9: Click Punch Out ───────────────────────────────────────
        print("[STEP 9] Clicking 'Punch Out' ...")
        punch_selectors = [
            "text=Punch Out",
            "button:has-text('Punch Out')",
            "input[value='Punch Out']",
            "a:has-text('Punch Out')",
            "[aria-label='Punch Out']",
            "[title='Punch Out']",
        ]
        if not await click_in_frames(page, punch_selectors, "Punch Out"):
            await dump_clickables(page, "Punch Out not found")
            raise RuntimeError("FAILED at STEP 9: Punch Out button not found")

        await page.wait_for_timeout(3000)
        print("=" * 60)
        print("[SUCCESS] Punch Out completed successfully!")
        print("=" * 60)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
