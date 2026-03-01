import csv
from lessons.models import Level, Question

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
    
    # 🧹 1. ล้างข้อมูลเก่าของด่านนี้ทิ้งไปก่อน ป้องกันคำศัพท์เบิ้ล
    level_obj.questions.all().delete()
    
    try:
        # 📥 2. เปิดไฟล์อ่าน
        with open(filepath, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                # ใช้ create เพราะเราล้างของเก่าไปแล้ว มั่นใจได้ว่าไม่ซ้ำ
                Question.objects.create(
                    level=level_obj,
                    question_type='word',
                    jp_text=row['expression'],
                    jp_reading=row['reading'] if row['reading'] else row['expression'],
                    
                    # 🔴 สำคัญ: เช็คชื่อคอลัมน์ตรงนี้ให้ตรงกับหัวตารางในไฟล์ CSV ของคุณนะครับ
                    th_meaning=row['ความหมาย'], # หรือถ้าตั้งชื่ออื่นไว้ เช่น thai_meaning ก็แก้ตามนั้น
                    en_meaning=row['meaning']   
                )
                count += 1
        print(f"✅ อัปเดต Lv.{level_num} สำเร็จ! นำเข้าทั้งหมด {count} คำ (มีทั้งไทยและอังกฤษ)")
        
    except FileNotFoundError:
        print(f"⚠️ หาไฟล์ {filepath} ไม่เจอ (ข้ามด่านนี้ไปก่อน)")
    except KeyError as e:
        print(f"❌ Error: ด่าน {level_num} พังเพราะหาคอลัมน์ชื่อ {e} ไม่เจอในไฟล์ CSV! รบกวนเช็คชื่อหัวตารางอีกทีครับ")

print("\n🎉 อัปเดตข้อมูลคำศัพท์ครบทั้ง 5 ระดับเรียบร้อยแล้ว!")