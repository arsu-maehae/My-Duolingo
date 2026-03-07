/* =========================================================
   play.js  —  JP Learn Game Engine
   Handles: multiple_choice | type_answer | fill_blank | sort_sentence
   2-attempt logic for MC modes (Levels 1 & 2)
   ========================================================= */

'use strict';

document.addEventListener('DOMContentLoaded', function () {

    /* ─────────────────────────────────────────────────────────
       0.  DATA BOOTSTRAP
    ───────────────────────────────────────────────────────── */
    const dataEl = document.getElementById('questions-data');
    if (!dataEl) return;  // no game on this page

    const questions = JSON.parse(dataEl.textContent);
    if (!questions || questions.length === 0) return;

    // LEVEL_ID is injected inline by the template
    const levelId = typeof LEVEL_ID !== 'undefined' ? LEVEL_ID : 0;

    /* ─────────────────────────────────────────────────────────
       1.  STATE
    ───────────────────────────────────────────────────────── */
    let currentIndex = 0;   // which question we're on
    let score        = 0;   // correct answers
    let attempts     = 0;   // attempts on the current question (resets each question)
    let answered     = false; // true once the question is locked

    /* ─────────────────────────────────────────────────────────
       2.  DOM REFERENCES
    ───────────────────────────────────────────────────────── */

    // Card & result
    const quizCard      = document.getElementById('quiz-card');
    const resultScreen  = document.getElementById('result-screen');
    const actionBtnWrap = document.getElementById('action-btn-wrap');

    // Nav
    const progressBar   = document.getElementById('progress-bar');
    const progressText  = document.getElementById('progress-text');
    const btnClosePage  = document.getElementById('btn-close-page');

    // Header elements inside card
    const modeLabel     = document.getElementById('mode-label');
    const btnSpeak      = document.getElementById('btn-speak');
    const jpTextEl      = document.getElementById('jp-text');
    const hintBox       = document.getElementById('hint-box');
    const jpReadingEl   = document.getElementById('jp-reading');

    // Mode containers
    const mcContainer        = document.getElementById('mc-container');
    const mcGrid             = document.getElementById('mc-grid');
    const typeContainer      = document.getElementById('type-container');
    const answerInput        = document.getElementById('answer-input');
    const fillBlankContainer = document.getElementById('fill-blank-container');
    const fillSentenceEl     = document.getElementById('fill-sentence-display');
    const fillThHintEl       = document.getElementById('fill-th-hint');
    const fillWordBank       = document.getElementById('fill-word-bank');
    const sortContainer      = document.getElementById('sort-container');
    const sortPromptText     = document.getElementById('sort-prompt-text');
    const sortAnswerZone     = document.getElementById('sort-answer-zone');
    const sortTileBank       = document.getElementById('sort-tile-bank');

    // Feedback
    const feedbackArea  = document.getElementById('feedback-area');
    const fbIcon        = feedbackArea.querySelector('.fb-icon');
    const fbTitle       = feedbackArea.querySelector('.fb-title');
    const fbDetail      = feedbackArea.querySelector('.fb-detail');

    // Action buttons
    const btnCheck      = document.getElementById('btn-check');
    const btnNext       = document.getElementById('btn-next');

    // Result screen
    const resultStars   = document.getElementById('result-stars');
    const resultTitle   = document.getElementById('result-title');
    const finalScoreEl  = document.getElementById('final-score');
    const resultMsg     = document.getElementById('result-msg');
    const btnRetryGame  = document.getElementById('btn-retry-game');
    const btnFinishGame = document.getElementById('btn-finish-game');

    /* ─────────────────────────────────────────────────────────
       3.  HELPERS
    ───────────────────────────────────────────────────────── */

    /** Hide all four mode containers */
    function hideAllModes() {
        mcContainer.style.display        = 'none';
        typeContainer.style.display      = 'none';
        fillBlankContainer.style.display = 'none';
        sortContainer.style.display      = 'none';
    }

    /** Strip punctuation and whitespace for loose comparison */
    function clean(str) {
        return String(str).toLowerCase().replace(/[\s\u3000\.,。!?！？;:\/（）()\-]/g, '');
    }

    /** Levenshtein similarity 0–1 */
    function similarity(a, b) {
        if (a === b) return 1;
        const la = a.length, lb = b.length;
        const max = Math.max(la, lb);
        if (max === 0) return 1;
        const dp = Array.from({ length: la + 1 }, (_, i) => [i]);
        for (let j = 0; j <= lb; j++) dp[0][j] = j;
        for (let i = 1; i <= la; i++) {
            for (let j = 1; j <= lb; j++) {
                dp[i][j] = Math.min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)
                );
            }
        }
        return (max - dp[la][lb]) / max;
    }

    /** Check a typed Thai answer against all valid meanings */
    function isTypedAnswerCorrect(userRaw, q) {
        const user = clean(userRaw);
        if (!user) return false;
        const candidates = q.th_meaning.split(',').concat((q.en_meaning || '').split(','));
        return candidates.some(c => {
            const cv = clean(c);
            if (!cv) return false;
            if (cv === user) return true;
            if (cv.includes(user) && user.length >= 2) return true;
            return similarity(cv, user) >= 0.78;
        });
    }

    /** Show / hide the check button enabled state */
    function setCheckEnabled(enabled) {
        btnCheck.disabled = !enabled;
    }

    /** Update progress bar and counter */
    function updateProgress() {
        const pct = (currentIndex / questions.length) * 100;
        progressBar.style.width = pct + '%';
        progressText.textContent = (currentIndex + 1) + ' / ' + questions.length;
    }

    /* ─────────────────────────────────────────────────────────
       4.  FEEDBACK DISPLAY
    ───────────────────────────────────────────────────────── */

    /** type: 'correct' | 'incorrect' | 'retry'  */
    function showFeedback(type, detail) {
        feedbackArea.className = '';   // clear all classes
        feedbackArea.classList.add('show');

        if (type === 'correct') {
            feedbackArea.classList.add('feedback-correct');
            fbIcon.textContent  = '✅';
            fbTitle.textContent = 'ถูกต้อง!';
            fbDetail.textContent = detail || '';
        } else if (type === 'incorrect') {
            feedbackArea.classList.add('feedback-incorrect');
            fbIcon.textContent  = '❌';
            fbTitle.textContent = 'ผิด!';
            fbDetail.textContent = detail || '';
        } else if (type === 'retry') {
            feedbackArea.classList.add('feedback-retry');
            fbIcon.textContent  = '⚠️';
            fbTitle.textContent = 'ยังไม่ถูก! ลองใหม่อีกครั้ง';
            fbDetail.textContent = detail || '';
        }
    }

    function hideFeedback() {
        feedbackArea.className = '';
    }

    /* ─────────────────────────────────────────────────────────
       5.  TTS
    ───────────────────────────────────────────────────────── */

    function speakJP(text) {
        if (!('speechSynthesis' in window)) return;
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = 'ja-JP';
        u.rate = 0.85;
        btnSpeak.classList.add('speaking');
        u.onend = () => btnSpeak.classList.remove('speaking');
        u.onerror = () => btnSpeak.classList.remove('speaking');
        window.speechSynthesis.speak(u);
    }

    btnSpeak.addEventListener('click', function () {
        const q = questions[currentIndex];
        if (!q) return;
        // For fill-in-the-blank (sentence with ___), speak the full sentence.
        // For all other modes (MC, type_answer, sort), speak just the word/phrase.
        const text = (q.mode === 'fill_blank' && q.jp_sentence)
            ? q.jp_sentence
            : q.jp_text;
        speakJP(text);
    });

    /* ─────────────────────────────────────────────────────────
       6.  READING HINT
    ───────────────────────────────────────────────────────── */

    hintBox.addEventListener('click', function () {
        hintBox.classList.toggle('revealed');
    });
    hintBox.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') hintBox.classList.toggle('revealed');
    });

    /* ─────────────────────────────────────────────────────────
       7.  LOAD QUESTION
    ───────────────────────────────────────────────────────── */

    function loadQuestion() {
        const q = questions[currentIndex];
        attempts  = 0;
        answered  = false;

        // Slide animation
        quizCard.classList.remove('slide-in');
        void quizCard.offsetWidth;            // reflow
        quizCard.classList.add('slide-in');

        // Reset hint
        hintBox.classList.remove('revealed');

        // Common fields
        if (q.mode === 'sort_sentence') {
            // Show full JP sentence as the main display
            jpTextEl.textContent      = q.jp_sentence || q.jp_text;
            jpTextEl.style.fontFamily = '';
            jpTextEl.style.fontSize   = '';
            hintBox.style.display     = '';
            jpReadingEl.textContent   = q.jp_reading || '—';
        } else {
            jpTextEl.textContent      = q.jp_text;
            jpTextEl.style.fontFamily = '';
            jpTextEl.style.fontSize   = '';
            hintBox.style.display     = '';
            jpReadingEl.textContent   = q.jp_reading || '—';
        }

        hideFeedback();
        hideAllModes();

        // Buttons
        btnCheck.style.display = 'block';
        btnNext.style.display  = 'none';
        setCheckEnabled(false);

        updateProgress();

        // Route to the correct mode renderer
        switch (q.mode) {
            case 'multiple_choice': renderMC(q);        break;
            case 'type_answer':     renderTypeAnswer(q); break;
            case 'fill_blank':      renderFillBlank(q);  break;
            case 'sort_sentence':   renderSort(q);       break;
            default:
                renderTypeAnswer(q);
        }
    }

    /* ─────────────────────────────────────────────────────────
       8.  MODE RENDERERS
    ───────────────────────────────────────────────────────── */

    /* ── 8a. Multiple Choice ── */
    function renderMC(q) {
        modeLabel.textContent = 'เลือกคำตอบที่ถูกต้อง';
        mcContainer.style.display = 'block';
        mcGrid.innerHTML = '';

        const letters = ['A', 'B', 'C', 'D'];
        q.choices.forEach(function (choice, idx) {
            const btn = document.createElement('button');
            btn.className      = 'mc-btn';
            btn.textContent    = choice;
            btn.dataset.value  = choice;
            btn.dataset.letter = letters[idx] || String(idx + 1);

            btn.addEventListener('click', function () {
                if (answered) return;
                mcGrid.querySelectorAll('.mc-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                setCheckEnabled(true);
            });

            mcGrid.appendChild(btn);
        });

        setCheckEnabled(false);
    }

    /* ── 8b. Type Answer ── */
    function renderTypeAnswer(q) {
        modeLabel.textContent = 'พิมพ์คำแปลภาษาไทย';
        typeContainer.style.display = 'block';
        answerInput.value    = '';
        answerInput.disabled = false;
        answerInput.className = '';  // clear correct/incorrect classes
        answerInput.focus();
        setCheckEnabled(false);

        // Enable check when there's input
        answerInput.oninput = function () {
            setCheckEnabled(answerInput.value.trim().length > 0 && !answered);
        };
    }

    /* ── 8c. Fill in the Blank ── */
    function renderFillBlank(q) {
        modeLabel.textContent = 'เติมคำให้สมบูรณ์';
        fillBlankContainer.style.display = 'block';
        fillWordBank.innerHTML = '';

        // Build Thai sentence display with styled blank
        const raw = q.th_sentence || '';
        const parts = raw.split('___');
        fillSentenceEl.innerHTML = '';
        if (parts.length >= 2) {
            fillSentenceEl.appendChild(document.createTextNode(parts[0]));
            const span = document.createElement('span');
            span.className = 'blank-slot';
            span.id = 'fill-blank-slot';
            span.textContent = '　　　';
            fillSentenceEl.appendChild(span);
            fillSentenceEl.appendChild(document.createTextNode(parts.slice(1).join('')));
        } else {
            fillSentenceEl.textContent = raw || '___';
        }

        // No extra hint shown
        fillThHintEl.textContent = '';

        // Word choice tiles (Thai words)
        q.choices.forEach(function (word) {
            const btn = document.createElement('button');
            btn.className   = 'word-tile';
            btn.textContent = word;
            btn.dataset.value = word;

            btn.addEventListener('click', function () {
                if (answered) return;
                if (btn.classList.contains('in-answer')) {
                    // Deselect
                    btn.classList.remove('in-answer');
                    const slot = document.getElementById('fill-blank-slot');
                    if (slot) slot.textContent = '　　　';
                    setCheckEnabled(false);
                } else {
                    // Deselect any previously selected tile
                    fillWordBank.querySelectorAll('.word-tile.in-answer').forEach(b => {
                        b.classList.remove('in-answer');
                    });
                    btn.classList.add('in-answer');
                    const slot = document.getElementById('fill-blank-slot');
                    if (slot) slot.textContent = word;
                    setCheckEnabled(true);
                }
            });

            fillWordBank.appendChild(btn);
        });

        setCheckEnabled(false);
    }

    /* ── 8d. Sentence Sort ── */
    function renderSort(q) {
        modeLabel.textContent = 'เรียงคำให้ถูกต้อง';
        sortContainer.style.display = 'block';
        sortTileBank.innerHTML = '';
        sortAnswerZone.innerHTML = '';
        sortAnswerZone.classList.remove('correct', 'incorrect');

        // Hide prompt box — JP is already shown above
        document.getElementById('sort-prompt').style.display = 'none';
        sortPromptText.textContent = '';

        // Placeholder in answer zone
        const placeholder = document.createElement('span');
        placeholder.className   = 'placeholder-text';
        placeholder.textContent = 'กดคำด้านล่างเพื่อวางที่นี่';
        sortAnswerZone.appendChild(placeholder);

        setCheckEnabled(false);

        // Build tiles (choices are pre-shuffled by the backend)
        (q.choices || []).forEach(function (word) {
            const tile = createSortTile(word, q);
            sortTileBank.appendChild(tile);
        });
    }

    function createSortTile(word, q) {
        const tile = document.createElement('button');
        tile.className   = 'word-tile';
        tile.textContent = word;
        tile.dataset.word = word;

        tile.addEventListener('click', function () {
            if (answered) return;

            if (tile.parentElement === sortAnswerZone) {
                // Move back to bank
                tile.classList.remove('in-answer');
                sortTileBank.appendChild(tile);
            } else {
                // Move to answer zone
                tile.classList.add('in-answer');
                // Remove placeholder if present
                const ph = sortAnswerZone.querySelector('.placeholder-text');
                if (ph) ph.remove();
                sortAnswerZone.appendChild(tile);
            }

            const answerCount = sortAnswerZone.querySelectorAll('.word-tile').length;
            setCheckEnabled(answerCount > 0 && !answered);
        });

        return tile;
    }

    /* ─────────────────────────────────────────────────────────
       9.  CHECK ANSWER
    ───────────────────────────────────────────────────────── */

    function checkAnswer() {
        if (answered) return;

        const q = questions[currentIndex];
        let correct = false;

        switch (q.mode) {
            case 'multiple_choice':
                correct = checkMC(q);
                break;
            case 'type_answer':
                correct = checkTyped(q);
                break;
            case 'fill_blank':
                correct = checkFillBlank(q);
                break;
            case 'sort_sentence':
                correct = checkSort(q);
                break;
        }

        if (correct) {
            handleCorrect(q);
        } else {
            handleWrong(q);
        }
    }

    /* ── 9a. MC check ── */
    function checkMC(q) {
        const selected = mcGrid.querySelector('.mc-btn.selected');
        return selected && clean(selected.dataset.value) === clean(q.answer);
    }

    /* ── 9b. Type check ── */
    function checkTyped(q) {
        return isTypedAnswerCorrect(answerInput.value, q);
    }

    /* ── 9c. Fill-blank check ── */
    function checkFillBlank(q) {
        const selected = fillWordBank.querySelector('.word-tile.in-answer');
        if (!selected) return false;
        return clean(selected.dataset.value) === clean(q.answer);
    }

    /* ── 9d. Sort check ── */
    function checkSort(q) {
        const placed = Array.from(sortAnswerZone.querySelectorAll('.word-tile'))
            .map(t => t.dataset.word);

        // q.answer is the ordered array of correct chunks
        const expected = Array.isArray(q.answer) ? q.answer : [q.answer];

        if (placed.length !== expected.length) return false;
        return placed.every((w, i) => clean(w) === clean(expected[i]));
    }

    /* ─────────────────────────────────────────────────────────
       10.  CORRECT / WRONG HANDLERS
    ───────────────────────────────────────────────────────── */

    function handleCorrect(q) {
        score++;
        answered = true;

        // Visual feedback on the input element
        markInputCorrect(q);

        showFeedback('correct', '');

        // Transition to Next button
        btnCheck.style.display = 'none';
        btnNext.style.display  = 'block';
    }

    function handleWrong(q) {
        attempts++;

        // Shake the quiz card
        quizCard.classList.remove('shake');
        void quizCard.offsetWidth;
        quizCard.classList.add('shake');

        // 2-attempt logic only applies to multiple_choice mode
        const hasTwoAttempts = (q.mode === 'multiple_choice');
        const maxAttempts    = hasTwoAttempts ? 2 : 1;

        if (hasTwoAttempts && attempts < maxAttempts) {
            // First wrong attempt on MC — allow retry
            showFeedback('retry');
            // Disable the chosen wrong button
            const selected = mcGrid.querySelector('.mc-btn.selected');
            if (selected) {
                selected.classList.remove('selected');
                selected.classList.add('incorrect');
                selected.disabled = true;
            }
            setCheckEnabled(false);
            // Do NOT move to next — stay on same question
        } else {
            // Final wrong — lock everything, reveal answer
            answered = true;
            markInputWrong(q);
            revealAnswer(q);

            showFeedback('incorrect', 'คำตอบที่ถูกต้องคือ: ' + getAnswerDisplay(q));

            btnCheck.style.display = 'none';
            btnNext.style.display  = 'block';
        }
    }

    /* ─────────────────────────────────────────────────────────
       11.  VISUAL MARKING  (correct / wrong highlights)
    ───────────────────────────────────────────────────────── */

    function markInputCorrect(q) {
        switch (q.mode) {
            case 'multiple_choice': {
                const sel = mcGrid.querySelector('.mc-btn.selected');
                if (sel) { sel.classList.remove('selected'); sel.classList.add('correct'); }
                disableAllMCBtns();
                break;
            }
            case 'type_answer':
                answerInput.classList.add('correct');
                answerInput.disabled = true;
                break;
            case 'fill_blank': {
                const sel = fillWordBank.querySelector('.word-tile.in-answer');
                if (sel) sel.style.background = '#d7ffb8';
                disableAllFillTiles();
                break;
            }
            case 'sort_sentence':
                sortAnswerZone.classList.add('correct');
                disableAllSortTiles();
                break;
        }
    }

    function markInputWrong(q) {
        switch (q.mode) {
            case 'multiple_choice':
                disableAllMCBtns();
                break;
            case 'type_answer':
                answerInput.classList.add('incorrect');
                answerInput.disabled = true;
                break;
            case 'fill_blank':
                disableAllFillTiles();
                break;
            case 'sort_sentence':
                sortAnswerZone.classList.add('incorrect');
                disableAllSortTiles();
                break;
        }
    }

    function revealAnswer(q) {
        switch (q.mode) {
            case 'multiple_choice': {
                mcGrid.querySelectorAll('.mc-btn').forEach(function (btn) {
                    if (clean(btn.dataset.value) === clean(q.answer)) {
                        btn.classList.remove('selected', 'incorrect');
                        btn.classList.add('correct');
                    }
                });
                break;
            }
            case 'fill_blank': {
                fillWordBank.querySelectorAll('.word-tile').forEach(function (btn) {
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
                sortAnswerZone.innerHTML = '';
                const expected = Array.isArray(q.answer) ? q.answer : [q.answer];
                expected.forEach(function (word) {
                    const span = document.createElement('span');
                    span.className   = 'word-tile';
                    span.textContent = word;
                    span.style.background   = '#ffe0e0';
                    span.style.borderColor  = 'var(--red)';
                    span.style.cursor       = 'default';
                    sortAnswerZone.appendChild(span);
                });
                break;
            }
            // type_answer: answer is shown in feedback detail
        }
    }

    /* Helper disable functions */
    function disableAllMCBtns() {
        mcGrid.querySelectorAll('.mc-btn').forEach(b => b.disabled = true);
    }
    function disableAllFillTiles() {
        fillWordBank.querySelectorAll('.word-tile').forEach(b => b.disabled = true);
    }
    function disableAllSortTiles() {
        sortAnswerZone.querySelectorAll('.word-tile').forEach(t => { t.disabled = true; t.style.cursor = 'default'; });
        sortTileBank.querySelectorAll('.word-tile').forEach(t => { t.disabled = true; t.style.cursor = 'default'; });
    }

    /** Human-readable correct answer for the feedback detail text */
    function getAnswerDisplay(q) {
        if (q.mode === 'sort_sentence') {
            return Array.isArray(q.answer) ? q.answer.join(' ') : q.answer;
        }
        if (q.mode === 'type_answer') {
            return q.th_meaning.split(',')[0].trim();
        }
        return q.answer;
    }

    /* ─────────────────────────────────────────────────────────
       12.  NEXT QUESTION / SHOW RESULTS
    ───────────────────────────────────────────────────────── */

    function nextQuestion() {
        currentIndex++;
        if (currentIndex < questions.length) {
            loadQuestion();
        } else {
            showResults();
        }
    }

    function showResults() {
        // Final progress bar = 100%
        progressBar.style.width = '100%';
        progressText.textContent = questions.length + ' / ' + questions.length;

        // Hide game UI, show result screen
        quizCard.style.display      = 'none';
        actionBtnWrap.style.display = 'none';
        resultScreen.style.display  = 'block';

        // Populate result screen
        finalScoreEl.textContent = score;

        const passing = Math.ceil(questions.length * 0.6);  // 60% to pass

        if (score >= passing) {
            const stars = score === questions.length ? '⭐⭐⭐' : score >= passing + 1 ? '⭐⭐' : '⭐';
            resultStars.textContent    = stars;
            resultTitle.textContent    = score === questions.length
                ? 'เพอร์เฟกต์! ตอบถูกทุกข้อ! 🎉'
                : 'ผ่านด่านแล้ว! เก่งมาก! 🎊';
            finalScoreEl.className     = 'score-correct';
            resultMsg.textContent      = 'ได้ ' + score + ' จาก ' + questions.length + ' คะแนน';
            if (btnRetryGame)  btnRetryGame.style.display  = 'block';
            if (btnFinishGame) btnFinishGame.style.display = 'block';
        } else {
            resultStars.textContent    = '💔';
            resultTitle.textContent    = 'พยายามอีกนิดนะ!';
            finalScoreEl.className     = 'score-correct';
            finalScoreEl.style.color   = 'var(--red)';
            resultMsg.textContent      = 'ได้ ' + score + ' จาก ' + questions.length
                + ' · ต้องได้ ' + passing + ' คะแนนขึ้นไปเพื่อผ่านด่าน';
            if (btnRetryGame)  btnRetryGame.style.display  = 'block';
            if (btnFinishGame) btnFinishGame.style.display = 'block';
        }
    }

    /* ─────────────────────────────────────────────────────────
       13.  BUTTON EVENT LISTENERS
    ───────────────────────────────────────────────────────── */

    btnCheck.addEventListener('click', checkAnswer);
    btnNext.addEventListener('click', nextQuestion);

    // Retry — reload the page to restart the same level
    if (btnRetryGame) {
        btnRetryGame.addEventListener('click', function (e) {
            e.preventDefault();
            location.reload();
        });
    }

    // Close page — go back to play_home (already an <a> tag, no JS needed,
    // but ensure speech synthesis stops)
    if (btnClosePage) {
        btnClosePage.addEventListener('click', function () {
            window.speechSynthesis.cancel();
        });
    }

    // Keyboard: Enter submits or advances
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            if (btnNext.style.display === 'block') {
                nextQuestion();
            } else if (!btnCheck.disabled) {
                checkAnswer();
            }
        }
    });

    /* ─────────────────────────────────────────────────────────
       14.  ENABLE CHECK BUTTON FOR EACH MODE (input watchers)
    ───────────────────────────────────────────────────────── */

    // answerInput changes are handled inside renderTypeAnswer (oninput)
    // MC, FillBlank, Sort enable check inside their click handlers

    /* ─────────────────────────────────────────────────────────
       15.  KICK OFF
    ───────────────────────────────────────────────────────── */

    loadQuestion();

}); // end DOMContentLoaded
