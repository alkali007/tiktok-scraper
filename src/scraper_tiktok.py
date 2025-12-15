import os
import asyncio
import json
import time
from urllib.parse import parse_qs, urlparse
from playwright.async_api import async_playwright, Playwright, expect, Response


async def handle_response(response):
    # 1. Print ALL URLs to see what Playwright is actually seeing (Debug)
    # print(f">> Network Response: {response.url}")

    # 2. Filter for the specific API endpoint
    # We look for "item_list" because the query params usually contain it
    if "api/post/item_list" in response.url:
        print(f"\n[+] Target API Found: {response.url}")

        try:
            # 3. Wait for the JSON body
            json_data = await response.json()

            # 4. Success! Do something with the data
            print("------------------------------------------------")
            print("CAPTURED DATA SAMPLE:")
            # Print just the first item to avoid flooding the console
            if "itemList" in json_data:
                print(f"Found {len(json_data['itemList'])} items.")
                print(f"First Item ID: {json_data['itemList'][0].get('id')}")

                # 2. Create a unique filename using the current timestamp
                # This prevents overwriting if multiple requests occur
                timestamp = int(time.time() * 1000)
                filename = f"response_{timestamp}.json"

                # 3. Save to file
                # ensure_ascii=False ensures emojis and special chars verify correctly
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=4, ensure_ascii=False)

                print(f"✅ Saved JSON to {filename}")

            else:
                print(json_data)
            print("------------------------------------------------\n")

        except Exception as e:
            print(f"[-] Could not parse JSON (might be 204 No Content): {e}")


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=True)

    my_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    context = await browser.new_context(
        user_agent=my_user_agent,  # <--- Inject User Agent here
        # Recommended to set viewport to match desktop
        viewport={"width": 1920, "height": 1080}
    )

    page = await context.new_page()

    # # --- KEY STEP: Register the listener BEFORE going to the site ---
    page.on("response", handle_response)

    await page.goto("https://www.tiktok.com/@yusmankusumaa")
    await page.reload(wait_until="networkidle")

    # # TikTok loads data dynamically.
    print("Waiting for network requests...")
    await page.wait_for_timeout(30000)  # Wait 10 seconds

    try:
        print("Waiting for Audio button...")
        # Try to find the button for 30 seconds
        await expect(page.get_by_role("button", name="Audio")).to_be_visible(timeout=5000)

        # If found (no error), click it
        await page.get_by_role("button", name="Audio").click()

    except Exception as e:
        # This block ONLY runs if the button was NOT found
        print("Button not found! Taking screenshot for debugging...")

        # Take the screenshot
        await page.screenshot(path="error_debug.png")

        # Optional: Print the specific error message
        print(f"The error was: {e}")

        # Optional: Stop the script here since we failed
        raise e

    selector = ".TUXModal .captcha-verify-container audio"
    
    await page.screenshot(path="error_debug.png")
    print("Waiting for audio element...")
    audio_element = await page.wait_for_selector(selector, timeout=10000)

    # 2. Extract the 'src' URL
    audio_src = await audio_element.get_attribute("src")
    print(f"Found audio source: {audio_src}")

    if audio_src:
        # 3. Download the file using the browser's context (keeps cookies/session valid)
        response = await page.request.get(audio_src)

        if response.status == 200:
            # Save the body of the response to a file
            file_name = "captcha_audio.mp3"
            with open(file_name, "wb") as f:
                f.write(response.body())
            print(f"Successfully saved to {os.path.abspath(file_name)}")
        else:
            print(f"Failed to download. Status code: {response.status}")
    else:
        print("Audio tag found, but 'src' attribute was empty.")

    # page.get_by_role("button", name="Play").click()
    # page.get_by_placeholder("Enter what you hear").click()
    # page.get_by_placeholder("Enter what you hear").fill("qkath")
    # page.get_by_role("button", name="Verify").click()

    # ---------------------
    context.storage_state(path="auth.json")
    context.close()
    browser.close()


async def main():
    async with async_playwright() as playwright:
    	await run(playwright)

if __name__ == "__main__":
    asyncio.run(main())
