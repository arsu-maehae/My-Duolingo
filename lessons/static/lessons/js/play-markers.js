/* =========================================================
   play-markers.js  —  Visual marking, correct/wrong handlers
   ========================================================= */

import { S } from './play-state.js';
import { D } from './play-dom.js';
import { clean, setCheckEnabled } from './play-helpers.js';
import { showFeedback } from './play-feedback.js';
import { loseHeart, animateLostHeart, showGameOver } from './play-hearts.js';

/* ─────────────────────────────────────────────────────────
   11.  VISUAL MARKING  (correct / wrong highlights)
───────────────────────────────────────────────────────── */

export function markInputCorrect(q) {
    switch (q.mode) {
        case 'multiple_choice': {
            const sel = D.mcGrid.querySelector('.mc-btn.selected');
            if (sel) { sel.classList.remove('selected'); sel.classList.add('correct'); }
            disableAllMCBtns();
            break;
        }
        case 'type_answer':
            D.answerInput.classList.add('correct');
            D.answerInput.disabled = true;
            break;
        case 'fill_blank': {
            const sel = D.fillWordBank.querySelector('.word-tile.in-answer');
            if (sel) sel.style.background = '#d7ffb8';
            disableAllFillTiles();
            break;
        }
        case 'sort_sentence':
            D.sortAnswerZone.classList.add('correct');
            disableAllSortTiles();
            break;
    }
}

export function markInputWrong(q) {
    switch (q.mode) {
        case 'multiple_choice':
            disableAllMCBtns();
            break;
        case 'type_answer':
            D.answerInput.classList.add('incorrect');
            D.answerInput.disabled = true;
            break;
        case 'fill_blank':
            disableAllFillTiles();
            break;
        case 'sort_sentence':
            D.sortAnswerZone.classList.add('incorrect');
            disableAllSortTiles();
            break;
    }
}

export function revealAnswer(q) {
    switch (q.mode) {
        case 'multiple_choice': {
            D.mcGrid.querySelectorAll('.mc-btn').forEach(function (btn) {
                if (clean(btn.dataset.value) === clean(q.answer)) {
                    btn.classList.remove('selected', 'incorrect');
                    btn.classList.add('correct');
                }
            });
            break;
        }
        case 'fill_blank': {
            D.fillWordBank.querySelectorAll('.word-tile').forEach(function (btn) {
                if (clean(btn.dataset.value) === clean(q.answer)) {
                    btn.classList.add('in-answer');
                    btn.style.background = '#ffdfe0';
                    const slot = document.getElementById('fill-blank-slot');
                    if (slot) {
                        slot.textContent  = q.answer;
                        slot.style.color  = 'var(--red)';
                        slot.style.borderBottomColor = 'var(--red)';
                    }
                }
            });
            break;
        }
        case 'sort_sentence': {
            // Show the correct order in the answer zone
            D.sortAnswerZone.innerHTML = '';
            const expected = Array.isArray(q.answer) ? q.answer : [q.answer];
            expected.forEach(function (word) {
                const span = document.createElement('span');
                span.className          = 'word-tile';
                span.textContent        = word;
                span.style.background   = '#ffe0e0';
                span.style.borderColor  = 'var(--red)';
                span.style.cursor       = 'default';
                D.sortAnswerZone.appendChild(span);
            });
            break;
        }
        // type_answer: answer is shown in feedback detail
    }
}

/* Helper disable functions */
export function disableAllMCBtns() {
    D.mcGrid.querySelectorAll('.mc-btn').forEach(b => b.disabled = true);
}
export function disableAllFillTiles() {
    D.fillWordBank.querySelectorAll('.word-tile').forEach(b => b.disabled = true);
}
export function disableAllSortTiles() {
    D.sortAnswerZone.querySelectorAll('.word-tile').forEach(t => { t.disabled = true; t.style.cursor = 'default'; });
    D.sortTileBank.querySelectorAll('.word-tile').forEach(t => { t.disabled = true; t.style.cursor = 'default'; });
}

/** Human-readable correct answer for the feedback detail text */
export function getAnswerDisplay(q) {
    if (q.mode === 'sort_sentence') {
        return Array.isArray(q.answer) ? q.answer.join(' ') : q.answer;
    }
    if (q.mode === 'type_answer') {
        return q.th_meaning.split(',')[0].trim();
    }
    return q.answer;
}

/* ─────────────────────────────────────────────────────────
   10.  CORRECT / WRONG HANDLERS
───────────────────────────────────────────────────────── */

export function handleCorrect(q) {
    S.score++;
    S.answered = true;

    markInputCorrect(q);
    showFeedback('correct', '');

    D.btnCheck.style.display = 'none';
    D.btnNext.style.display  = 'block';
}

export function handleWrong(q) {
    S.attempts++;

    // Shake the quiz card
    D.quizCard.classList.remove('shake');
    void D.quizCard.offsetWidth;
    D.quizCard.classList.add('shake');

    // 2-attempt logic only applies to multiple_choice mode
    const hasTwoAttempts = (q.mode === 'multiple_choice');
    const maxAttempts    = hasTwoAttempts ? 2 : 1;

    if (hasTwoAttempts && S.attempts < maxAttempts) {
        // First wrong attempt on MC — allow retry
        showFeedback('retry');
        // Disable the chosen wrong button
        const selected = D.mcGrid.querySelector('.mc-btn.selected');
        if (selected) {
            selected.classList.remove('selected');
            selected.classList.add('incorrect');
            selected.disabled = true;
        }
        setCheckEnabled(false);
        // Do NOT move to next — stay on same question
    } else {
        // Final wrong — lock everything, reveal answer
        S.answered = true;
        markInputWrong(q);
        revealAnswer(q);

        showFeedback('incorrect', 'คำตอบที่ถูกต้องคือ: ' + getAnswerDisplay(q));

        D.btnCheck.style.display = 'none';
        D.btnNext.style.display  = 'block';

        // Lose a heart
        const remaining = loseHeart();
        animateLostHeart();
        if (remaining <= 0) {
            setTimeout(showGameOver, 900);
        }
    }
}
