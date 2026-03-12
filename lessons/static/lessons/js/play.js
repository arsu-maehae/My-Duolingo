/* =========================================================
   play.js  —  JP Learn Game Engine (entry point)
   Imports all sub-modules and wires up the game loop.
   Handles: multiple_choice | type_answer | fill_blank | sort_sentence
   2-attempt logic for MC modes (Levels 1 & 2)
   ========================================================= */

import { S }                                                from './play-state.js';
import { D, initDom }                                       from './play-dom.js';
import { hideAllModes, setCheckEnabled, updateProgress }    from './play-helpers.js';
import { hideFeedback, initFeedbackEvents }                  from './play-feedback.js';
import { renderMC, renderTypeAnswer, renderFillBlank, renderSort } from './play-renderers.js';
import { checkMC, checkTyped, checkFillBlank, checkSort }  from './play-checkers.js';
import { handleCorrect, handleWrong }                       from './play-markers.js';
import { updateHeartsDisplay, resetHearts, hideGameOver }  from './play-hearts.js';

document.addEventListener('DOMContentLoaded', function () {

    /* ─────────────────────────────────────────────────────────
       0.  DATA BOOTSTRAP
    ───────────────────────────────────────────────────────── */
    const dataEl = document.getElementById('questions-data');
    if (!dataEl) return;  // no game on this page

    const parsed = JSON.parse(dataEl.textContent);
    if (!parsed || parsed.length === 0) return;

    // Populate shared state (window.LEVEL_ID injected inline by the template)
    S.questions = parsed;
    S.levelId   = (typeof window.LEVEL_ID !== 'undefined') ? window.LEVEL_ID : 0;

    /* ─────────────────────────────────────────────────────────
       1.  INIT DOM & EVENTS
    ───────────────────────────────────────────────────────── */
    initDom();
    initFeedbackEvents();

    // Init hearts display
    updateHeartsDisplay();

    // Wire refill-hearts button (resets all progress → back to Level 1 only)
    const btnRefill = document.getElementById('btn-refill-hearts');
    if (btnRefill) {
        btnRefill.addEventListener('click', async function () {
            btnRefill.disabled = true;
            btnRefill.textContent = '⏳ กำลังรีเซ็ต...';
            if (window.USER_AUTHENTICATED && window.RESET_PROGRESS_URL) {
                try {
                    await fetch(window.RESET_PROGRESS_URL, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': window.CSRF_TOKEN,
                            'Content-Type': 'application/json',
                        },
                    });
                } catch (e) { /* continue even on network error */ }
            }
            resetHearts();
            window.location.href = window.PLAY_HOME_URL || '/play/';
        });
    }

    /* ─────────────────────────────────────────────────────────
       7.  LOAD QUESTION
    ───────────────────────────────────────────────────────── */

    function loadQuestion() {
        const q = S.questions[S.currentIndex];
        S.attempts = 0;
        S.answered = false;

        // Slide animation
        D.quizCard.classList.remove('slide-in');
        void D.quizCard.offsetWidth;            // reflow
        D.quizCard.classList.add('slide-in');

        // Reset hint
        D.hintBox.classList.remove('revealed');

        // Common fields
        if (q.mode === 'sort_sentence') {
            // Show full JP sentence as the main display
            D.jpTextEl.textContent      = q.jp_sentence || q.jp_text;
            D.jpTextEl.style.fontFamily = '';
            D.jpTextEl.style.fontSize   = '';
            D.hintBox.style.display     = '';
            D.jpReadingEl.textContent   = q.jp_reading || '—';
        } else {
            D.jpTextEl.textContent      = q.jp_text;
            D.jpTextEl.style.fontFamily = '';
            D.jpTextEl.style.fontSize   = '';
            D.hintBox.style.display     = '';
            D.jpReadingEl.textContent   = q.jp_reading || '—';
        }

        hideFeedback();
        hideAllModes();

        // Buttons
        D.btnCheck.style.display = 'block';
        D.btnNext.style.display  = 'none';
        setCheckEnabled(false);

        updateProgress();

        // Route to the correct mode renderer
        switch (q.mode) {
            case 'multiple_choice': renderMC(q);         break;
            case 'type_answer':     renderTypeAnswer(q); break;
            case 'fill_blank':      renderFillBlank(q);  break;
            case 'sort_sentence':   renderSort(q);       break;
            default:                renderTypeAnswer(q);
        }
    }

    /* ─────────────────────────────────────────────────────────
       9.  CHECK ANSWER
    ───────────────────────────────────────────────────────── */

    function checkAnswer() {
        if (S.answered) return;

        const q = S.questions[S.currentIndex];
        let correct = false;

        switch (q.mode) {
            case 'multiple_choice': correct = checkMC(q);        break;
            case 'type_answer':     correct = checkTyped(q);     break;
            case 'fill_blank':      correct = checkFillBlank(q); break;
            case 'sort_sentence':   correct = checkSort(q);      break;
        }

        if (correct) {
            handleCorrect(q);
        } else {
            handleWrong(q);
        }
    }

    /* ─────────────────────────────────────────────────────────
       12.  NEXT QUESTION / SHOW RESULTS
    ───────────────────────────────────────────────────────── */

    function nextQuestion() {
        S.currentIndex++;
        if (S.currentIndex < S.questions.length) {
            loadQuestion();
        } else {
            showResults();
        }
    }

    function showResults() {
        // Final progress bar = 100%
        D.progressBar.style.width = '100%';
        D.progressText.textContent = S.questions.length + ' / ' + S.questions.length;

        // Hide game UI, show result screen
        D.quizCard.style.display      = 'none';
        D.actionBtnWrap.style.display = 'none';
        D.resultScreen.style.display  = 'block';

        const total   = S.questions.length;
        const wrong   = total - S.score;
        const passing = Math.ceil(total * 0.6);  // 60% to pass
        const pct     = Math.round((S.score / total) * 100);

        // Score ring gradient
        D.resultScreen.querySelector('.score-ring').style.setProperty('--pct', pct + '%');

        // Stat boxes
        const statCorrect = document.getElementById('stat-correct');
        const statWrong   = document.getElementById('stat-wrong');
        const statTotal   = document.getElementById('stat-total');
        if (statCorrect) statCorrect.textContent = S.score;
        if (statWrong)   statWrong.textContent   = wrong;
        if (statTotal)   statTotal.textContent   = total;

        // Score number
        D.finalScoreEl.textContent = S.score;

        if (S.score >= passing) {
            const stars = S.score === total ? '⭐⭐⭐'
                        : S.score >= passing + 1 ? '⭐⭐'
                        : '⭐';
            D.resultStars.textContent = stars;
            D.resultTitle.textContent = S.score === total
                ? 'เพอร์เฟกต์! ตอบถูกทุกข้อ! 🎉'
                : 'ผ่านด่านแล้ว! เก่งมาก! 🎊';
            D.finalScoreEl.className  = 'score-correct';
            D.resultMsg.textContent   = 'ได้ ' + S.score + ' จาก ' + total + ' คะแนน';
            if (D.btnRetryGame)  D.btnRetryGame.style.display  = 'block';
            if (D.btnFinishGame) D.btnFinishGame.style.display = 'block';
        } else {
            D.resultStars.textContent = '💔';
            D.resultTitle.textContent = 'พยายามอีกนิดนะ!';
            D.finalScoreEl.className  = 'score-fail';
            D.resultMsg.textContent   = 'ต้องได้ ' + passing + ' คะแนนขึ้นไปจึงจะผ่านด่าน';
            if (D.btnRetryGame)  D.btnRetryGame.style.display  = 'block';
            if (D.btnFinishGame) D.btnFinishGame.style.display = 'block';
        }

        // Save progress to server (only if user is logged in)
        // Store promise so the finish button can wait for it before navigating.
        window._savePromise = (window.USER_AUTHENTICATED && window.SAVE_PROGRESS_URL)
            ? fetch(window.SAVE_PROGRESS_URL, {
                method: 'POST',
                keepalive: true,   // complete even if page navigates away
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.CSRF_TOKEN,
                },
                body: JSON.stringify({
                    level_id: S.levelId,
                    score: S.score,
                    total: total,
                    question_ids: S.questions.map(function(q) { return q.question_id; }).filter(Boolean),
                }),
              }).catch(() => {})
            : Promise.resolve();
    }

    /* ─────────────────────────────────────────────────────────
       13.  BUTTON EVENT LISTENERS
    ───────────────────────────────────────────────────────── */

    D.btnCheck.addEventListener('click', checkAnswer);
    D.btnNext.addEventListener('click', nextQuestion);

    // Retry — reload the page to restart the same level
    if (D.btnRetryGame) {
        D.btnRetryGame.addEventListener('click', function (e) {
            e.preventDefault();
            location.reload();
        });
    }

    // Finish — wait for the save AJAX to complete before navigating away,
    // so progress is always recorded even on fast connections.
    if (D.btnFinishGame) {
        D.btnFinishGame.addEventListener('click', function (e) {
            e.preventDefault();
            const dest = D.btnFinishGame.href;
            const save = window._savePromise || Promise.resolve();
            // Wait up to 2 s for save, then navigate regardless
            Promise.race([save, new Promise(r => setTimeout(r, 2000))])
                .then(() => { window.location.href = dest; });
        });
    }

    // Close page — go back to play_home (already an <a> tag, no JS needed,
    // but ensure speech synthesis stops)
    if (D.btnClosePage) {
        D.btnClosePage.addEventListener('click', function () {
            window.speechSynthesis.cancel();
        });
    }

    // Keyboard: Enter submits or advances
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            if (D.btnNext.style.display === 'block') {
                nextQuestion();
            } else if (!D.btnCheck.disabled) {
                checkAnswer();
            }
        }
    });

    /* ─────────────────────────────────────────────────────────
       15.  KICK OFF
    ───────────────────────────────────────────────────────── */

    loadQuestion();

}); // end DOMContentLoaded
