/* =========================================================
   play-renderers.js  —  Mode-specific UI renderers
   Handles: multiple_choice | type_answer | fill_blank | sort_sentence
   ========================================================= */

import { S } from './play-state.js';
import { D } from './play-dom.js';
import { setCheckEnabled } from './play-helpers.js';

/* ── 8a. Multiple Choice ── */
export function renderMC(q) {
    D.modeLabel.textContent = 'เลือกคำตอบที่ถูกต้อง';
    D.mcContainer.style.display = 'block';
    D.mcGrid.innerHTML = '';

    const letters = ['A', 'B', 'C', 'D'];
    q.choices.forEach(function (choice, idx) {
        const btn = document.createElement('button');
        btn.className     = 'mc-btn';
        btn.dataset.value = choice;
        btn.dataset.letter = letters[idx] || String(idx + 1);

        const letterSpan = document.createElement('span');
        letterSpan.className   = 'mc-btn-letter';
        letterSpan.textContent = letters[idx] || String(idx + 1);

        const textSpan = document.createElement('span');
        textSpan.className   = 'mc-btn-text';
        textSpan.textContent = choice;

        btn.appendChild(letterSpan);
        btn.appendChild(textSpan);

        btn.addEventListener('click', function () {
            if (S.answered) return;
            D.mcGrid.querySelectorAll('.mc-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            setCheckEnabled(true);
        });

        D.mcGrid.appendChild(btn);
    });

    setCheckEnabled(false);
}

/* ── 8b. Type Answer ── */
export function renderTypeAnswer(q) {
    D.modeLabel.textContent = 'พิมพ์คำแปลภาษาไทย';
    D.typeContainer.style.display = 'block';
    D.answerInput.value    = '';
    D.answerInput.disabled = false;
    D.answerInput.className = '';  // clear correct/incorrect classes
    D.answerInput.focus();
    setCheckEnabled(false);

    // Enable check when there's input
    D.answerInput.oninput = function () {
        setCheckEnabled(D.answerInput.value.trim().length > 0 && !S.answered);
    };
}

/* ── 8c. Fill in the Blank ── */
export function renderFillBlank(q) {
    D.modeLabel.textContent = 'เติมคำให้สมบูรณ์';
    D.fillBlankContainer.style.display = 'block';
    D.fillWordBank.innerHTML = '';

    // Build Thai sentence display with styled blank
    const raw = q.th_sentence || '';
    const parts = raw.split('___');
    D.fillSentenceEl.innerHTML = '';
    if (parts.length >= 2) {
        D.fillSentenceEl.appendChild(document.createTextNode(parts[0]));
        const span = document.createElement('span');
        span.className = 'blank-slot';
        span.id = 'fill-blank-slot';
        span.textContent = '　　　';
        D.fillSentenceEl.appendChild(span);
        D.fillSentenceEl.appendChild(document.createTextNode(parts.slice(1).join('')));
    } else {
        D.fillSentenceEl.textContent = raw || '___';
    }

    // No extra hint shown
    D.fillThHintEl.textContent = '';

    // Word choice tiles (Thai words)
    q.choices.forEach(function (word) {
        const btn = document.createElement('button');
        btn.className     = 'word-tile';
        btn.textContent   = word;
        btn.dataset.value = word;

        btn.addEventListener('click', function () {
            if (S.answered) return;
            if (btn.classList.contains('in-answer')) {
                // Deselect
                btn.classList.remove('in-answer');
                const slot = document.getElementById('fill-blank-slot');
                if (slot) slot.textContent = '　　　';
                setCheckEnabled(false);
            } else {
                // Deselect any previously selected tile
                D.fillWordBank.querySelectorAll('.word-tile.in-answer').forEach(b => {
                    b.classList.remove('in-answer');
                });
                btn.classList.add('in-answer');
                const slot = document.getElementById('fill-blank-slot');
                if (slot) slot.textContent = word;
                setCheckEnabled(true);
            }
        });

        D.fillWordBank.appendChild(btn);
    });

    setCheckEnabled(false);
}

/* ── 8d. Sentence Sort ── */
export function renderSort(q) {
    D.modeLabel.textContent = 'เรียงคำให้ถูกต้อง';
    D.sortContainer.style.display = 'block';
    D.sortTileBank.innerHTML = '';
    D.sortAnswerZone.innerHTML = '';
    D.sortAnswerZone.classList.remove('correct', 'incorrect');

    // Hide prompt box — JP is already shown above
    document.getElementById('sort-prompt').style.display = 'none';
    D.sortPromptText.textContent = '';

    // Placeholder in answer zone
    const placeholder = document.createElement('span');
    placeholder.className   = 'placeholder-text';
    placeholder.textContent = 'แตะคำด้านล่างเพื่อวางที่นี่';
    D.sortAnswerZone.appendChild(placeholder);

    setCheckEnabled(false);

    // Build tiles (choices are pre-shuffled by the backend)
    (q.choices || []).forEach(function (word) {
        const tile = createSortTile(word);
        D.sortTileBank.appendChild(tile);
    });
}

export function createSortTile(word) {
    const tile = document.createElement('button');
    tile.className    = 'word-tile';
    tile.textContent  = word;
    tile.dataset.word = word;

    tile.addEventListener('click', function () {
        if (S.answered) return;

        if (tile.parentElement === D.sortAnswerZone) {
            // Move back to bank
            tile.classList.remove('in-answer');
            D.sortTileBank.appendChild(tile);
        } else {
            // Move to answer zone
            tile.classList.add('in-answer');
            // Remove placeholder if present
            const ph = D.sortAnswerZone.querySelector('.placeholder-text');
            if (ph) ph.remove();
            D.sortAnswerZone.appendChild(tile);
        }

        const answerCount = D.sortAnswerZone.querySelectorAll('.word-tile').length;
        setCheckEnabled(answerCount > 0 && !S.answered);
    });

    return tile;
}
