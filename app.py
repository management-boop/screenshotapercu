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
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------- Utilities --------
def capture_screenshot(url: str, timeout=30) -> str:
    """
    Capture a screenshot of the webpage, handling pop-ups.
    This function is self-contained and thread-safe.
    """
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        
        driver.set_window_size(1280, 720)
        driver.get(url)
        
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        try:
            # More robust pop-up handling
            buttons = driver.find_elements(By.XPATH, "//button")
            for button in buttons:
                text = button.text.lower()
                if any(keyword in text for keyword in ['continue', 'proceed', 'i am 19', 'agree', 'accept']):
                    try:
                        button.click()
                        time.sleep(2) # Wait for action to complete
                        break # Assume one pop-up is enough
                    except Exception:
                        pass # Button might not be clickable
        except Exception as e:
            print(f"No clickable pop-up button found for {url}: {str(e)}")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        screenshot = driver.get_screenshot_as_png()
        return "data:image/png;base64," + base64.b64encode(screenshot).decode()
    except Exception as e:
        print(f"Error capturing screenshot for {url}: {str(e)}")
        return None
    finally:
        if driver:
            driver.quit()

def parse_urls(text: str) -> List[str]:
    out = []
    for line in (text or "").splitlines():
        line = line.strip()
        if line.lower().startswith("http"):
            out.append(line)
    seen = set()
    return [u for u in out if not (u in seen or seen.add(u))]

# -------- Main Function --------
def extract_screenshots(url_text: str, csv_file, max_urls: int):
    urls = parse_urls(url_text)
    if csv_file is not None:
        try:
            df = pd.read_csv(csv_file.name)
            url_cols = [c for c in df.columns if "url" in c.lower()] or [df.columns[0]]
            urls.extend([str(u) for u in df[url_cols[0]] if str(u).startswith("http")])
        except Exception as e:
            return f"Error reading CSV: {e}", ""

    urls = list(dict.fromkeys(urls))[:max_urls]
    if not urls:
        return "No valid URLs provided.", ""

    html_results = {url: "" for url in urls}

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_url = {executor.submit(capture_screenshot, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data_uri = future.result()
                if data_uri:
                    html_results[url] = (
                        f"<div style='display:flex;align-items:center;gap:16px'>"
                        f"<img src='{data_uri}' style='width:180px;border:1px solid #ddd;border-radius:8px'/>"
                        f"<a href='{url}' target='_blank' style='font-size:12px;word-break:break-all'>{url}</a>"
                        f"</div>"
                    )
                else:
                    html_results[url] = (
                        f"<div style='display:flex;align-items:center;gap:16px'>"
                        f"<div style='width:180px;height:120px;display:flex;align-items:center;justify-content:center;border:1px solid #ddd;border-radius:8px;background:#f6f6f6'>NO IMAGE</div>"
                        f"<a href='{url}' target='_blank' style='font-size:12px;word-break:break-all'>{url}</a>"
                        f"</div>"
                    )
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                html_results[url] = (
                    f"<div style='display:flex;align-items:center;gap:16px'>"
                    f"<div style='width:180px;height:120px;display:flex;align-items:center;justify-content:center;border:1px solid #ddd;border-radius:8px;background:#f6f6f6'>ERROR</div>"
                    f"<a href='{url}' target='_blank' style='font-size:12px;word-break:break-all'>{url}</a>"
                    f"</div>"
                )

    # Preserve original order
    ordered_html = [html_results[u] for u in urls]
    result_html = "<div style='display:flex;flex-direction:column;gap:14px'>\n" + "\n".join(ordered_html) + "\n</div>"

    return f"Processed {len(urls)} URLs.", result_html

# -------- Gradio Interface --------
with gr.Blocks(title="Auction Screenshot Extractor") as demo:
    gr.Markdown("### Auction Screenshot Extractor")
    gr.Markdown("Paste auction URLs (one per line) or upload a CSV with 'url' column. The tool captures a screenshot of each page and displays it next to the URL.")

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

if __name__ == "__main__":
    demo.launch(share=True, debug=True)
