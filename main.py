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

        # ── 2. Fill User ID ───────────────────────────────────────────────
        print("[INFO] Filling User ID ...")
        user_selectors = [
            "#USER",
            "input[name='USER']",
            "input[id*='user' i]",
            "input[name*='user' i]",
            "input[placeholder*='user' i]",
            "input[type='text']",
        ]
        filled_user = False
        for sel in user_selectors:
            try:
                await page.wait_for_selector(sel, timeout=5_000)
                await page.fill(sel, USERNAME)
                filled_user = True
                print(f"[INFO] Filled User ID via: {sel}")
                break
            except Exception:
                pass
        if not filled_user:
            print("[ERROR] Could not find User ID field")
            print("[DEBUG] Page HTML snippet:")
            print(await page.content())
            raise RuntimeError("User ID field not found")

        # ── 3. Click Next / Continue (ADP shows user first, then password) ─
        next_selectors = [
            "input[type='submit']",
            "button[type='submit']",
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "#submit-button",
            "[data-testid='submit']",
        ]
        for sel in next_selectors:
            try:
                await page.click(sel, timeout=4_000)
                print(f"[INFO] Clicked Next via: {sel}")
                await page.wait_for_timeout(2_000)
                break
            except Exception:
                pass

        # ── 4. Fill Password ──────────────────────────────────────────────
        print("[INFO] Filling Password ...")
        pass_selectors = [
            "#PASSWORD",
            "input[name='PASSWORD']",
            "input[type='password']",
            "input[id*='pass' i]",
            "input[name*='pass' i]",
        ]
        filled_pass = False
        for sel in pass_selectors:
            try:
                await page.wait_for_selector(sel, timeout=5_000)
                await page.fill(sel, PASSWORD)
                filled_pass = True
                print(f"[INFO] Filled Password via: {sel}")
                break
            except Exception:
                pass
        if not filled_pass:
            print("[ERROR] Could not find Password field")
            raise RuntimeError("Password field not found")

        # ── 5. Submit login ───────────────────────────────────────────────
        print("[INFO] Submitting login form ...")
        submitted = False
        for sel in next_selectors:
            try:
                await page.click(sel, timeout=4_000)
                submitted = True
                print(f"[INFO] Submitted via: {sel}")
                break
            except Exception:
                pass
        if not submitted:
            await page.keyboard.press("Enter")
            print("[INFO] Submitted via Enter key")

        try:
            await page.wait_for_load_state("networkidle", timeout=30_000)
        except PlaywrightTimeout:
            print("[WARN] networkidle timeout after login - continuing")

        await page.wait_for_timeout(3_000)
        print(f"[INFO] Post-login title: {await page.title()}")
        print(f"[INFO] Post-login URL  : {page.url}")

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
        ]
        clicked_me = False
        for sel in me_selectors:
            try:
                await page.click(sel, timeout=5_000)
                clicked_me = True
                print(f"[INFO] Clicked 'Me' via: {sel}")
                break
            except Exception:
                pass
        if not clicked_me:
            print("[WARN] Could not find 'Me' - dumping visible links:")
            links = await page.eval_on_selector_all(
                "a, button", "els => els.map(e => e.innerText.trim()).filter(Boolean)"
            )
            print("[DEBUG] Links/buttons:", links[:40])
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
        ]
        clicked_ta = False
        for sel in ta_selectors:
            try:
                await page.click(sel, timeout=5_000)
                clicked_ta = True
                print(f"[INFO] Clicked 'Time & Attendance' via: {sel}")
                break
            except Exception:
                pass
        if not clicked_ta:
            print("[WARN] Could not find Time & Attendance - dumping links:")
            links = await page.eval_on_selector_all(
                "a, button", "els => els.map(e => e.innerText.trim()).filter(Boolean)"
            )
            print("[DEBUG] Links/buttons:", links[:40])
            raise RuntimeError("'Time & Attendance' not found")

        await page.wait_for_load_state("networkidle", timeout=30_000)
        await page.wait_for_timeout(3_000)
        print(f"[INFO] Time & Attendance page title: {await page.title()}")

        # ── 9. Handle frames — Punch Out may be inside an iframe ──────────
        punch_clicked = False

        async def try_punch_in_frame(frame):
            punch_selectors = [
                "text=Punch Out",
                "button:has-text('Punch Out')",
                "input[value='Punch Out']",
                "a:has-text('Punch Out')",
                "[aria-label='Punch Out']",
                "[title='Punch Out']",
            ]
            for sel in punch_selectors:
                try:
                    await frame.click(sel, timeout=4_000)
                    print(f"[INFO] Clicked 'Punch Out' in frame via: {sel}")
                    return True
                except Exception:
                    pass
            return False

        # Try main page first
        punch_clicked = await try_punch_in_frame(page)

        # Try all iframes if not found on main page
        if not punch_clicked:
            print("[INFO] Punch Out not on main page, checking iframes ...")
            for frame in page.frames:
                result = await try_punch_in_frame(frame)
                if result:
                    punch_clicked = True
                    break

        if not punch_clicked:
            print("[WARN] Could not find Punch Out - dumping all frame content:")
            for i, frame in enumerate(page.frames):
                try:
                    links = await frame.eval_on_selector_all(
                        "a, button, input[type=button], input[type=submit]",
                        "els => els.map(e => (e.innerText || e.value || '').trim()).filter(Boolean)"
                    )
                    print(f"[DEBUG] Frame {i} buttons/links:", links[:30])
                except Exception as e:
                    print(f"[DEBUG] Frame {i} error: {e}")
            raise RuntimeError("'Punch Out' button not found")

        await page.wait_for_timeout(3_000)
        print("[SUCCESS] Punch Out completed successfully!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
