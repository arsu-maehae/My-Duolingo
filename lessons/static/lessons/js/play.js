document.addEventListener('DOMContentLoaded', function() {
    const questionsElement = document.getElementById('questions-data');
    if (!questionsElement) return; 
    
    const questions = JSON.parse(questionsElement.textContent);
    let currentIndex = 0;
    let score = 0;

    const jpText = document.getElementById('jp-text');
    const jpReading = document.getElementById('jp-reading');
    const hintBox = document.getElementById('hint-box');   
    const hintText = document.getElementById('hint-text'); 
    
    // UI Elements
    const wordInputContainer = document.getElementById('word-input-container');
    const answerInput = document.getElementById('answer-input');
    const sentenceUiContainer = document.getElementById('sentence-ui-container');
    const selectedWordsZone = document.getElementById('selected-words-zone');
    const wordBankZone = document.getElementById('word-bank-zone');
    
    const btnSpeak = document.getElementById('btn-speak');
    const btnCheck = document.getElementById('btn-check');
    const btnNext = document.getElementById('btn-next');
    const btnOverride = document.getElementById('btn-override'); 
    const feedbackArea = document.getElementById('feedback-area');
    const progressText = document.getElementById('progress-text');
    const quizCard = document.getElementById('quiz-card');
    const resultScreen = document.getElementById('result-screen');
    const finalScore = document.getElementById('final-score');

    function loadQuestion() {
        const currentQ = questions[currentIndex];
        jpText.textContent = currentQ.jp_text;
        
        // แยกการแสดงผลคำอ่าน
        if (currentQ.type === 'sentence') {
            const romajiMatch = currentQ.jp_reading.match(/\((.*?)\)/);
            if (romajiMatch) {
                jpReading.textContent = `(${romajiMatch[1]})`;
            } else {
                jpReading.textContent = currentQ.jp_reading;
            }
        } else {
            const hiraganaReading = currentQ.jp_reading;
            const romajiReading = wanakana.toRomaji(hiraganaReading);
            jpReading.textContent = `(${romajiReading})`;
        }

        // สลับ UI
        if (currentQ.type === 'sentence') {
            wordInputContainer.classList.add('d-none');
            sentenceUiContainer.classList.remove('d-none');
            setupSentenceUI(currentQ.choices);
        } else {
            sentenceUiContainer.classList.add('d-none');
            wordInputContainer.classList.remove('d-none');
            answerInput.value = '';
            answerInput.disabled = false;
            answerInput.focus(); 
        }
        
        feedbackArea.classList.add('d-none');
        btnCheck.classList.remove('d-none');
        btnNext.classList.add('d-none');
        if (btnOverride) btnOverride.classList.add('d-none'); 
        progressText.textContent = `${currentIndex + 1}/${questions.length}`;
        document.getElementById('progress-bar').style.width = `${((currentIndex) / questions.length) * 100}%`;
    }

    function setupSentenceUI(choices) {
        selectedWordsZone.innerHTML = ''; 
        wordBankZone.innerHTML = '';
        
        choices.forEach(word => {
            const btn = document.createElement('button');
            btn.className = 'btn btn-outline-secondary btn-lg rounded-pill shadow-sm';
            btn.textContent = word;
            btn.onclick = function() {
                if (btn.parentElement === selectedWordsZone) {
                    wordBankZone.appendChild(btn);
                } else {
                    selectedWordsZone.appendChild(btn);
                }
            };
            wordBankZone.appendChild(btn);
        });
    }

    function playAudio() {
        const currentQ = questions[currentIndex];
        let textToSpeak = currentQ.jp_text; 
        if (currentQ.type === 'word' && currentQ.jp_reading) {
            textToSpeak = currentQ.jp_reading;
        }
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.lang = 'ja-JP'; 
        window.speechSynthesis.speak(utterance);
    }

    function showCorrectFeedback() {
        feedbackArea.classList.remove('alert-danger');
        feedbackArea.classList.add('alert-success');
        feedbackArea.innerHTML = '<strong><i class="fas fa-check-circle"></i> ถูกต้อง!</strong>';
        if (btnOverride) btnOverride.classList.add('d-none');
        score++;
    }

    if (btnOverride) {
        btnOverride.addEventListener('click', showCorrectFeedback);
    }

    // 🌟 1. ฟังก์ชันตัวช่วยวัดระดับความเหมือน (คำนวณ 0.0 ถึง 1.0)
    function getSimilarity(str1, str2) {
        if (str1 === str2) return 1.0;
        const len1 = str1.length, len2 = str2.length;
        const maxLen = Math.max(len1, len2);
        if (maxLen === 0) return 1.0;

        let matrix = [];
        for (let i = 0; i <= len1; i++) matrix[i] = [i];
        for (let j = 0; j <= len2; j++) matrix[0][j] = j;

        for (let i = 1; i <= len1; i++) {
            for (let j = 1; j <= len2; j++) {
                const cost = str1[i - 1] === str2[j - 1] ? 0 : 1;
                matrix[i][j] = Math.min(
                    matrix[i - 1][j] + 1,      
                    matrix[i][j - 1] + 1,      
                    matrix[i - 1][j - 1] + cost 
                );
            }
        }
        return (maxLen - matrix[len1][len2]) / maxLen;
    }

    function checkAnswer() {
        const currentQ = questions[currentIndex];
        const cleanString = (str) => str.toLowerCase().replace(/[\s\.。!?,;\(\)（）]/g, '');
        
        let userAnswer = '';
        
        if (currentQ.type === 'sentence') {
            const selectedButtons = Array.from(selectedWordsZone.children);
            userAnswer = cleanString(selectedButtons.map(b => b.textContent).join(''));
            Array.from(wordBankZone.children).forEach(b => b.disabled = true);
            selectedButtons.forEach(b => b.disabled = true);
        } else {
            userAnswer = cleanString(answerInput.value);
            answerInput.disabled = true; 
        }

        const validThAnswers = currentQ.th_meaning.split(',').map(p => cleanString(p));
        const validEnAnswers = currentQ.en_meaning.split(',').map(p => cleanString(p));
        const allValidAnswers = [...validThAnswers, ...validEnAnswers];

        btnCheck.classList.add('d-none'); 
        btnNext.classList.remove('d-none'); 
        feedbackArea.classList.remove('d-none', 'alert-success', 'alert-danger');

        let isCorrect = false;

        // 🌟 2. อัปเกรดระบบตรวจคำตอบ ให้ยอมรับความคล้ายคลึง
        isCorrect = allValidAnswers.some(valid => {
            // ถ้ายืนยันตรงกัน 100% ก็ให้ผ่านเลย
            if (valid === userAnswer) return true;
            
            // หาค่าความเหมือนเป็นเปอร์เซ็นต์
            let similarityScore = getSimilarity(valid, userAnswer);
            
            // 🎯 ถ้าเป็นโหมดประโยค ขอแค่เหมือนเกิน 75% ถือว่าผ่าน! (ขาดคำว่า นี่/เป็น/อยู่ ไปบ้างก็ไม่เป็นไร)
            if (currentQ.type === 'sentence' && similarityScore >= 0.65) return true;
            
            // 🎯 ถ้าเป็นโหมดคำศัพท์เดี่ยว พิมพ์ตกหล่นได้นิดหน่อย (ยอมให้ 80%) หรือพิมพ์ถูกบางส่วน (includes) ก็ให้ผ่าน
            if (currentQ.type === 'word') {
                if (valid.includes(userAnswer) && userAnswer.length >= 2) return true;
                if (similarityScore >= 0.80) return true;
            }
            
            return false;
        });

        if (isCorrect) {
            showCorrectFeedback();
        } else {
            feedbackArea.classList.add('alert-danger');
            feedbackArea.innerHTML = `
                <strong><i class="fas fa-times-circle"></i> ผิด!</strong><br>
                <div class="mt-2 text-start" style="font-size: 1.1em;">
                    <p class="mb-1 text-dark"><b>เฉลยที่ถูกต้อง:</b> ${currentQ.th_meaning.split(',')[0]}</p>
                </div>
            `;
            if (btnOverride) btnOverride.classList.remove('d-none'); 
        }
    }

    function nextQuestion() {
        currentIndex++;
        if (currentIndex < questions.length) {
            loadQuestion(); 
        } else {
            quizCard.classList.add('d-none');
            resultScreen.classList.remove('d-none');
            finalScore.textContent = score;
        }
    }

    btnSpeak.addEventListener('click', playAudio);
    btnCheck.addEventListener('click', checkAnswer);
    btnNext.addEventListener('click', nextQuestion);
    
    answerInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            if (!btnCheck.classList.contains('d-none')) {
                checkAnswer();
            } else if (!btnNext.classList.contains('d-none')) {
                nextQuestion();
            }
        }
    });

    hintBox.addEventListener('mouseenter', function() {
        hintText.style.opacity = '0';  
        jpReading.style.opacity = '1'; 
    });

    hintBox.addEventListener('mouseleave', function() {
        hintText.style.opacity = '1';  
        jpReading.style.opacity = '0'; 
    });

    if (questions.length > 0) {
        loadQuestion();
        setTimeout(playAudio, 500);
    }
});