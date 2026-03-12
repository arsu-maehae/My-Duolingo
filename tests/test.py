"""
Unit tests for JP Learn
=======================
Tests individual model behaviour and view logic in isolation.

Run with:
    python manage.py test tests
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from lessons.models import EncounteredWord, Level, Question, UserProgress


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_level(number=1, title="Easy", passing_score=3):
    return Level.objects.create(level_number=number, title=title, passing_score=passing_score)


def _make_question(level, jp_text="食べる", th_meaning="กิน", question_type="word"):
    return Question.objects.create(
        level=level,
        jp_text=jp_text,
        jp_reading="たべる",
        th_meaning=th_meaning,
        question_type=question_type,
        jlpt_level="N5",
    )


# ─── Model Tests ──────────────────────────────────────────────────────────────

class LevelModelTest(TestCase):
    """Unit tests for the Level model"""

    def test_str_returns_formatted_string(self):
        level = _make_level(number=1, title="Easy")
        self.assertEqual(str(level), "Lv.1 - Easy")

    def test_default_passing_score_is_3(self):
        level = Level.objects.create(level_number=2, title="Medium")
        self.assertEqual(level.passing_score, 3)


class QuestionModelTest(TestCase):
    """Unit tests for the Question model"""

    def setUp(self):
        self.level = _make_level()

    def test_str_contains_jp_text_and_meaning(self):
        q = _make_question(self.level, jp_text="食べる", th_meaning="กิน")
        self.assertIn("食べる", str(q))
        self.assertIn("กิน", str(q))

    def test_default_question_type_is_word(self):
        q = Question.objects.create(
            level=self.level, jp_text="飲む", th_meaning="ดื่ม", jlpt_level="N5"
        )
        self.assertEqual(q.question_type, "word")


class UserProgressModelTest(TestCase):
    """Unit tests for the UserProgress model"""

    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.level = _make_level()

    def test_default_is_passed_is_false(self):
        prog = UserProgress.objects.create(user=self.user, level=self.level)
        self.assertFalse(prog.is_passed)

    def test_default_highest_score_is_zero(self):
        prog = UserProgress.objects.create(user=self.user, level=self.level)
        self.assertEqual(prog.highest_score, 0)


class EncounteredWordModelTest(TestCase):
    """Unit tests for the EncounteredWord model"""

    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.level = _make_level()
        self.question = _make_question(self.level)

    def test_unique_together_prevents_duplicates(self):
        EncounteredWord.objects.create(user=self.user, question=self.question)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            EncounteredWord.objects.create(user=self.user, question=self.question)


# ─── View Tests ───────────────────────────────────────────────────────────────

class SaveProgressViewTest(TestCase):
    """Unit tests for the save_progress API view"""

    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.level = _make_level()
        self.client.login(username="u", password="p")

    def _post(self, data):
        return self.client.post(
            reverse("save_progress"),
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_score_above_60_percent_marks_passed(self):
        self._post({"level_id": self.level.id, "score": 3, "total": 5, "question_ids": []})
        self.assertTrue(UserProgress.objects.get(user=self.user, level=self.level).is_passed)

    def test_score_below_60_percent_does_not_mark_passed(self):
        self._post({"level_id": self.level.id, "score": 2, "total": 5, "question_ids": []})
        self.assertFalse(UserProgress.objects.get(user=self.user, level=self.level).is_passed)

    def test_highest_score_never_decreases(self):
        self._post({"level_id": self.level.id, "score": 4, "total": 5, "question_ids": []})
        self._post({"level_id": self.level.id, "score": 2, "total": 5, "question_ids": []})
        self.assertEqual(UserProgress.objects.get(user=self.user, level=self.level).highest_score, 4)

    def test_unauthenticated_returns_skip(self):
        self.client.logout()
        resp = self._post({"level_id": self.level.id, "score": 3, "total": 5, "question_ids": []})
        self.assertEqual(resp.json()["status"], "skip")

    def test_question_ids_saved_as_encountered_words(self):
        q1 = _make_question(self.level, jp_text="走る", th_meaning="วิ่ง")
        q2 = _make_question(self.level, jp_text="飲む", th_meaning="ดื่ม")
        self._post({
            "level_id": self.level.id, "score": 3, "total": 5,
            "question_ids": [q1.id, q2.id],
        })
        self.assertEqual(EncounteredWord.objects.filter(user=self.user).count(), 2)


class ResetProgressViewTest(TestCase):
    """Unit tests for the reset_progress API view"""

    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.level = _make_level()
        self.client.login(username="u", password="p")

    def _post(self):
        return self.client.post(reverse("reset_progress"), content_type="application/json")

    def test_deletes_all_user_progress(self):
        UserProgress.objects.create(user=self.user, level=self.level, is_passed=True)
        self._post()
        self.assertEqual(UserProgress.objects.filter(user=self.user).count(), 0)

    def test_keeps_encountered_words(self):
        q = _make_question(self.level)
        UserProgress.objects.create(user=self.user, level=self.level, is_passed=True)
        EncounteredWord.objects.create(user=self.user, question=q)
        self._post()
        self.assertEqual(EncounteredWord.objects.filter(user=self.user).count(), 1)

    def test_unauthenticated_returns_skip(self):
        self.client.logout()
        resp = self._post()
        self.assertEqual(resp.json()["status"], "skip")


class PlayHomeViewTest(TestCase):
    """Unit tests for the play_home view"""

    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.lv1 = _make_level(number=1, title="Easy")
        self.lv2 = _make_level(number=2, title="Medium")

    def test_level2_locked_without_level1_pass(self):
        self.client.login(username="u", password="p")
        resp = self.client.get(reverse("play_home"))
        self.assertIn(2, resp.context["locked_levels"])

    def test_level2_unlocked_after_passing_level1(self):
        UserProgress.objects.create(user=self.user, level=self.lv1, is_passed=True)
        self.client.login(username="u", password="p")
        resp = self.client.get(reverse("play_home"))
        self.assertNotIn(2, resp.context["locked_levels"])


class LevelGatingViewTest(TestCase):
    """Unit tests for level access gating in play_level view"""

    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.lv1 = _make_level(number=1, title="Easy")
        self.lv2 = _make_level(number=2, title="Medium")
        for jp, th in [("食べる", "กิน"), ("飲む", "ดื่ม"), ("走る", "วิ่ง"), ("寝る", "นอน"), ("話す", "พูด")]:
            _make_question(self.lv1, jp_text=f"1_{jp}", th_meaning=th)
            _make_question(self.lv2, jp_text=f"2_{jp}", th_meaning=th)
        self.client.login(username="u", password="p")

    def test_authenticated_user_blocked_from_level2_without_progress(self):
        resp = self.client.get(reverse("play_level", args=[2]))
        self.assertRedirects(resp, reverse("play_home"))

    def test_authenticated_user_can_access_level2_after_passing_level1(self):
        UserProgress.objects.create(user=self.user, level=self.lv1, is_passed=True)
        resp = self.client.get(reverse("play_level", args=[2]))
        self.assertEqual(resp.status_code, 200)
