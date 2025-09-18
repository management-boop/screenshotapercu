# Install dependencies
!pip install gradio selenium pandas requests
!apt-get update
!apt-get install -y chromium-chromedriver

import io
import base64
from typing import List
import gradio as gr
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import os

# -------- Utilities --------
def capture_screenshot(url: str, timeout=30) -> str:
    """Capture a screenshot of the webpage, handling pop-ups, and return as a base64-encoded data URI."""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        
        driver.set_window_size(1280, 720)  # Set window size for consistent thumbnails
        driver.get(url)
        
        # Wait for page to load and pop-ups to appear
        time.sleep(10)  # Increased initial wait for slow-loading pages
        
        # Handle age verification or cookie consent pop-ups
        try:
            # Switch to iframe if pop-up is in one
            driver.switch_to.default_content()
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                driver.switch_to.frame(iframe)
                try:
                    WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]"))
                    ).click()
                    print(f"Clicked 'continue' in iframe for {url}")
                    break
                except:
                    driver.switch_to.default_content()
            else:
                # Try main content
                element = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'proceed') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'i am 19') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]"))
                )
                ActionChains(driver).move_to_element(element).click(element).perform()
                print(f"Clicked pop-up button for {url}")
        except Exception as e:
            print(f"No clickable pop-up button found for {url}: {str(e)}")
            # Scroll and retry
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            try:
                element = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]")
                ActionChains(driver).move_to_element(element).click(element).perform()
                print(f"Clicked 'continue' after scroll for {url}")
            except Exception as e:
                print(f"Retry failed: {str(e)}")

        # Additional wait after interaction
        time.sleep(3)
        
        # Capture screenshot
        screenshot = driver.get_screenshot_as_png()
        driver.quit()
        
        # Convert to data URI
        return "data:image/png;base64," + base64.b64encode(screenshot).decode()
    except Exception as e:
        print(f"Error capturing screenshot for {url}: {str(e)}")
        driver.quit() if 'driver' in locals() else None
        return None

def parse_urls(text: str) -> List[str]:
    """Parse and deduplicate URLs from text input."""
    out = []
    for line in (text or "").splitlines():
        line = line.strip()
        if line.lower().startswith("http"):
            out.append(line)
    seen = set()
    return [u for u in out if not (u in seen or seen.add(u))]

# -------- Main Function --------
def extract_screenshots(url_text: str, csv_file, max_urls: int):
    """Process auction URLs: capture screenshots and display thumbnails next to URLs."""
    # Collect URLs
    urls = parse_urls(url_text)
    if csv_file is not None:
        try:
            # Treat csv_file as a path and open it
            with open(csv_file, 'r') as f:
                df = pd.read_csv(f)
            url_cols = [c for c in df.columns if "url" in c.lower()] or [df.columns[0]]
            urls += [str(u) for u in df[url_cols[0]] if str(u).startswith("http")]
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}")
            return f"Error processing CSV: {str(e)}", ""
    urls = list(dict.fromkeys(urls))[:max_urls]
    if not urls:
        return "No valid URLs provided.", ""

    # Process URLs and build HTML
    html = ["<div style='display:flex;flex-direction:column;gap:14px'>"]
    for u in urls:
        try:
            # Capture screenshot
            data_uri = capture_screenshot(u)
            if data_uri is None:
                html.append(
                    f"<div style='display:flex;align-items:center;gap:16px'>"
                    f"<div style='width:180px;height:120px;display:flex;align-items:center;justify-content:center;border:1px solid #ddd;border-radius:8px;background:#f6f6f6'>NO IMAGE</div>"
                    f"<a href='{u}' target='_blank' style='font-size:12px;word-break:break-all'>{u}</a>"
                    f"</div>"
                )
                continue

            html.append(
                f"<div style='display:flex;align-items:center;gap:16px'>"
                f"<img src='{data_uri}' style='width:180px;border:1px solid #ddd;border-radius:8px'/>"
                f"<a href='{u}' target='_blank' style='font-size:12px;word-break:break-all'>{u}</a>"
                f"</div>"
            )
        except Exception as e:
            print(f"Error processing {u}: {str(e)}")
            html.append(
                f"<div style='display:flex;align-items:center;gap:16px'>"
                f"<div style='width:180px;height:120px;display:flex;align-items:center;justify-content:center;border:1px solid #ddd;border-radius:8px;background:#f6f6f6'>ERROR</div>"
                f"<a href='{u}' target='_blank' style='font-size:12px;word-break:break-all'>{u}</a>"
                f"</div>"
            )

    html.append("</div>")
    result_html = "\n".join(html)
    return f"Processed {len(urls)} URLs.", result_html

# -------- Gradio Interface --------
with gr.Blocks(title="Auction Screenshot Extractor") as demo:
    gr.Markdown("### Auction Screenshot Extractor")
    gr.Markdown("Paste auction URLs (one per line) or upload a CSV with 'url' column. The tool captures a screenshot of each page and displays it next to the URL. Pop-ups are automated where possible.")

    with gr.Row():
        with gr.Column(scale=2):
            urls = gr.Textbox(label="Paste Auction URLs (one per line)", lines=10, placeholder="e.g., https://whiskyauctioneer.com/lot/003001/macallan-18-year-old-fine-oak")
            csvf = gr.File(label="Or Upload CSV (with 'url' column)", file_types=[".csv"])
            max_urls = gr.Slider(1, 100, value=10, step=1, label="Max URLs to Process")
        with gr.Column(scale=1):
            go = gr.Button("Extract Screenshots", variant="primary")
            status = gr.Markdown()
            right = gr.HTML(label="Results (Screenshots Next to URLs)")

    go.click(
        fn=extract_screenshots,
        inputs=[urls, csvf, max_urls],
        outputs=[status, right]
    )

# Launch in Colab
demo.launch(share=True, debug=True)

# Save for local use
with open('auction_screenshot_extractor.py', 'w') as f:
    f.write(''.join([line for line in open(__file__, 'r').readlines() if not line.strip().startswith('#')]))  # Save content, skipping comments
from google.colab import files
files.download('auction_screenshot_extractor.py')
