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


async def safe_click(page_or_frame, selectors, label="element", timeout=5000):
    """Try a list of selectors; return True if one worked."""
    for sel in selectors:
        try:
            await page_or_frame.click(sel, timeout=timeout)
            print(f"[INFO] Clicked {label} via: {sel}")
            return True
        except Exception:
            pass
    return False


async def safe_fill(page_or_frame, selectors, value, label="field", timeout=5000):
    """Try a list of selectors to fill a field; return True if one worked."""
    for sel in selectors:
        try:
            await page_or_frame.wait_for_selector(sel, timeout=timeout, state="visible")
            await page_or_frame.fill(sel, value)
            print(f"[INFO] Filled {label} via: {sel}")
            return True
        except Exception:
            pass
    return False


async def dump_inputs(page):
    """Debug helper — print all visible input fields."""
    inputs = await page.eval_on_selector_all(
        "input",
        "els => els.map(e => ({type: e.type, id: e.id, name: e.name, placeholder: e.placeholder, visible: e.offsetParent !== null}))"
    )
    print(f"[DEBUG] Inputs on page: {inputs}")


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
        print(f"[INFO] Navigating to: {LOGIN_URL}")
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(3_000)
        print(f"[INFO] Page title: {await page.title()}")
        await dump_inputs(page)

        # ── 2. Fill User ID ───────────────────────────────────────────────
        print("[INFO] Filling User ID ...")
        user_selectors = [
            "#USER",
            "input[name='USER']",
            "input[id='USER']",
            "input[autocomplete='username']",
            "input[id*='user' i][type='text']",
            "input[name*='user' i][type='text']",
            "input[placeholder*='user' i]",
            "input[type='text']",
        ]
        if not await safe_fill(page, user_selectors, USERNAME, "User ID"):
            print("[ERROR] Could not find User ID field")
            await dump_inputs(page)
            raise RuntimeError("User ID field not found")

        # ── 3. Submit / Next after username ───────────────────────────────
        # ADP VISTA is a two-step login: username page → password page
        print("[INFO] Submitting username (Next step) ...")
        submit_selectors = [
            "input[type='submit']",
            "button[type='submit']",
            "#submit-button",
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Sign In')",
            "button:has-text('Log In')",
            "[data-testid='submit']",
            "input[value='Next']",
            "input[value='Submit']",
            "input[value='Sign In']",
        ]
        clicked_next = await safe_click(page, submit_selectors, "Next button")
        if not clicked_next:
            # Fallback: press Enter in the username field
            print("[INFO] No submit button found, pressing Enter in username field")
            for sel in user_selectors:
                try:
                    await page.press(sel, "Enter")
                    clicked_next = True
                    print(f"[INFO] Pressed Enter in: {sel}")
                    break
                except Exception:
                    pass

        # Wait for the password page to load
        await page.wait_for_timeout(4_000)
        print(f"[INFO] After Next — title: {await page.title()}")
        print(f"[INFO] After Next — URL  : {page.url}")
        await dump_inputs(page)

        # ── 4. Fill Password ──────────────────────────────────────────────
        print("[INFO] Filling Password ...")
        pass_selectors = [
            "#PASSWORD",
            "input[name='PASSWORD']",
            "input[id='PASSWORD']",
            "input[type='password']",
            "input[autocomplete='current-password']",
            "input[id*='pass' i]",
            "input[name*='pass' i]",
            "input[placeholder*='pass' i]",
        ]
        if not await safe_fill(page, pass_selectors, PASSWORD, "Password"):
            print("[ERROR] Password field not found on main page, trying iframes ...")
            filled_pass = False
            for frame in page.frames:
                if await safe_fill(frame, pass_selectors, PASSWORD, "Password (iframe)"):
                    filled_pass = True
                    break
            if not filled_pass:
                await dump_inputs(page)
                raise RuntimeError("Password field not found")

        # ── 5. Submit login ───────────────────────────────────────────────
        print("[INFO] Submitting login (password step) ...")
        clicked_submit = await safe_click(page, submit_selectors, "Submit button")
        if not clicked_submit:
            await page.keyboard.press("Enter")
            print("[INFO] Submitted via Enter key")

        try:
            await page.wait_for_load_state("networkidle", timeout=30_000)
        except PlaywrightTimeout:
            print("[WARN] networkidle timeout after login - continuing")

        await page.wait_for_timeout(3_000)
        print(f"[INFO] Logged in — title: {await page.title()}")
        print(f"[INFO] Logged in — URL  : {page.url}")

        # ── 6. Dismiss popup with ESC ─────────────────────────────────────
        print("[INFO] Pressing ESC to dismiss any popup ...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(2_000)

        # ── 7. Click 'Me' in sidebar ──────────────────────────────────────
        print("[INFO] Looking for 'Me' in sidebar ...")
        me_selectors = [
            "text=Me",
            "[aria-label='Me']",
            "a:has-text('Me')",
            "li:has-text('Me') > a",
            "nav >> text=Me",
            "[title='Me']",
            "span:has-text('Me')",
        ]
        if not await safe_click(page, me_selectors, "'Me' sidebar"):
            links = await page.eval_on_selector_all(
                "a, button", "els => els.map(e => e.innerText.trim()).filter(Boolean)"
            )
            print("[DEBUG] Visible links/buttons:", links[:50])
            raise RuntimeError("'Me' sidebar item not found")

        await page.wait_for_load_state("networkidle", timeout=15_000)
        await page.wait_for_timeout(2_000)

        # ── 8. Click 'Time & Attendance' ──────────────────────────────────
        print("[INFO] Looking for 'Time & Attendance' ...")
        ta_selectors = [
            "text=Time & Attendance",
            "text=Time and Attendance",
            "a:has-text('Time & Attendance')",
            "a:has-text('Time and Attendance')",
            "a:has-text('Attendance')",
            "[title*='Time']",
            "span:has-text('Time & Attendance')",
        ]
        if not await safe_click(page, ta_selectors, "'Time & Attendance'"):
            links = await page.eval_on_selector_all(
                "a, button", "els => els.map(e => e.innerText.trim()).filter(Boolean)"
            )
            print("[DEBUG] Visible links/buttons:", links[:50])
            raise RuntimeError("'Time & Attendance' not found")

        await page.wait_for_load_state("networkidle", timeout=30_000)
        await page.wait_for_timeout(3_000)
        print(f"[INFO] T&A page title: {await page.title()}")

        # ── 9. Click 'Punch Out' (check iframes too) ──────────────────────
        print("[INFO] Looking for 'Punch Out' ...")
        punch_selectors = [
            "text=Punch Out",
            "button:has-text('Punch Out')",
            "input[value='Punch Out']",
            "a:has-text('Punch Out')",
            "[aria-label='Punch Out']",
            "[title='Punch Out']",
        ]

        punch_clicked = await safe_click(page, punch_selectors, "'Punch Out'")

        if not punch_clicked:
            print("[INFO] Not on main page, searching iframes ...")
            for frame in page.frames:
                result = await safe_click(frame, punch_selectors, "'Punch Out' (iframe)")
                if result:
                    punch_clicked = True
                    break

        if not punch_clicked:
            print("[DEBUG] Dumping all frames content ...")
            for i, frame in enumerate(page.frames):
                try:
                    btns = await frame.eval_on_selector_all(
                        "a, button, input[type=button], input[type=submit]",
                        "els => els.map(e => (e.innerText || e.value || '').trim()).filter(Boolean)"
                    )
                    print(f"[DEBUG] Frame {i}: {btns[:30]}")
                except Exception as e:
                    print(f"[DEBUG] Frame {i} error: {e}")
            raise RuntimeError("'Punch Out' button not found")

        await page.wait_for_timeout(3_000)
        print("[SUCCESS] Punch Out completed!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
