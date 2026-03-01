from django.shortcuts import render, get_object_or_404
from .models import Level, Question
import random

def home(request):
    # ดึงด่านทั้งหมดออกมา เรียงตามเลข Level จากน้อยไปมาก
    levels = Level.objects.all().order_by('level_number')
    
    # ส่งข้อมูล levels ไปให้หน้าไฟล์ home.html
    return render(request, 'lessons/home.html', {'levels': levels})

def play_level(request, level_id):
    # 1. หาด่านที่ขุนแผนกดเลือกมา
    level = get_object_or_404(Level, level_number=level_id)
    
    # 2. ดึงคำศัพท์ทั้งหมดในด่านนี้มา
    all_questions = list(level.questions.all())
    
    # 3. สุ่มมาแค่ 5 ข้อ (ถ้ามีศัพท์เกิน 5 คำ)
    if len(all_questions) > 5:
        selected_questions = random.sample(all_questions, 5)
    else:
        selected_questions = all_questions
        
    # 4. แปลงข้อมูลให้อยู่ในรูปแบบที่ JavaScript เอาไปใช้ง่ายๆ (เป็น List of Dictionaries)
    questions_data = []
    for q in selected_questions:
        questions_data.append({
            'jp_text': q.jp_text,
            'jp_reading': q.jp_reading,
            'th_meaning': q.th_meaning,
            'en_meaning': q.en_meaning
        })
        
    # 5. ส่งข้อมูลไปให้หน้า play.html (เดี๋ยวเราจะสร้างหน้านี้กัน)
    return render(request, 'lessons/play.html', {
        'level': level,
        'questions': questions_data
    })