#!/usr/bin/env python3
"""
browser_tool.py - Headless Browser Tool for Agent API

This module provides a simple browser automation tool that can be uploaded
to the Agent API sandbox as a resource. It uses Playwright in headless mode
to provide screenshot, click, type, and scroll functionality.

Usage in Agent API sandbox:
    1. Install: pip install playwright && playwright install chromium
    2. Import and use:

    from browser_tool import BrowserTool

    browser = BrowserTool()
    browser.goto("https://example.com")
    browser.screenshot("/tmp/page.png")
    browser.click(500, 300)
    browser.type_text("Hello world")
    browser.scroll("down", 3)
    browser.close()
"""

import base64
import json
import time
from pathlib import Path
from typing import Optional, Literal, Tuple
from dataclasses import dataclass


@dataclass
class BrowserResult:
    """Result from a browser action."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    screenshot_base64: Optional[str] = None

    def to_dict(self):
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "screenshot_path": self.screenshot_path,
        }


class BrowserTool:
    """
    A headless browser tool that provides computer-use-like functionality.
    Works in environments without X11 by using Playwright's headless mode.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 800,
        headless: bool = True,
        slow_mo: int = 0,
        use_local_proxy: bool = True,
        local_proxy_port: int = 8888,
    ):
        """
        Initialize the browser tool.

        Args:
            width: Browser viewport width in pixels
            height: Browser viewport height in pixels
            headless: Run browser in headless mode (required for sandbox)
            slow_mo: Slow down operations by this many milliseconds
            use_local_proxy: Use local proxy for JWT auth (required in sandbox)
            local_proxy_port: Port for the local proxy (default 8888)
        """
        self.width = width
        self.height = height
        self.headless = headless
        self.slow_mo = slow_mo
        self.use_local_proxy = use_local_proxy
        self.local_proxy_port = local_proxy_port
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._screenshot_dir = Path("/tmp/browser_screenshots")
        self._screenshot_count = 0
        self._console_errors = []
        self._failed_requests = []

    def _ensure_browser(self):
        """Ensure browser is initialized."""
        if self._page is not None:
            return

        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()

        # Build launch args
        launch_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
        ]

        # Use local proxy if enabled (for JWT auth in sandbox)
        proxy_settings = None
        if self.use_local_proxy:
            proxy_settings = {
                'server': f'http://127.0.0.1:{self.local_proxy_port}'
            }

        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
            proxy=proxy_settings,
        )
        self._context = self._browser.new_context(
            viewport={'width': self.width, 'height': self.height},
            ignore_https_errors=True,
        )
        self._page = self._context.new_page()

        # Track console errors
        self._page.on('console', lambda msg:
            self._console_errors.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            }) if msg.type == 'error' else None
        )

        # Track failed requests
        self._page.on('requestfailed', lambda req:
            self._failed_requests.append({
                'url': req.url,
                'failure': req.failure
            })
        )

        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

    def goto(self, url: str, wait_until: str = 'networkidle', timeout: int = 30000) -> BrowserResult:
        """
        Navigate to a URL.

        Args:
            url: The URL to navigate to
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
            timeout: Timeout in milliseconds

        Returns:
            BrowserResult with navigation outcome
        """
        self._ensure_browser()
        try:
            response = self._page.goto(url, wait_until=wait_until, timeout=timeout)
            status = response.status if response else 0
            final_url = self._page.url
            return BrowserResult(
                success=True,
                output=f"Navigated to {final_url} (status: {status})"
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = True,
        return_base64: bool = False
    ) -> BrowserResult:
        """
        Take a screenshot of the current page.

        Args:
            path: File path to save screenshot (auto-generated if None)
            full_page: Capture the full scrollable page
            return_base64: Include base64-encoded image in result

        Returns:
            BrowserResult with screenshot path
        """
        self._ensure_browser()
        try:
            if path is None:
                self._screenshot_count += 1
                path = str(self._screenshot_dir / f"screenshot_{self._screenshot_count:03d}.png")

            self._page.screenshot(path=path, full_page=full_page)

            result = BrowserResult(
                success=True,
                output=f"Screenshot saved to {path}",
                screenshot_path=path
            )

            if return_base64:
                with open(path, 'rb') as f:
                    result.screenshot_base64 = base64.b64encode(f.read()).decode()

            return result
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def click(
        self,
        x: int,
        y: int,
        button: Literal['left', 'right', 'middle'] = 'left',
        click_count: int = 1,
        delay: int = 0
    ) -> BrowserResult:
        """
        Click at the specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ('left', 'right', 'middle')
            click_count: Number of clicks (1=single, 2=double, 3=triple)
            delay: Delay between mousedown and mouseup in milliseconds

        Returns:
            BrowserResult with click outcome
        """
        self._ensure_browser()
        try:
            self._page.mouse.click(x, y, button=button, click_count=click_count, delay=delay)
            return BrowserResult(
                success=True,
                output=f"Clicked at ({x}, {y}) with {button} button"
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def type_text(self, text: str, delay: int = 50) -> BrowserResult:
        """
        Type text using the keyboard.

        Args:
            text: Text to type
            delay: Delay between key presses in milliseconds

        Returns:
            BrowserResult with typing outcome
        """
        self._ensure_browser()
        try:
            self._page.keyboard.type(text, delay=delay)
            return BrowserResult(
                success=True,
                output=f"Typed {len(text)} characters"
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def press_key(self, key: str) -> BrowserResult:
        """
        Press a key or key combination.

        Args:
            key: Key to press (e.g., 'Enter', 'Tab', 'Control+a', 'Meta+c')

        Returns:
            BrowserResult with key press outcome
        """
        self._ensure_browser()
        try:
            self._page.keyboard.press(key)
            return BrowserResult(
                success=True,
                output=f"Pressed key: {key}"
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def scroll(
        self,
        direction: Literal['up', 'down', 'left', 'right'] = 'down',
        amount: int = 3,
        x: Optional[int] = None,
        y: Optional[int] = None
    ) -> BrowserResult:
        """
        Scroll the page.

        Args:
            direction: Scroll direction
            amount: Number of scroll units (each unit ~100px)
            x: X coordinate to scroll at (center if None)
            y: Y coordinate to scroll at (center if None)

        Returns:
            BrowserResult with scroll outcome
        """
        self._ensure_browser()
        try:
            if x is None:
                x = self.width // 2
            if y is None:
                y = self.height // 2

            delta_x = 0
            delta_y = 0
            pixels = amount * 100

            if direction == 'up':
                delta_y = -pixels
            elif direction == 'down':
                delta_y = pixels
            elif direction == 'left':
                delta_x = -pixels
            elif direction == 'right':
                delta_x = pixels

            self._page.mouse.wheel(delta_x, delta_y)
            time.sleep(0.3)  # Let scroll settle

            return BrowserResult(
                success=True,
                output=f"Scrolled {direction} by {amount} units"
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def mouse_move(self, x: int, y: int) -> BrowserResult:
        """
        Move the mouse to specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            BrowserResult with mouse move outcome
        """
        self._ensure_browser()
        try:
            self._page.mouse.move(x, y)
            return BrowserResult(
                success=True,
                output=f"Moved mouse to ({x}, {y})"
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def wait(self, milliseconds: int = 1000) -> BrowserResult:
        """
        Wait for specified time.

        Args:
            milliseconds: Time to wait in milliseconds

        Returns:
            BrowserResult indicating wait completed
        """
        try:
            time.sleep(milliseconds / 1000)
            return BrowserResult(
                success=True,
                output=f"Waited {milliseconds}ms"
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    def get_url(self) -> str:
        """Get the current page URL."""
        self._ensure_browser()
        return self._page.url

    def get_title(self) -> str:
        """Get the current page title."""
        self._ensure_browser()
        return self._page.title()

    def get_links(self, same_domain: bool = True) -> list[str]:
        """
        Get all links on the current page.

        Args:
            same_domain: Only return links on the same domain

        Returns:
            List of URLs
        """
        self._ensure_browser()
        from urllib.parse import urlparse

        links = self._page.eval_on_selector_all(
            'a[href]',
            'elements => elements.map(e => e.href)'
        )

        if same_domain:
            current_domain = urlparse(self._page.url).netloc
            links = [
                link for link in links
                if urlparse(link).netloc == current_domain
            ]

        return list(set(links))  # Remove duplicates

    def get_console_errors(self) -> list[dict]:
        """Get all console errors captured during this session."""
        return self._console_errors.copy()

    def get_failed_requests(self) -> list[dict]:
        """Get all failed network requests during this session."""
        return self._failed_requests.copy()

    def close(self):
        """Close the browser and clean up resources."""
        if self._page:
            self._page.close()
            self._page = None
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None


def validate_website(url: str, max_pages: int = 10, screenshot_dir: str = "/tmp/validation/screenshots"):
    """
    Validate a website by visiting pages and taking screenshots.

    Args:
        url: Starting URL
        max_pages: Maximum pages to visit
        screenshot_dir: Directory to save screenshots

    Returns:
        Dictionary with validation results
    """
    from urllib.parse import urlparse

    browser = BrowserTool()
    results = {
        "site": url,
        "pages": [],
        "issues": [],
        "console_errors": [],
        "failed_requests": []
    }

    Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

    visited = set()
    to_visit = [url]
    page_num = 0

    try:
        while to_visit and page_num < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue

            visited.add(current_url)
            page_num += 1

            print(f"[{page_num}/{max_pages}] Visiting: {current_url}")

            # Navigate
            nav_result = browser.goto(current_url)

            if not nav_result.success:
                results["issues"].append({
                    "url": current_url,
                    "type": "navigation_error",
                    "severity": "high",
                    "description": nav_result.error
                })
                continue

            final_url = browser.get_url()
            title = browser.get_title()

            # Take screenshot
            screenshot_path = f"{screenshot_dir}/page_{page_num:03d}.png"
            screenshot_result = browser.screenshot(screenshot_path)

            # Record page info
            page_info = {
                "url": final_url,
                "title": title,
                "status": "ok",
                "screenshot": screenshot_path if screenshot_result.success else None,
            }
            results["pages"].append(page_info)

            # Get links for crawling
            if page_num == 1:
                # Update domain based on final URL (handle redirects)
                final_domain = urlparse(final_url).netloc
                results["final_domain"] = final_domain

            links = browser.get_links(same_domain=True)
            for link in links:
                if link not in visited and link not in to_visit:
                    to_visit.append(link)

    except Exception as e:
        results["issues"].append({
            "url": current_url if 'current_url' in dir() else url,
            "type": "error",
            "severity": "high",
            "description": str(e)
        })
    finally:
        results["console_errors"] = browser.get_console_errors()
        results["failed_requests"] = browser.get_failed_requests()
        browser.close()

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python browser_tool.py <url> [max_pages]")
        sys.exit(1)

    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"Validating {url} (max {max_pages} pages)...")
    results = validate_website(url, max_pages)

    print(f"\n=== Results ===")
    print(f"Pages visited: {len(results['pages'])}")
    print(f"Issues found: {len(results['issues'])}")
    print(f"Console errors: {len(results['console_errors'])}")
    print(f"Failed requests: {len(results['failed_requests'])}")

    # Save results
    with open("/tmp/validation/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to /tmp/validation/results.json")
