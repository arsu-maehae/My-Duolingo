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
    
    with open(filepath, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            Question.objects.get_or_create(
                level=level_obj,
                question_type='word',
                jp_text=row['expression'],
                jp_reading=row['reading'] if row['reading'] else row['expression'],
                th_meaning=row['meaning'],
                en_meaning=row['original_en']
            )
print("🎉 กู้ข้อมูลคำศัพท์ครบทั้ง 5 ระดับเรียบร้อยแล้ว!")