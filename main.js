const { chromium } = require('playwright');

const LOGIN_URL = process.env.LOGIN_URL ||
  'https://online.apac.adp.com/signin/v1/?APPID=ADPVISTA-IN' +
  '&productId=ff803a24-0ee0-47fc-e053-f282530bfabe' +
  '&returnURL=https://www.vista.adp.com/in/' +
  '&callingAppId=ADPVISTA' +
  '&TARGET=-SM-https://www.vista.adp.com/in/';

const PUNCH_URL  = 'https://cleartelligence.securtime.adp.com/welcome';
const USERNAME   = process.env.USERNAME || '';
const PASSWORD   = process.env.PASSWORD || '';

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
      'AppleWebKit/537.36 (KHTML, like Gecko) ' +
      'Chrome/124.0.0.0 Safari/537.36'
  });

  // ── STEP 1: Open VISTA login ────────────────────────────────────────
  console.log('='.repeat(60));
  console.log('[STEP 1] Opening VISTA login page ...');
  const loginPage = await context.newPage();
  await loginPage.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await loginPage.waitForTimeout(3000);
  console.log('  Title :', await loginPage.title());

  // ── STEP 2: Fill username ───────────────────────────────────────────
  console.log('[STEP 2] Filling username ...');
  const userSelectors = [
    '#USER',
    "input[name='USER']",
    "input[autocomplete='username']",
    "input[type='text']"
  ];
  let filledUser = false;
  for (const sel of userSelectors) {
    try {
      await loginPage.waitForSelector(sel, { timeout: 3000, state: 'visible' });
      await loginPage.fill(sel, USERNAME);
      console.log('  OK: username filled via', sel);
      filledUser = true;
      break;
    } catch (_) {}
  }
  if (!filledUser) throw new Error('FAILED at STEP 2: Username field not found');

  // ── STEP 3: Submit username ─────────────────────────────────────────
  console.log('[STEP 3] Submitting username ...');
  const submitSelectors = [
    "input[type='submit']",
    "button[type='submit']",
    "button:has-text('Next')",
    "button:has-text('Sign In')",
    "input[value='Next']",
    "input[value='Submit']"
  ];
  let submitted = false;
  for (const sel of submitSelectors) {
    try {
      await loginPage.click(sel, { timeout: 3000 });
      console.log('  OK: clicked submit via', sel);
      submitted = true;
      break;
    } catch (_) {}
  }
  if (!submitted) {
    await loginPage.keyboard.press('Enter');
    console.log('  Fallback: Enter key');
  }
  await loginPage.waitForTimeout(4000);

  // ── STEP 4: Fill password ───────────────────────────────────────────
  console.log('[STEP 4] Filling password ...');
  const passSelectors = [
    '#PASSWORD',
    "input[name='PASSWORD']",
    "input[type='password']",
    "input[autocomplete='current-password']"
  ];
  let filledPass = false;
  for (const sel of passSelectors) {
    try {
      await loginPage.waitForSelector(sel, { timeout: 4000, state: 'visible' });
      await loginPage.fill(sel, PASSWORD);
      console.log('  OK: password filled via', sel);
      filledPass = true;
      break;
    } catch (_) {}
  }
  if (!filledPass) throw new Error('FAILED at STEP 4: Password field not found');

  // ── STEP 5: Submit login ────────────────────────────────────────────
  console.log('[STEP 5] Submitting login ...');
  submitted = false;
  for (const sel of submitSelectors) {
    try {
      await loginPage.click(sel, { timeout: 3000 });
      console.log('  OK: login submitted via', sel);
      submitted = true;
      break;
    } catch (_) {}
  }
  if (!submitted) {
    await loginPage.keyboard.press('Enter');
    console.log('  Fallback: Enter key');
  }

  try {
    await loginPage.waitForLoadState('networkidle', { timeout: 30000 });
  } catch (_) {
    console.log('  WARN: networkidle timeout - continuing');
  }
  await loginPage.waitForTimeout(3000);
  console.log('  Title after login:', await loginPage.title());
  console.log('  URL   after login:', loginPage.url());

  // ── STEP 6: Open Punch Out URL in a new tab ─────────────────────────
  console.log('[STEP 6] Opening Punch Out page in new tab:', PUNCH_URL);
  const punchPage = await context.newPage();
  await punchPage.goto(PUNCH_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await punchPage.waitForTimeout(4000);
  console.log('  Title :', await punchPage.title());
  console.log('  URL   :', punchPage.url());

  // ── STEP 7: Click Punch Out ─────────────────────────────────────────
  console.log('[STEP 7] Looking for Punch Out button ...');
  const punchSelectors = [
    'text=Punch Out',
    "button:has-text('Punch Out')",
    "input[value='Punch Out']",
    "a:has-text('Punch Out')",
    "[aria-label='Punch Out']",
    "[title='Punch Out']",
    "text=punch out",
    "button:has-text('punch out')"
  ];

  // Also search inside iframes
  const tryClickPunch = async (frame, label) => {
    for (const sel of punchSelectors) {
      try {
        await frame.click(sel, { timeout: 4000 });
        console.log(`  OK: Punch Out clicked in ${label} via ${sel}`);
        return true;
      } catch (_) {}
    }
    return false;
  };

  let punchDone = await tryClickPunch(punchPage, 'main page');

  if (!punchDone) {
    console.log('  Not on main page - checking iframes ...');
    for (const frame of punchPage.frames()) {
      if (frame === punchPage.mainFrame()) continue;
      console.log('  Checking frame:', frame.url().substring(0, 80));
      punchDone = await tryClickPunch(frame, `frame:${frame.url().substring(0, 60)}`);
      if (punchDone) break;
    }
  }

  if (!punchDone) {
    // Dump all clickable elements for debugging
    console.log('[DEBUG] Dumping all frames on punch page:');
    for (const frame of punchPage.frames()) {
      try {
        const items = await frame.$$eval(
          'a, button, input[type=button], input[type=submit], [role=button]',
          els => els.map(e => (e.innerText || e.value || e.getAttribute('aria-label') || '').trim()).filter(Boolean)
        );
        if (items.length) console.log(`  Frame ${frame.url().substring(0,80)}: ${JSON.stringify(items.slice(0,30))}`);
      } catch (_) {}
    }
    throw new Error('FAILED at STEP 7: Punch Out button not found');
  }

  await punchPage.waitForTimeout(3000);
  console.log('='.repeat(60));
  console.log('[SUCCESS] Punch Out completed!');
  console.log('='.repeat(60));
  await browser.close();
})();
