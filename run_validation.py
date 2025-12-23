#!/usr/bin/env python3
"""
Website Validation Script using Playwright with existing Chromium
"""
import json
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

CHROMIUM_PATH = '/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome'
LOCAL_PROXY = 'http://127.0.0.1:8888'
TARGET_URL = 'https://docs.anthropic.com'
MAX_PAGES = 500
SCREENSHOT_DIR = '/tmp/validation/screenshots'

print("=" * 60)
print(f"Website Validation: {TARGET_URL}")
print("=" * 60)

results = {
    "site": TARGET_URL,
    "final_domain": None,
    "pages": [],
    "issues": [],
    "console_errors": [],
    "failed_requests": []
}

visited = set()
to_visit = [TARGET_URL]
page_num = 0

console_errors = []
failed_requests = []

with sync_playwright() as p:
    print("Launching browser...")
    browser = p.chromium.launch(
        executable_path=CHROMIUM_PATH,
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
        ],
        proxy={'server': LOCAL_PROXY}
    )

    context = browser.new_context(
        viewport={'width': 1280, 'height': 800},
        ignore_https_errors=True,
    )

    page = context.new_page()

    # Track console errors
    def on_console(msg):
        if msg.type == 'error':
            console_errors.append({
                'type': msg.type,
                'text': msg.text,
            })
    page.on('console', on_console)

    # Track failed requests
    def on_request_failed(req):
        # Ignore ERR_ABORTED as these are usually intentional navigation cancellations
        if 'ERR_ABORTED' not in str(req.failure):
            failed_requests.append({
                'url': req.url,
                'failure': str(req.failure)
            })
    page.on('requestfailed', on_request_failed)

    print("Browser launched successfully!")

    while to_visit and page_num < MAX_PAGES:
        url = to_visit.pop(0)

        # Normalize URL - remove fragments
        if '#' in url:
            url = url.split('#')[0]

        if url in visited or not url:
            continue

        visited.add(url)
        page_num += 1

        print(f"\n[{page_num}/{MAX_PAGES}] Visiting: {url}")

        try:
            # Use 'load' instead of 'networkidle' for faster page loads
            response = page.goto(url, wait_until='load', timeout=60000)

            # Wait a bit more for dynamic content
            page.wait_for_timeout(2000)

            status = response.status if response else 0

            final_url = page.url
            title = page.title()

            # On first page, capture the final domain (in case of redirects)
            if page_num == 1:
                final_domain = urlparse(final_url).netloc
                results["final_domain"] = final_domain
                print(f"  Final domain after redirect: {final_domain}")

            # Take screenshot
            screenshot_name = f'page_{page_num:03d}.png'
            screenshot_path = f'{SCREENSHOT_DIR}/{screenshot_name}'
            page.screenshot(path=screenshot_path, full_page=True)

            print(f"  Status: {status} | Title: {title[:50]}...")
            print(f"  Screenshot: {screenshot_name}")

            if status >= 400:
                results["issues"].append({
                    "url": final_url,
                    "type": f"http_{status}",
                    "severity": "high" if status >= 500 else "medium",
                    "description": f"HTTP {status} error"
                })

            results["pages"].append({
                "url": final_url,
                "title": title,
                "status": status,
                "screenshot": screenshot_name
            })

            # Get links for crawling - filter to same domain
            links = page.eval_on_selector_all('a[href]', 'elements => elements.map(e => e.href)')
            new_links = 0
            for link in links:
                # Skip anchors and non-http links
                if '#' in link:
                    link = link.split('#')[0]
                if not link or not link.startswith('http'):
                    continue
                # Check if same domain
                link_domain = urlparse(link).netloc
                if results["final_domain"] and link_domain == results["final_domain"]:
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)
                        new_links += 1

            print(f"  Found {len(links)} links, {new_links} new to visit, {len(to_visit)} in queue")

        except Exception as e:
            error_str = str(e)
            print(f"  ERROR: {error_str[:100]}...")
            results["issues"].append({
                "url": url,
                "type": "navigation_error",
                "severity": "high",
                "description": error_str[:500]
            })

        # Small delay to be nice to the server
        time.sleep(0.3)

    browser.close()

results["console_errors"] = console_errors
results["failed_requests"] = failed_requests

# Save results
with open('/tmp/validation/issues.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 60)
print("VALIDATION COMPLETE")
print("=" * 60)
print(f"Pages visited: {len(results['pages'])}")
print(f"Navigation issues: {len([i for i in results['issues'] if i['type'] == 'navigation_error'])}")
print(f"HTTP errors: {len([i for i in results['issues'] if i['type'].startswith('http_')])}")
print(f"Console errors: {len(results['console_errors'])}")
print(f"Failed requests: {len(results['failed_requests'])}")
print(f"\nResults saved to /tmp/validation/issues.json")
print(f"Screenshots saved to {SCREENSHOT_DIR}/")
