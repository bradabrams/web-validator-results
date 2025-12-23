#!/usr/bin/env python3
"""
UX Mockup Generator - Creates mockups with suggested improvements
"""
import json
from playwright.sync_api import sync_playwright

CHROMIUM_PATH = '/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome'
LOCAL_PROXY = 'http://127.0.0.1:8888'
SCREENSHOT_DIR = '/tmp/validation/screenshots'

def create_mockups():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM_PATH,
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
            proxy={'server': LOCAL_PROXY}
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            ignore_https_errors=True,
        )
        page = context.new_page()

        # Mockup 1: Home Page - Add prominent CTA and improve hero section
        print("Creating Mockup 1: Home Page improvements...")
        page.goto('https://platform.claude.com/docs/en/home', wait_until='load', timeout=60000)
        page.wait_for_timeout(3000)

        # Apply UX improvements to home page
        page.evaluate('''() => {
            // 1. Make the main heading more impactful
            const h1 = document.querySelector('h1');
            if (h1) {
                h1.style.cssText = 'font-size: 3rem; font-weight: 700; margin-bottom: 24px; color: #1a1a1a;';
            }

            // 2. Add a prominent "Get Started" CTA button
            const searchBox = document.querySelector('input[placeholder*="Ask Claude"]');
            if (searchBox && searchBox.parentElement) {
                const ctaContainer = document.createElement('div');
                ctaContainer.style.cssText = 'display: flex; gap: 16px; justify-content: center; margin: 24px 0;';
                ctaContainer.innerHTML = `
                    <a href="/docs/en/get-started" style="
                        background: linear-gradient(135deg, #D97706 0%, #B45309 100%);
                        color: white;
                        padding: 14px 32px;
                        border-radius: 8px;
                        font-weight: 600;
                        font-size: 16px;
                        text-decoration: none;
                        box-shadow: 0 4px 14px rgba(217, 119, 6, 0.4);
                        transition: transform 0.2s;
                    ">🚀 Get Started Free</a>
                    <a href="/docs/en/api/overview" style="
                        background: transparent;
                        color: #1a1a1a;
                        padding: 14px 32px;
                        border-radius: 8px;
                        font-weight: 600;
                        font-size: 16px;
                        text-decoration: none;
                        border: 2px solid #e5e5e5;
                    ">View API Reference</a>
                `;
                searchBox.parentElement.parentElement.insertBefore(ctaContainer, searchBox.parentElement.nextSibling);
            }

            // 3. Add visual indicators to card sections
            const cards = document.querySelectorAll('[class*="card"], [class*="Card"]');
            cards.forEach((card, i) => {
                card.style.transition = 'transform 0.2s, box-shadow 0.2s';
                card.style.cursor = 'pointer';
            });

            // 4. Improve section headings
            const sectionHeadings = document.querySelectorAll('h2');
            sectionHeadings.forEach(h2 => {
                h2.style.cssText = 'font-size: 1.75rem; font-weight: 600; margin: 48px 0 24px 0; color: #1a1a1a; border-bottom: 2px solid #f5f5f5; padding-bottom: 12px;';
            });
        }''')

        page.screenshot(path=f'{SCREENSHOT_DIR}/mockup_home.png', full_page=True)
        print("  Saved: mockup_home.png")

        # Mockup 2: Get Started Page - Improve code block visibility and steps
        print("Creating Mockup 2: Get Started page improvements...")
        page.goto('https://platform.claude.com/docs/en/get-started', wait_until='load', timeout=60000)
        page.wait_for_timeout(3000)

        page.evaluate('''() => {
            // 1. Add step numbers with better visibility
            const steps = document.querySelectorAll('h3, h4');
            let stepNum = 0;
            steps.forEach(step => {
                if (step.textContent.includes('Set your') || step.textContent.includes('Make your') || step.textContent.includes('Prerequisites')) {
                    stepNum++;
                }
            });

            // 2. Enhance code blocks
            const codeBlocks = document.querySelectorAll('pre');
            codeBlocks.forEach(block => {
                block.style.cssText = `
                    background: #1e1e1e;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 20px 0;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    overflow-x: auto;
                    position: relative;
                `;
                // Add copy button indicator
                const copyHint = document.createElement('div');
                copyHint.style.cssText = 'position: absolute; top: 10px; right: 10px; background: #3b3b3b; color: #888; padding: 4px 12px; border-radius: 4px; font-size: 12px;';
                copyHint.textContent = '📋 Click to copy';
                block.style.position = 'relative';
                block.appendChild(copyHint);
            });

            // 3. Add progress indicator
            const mainContent = document.querySelector('main') || document.querySelector('article');
            if (mainContent) {
                const progressBar = document.createElement('div');
                progressBar.style.cssText = `
                    position: fixed;
                    top: 60px;
                    left: 0;
                    width: 30%;
                    height: 4px;
                    background: linear-gradient(90deg, #D97706, #B45309);
                    z-index: 1000;
                    border-radius: 0 2px 2px 0;
                `;
                document.body.appendChild(progressBar);
            }

            // 4. Highlight the Prerequisites section
            const prereqHeading = Array.from(document.querySelectorAll('h2, h3')).find(h => h.textContent.includes('Prerequisites'));
            if (prereqHeading) {
                const prereqSection = prereqHeading.nextElementSibling;
                if (prereqSection) {
                    prereqSection.style.cssText = `
                        background: #FEF3C7;
                        border-left: 4px solid #D97706;
                        padding: 16px 20px;
                        border-radius: 0 8px 8px 0;
                        margin: 16px 0;
                    `;
                }
            }

            // 5. Add estimated time
            const h1 = document.querySelector('h1');
            if (h1) {
                const timeEstimate = document.createElement('div');
                timeEstimate.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; background: #f0fdf4; color: #166534; padding: 6px 12px; border-radius: 20px; font-size: 14px; margin-left: 12px;';
                timeEstimate.innerHTML = '⏱️ ~5 min read';
                h1.appendChild(timeEstimate);
            }
        }''')

        page.screenshot(path=f'{SCREENSHOT_DIR}/mockup_getstarted.png', full_page=True)
        print("  Saved: mockup_getstarted.png")

        # Mockup 3: Prompt Library - Add filtering and better card hover states
        print("Creating Mockup 3: Prompt Library improvements...")
        page.goto('https://platform.claude.com/docs/en/resources/prompt-library/library', wait_until='load', timeout=60000)
        page.wait_for_timeout(3000)

        page.evaluate('''() => {
            // 1. Add category filter pills
            const header = document.querySelector('h1');
            if (header) {
                const filterContainer = document.createElement('div');
                filterContainer.style.cssText = 'display: flex; gap: 10px; flex-wrap: wrap; margin: 20px 0 30px 0;';
                const categories = ['All', 'Writing', 'Coding', 'Analysis', 'Business', 'Creative', 'Education'];
                categories.forEach((cat, i) => {
                    const pill = document.createElement('button');
                    pill.textContent = cat;
                    pill.style.cssText = `
                        padding: 8px 20px;
                        border-radius: 20px;
                        border: none;
                        cursor: pointer;
                        font-size: 14px;
                        font-weight: 500;
                        transition: all 0.2s;
                        ${i === 0 ? 'background: #D97706; color: white;' : 'background: #f5f5f5; color: #666;'}
                    `;
                    filterContainer.appendChild(pill);
                });
                header.parentElement.insertBefore(filterContainer, header.nextSibling.nextSibling);
            }

            // 2. Improve card hover states
            const cards = document.querySelectorAll('a[href*="prompt-library"]');
            cards.forEach(card => {
                if (card.closest('nav')) return; // Skip nav links
                card.style.cssText = `
                    display: block;
                    padding: 20px;
                    border-radius: 12px;
                    background: white;
                    border: 1px solid #e5e5e5;
                    transition: all 0.2s ease;
                    text-decoration: none;
                `;
                card.onmouseover = () => {
                    card.style.transform = 'translateY(-4px)';
                    card.style.boxShadow = '0 12px 24px rgba(0,0,0,0.1)';
                    card.style.borderColor = '#D97706';
                };
                card.onmouseout = () => {
                    card.style.transform = 'translateY(0)';
                    card.style.boxShadow = 'none';
                    card.style.borderColor = '#e5e5e5';
                };
            });

            // 3. Add "Popular" badge to some prompts
            const allCards = document.querySelectorAll('[class*="grid"] > div, [class*="Grid"] > div');
            if (allCards.length > 3) {
                [0, 2, 5].forEach(idx => {
                    if (allCards[idx]) {
                        const badge = document.createElement('span');
                        badge.textContent = '🔥 Popular';
                        badge.style.cssText = 'position: absolute; top: 10px; right: 10px; background: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;';
                        allCards[idx].style.position = 'relative';
                        allCards[idx].appendChild(badge);
                    }
                });
            }

            // 4. Improve search box
            const searchInput = document.querySelector('input[type="search"], input[placeholder*="Search"]');
            if (searchInput) {
                searchInput.style.cssText = `
                    width: 100%;
                    padding: 14px 20px 14px 48px;
                    border: 2px solid #e5e5e5;
                    border-radius: 12px;
                    font-size: 16px;
                    transition: border-color 0.2s;
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%23999' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath d='m21 21-4.35-4.35'/%3E%3C/svg%3E");
                    background-repeat: no-repeat;
                    background-position: 16px center;
                `;
            }

            // 5. Add result count
            const mainHeading = document.querySelector('h1');
            if (mainHeading) {
                const countBadge = document.createElement('span');
                countBadge.textContent = '60+ prompts';
                countBadge.style.cssText = 'font-size: 16px; font-weight: 400; color: #666; margin-left: 16px;';
                mainHeading.appendChild(countBadge);
            }
        }''')

        page.screenshot(path=f'{SCREENSHOT_DIR}/mockup_promptlibrary.png', full_page=True)
        print("  Saved: mockup_promptlibrary.png")

        browser.close()
        print("\nAll mockups created successfully!")

if __name__ == '__main__':
    create_mockups()
