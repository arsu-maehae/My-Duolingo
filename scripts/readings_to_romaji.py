"""
แปลง jp_reading จาก hiragana → romaji (hepburn) สำหรับ word questions
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jplearn.settings')
import django
django.setup()

import pykakasi
from lessons.models import Question

kks = pykakasi.kakasi()

updated = 0
qs = Question.objects.filter(question_type='word').exclude(jp_reading='')

for q in qs:
    result     = kks.convert(q.jp_reading)
    romaji     = ''.join(item['hepburn'] for item in result)
    if romaji and romaji != q.jp_reading:
        q.jp_reading = romaji
        q.save(update_fields=['jp_reading'])
        updated += 1

print(f"✅ แปลงเสร็จ {updated} คำ")

# Show a few samples
for q in Question.objects.filter(question_type='word')[:8]:
    print(f"  {q.jp_text} → {q.jp_reading}")
