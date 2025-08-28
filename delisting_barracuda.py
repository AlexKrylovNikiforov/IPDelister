from __future__ import annotations
from enum import Enum
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FFService
from selenium.webdriver.edge.service import Service as EdgeService
import os

def _evict_driver_from_path(exe_name: str) -> None:
    path = os.environ.get("PATH", "")
    parts = []
    for d in path.split(os.pathsep):
        if not os.path.exists(os.path.join(d, exe_name)):
            parts.append(d)
    os.environ["PATH"] = os.pathsep.join(parts)

def _clean_path():

    bad_names = {"chromedriver", "msedgedriver", "geckodriver"}
    new_path = []
    for p in os.environ.get("PATH", "").split(os.pathsep):
        try:
            if any(os.path.exists(os.path.join(p, name)) for name in bad_names):
                # Пропускаем эту папку
                continue
        except Exception:
            pass
        new_path.append(p)
    os.environ["PATH"] = os.pathsep.join(new_path)

class Browser(str, Enum):
    firefox = "firefox"
    chrome = "chrome"
    edge = "edge"

def build_driver(browser: Browser, headless: bool):
    _clean_path()
    
    if browser == Browser.firefox:
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        opts = FirefoxOptions()
        if headless:
            opts.add_argument("-headless")
        service = FFService(log_output=os.devnull)  # для новых selenium
        return webdriver.Firefox(options=opts, service=service)

    if browser == Browser.chrome:
        _evict_driver_from_path("chromedriver")
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        # тише логи Chromium/Driver
        opts.add_argument("--disable-logging")
        opts.add_argument("--log-level=3")
        service = ChromeService(log_path=os.devnull)
        return webdriver.Chrome(options=opts, service=service)

    if browser == Browser.edge:
        from selenium.webdriver.edge.options import Options as EdgeOptions
        opts = EdgeOptions()
        if headless:
            opts.add_argument("--headless=new")
        service = EdgeService(log_path=os.devnull)
        return webdriver.Edge(options=opts, service=service)

    raise ValueError(f"Unsupported browser: {browser}")

class BarracudaDelist:
    URL = "https://www.barracudacentral.org/rbl/removal-request"

    def __init__(self, ip: str, headless: bool = True, timeout: int = 60, browser: Browser = Browser.chrome):
        self.ip = ip
        self.timeout = timeout
        self.driver = build_driver(browser, headless)
        self.wait = WebDriverWait(self.driver, timeout)
        self.report_entry = {"ip": self.ip}

    def connect(self):
        self.driver.get(self.URL)

    def _find_first(self, strategies):
        for by, value in strategies:
            els = self.driver.find_elements(by, value)
            if els:
                return els[0]
        raise NoSuchElementException(f"None of the selectors worked: {strategies}")

    def set_data(self, email: str, phone: str, reason: str = ""):
        # Fill IP
        ip_box = self._find_first([
            (By.NAME, "address"),
            (By.CSS_SELECTOR, "input[name='address']"),
        ])
        ip_box.clear(); ip_box.send_keys(self.ip)

        # Email
        mail_box = self._find_first([
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
        ])
        mail_box.clear(); mail_box.send_keys(email)

        # Phone
        phone_box = self._find_first([
            (By.NAME, "phone"),
            (By.CSS_SELECTOR, "input[name='phone']"),
        ])
        phone_box.clear(); phone_box.send_keys(phone)

        # Comments/Reason (optional field name)
        possible_names = ("comments", "why", "reason", "message")
        comment_box = None
        for name in possible_names:
            try:
                comment_box = self.driver.find_element(By.NAME, name)
                break
            except NoSuchElementException:
                continue
        if comment_box and reason:
            comment_box.clear(); comment_box.send_keys(reason)

    def submit(self):
        # Try common submit selectors
        for selector in ("input[type='submit']", "button[type='submit']", "button[name='submit']", "[name='submit']", "button"):
            els = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if els:
                els[0].click()
                return
        raise NoSuchElementException("Submit button not found")

    def check_error_presence(self) -> None:
        # If form shows error section, mark as not listed / error
        try:
            form_error_element = self.driver.find_element(
                By.XPATH,
                "//div[contains(@class,'form-error')]//h4[contains(., 'Please correct the following errors')]"
            )
            if form_error_element:
                self.report_entry["status"] = "Error: IP not listed or validation failed"
                return
        except NoSuchElementException:
            pass
        # Otherwise continue to check success page
        self.proceed_removal()

    def proceed_removal(self) -> None:
        try:
            # Wait for either a success title or any acknowledgement
            self.wait.until(EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Request Received')]") ),
                EC.presence_of_element_located((By.XPATH, "//div[contains(., 'removal request has been received')]") ),
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'thank you')]") )
            ))
            # Try to capture confirmation number if present
            confirmation = None
            for xp in ("//font/b", "//*[contains(., 'Confirmation')]/following::b[1]", "//b[contains(., '#')]"):
                els = self.driver.find_elements(By.XPATH, xp)
                if els:
                    confirmation = els[0].text.strip()
                    break
            if confirmation:
                self.report_entry["status"] = "Request submitted"
                self.report_entry["confirmation"] = confirmation
            else:
                self.report_entry["status"] = "Request submitted (no confirmation number found)"
        except TimeoutException:
            page_html = self.driver.page_source.lower()
            if "not currently listed" in page_html:
                self.report_entry["status"] = "IP not listed"
            else:
                self.report_entry["status"] = "Unknown / timeout — check manually"
        finally:
            try:
                self.driver.quit()
            except Exception:
                pass
