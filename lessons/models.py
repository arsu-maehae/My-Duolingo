from django.db import models
from django.contrib.auth.models import User

# 1. ตาราง Level (ด่านหลัก)
class Level(models.Model):
    level_number = models.IntegerField(unique=True) # เลขด่าน เช่น 1, 2, 3
    title = models.CharField(max_length=100)        # ชื่อด่าน เช่น "คำศัพท์เบื้องต้น"
    passing_score = models.IntegerField(default=3)  # คะแนนขั้นต่ำที่ต้องได้เพื่อผ่านด่าน

    def __str__(self):
        return f"Lv.{self.level_number} - {self.title}"

# 2. ตาราง Question (คลังคำศัพท์และประโยค)
class Question(models.Model):
    QUESTION_TYPES = (
        ('word', 'คำศัพท์'),
        ('sentence', 'ประโยค'),
    )
    
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='word')
    
    jp_text = models.CharField(max_length=200)      # ภาษาญี่ปุ่น เช่น 食べる
    jp_reading = models.CharField(max_length=200, blank=True) # คำอ่าน เช่น Taberu
    th_meaning = models.CharField(max_length=200)   # คำแปลภาษาไทย (คำตอบ)

    def __str__(self):
        return f"[{self.level.level_number}] {self.jp_text} = {self.th_meaning}"

# 3. ตาราง UserProgress (เก็บความคืบหน้าของผู้เล่น)
class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    is_passed = models.BooleanField(default=False)
    highest_score = models.IntegerField(default=0)

    def __str__(self):
        return f"ผู้เล่น: {self.user.username} | Lv.{self.level.level_number} | ผ่าน: {self.is_passed}"