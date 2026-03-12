"""
Browser-based end-to-end tests for JP Learn
=============================================
Opens a real Chrome browser (headless) against a live Django dev server.

Run with:
    python manage.py test functional.test_browser

Requirements:
    pip install selenium
    google-chrome must be installed
"""

import time

from django.contrib.auth import (
    BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY,
)
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from lessons.models import Level, Question, UserProgress


# ─── helpers ───────────────────────────────────────────────────────────────────

def _chrome():
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,800")
    return webdriver.Chrome(options=opts)


PAUSE = 1.5   # seconds to pause between steps so you can watch


def _wait(driver, timeout=8):
    return WebDriverWait(driver, timeout)


def _make_db(levels_only=False):
    """
    Create levels 1-5 + questions using get_or_create so it's safe to call
    multiple times (works whether db was flushed between tests or not).
    """
    WORDS    = ["食べる", "飲む", "走る", "寝る", "話す", "聞く", "歩く", "買う"]
    MEANINGS = ["กิน",   "ดื่ม", "วิ่ง", "นอน", "พูด", "ฟัง", "เดิน", "ซื้อ"]

    levels = {}
    for n, title, ps in [
        (1, "Easy", 3), (2, "Medium", 3), (3, "Mixed", 3),
        (4, "Fill-in", 3), (5, "Sort", 3),
    ]:
        levels[n], _ = Level.objects.get_or_create(
            level_number=n, defaults={"title": title, "passing_score": ps}
        )

    if levels_only:
        return levels

    # Lv1 & Lv2 – word questions for MC
    for jp, th in zip(WORDS, MEANINGS):
        for lv in (levels[1], levels[2]):
            Question.objects.get_or_create(
                level=lv, jp_text=f"{lv.level_number}_{jp}",
                defaults=dict(question_type="word", jp_reading="よむ",
                              th_meaning=th, jlpt_level="N5"),
            )
    # Lv3 – words + sentences
    for i in range(4):
        Question.objects.get_or_create(
            level=levels[3], jp_text=f"3w{i}",
            defaults=dict(question_type="word", jp_reading="たんご",
                          th_meaning=MEANINGS[i], jlpt_level="N3"),
        )
        Question.objects.get_or_create(
            level=levels[3], jp_text=f"3s{i}",
            defaults=dict(question_type="sentence", jp_reading="",
                          th_meaning=MEANINGS[i],
                          jp_sentence="私は学校に行きます。",
                          th_sentence="ฉัน ไป โรงเรียน", jlpt_level="N3"),
        )
    # Lv4 – fill-in sentences
    for i in range(6):
        Question.objects.get_or_create(
            level=levels[4], jp_text=f"4s{i}",
            defaults=dict(question_type="sentence", jp_reading="",
                          th_meaning=MEANINGS[i % 8],
                          jp_sentence="私は学校に行きます。",
                          th_sentence="ฉัน ไป โรงเรียน", jlpt_level="N2"),
        )
    # Lv5 – sort sentences
    for i in range(6):
        Question.objects.get_or_create(
            level=levels[5], jp_text=f"5s{i}",
            defaults=dict(question_type="sentence", jp_reading="",
                          th_meaning=MEANINGS[i % 8],
                          jp_sentence="私|は|学校|に|行きます",
                          th_sentence="ฉัน ไป โรงเรียน", jlpt_level="N1"),
        )
    return levels


def _force_login(driver, live_server_url, user):
    """
    Inject a valid Django session cookie directly into the browser.
    Avoids the login form entirely – reliable for testing locked UI states.
    """
    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    # Must be on the same origin to add cookies
    driver.get(live_server_url)
    driver.add_cookie({"name": "sessionid", "value": session.session_key, "path": "/"})


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Authentication flows
# ═══════════════════════════════════════════════════════════════════════════════

class AuthBrowserTests(StaticLiveServerTestCase):
    """Fresh browser per test — zero cookie/session carry-over."""

    def setUp(self):
        self.driver = _chrome()

    def tearDown(self):
        self.driver.quit()

    def w(self):
        return _wait(self.driver)

    def test_01_register_new_user(self):
        self.driver.get(f"{self.live_server_url}/register/")
        self.w().until(EC.presence_of_element_located((By.NAME, "username")))
        time.sleep(PAUSE)
        self.driver.find_element(By.NAME, "username").send_keys("testuser")
        time.sleep(PAUSE)
        self.driver.find_element(By.NAME, "password1").send_keys("testpass123")
        self.driver.find_element(By.NAME, "password2").send_keys("testpass123")
        time.sleep(PAUSE)
        self.driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        self.w().until(EC.url_to_be(f"{self.live_server_url}/"))
        time.sleep(PAUSE)
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_02_login_with_valid_credentials(self):
        User.objects.create_user(username="u1", password="p1")
        self.driver.get(f"{self.live_server_url}/login/")
        self.w().until(EC.presence_of_element_located((By.NAME, "username")))
        time.sleep(PAUSE)
        self.driver.find_element(By.NAME, "username").send_keys("u1")
        time.sleep(PAUSE)
        self.driver.find_element(By.NAME, "password").send_keys("p1")
        time.sleep(PAUSE)
        self.driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        self.w().until(EC.url_changes(f"{self.live_server_url}/login/"))
        time.sleep(PAUSE)
        self.assertNotIn("/login/", self.driver.current_url)


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  Play Home – level cards & lock badges
# ═══════════════════════════════════════════════════════════════════════════════

class PlayHomeBrowserTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = _chrome()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        _make_db()

    def w(self):
        return _wait(self.driver)

    def test_01_hearts_shows_7_and_level_cards_load(self):
        self.driver.get(f"{self.live_server_url}/play/")
        self.w().until(EC.presence_of_element_located((By.CLASS_NAME, "level-card")))
        time.sleep(PAUSE)
        self.assertEqual(len(self.driver.find_elements(By.CLASS_NAME, "level-card")), 5)
        self.assertEqual(self.driver.find_element(By.ID, "hg-count").text, "7")

    def test_02_authenticated_user_sees_lock_badges(self):
        user = User.objects.create_user(username="locked_tester", password="pass")
        _force_login(self.driver, self.live_server_url, user)
        self.driver.get(f"{self.live_server_url}/play/")
        self.w().until(EC.presence_of_element_located((By.CLASS_NAME, "lock-badge")))
        time.sleep(PAUSE)
        self.assertGreaterEqual(len(self.driver.find_elements(By.CLASS_NAME, "lock-badge")), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Play Level 1 – game UI
# ═══════════════════════════════════════════════════════════════════════════════

class PlayLevel1BrowserTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = _chrome()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        _make_db()

    def w(self):
        return _wait(self.driver)

    def test_01_js_renders_mc_buttons(self):
        self.driver.get(f"{self.live_server_url}/play/1/")
        self.w().until(EC.presence_of_element_located((By.CSS_SELECTOR, ".mc-btn")))
        time.sleep(PAUSE)
        self.assertGreaterEqual(len(self.driver.find_elements(By.CSS_SELECTOR, ".mc-btn")), 2)

    def test_02_selecting_answer_enables_check_button(self):
        self.driver.get(f"{self.live_server_url}/play/1/")
        self.w().until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".mc-btn")))
        time.sleep(PAUSE)
        self.driver.find_elements(By.CSS_SELECTOR, ".mc-btn")[0].click()
        self.w().until(lambda d: not d.find_element(By.ID, "btn-check").get_attribute("disabled"))
        time.sleep(PAUSE)
        self.assertIsNone(self.driver.find_element(By.ID, "btn-check").get_attribute("disabled"))

    def test_03_close_returns_to_play_home(self):
        self.driver.get(f"{self.live_server_url}/play/1/")
        self.w().until(EC.element_to_be_clickable((By.ID, "btn-close-page")))
        time.sleep(PAUSE)
        self.driver.find_element(By.ID, "btn-close-page").click()
        self.w().until(EC.url_contains("/play/"))
        time.sleep(PAUSE)
        self.assertNotIn("/play/1/", self.driver.current_url)
