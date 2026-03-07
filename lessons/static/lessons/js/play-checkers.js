/* =========================================================
   play-checkers.js  —  Per-mode answer validation
   Each function returns true/false (no side effects).
   ========================================================= */

import { D } from './play-dom.js';
import { clean, isTypedAnswerCorrect } from './play-helpers.js';

/* ── 9a. MC check ── */
export function checkMC(q) {
    const selected = D.mcGrid.querySelector('.mc-btn.selected');
    return selected && clean(selected.dataset.value) === clean(q.answer);
}

/* ── 9b. Type check ── */
export function checkTyped(q) {
    return isTypedAnswerCorrect(D.answerInput.value, q);
}

/* ── 9c. Fill-blank check ── */
export function checkFillBlank(q) {
    const selected = D.fillWordBank.querySelector('.word-tile.in-answer');
    if (!selected) return false;
    return clean(selected.dataset.value) === clean(q.answer);
}

/* ── 9d. Sort check ── */
export function checkSort(q) {
    const placed = Array.from(D.sortAnswerZone.querySelectorAll('.word-tile'))
        .map(t => t.dataset.word);

    // q.answer is the ordered array of correct chunks
    const expected = Array.isArray(q.answer) ? q.answer : [q.answer];

    if (placed.length !== expected.length) return false;
    return placed.every((w, i) => clean(w) === clean(expected[i]));
}
