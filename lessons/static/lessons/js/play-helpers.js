/* =========================================================
   play-helpers.js  —  Pure utility & shared UI helpers
   ========================================================= */

import { S } from './play-state.js';
import { D } from './play-dom.js';

/** Hide all four mode containers */
export function hideAllModes() {
    D.mcContainer.style.display        = 'none';
    D.typeContainer.style.display      = 'none';
    D.fillBlankContainer.style.display = 'none';
    D.sortContainer.style.display      = 'none';
}

/** Strip punctuation and whitespace for loose comparison */
export function clean(str) {
    return String(str).toLowerCase().replace(/[\s\u3000\.,。!?！？;:\/（）()\-]/g, '');
}

/** Levenshtein similarity 0–1 */
export function similarity(a, b) {
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
export function isTypedAnswerCorrect(userRaw, q) {
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
export function setCheckEnabled(enabled) {
    D.btnCheck.disabled = !enabled;
}

/** Update progress bar and counter */
export function updateProgress() {
    const pct = (S.currentIndex / S.questions.length) * 100;
    D.progressBar.style.width = pct + '%';
    D.progressText.textContent = (S.currentIndex + 1) + ' / ' + S.questions.length;
}
