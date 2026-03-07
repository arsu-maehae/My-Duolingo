/* =========================================================
   play-feedback.js  —  Feedback display, TTS, reading-hint
   ========================================================= */

import { S } from './play-state.js';
import { D } from './play-dom.js';

/* ─────────────────────────────────────────────────────────
   Feedback area
───────────────────────────────────────────────────────── */

/** type: 'correct' | 'incorrect' | 'retry' */
export function showFeedback(type, detail) {
    D.feedbackArea.className = '';   // clear all classes
    D.feedbackArea.classList.add('show');

    if (type === 'correct') {
        D.feedbackArea.classList.add('feedback-correct');
        D.fbIcon.textContent   = '✅';
        D.fbTitle.textContent  = 'ถูกต้อง!';
        D.fbDetail.textContent = detail || '';
    } else if (type === 'incorrect') {
        D.feedbackArea.classList.add('feedback-incorrect');
        D.fbIcon.textContent   = '❌';
        D.fbTitle.textContent  = 'ผิด!';
        D.fbDetail.textContent = detail || '';
    } else if (type === 'retry') {
        D.feedbackArea.classList.add('feedback-retry');
        D.fbIcon.textContent   = '⚠️';
        D.fbTitle.textContent  = 'ยังไม่ถูก! ลองใหม่อีกครั้ง';
        D.fbDetail.textContent = detail || '';
    }
}

export function hideFeedback() {
    D.feedbackArea.className = '';
}

/* ─────────────────────────────────────────────────────────
   TTS
───────────────────────────────────────────────────────── */

export function speakJP(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'ja-JP';
    u.rate = 0.85;
    D.btnSpeak.classList.add('speaking');
    u.onend  = () => D.btnSpeak.classList.remove('speaking');
    u.onerror = () => D.btnSpeak.classList.remove('speaking');
    window.speechSynthesis.speak(u);
}

/* ─────────────────────────────────────────────────────────
   Event listeners — call once after initDom()
───────────────────────────────────────────────────────── */

export function initFeedbackEvents() {
    D.btnSpeak.addEventListener('click', function () {
        const q = S.questions[S.currentIndex];
        if (!q) return;
        // For fill_blank speak the full sentence; otherwise speak the word/phrase
        const text = (q.mode === 'fill_blank' && q.jp_sentence)
            ? q.jp_sentence
            : q.jp_text;
        speakJP(text);
    });

    D.hintBox.addEventListener('click', function () {
        D.hintBox.classList.toggle('revealed');
    });
    D.hintBox.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') D.hintBox.classList.toggle('revealed');
    });
}
