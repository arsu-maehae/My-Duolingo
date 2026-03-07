"""
อัปเดต jp_reading ของ word questions ให้ใช้ hiragana จาก CSV
แทน romaji ที่ insert_data.py แปลงไว้
"""
import os
import sys
import csv

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jplearn.settings')

import django
django.setup()

from lessons.models import Question

CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'jp_datasets')

files = ['n5.csv', 'n4.csv', 'n3.csv', 'n2.csv', 'n1.csv']

total_updated = 0

for fname in files:
    path = os.path.join(CSV_DIR, fname)
    if not os.path.exists(path):
        print(f"  ไม่พบไฟล์ {fname} — ข้าม")
        continue

    updated = 0
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            expression = row.get('expression', '').strip()
            reading    = row.get('reading', '').strip()

            if not expression or not reading:
                continue

            # อัปเดตเฉพาะ word questions ที่ jp_text ตรงกัน
            count = Question.objects.filter(
                question_type='word',
                jp_text=expression
            ).update(jp_reading=reading)
            updated += count

    print(f"✅ {fname}: อัปเดต {updated} คำ")
    total_updated += updated

print(f"\n🎉 เสร็จสิ้น! อัปเดตทั้งหมด {total_updated} คำ")
