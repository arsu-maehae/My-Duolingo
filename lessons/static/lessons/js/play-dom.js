/* =========================================================
   play-dom.js  —  All DOM element references
   Call initDom() once inside DOMContentLoaded before any
   other module function touches the DOM.
   ========================================================= */

export const D = {};

export function initDom() {
    // Card & result
    D.quizCard      = document.getElementById('quiz-card');
    D.resultScreen  = document.getElementById('result-screen');
    D.actionBtnWrap = document.getElementById('action-btn-wrap');

    // Nav
    D.progressBar   = document.getElementById('progress-bar');
    D.progressText  = document.getElementById('progress-text');
    D.btnClosePage  = document.getElementById('btn-close-page');
    D.heartsEl      = document.getElementById('hearts-display');
    D.gameOverScreen = document.getElementById('game-over-screen');

    // Header elements inside card
    D.modeLabel     = document.getElementById('mode-label');
    D.btnSpeak      = document.getElementById('btn-speak');
    D.jpTextEl      = document.getElementById('jp-text');
    D.hintBox       = document.getElementById('hint-box');
    D.jpReadingEl   = document.getElementById('jp-reading');

    // Mode containers
    D.mcContainer        = document.getElementById('mc-container');
    D.mcGrid             = document.getElementById('mc-grid');
    D.typeContainer      = document.getElementById('type-container');
    D.answerInput        = document.getElementById('answer-input');
    D.fillBlankContainer = document.getElementById('fill-blank-container');
    D.fillSentenceEl     = document.getElementById('fill-sentence-display');
    D.fillThHintEl       = document.getElementById('fill-th-hint');
    D.fillWordBank       = document.getElementById('fill-word-bank');
    D.sortContainer      = document.getElementById('sort-container');
    D.sortPromptText     = document.getElementById('sort-prompt-text');
    D.sortAnswerZone     = document.getElementById('sort-answer-zone');
    D.sortTileBank       = document.getElementById('sort-tile-bank');

    // Feedback
    D.feedbackArea  = document.getElementById('feedback-area');
    D.fbIcon        = D.feedbackArea.querySelector('.fb-icon');
    D.fbTitle       = D.feedbackArea.querySelector('.fb-title');
    D.fbDetail      = D.feedbackArea.querySelector('.fb-detail');

    // Action buttons
    D.btnCheck      = document.getElementById('btn-check');
    D.btnNext       = document.getElementById('btn-next');

    // Result screen
    D.resultStars   = document.getElementById('result-stars');
    D.resultTitle   = document.getElementById('result-title');
    D.finalScoreEl  = document.getElementById('final-score');
    D.resultMsg     = document.getElementById('result-msg');
    D.btnRetryGame  = document.getElementById('btn-retry-game');
    D.btnFinishGame = document.getElementById('btn-finish-game');
}
