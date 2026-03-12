/* =========================================================
   play-hearts.js  —  Global hearts (lives) system
   7 hearts shared across all levels, stored in localStorage.
   Losing all 7 triggers the game-over overlay.
   ========================================================= */

import { D } from './play-dom.js';

export const MAX_HEARTS  = 7;
const STORAGE_KEY        = 'jp_learn_hearts';

export function getHearts() {
    const val = parseInt(localStorage.getItem(STORAGE_KEY), 10);
    return (isNaN(val) || val < 0) ? MAX_HEARTS : Math.min(val, MAX_HEARTS);
}

export function setHearts(n) {
    localStorage.setItem(STORAGE_KEY, String(Math.max(0, n)));
}

export function resetHearts() {
    setHearts(MAX_HEARTS);
}

/** Lose one heart; returns remaining count */
export function loseHeart() {
    const h = Math.max(0, getHearts() - 1);
    setHearts(h);
    return h;
}

/** Re-render the compact hearts badge in the nav bar */
export function updateHeartsDisplay() {
    const el = D.heartsEl;
    if (!el) return;
    const current = getHearts();
    el.innerHTML = `<span class="heart-emoji">❤️</span><span class="heart-count">${current}</span>`;
    el.classList.toggle('zero-hearts', current === 0);
}

/** Animate the badge when a heart is lost */
export function animateLostHeart() {
    updateHeartsDisplay();
    const el = D.heartsEl;
    if (!el) return;
    el.classList.remove('shake-heart');
    void el.offsetWidth;
    el.classList.add('shake-heart');
    setTimeout(() => el.classList.remove('shake-heart'), 450);
}

/** Show the game-over overlay */
export function showGameOver() {
    if (D.gameOverScreen) {
        D.gameOverScreen.style.display = 'flex';
    }
}

/** Hide the game-over overlay */
export function hideGameOver() {
    if (D.gameOverScreen) {
        D.gameOverScreen.style.display = 'none';
    }
}
