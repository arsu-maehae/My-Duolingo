/* =========================================================
   play-state.js  —  Shared mutable game state
   Exported as a single object S so all modules see the
   same live reference when properties are mutated.
   ========================================================= */

export const S = {
    questions:    [],   // populated once data is bootstrapped
    levelId:      0,
    currentIndex: 0,
    score:        0,
    attempts:     0,    // resets each question
    answered:     false,
};
