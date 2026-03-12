import json
import random
import re

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST
from pythainlp.tokenize import word_tokenize as th_tokenize

from .forms import LoginForm, RegisterForm
from .models import Level, Question, UserProgress, EncounteredWord


# ---------------------------------------------------------------------------
# Utility: split a Japanese sentence into word-level chunks for Level 5
# ---------------------------------------------------------------------------
def _split_jp_chunks(sentence):
    """
    Return a list of meaningful Japanese word chunks.
    Uses '|' as an explicit separator if present; otherwise splits
    after common particles (は が を に で へ と も) as a heuristic.
    """
    clean = sentence.rstrip('。？！')
    if '|' in clean:
        return [s.strip() for s in clean.split('|') if s.strip()]
    parts = re.split(r'(?<=[はがをにでへとも、])', clean)
    parts = [p for p in parts if p.strip()]
    if len(parts) <= 1:
        # Fallback: every 3 characters
        parts = [clean[i:i + 3] for i in range(0, len(clean), 3)]
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Per-mode question builders
# ---------------------------------------------------------------------------
def _first_meaning(text):
    """Return only the first Thai meaning (before the first comma)."""
    return text.split(',')[0].strip() if text else text


def _mc_question(q, all_meanings):
    """Multiple-choice: 4 Thai-meaning options, each trimmed to first word."""
    answer_first = _first_meaning(q.th_meaning)
    wrong_pool = [
        _first_meaning(m) for m in all_meanings
        if _first_meaning(m) != answer_first
    ]
    # deduplicate
    seen = set()
    unique_wrongs = []
    for w in wrong_pool:
        if w not in seen:
            seen.add(w)
            unique_wrongs.append(w)
    wrongs = random.sample(unique_wrongs, min(3, len(unique_wrongs)))
    choices = [answer_first] + wrongs
    random.shuffle(choices)
    return {
        'mode': 'multiple_choice',
        'question_id': q.id,
        'jp_text': q.jp_text,
        'jp_reading': q.jp_reading,
        'th_meaning': answer_first,
        'en_meaning': q.en_meaning or '',
        'jp_sentence': q.jp_sentence,
        'th_sentence': q.th_sentence,
        'choices': choices,
        'answer': answer_first,
        'chunks': [],
    }


def _type_answer_question(q):
    """Free-type: user types the Thai meaning from the Japanese word."""
    return {
        'mode': 'type_answer',
        'question_id': q.id,
        'jp_text': q.jp_text,
        'jp_reading': q.jp_reading,
        'th_meaning': q.th_meaning,
        'en_meaning': q.en_meaning or '',
        'jp_sentence': q.jp_sentence,
        'th_sentence': q.th_sentence,
        'choices': [],
        'answer': q.th_meaning,
        'chunks': [],
    }


def _fill_blank_question(q, all_meanings):
    """
    Fill-in-the-blank: show Thai sentence with last word blanked.
    Choices are Thai meanings (1 correct + 4 distractors).
    """
    th_sent = (q.th_sentence or q.th_meaning or '').strip()

    # Tokenize Thai sentence; blank a random meaningful token (len >= 2)
    tokens = [t for t in th_tokenize(th_sent, engine='newmm') if t.strip()]
    candidates = [i for i, t in enumerate(tokens) if len(t) >= 2]
    if candidates:
        idx        = random.choice(candidates)
        blank_word = tokens[idx]
        th_display = ''.join(tokens[:idx]) + '___' + ''.join(tokens[idx+1:])
    elif tokens:
        blank_word = tokens[-1]
        th_display = ''.join(tokens[:-1]) + '___'
    else:
        blank_word = th_sent
        th_display = '___'

    # Build wrong choices: split every meaning by comma AND space → individual short words
    seen = {blank_word}
    unique_wrongs = []
    for m in all_meanings:
        for part in m.split(','):
            for word in part.strip().split():
                word = word.strip()
                if word and word not in seen and len(word) >= 2:
                    seen.add(word)
                    unique_wrongs.append(word)
    random.shuffle(unique_wrongs)
    wrongs  = unique_wrongs[:4]
    choices = [blank_word] + wrongs
    random.shuffle(choices)

    return {
        'mode': 'fill_blank',
        'question_id': q.id,
        'jp_text': q.jp_text,
        'jp_reading': q.jp_reading,
        'th_meaning': q.th_meaning,
        'en_meaning': q.en_meaning or '',
        'jp_sentence': q.jp_sentence,
        'th_sentence': th_display,   # Thai sentence with ___
        'choices': choices,
        'answer': blank_word,
        'chunks': [],
    }


def _sort_sentence_question(q, all_meanings):
    """
    Sentence-sort: show JP sentence, user arranges Thai word tiles to form the translation.
    """
    th_sent = (q.th_sentence or q.th_meaning or '').strip()
    correct_chunks = [t for t in th_tokenize(th_sent, engine='newmm') if t.strip()]

    # Thai decoy words from other meanings pool
    seen = set(correct_chunks)
    decoy_pool = []
    for m in all_meanings:
        for part in m.split(','):
            for word in part.strip().split():
                word = word.strip()
                if word and word not in seen and len(word) >= 2:
                    seen.add(word)
                    decoy_pool.append(word)
    random.shuffle(decoy_pool)
    decoys = decoy_pool[:2]

    all_tiles = correct_chunks + decoys
    random.shuffle(all_tiles)
    return {
        'mode': 'sort_sentence',
        'question_id': q.id,
        'jp_text': q.jp_sentence or q.jp_text,  # full JP sentence shown at top
        'jp_reading': q.jp_reading,
        'th_meaning': q.th_meaning,
        'en_meaning': q.en_meaning or '',
        'jp_sentence': q.jp_sentence,
        'th_sentence': q.th_sentence,
        'choices': all_tiles,       # shuffled Thai word tiles
        'answer': correct_chunks,   # correct Thai word order
        'chunks': all_tiles,
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Authentication Views
# ---------------------------------------------------------------------------

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'lessons/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next') or 'home'
            return redirect(next_url)
    else:
        form = LoginForm()
    return render(request, 'lessons/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    progress_list = (
        UserProgress.objects
        .filter(user=request.user)
        .select_related('level')
        .order_by('level__level_number')
    )
    total_passed = progress_list.filter(is_passed=True).count()
    return render(request, 'lessons/profile.html', {
        'progress_list': progress_list,
        'total_passed': total_passed,
    })


@require_POST
def save_progress(request):
    """AJAX endpoint called by play.js when a level is completed."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'skip'})
    try:
        data = json.loads(request.body)
        level_id = int(data['level_id'])
        score = int(data.get('score', 0))
        total = int(data.get('total', 5))
        question_ids = [int(x) for x in data.get('question_ids', []) if str(x).isdigit()]
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'error'}, status=400)

    is_passed = score >= (total * 0.6)
    level = get_object_or_404(Level, pk=level_id)
    progress, _ = UserProgress.objects.get_or_create(user=request.user, level=level)
    if is_passed:
        progress.is_passed = True
    if score > progress.highest_score:
        progress.highest_score = score
    progress.save()

    # Save which specific questions were encountered during this session
    if question_ids:
        valid_qs = Question.objects.filter(pk__in=question_ids, level=level)
        EncounteredWord.objects.bulk_create(
            [EncounteredWord(user=request.user, question=q) for q in valid_qs],
            ignore_conflicts=True,
        )

    return JsonResponse({'status': 'ok', 'is_passed': progress.is_passed})


@require_POST
def reset_progress(request):
    """AJAX endpoint: deletes all UserProgress when hearts run out.
    EncounteredWord (ทบทวนคำศัพท์) is intentionally kept intact."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'skip'})
    UserProgress.objects.filter(user=request.user).delete()
    return JsonResponse({'status': 'ok'})


# ---------------------------------------------------------------------------
# Main Views
# ---------------------------------------------------------------------------

def home(request):
    """Landing page with Vocabulary Bank and Start Testing buttons."""
    return render(request, 'lessons/home.html')

def vocab_bank(request):
    """Single Page Vocabulary Bank (N5-N1 Tabs)"""
    selected_level = request.GET.get('level', 'N5').upper()
    
    if selected_level not in ['N1', 'N2', 'N3', 'N4', 'N5']:
        selected_level = 'N5'
        
    # 🌟 จุดที่แก้: เพิ่ม question_type='word' เข้าไปใน .filter()
    # เพื่อกรองเอาแค่คำศัพท์ ไม่เอาแถวที่เป็นประโยคมาโชว์มั่วซั่ว
    questions = Question.objects.filter(jlpt_level=selected_level, question_type='word').order_by('jp_text')
    # ตัดความหมายภาษาไทยให้เหลือคำแรกก่อนเครื่องหมายจุลภาค (server-side)
    for q in questions:
        q.th_meaning_first = q.th_meaning.split(',')[0].strip() if q.th_meaning else ''    
    return render(request, 'lessons/vocab_bank.html', {
        'questions': questions,
        'current_level': selected_level
    })

# (ลบ def vocab_bank_level ทิ้งไปเลยครับ ไม่ได้ใช้แล้ว!)

def play_home(request):
    """Level-selection screen for the game (shows 5 game levels)."""
    levels = Level.objects.all().order_by('level_number')
    progress_map = {}
    if request.user.is_authenticated:
        for p in UserProgress.objects.filter(user=request.user).select_related('level'):
            progress_map[p.level_id] = {
                'is_passed': p.is_passed,
                'highest_score': p.highest_score,
            }

    # locked_levels: set of level_numbers that cannot be played yet.
    # Level 1 is always open. Level N requires passing Level N-1.
    # Locking applies to authenticated users only (guests can't save progress).
    level_num_to_id = {lv.level_number: lv.id for lv in levels}
    locked_levels = set()
    if request.user.is_authenticated:
        for lv in levels:
            if lv.level_number == 1:
                continue
            prev_id = level_num_to_id.get(lv.level_number - 1)
            prev_passed = (
                prev_id is not None
                and progress_map.get(prev_id, {}).get('is_passed', False)
            )
            if not prev_passed:
                locked_levels.add(lv.level_number)

    # Vocab from specific questions the user has actually encountered during sessions
    played_vocab = []
    if request.user.is_authenticated:
        encountered = (
            EncounteredWord.objects
            .filter(user=request.user)
            .select_related('question', 'question__level')
            .order_by('question__level__level_number', 'question__jp_text')
        )
        for ew in encountered:
            q = ew.question
            q.th_meaning_first = q.th_meaning.split(',')[0].strip() if q.th_meaning else ''
            played_vocab.append(q)

    return render(request, 'lessons/play_home.html', {
        'levels': levels,
        'progress_map': progress_map,
        'locked_levels': locked_levels,
        'played_vocab': played_vocab,
    })


def play_level(request, level_id):
    """
    Prepare JSON question data for one of the 5 game levels and render play.html.

    Level 1 & 2: multiple_choice (4 options)
    Level 3:     Q1-3 type_answer, Q4-5 fill_blank
    Level 4:     fill_blank (all 5)
    Level 5:     sort_sentence (all 5)
    """
    # Gate: authenticated users must pass Level N-1 before accessing Level N.
    # Guest users are not gated (they can't save progress anyway).
    if level_id > 1 and request.user.is_authenticated:
        try:
            prev_level = Level.objects.get(level_number=level_id - 1)
            prog = UserProgress.objects.filter(user=request.user, level=prev_level).first()
            if not (prog and prog.is_passed):
                return redirect('play_home')
        except Level.DoesNotExist:
            pass

    level = get_object_or_404(Level, level_number=level_id)

    # Separate word-type and sentence-type question pools
    word_qs     = list(level.questions.filter(question_type='word'))
    sentence_qs = list(level.questions.filter(question_type='sentence'))
    all_qs      = word_qs + sentence_qs

    if not all_qs:
        return render(request, 'lessons/play.html', {
            'level': level,
            'questions_data': [],
            'level_id': level_id,
            'error': 'ยังไม่มีคำถามในด่านนี้',
        })

    # Distractor pools (words only for meanings, sentences only for jp_text)
    all_meanings  = [q.th_meaning for q in word_qs]
    all_jp_texts  = [q.jp_text    for q in word_qs]
    questions_data = []

    if level_id in (1, 2):
        # --- Multiple Choice: คำศัพท์เดียว → เลือกความหมาย 4 ตัวเลือก ---
        pool_src = word_qs if word_qs else all_qs
        pool = random.sample(pool_src, min(5, len(pool_src)))
        for q in pool:
            questions_data.append(_mc_question(q, all_meanings))

    elif level_id == 3:
        # --- Mixed: type_answer (Q1–3 words) + fill_blank (Q4–5 sentences) ---
        word_pool = random.sample(word_qs, min(3, len(word_qs))) if word_qs else []
        sent_pool = random.sample(
            [q for q in sentence_qs if q.jp_sentence] or sentence_qs,
            min(2, len(sentence_qs))
        ) if sentence_qs else []
        pool = word_pool + sent_pool
        for idx, q in enumerate(pool):
            if idx < 3:
                questions_data.append(_type_answer_question(q))
            else:
                if q.jp_sentence:
                    questions_data.append(_fill_blank_question(q, all_meanings))
                else:
                    questions_data.append(_mc_question(q, all_meanings))

    elif level_id == 4:
        # --- Fill in the Blank (all 5, prefer sentence-type) ---
        fb_pool_src = [q for q in sentence_qs if q.jp_sentence] or \
                      [q for q in all_qs if q.jp_sentence]
        if not fb_pool_src:
            fb_pool_src = all_qs
        pool = random.sample(fb_pool_src, min(5, len(fb_pool_src)))
        for q in pool:
            questions_data.append(_fill_blank_question(q, all_meanings))

    elif level_id == 5:
        # --- Sentence Sort (all 5, prefer sentence-type with both fields) ---
        ss_pool_src = [q for q in sentence_qs if q.jp_sentence and q.th_sentence] or \
                      [q for q in all_qs if q.jp_sentence and q.th_sentence]
        if not ss_pool_src:
            ss_pool_src = all_qs
        pool = random.sample(ss_pool_src, min(5, len(ss_pool_src)))
        for q in pool:
            questions_data.append(_sort_sentence_question(q, all_meanings))

    else:
        raise Http404("Invalid level")

    return render(request, 'lessons/play.html', {
        'level': level,
        'questions_data': questions_data,
        'level_id': level_id,
    })