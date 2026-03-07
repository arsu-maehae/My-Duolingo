import os
import sys
import django
import csv
from pathlib import Path
import pykakasi

PROJECT_ROOT = os.getcwd()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jplearn.settings")
django.setup()

from lessons.models import Level, Question

def run():
    kks = pykakasi.kakasi()

    file_mapping = {
        'jp_datasets/n5.csv': (1, 'N5'),
        'jp_datasets/n4.csv': (2, 'N4'),
        'jp_datasets/n3.csv': (3, 'N3'),
        'jp_datasets/n2.csv': (4, 'N2'),
        'jp_datasets/n1.csv': (5, 'N1')
    }

    for filepath, (level_num, jlpt_label) in file_mapping.items():
        level_title = f"JLPT {jlpt_label} Vocabulary"
        level_obj, created = Level.objects.get_or_create(level_number=level_num, defaults={'title': level_title})
        
        level_obj.questions.all().delete()
        
        try:
            csv_path = os.path.join(PROJECT_ROOT, filepath)
            
            with open(csv_path, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                count_words = 0
                count_sentences = 0
                
                for row in reader:
                    jp_sent = row.get('jp_sentence', '').strip()
                    th_sent = row.get('th_sentence', '').strip()

                    # 🌟 แปลงคำอ่านให้เป็น "โรมาจิ (Romaji)" ภาษาอังกฤษล้วนๆ
                    base_reading = row['reading'] if row['reading'] else row['expression']
                    word_kks = kks.convert(base_reading)
                    word_romaji = "".join([item['hepburn'] for item in word_kks])
                    
                    # ใช้แค่โรมาจิล้วนๆ เลย (เช่น aa, asoko, achira)
                    final_word_reading = word_romaji

                    # บันทึกคำศัพท์ (Word)
                    Question.objects.create(
                        level=level_obj,
                        question_type='word',
                        jlpt_level=jlpt_label,
                        jp_text=row['expression'],
                        jp_reading=final_word_reading, # 👈 ตรงนี้จะกลายเป็นภาษาอังกฤษล้วนแล้ว
                        th_meaning=row['ความหมาย'],
                        en_meaning=row['meaning'],
                        jp_sentence=jp_sent,
                        th_sentence=th_sent
                    )
                    count_words += 1
                    
                    # บันทึกประโยค (Sentence)
                    if jp_sent and th_sent:
                        result = kks.convert(jp_sent)
                        sentence_hira = "".join([item['hira'] for item in result])
                        sentence_romaji = " ".join([item['hepburn'] for item in result])
                        # ส่วนประโยคตัวอย่างของด่าน 5 ให้มีทั้งฮิรางานะและโรมาจิเหมือนเดิม จะได้ใบ้ผู้เล่นได้
                        full_sentence_reading = f"{sentence_hira} ({sentence_romaji})"
                        
                        Question.objects.create(
                            level=level_obj,
                            question_type='sentence',
                            jlpt_level=jlpt_label,
                            jp_text=jp_sent,
                            jp_reading=full_sentence_reading, 
                            th_meaning=th_sent,
                            jp_sentence=jp_sent,
                            th_sentence=th_sent,
                            en_meaning=f"Vocab: {row['expression']} - {row['meaning']}"
                        )
                        count_sentences += 1
                        
            print(f"✅ อัปเดต Lv.{level_num} สำเร็จ! ได้คำศัพท์ {count_words} คำ | ประโยค {count_sentences} ประโยค")
            
        except FileNotFoundError:
            print(f"⚠️ หาไฟล์ {filepath} ไม่เจอ (ข้ามด่านนี้ไปก่อน)")
        except Exception as e:
            print(f"❌ Error: ด่าน {level_num} มีปัญหา: {e}")

    print("\n🎉 อัปเดตข้อมูลครบทุกระดับเรียบร้อยแล้ว!")

if __name__ == "__main__":
    run()