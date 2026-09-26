#!/usr/bin/env python3
"""Boot the app and capture the main screens with Playwright + the local
Chrome (no browser download): empty estimator, core inputs with live
readiness, filled inputs, results, Models page, Data page.

    .venv/bin/python scripts/screenshot.py [--out screenshots] [--port 8799]

Needs `pip install playwright` (in requirements-dev.txt) and Google Chrome.
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wait_healthy(port, timeout=30):
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def capture(port, out):
    from playwright.sync_api import sync_playwright

    url = f"http://localhost:{port}"

    def sb(page, label):
        return page.locator('div[data-testid="stSelectbox"]', has_text=label).first.locator("input")

    def ni(page, label):
        return page.locator('div[data-testid="stNumberInput"]', has_text=label).first.locator("input")

    def pick(page, label, text):
        sb(page, label).click()
        time.sleep(0.3)
        page.keyboard.type(text)
        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(1.0)

    def shot(page, name):
        # Streamlit scrolls inside its own container; reset every scrollable so
        # full_page starts at the top.
        page.evaluate("for (const el of document.querySelectorAll('*')) { if (el.scrollHeight > el.clientHeight) el.scrollTop = 0 }")
        time.sleep(0.3)
        page.screenshot(path=os.path.join(out, name), full_page=True)
        print("  saved", name)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light").new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("text=Model readiness")
        time.sleep(1.5)
        shot(page, "01_empty.png")
        pick(page, "Archetype", "Petrochemical")
        pick(page, "Location", "US Gulf Coast")
        page.wait_for_selector("text=Ready", timeout=15000)
        shot(page, "02_core.png")
        pick(page, "Facility type", "polypropylene")
        c = ni(page, "Primary capacity")
        c.click()
        c.fill("450")
        c.press("Tab")
        time.sleep(1.0)
        pick(page, "Unit", "KTA")
        pick(page, "Equipment type", "pump")
        n = ni(page, "Count")
        n.click()
        n.fill("8")
        n.press("Tab")
        time.sleep(0.5)
        page.get_by_role("button", name="Add").first.click()
        time.sleep(1.0)
        shot(page, "03_filled.png")
        page.get_by_role("button", name="Run screening estimate").click()
        page.wait_for_selector("text=Best estimate", timeout=30000)
        time.sleep(3)
        shot(page, "04_results.png")
        page.locator('div[data-testid="stMetric"]').first.locator("xpath=../..").screenshot(
            path=os.path.join(out, "04b_kpis.png"))
        print("  saved 04b_kpis.png")
        page.get_by_role("link", name="Models").first.click()
        page.wait_for_selector("text=Model specs", timeout=30000)
        time.sleep(2)
        shot(page, "05_models.png")
        page.get_by_role("link", name="Data").first.click()
        page.wait_for_selector("text=Loaded tables", timeout=30000)
        time.sleep(2)
        shot(page, "06_data.png")
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "screenshots"))
    ap.add_argument("--port", type=int, default=8799)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    streamlit = os.path.join(ROOT, ".venv", "bin", "streamlit")
    proc = subprocess.Popen([streamlit, "run", os.path.join(ROOT, "app.py"), "--server.headless", "true",
                             "--server.port", str(args.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_healthy(args.port):
            print("app did not become healthy", file=sys.stderr)
            sys.exit(1)
        capture(args.port, args.out)
        print(f"done: {args.out}")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
