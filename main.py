import os
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

LOGIN_URL  = os.environ.get("LOGIN_URL",  "")
USERNAME   = os.environ.get("USERNAME",   "")
PASSWORD   = os.environ.get("PASSWORD",   "")

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page    = await context.new_page()

        # 1. Navigate to login page
        print(f"[INFO] Opening login page: {LOGIN_URL}")
        await page.goto(LOGIN_URL, wait_until="networkidle")

        # 2. Fill credentials and login
        print("[INFO] Filling credentials ...")
        await page.fill("input[type='text'], input[name*='user'], input[id*='user']", USERNAME)
        await page.fill("input[type='password']", PASSWORD)
        await page.press("input[type='password']", "Enter")
        print("[INFO] Submitted login form")

        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except PlaywrightTimeout:
            print("[WARN] Timeout after login - continuing")

        # 3. Dismiss popup with ESC if any
        print("[INFO] Pressing ESC to dismiss popup if any ...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1500)

        # 4. Click Me in sidebar
        print("[INFO] Clicking Me in sidebar ...")
        me_selectors = [
            "text=Me",
            "[aria-label='Me']",
            "nav a:has-text('Me')",
            "aside a:has-text('Me')",
            "li:has-text('Me') > a",
        ]
        clicked_me = False
        for sel in me_selectors:
            try:
                await page.click(sel, timeout=5000)
                clicked_me = True
                print(f"[INFO] Clicked Me via: {sel}")
                break
            except Exception:
                pass
        if not clicked_me:
            body = await page.inner_text("body")
            print("[DEBUG] Page body:", body[:500])
            raise RuntimeError("Me sidebar item not found")

        await page.wait_for_load_state("networkidle", timeout=15000)

        # 5. Click Time and Attendance
        print("[INFO] Clicking Time and Attendance ...")
        ta_selectors = [
            "text=Time & Attendance",
            "text=Time and Attendance",
            "a:has-text('Time')",
        ]
        clicked_ta = False
        for sel in ta_selectors:
            try:
                await page.click(sel, timeout=5000)
                clicked_ta = True
                print(f"[INFO] Clicked Time and Attendance via: {sel}")
                break
            except Exception:
                pass
        if not clicked_ta:
            raise RuntimeError("Time and Attendance item not found")

        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        # 6. Click Punch Out
        print("[INFO] Clicking Punch Out ...")
        punch_selectors = [
            "text=Punch Out",
            "button:has-text('Punch Out')",
            "input[value='Punch Out']",
            "[aria-label='Punch Out']",
        ]
        clicked_punch = False
        for sel in punch_selectors:
            try:
                await page.click(sel, timeout=5000)
                clicked_punch = True
                print(f"[INFO] Clicked Punch Out via: {sel}")
                break
            except Exception:
                pass
        if not clicked_punch:
            raise RuntimeError("Punch Out button not found")

        await page.wait_for_timeout(2000)
        print("[SUCCESS] Punch Out done!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
