import os
import sys
import django
import csv
from pathlib import Path
import pykakasi  # 👈 1. นำเข้าไลบรารีแปลงคำอ่าน

# ตั้งค่าให้ Python รู้จัก Django Project
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_duolingo.settings")
django.setup()

from lessons.models import Level, Question

def run():
    # 👈 2. เปิดใช้งานตัวแปลงคันจิเป็นฮิรางานะ/โรมาจิ
    kks = pykakasi.kakasi()

    file_mapping = {
        'jp_datasets/n5.csv': 1,
        'jp_datasets/n4.csv': 2,
        'jp_datasets/n3.csv': 3,
        'jp_datasets/n2.csv': 4,
        'jp_datasets/n1.csv': 5
    }

    for filepath, level_num in file_mapping.items():
        level_title = f"JLPT N{6 - level_num} Vocabulary"
        level_obj, created = Level.objects.get_or_create(level_number=level_num, defaults={'title': level_title})
        
        # 🧹 ล้างข้อมูลเก่าของด่านนี้ทิ้งไปก่อน
        level_obj.questions.all().delete()
        
        try:
            with open(filepath, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                count_words = 0
                count_sentences = 0
                
                for row in reader:
                    # 1. นำเข้าคำศัพท์ (Word)
                    Question.objects.create(
                        level=level_obj,
                        question_type='word',
                        jp_text=row['expression'],
                        jp_reading=row['reading'] if row['reading'] else row['expression'],
                        th_meaning=row['ความหมาย'],
                        en_meaning=row['meaning']   
                    )
                    count_words += 1
                    
                    # 2. นำเข้าประโยค (Sentence)
                    if row.get('jp_sentence') and row.get('th_sentence'):
                        
                        # 🌟 3. ให้ pykakasi ช่วยอ่านประโยคคันจิยาวๆ ให้กลายเป็นฮิรางานะและโรมาจิ
                        result = kks.convert(row['jp_sentence'])
                        sentence_hira = "".join([item['hira'] for item in result])
                        sentence_romaji = " ".join([item['hepburn'] for item in result])
                        
                        # นำมาต่อกันให้สวยงาม เช่น あした、ともだちにあいます。 (ashita, tomodachi ni aimasu.)
                        full_sentence_reading = f"{sentence_hira} ({sentence_romaji})"
                        
                        Question.objects.create(
                            level=level_obj,
                            question_type='sentence',
                            jp_text=row['jp_sentence'],
                            jp_reading=full_sentence_reading, # 👈 ส่งคำอ่านเต็มๆ เข้า Database
                            th_meaning=row['th_sentence'],
                            en_meaning=f"Vocab: {row['expression']} - {row['meaning']}"
                        )
                        count_sentences += 1
                        
            print(f"✅ อัปเดต Lv.{level_num} สำเร็จ! ได้คำศัพท์ {count_words} คำ | ประโยค {count_sentences} ประโยค")
            
        except FileNotFoundError:
            print(f"⚠️ หาไฟล์ {filepath} ไม่เจอ (ข้ามด่านนี้ไปก่อน)")
        except Exception as e:
            print(f"❌ Error: ด่าน {level_num} มีปัญหา: {e}")

    print("\n🎉 อัปเดตข้อมูลครบทุกระดับเรียบร้อยแล้ว!")

run()