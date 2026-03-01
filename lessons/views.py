from django.shortcuts import render, get_object_or_404
from .models import Level, Question
import random
from pythainlp.tokenize import word_tokenize # 👈 นำเข้าตัวตัดคำภาษาไทย

def home(request):
    levels = Level.objects.all().order_by('level_number')
    return render(request, 'lessons/home.html', {'levels': levels})

def play_level(request, level_id):
    level = get_object_or_404(Level, level_number=level_id)
    
    # 1. ดึงข้อสอบ
    all_words = list(level.questions.filter(question_type='word'))
    selected_words = random.sample(all_words, min(len(all_words), 3))
    
    all_sentences = list(level.questions.filter(question_type='sentence'))
    selected_sentences = random.sample(all_sentences, min(len(all_sentences), 2))
    selected_questions = selected_words + selected_sentences
    
    # ดึงคำแปลภาษาไทยทั้งหมดในด่านนี้มาเตรียมไว้ทำ "คำหลอก"
    all_th_meanings = list(level.questions.values_list('th_meaning', flat=True))
    
    # 2. เตรียมข้อมูลส่งให้หน้าเว็บ
    questions_data = []
    for q in selected_questions:
        data = {
            'type': q.question_type,
            'jp_text': q.jp_text,
            'jp_reading': q.jp_reading,
            'th_meaning': q.th_meaning,
            'en_meaning': q.en_meaning,
            'choices': [] # 👈 กล่องเก็บคำศัพท์ให้กดเลือก
        }
        
        # 🌟 ถ้าเป็นประโยค ให้สร้างปุ่มคำศัพท์ (เฉลย + คำหลอก)
        if q.question_type == 'sentence':
            correct_ans = q.th_meaning.split(',')[0].strip() # เอาเฉลยแบบแรกสุดมาใช้
            
            # ตัดคำเฉลย (เช่น "ฉัน/กิน/ข้าว")
            correct_words = word_tokenize(correct_ans, engine='newmm', keep_whitespace=False)
            
            # สุ่มคำหลอกมา 3 คำ
            fake_words = []
            for _ in range(3):
                random_meaning = random.choice(all_th_meanings).split(',')[0]
                random_tokens = word_tokenize(random_meaning, engine='newmm', keep_whitespace=False)
                if random_tokens:
                    fake_words.append(random.choice(random_tokens))
            
            # เอาคำจริงกับคำหลอกมารวมกันแล้วสับเปลี่ยนตำแหน่ง
            choices = correct_words + fake_words
            random.shuffle(choices)
            data['choices'] = choices
            
        questions_data.append(data)
        
    return render(request, 'lessons/play.html', {
        'level': level,
        'questions': questions_data
    })