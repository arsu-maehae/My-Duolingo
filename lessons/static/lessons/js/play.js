document.addEventListener('DOMContentLoaded', function() {
    // 1. ดึงข้อมูลคำศัพท์ที่ Django โยนมาให้
    const questionsElement = document.getElementById('questions-data');
    if (!questionsElement) return; // ถ้าหาข้อมูลไม่เจอให้หยุดทำงาน (กัน Error)
    
    const questions = JSON.parse(questionsElement.textContent);
    
    // ตัวแปรควบคุมเกม
    let currentIndex = 0;
    let score = 0;

    // ดึง Element จากหน้าเว็บมาเตรียมไว้
    const jpText = document.getElementById('jp-text');
    const jpReading = document.getElementById('jp-reading');
    const hintBox = document.getElementById('hint-box');   // 👈 เพิ่มบรรทัดนี้
    const hintText = document.getElementById('hint-text'); // 👈 เพิ่มบรรทัดนี้
    const answerInput = document.getElementById('answer-input');
    const btnSpeak = document.getElementById('btn-speak');
    const btnCheck = document.getElementById('btn-check');
    const btnNext = document.getElementById('btn-next');
    const feedbackArea = document.getElementById('feedback-area');
    const progressText = document.getElementById('progress-text');
    const quizCard = document.getElementById('quiz-card');
    const resultScreen = document.getElementById('result-screen');
    const finalScore = document.getElementById('final-score');

    // ฟังก์ชัน: โหลดคำถามขึ้นหน้าจอ
    function loadQuestion() {
        const currentQ = questions[currentIndex];
        jpText.textContent = currentQ.jp_text;
        
        // 🪄 ใช้ WanaKana แปลงฮิรางานะ (เช่น はな) ให้เป็น โรมาจิ (เช่น hana)
        const hiraganaReading = currentQ.jp_reading;
        const romajiReading = wanakana.toRomaji(hiraganaReading);
        
        // เอามาโชว์คู่กันไปเลย! ขุนแผนจะได้จำได้ทั้งสองแบบ เช่น はな (hana)
        jpReading.textContent = `${hiraganaReading} (${romajiReading})`;

        answerInput.value = '';
        answerInput.disabled = false;
        answerInput.focus(); 
        
        feedbackArea.classList.add('d-none');
        btnCheck.classList.remove('d-none');
        btnNext.classList.add('d-none');
        progressText.textContent = `${currentIndex + 1}/${questions.length}`;
    }

    // ฟังก์ชัน: ให้คอมพิวเตอร์อ่านออกเสียงภาษาญี่ปุ่น
    function playAudio() {
        const textToSpeak = questions[currentIndex].jp_text; 
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.lang = 'ja-JP'; 
        window.speechSynthesis.speak(utterance);
    }

    // ฟังก์ชัน: ตรวจคำตอบ
    function checkAnswer() {
        const currentQ = questions[currentIndex];
        const userAnswer = answerInput.value.trim().toLowerCase();
        
        // 🧠 ฟังก์ชันช่วยแยกคำตอบ: ตัดลูกน้ำและตัดข้อความในวงเล็บทิ้ง
        function getPossibleAnswers(text) {
            if (!text) return [];
            let cleanText = text.replace(/\(.*?\)/g, '').replace(/（.*?）/g, '');
            let parts = cleanText.split(/,|;/);
            return parts.map(p => p.trim().toLowerCase()).filter(p => p.length > 0);
        }

        const validThAnswers = getPossibleAnswers(currentQ.th_meaning);
        const validEnAnswers = getPossibleAnswers(currentQ.en_meaning);
        const allValidAnswers = [...validThAnswers, ...validEnAnswers];

        answerInput.disabled = true; 
        btnCheck.classList.add('d-none'); 
        btnNext.classList.remove('d-none'); 
        feedbackArea.classList.remove('d-none', 'alert-success', 'alert-danger');

        // 🎯 ตรวจคำตอบแบบ "ใจดีขึ้น" (อนุโลมให้พิมพ์แค่บางส่วนได้)
        const isCorrect = allValidAnswers.some(valid => {
            // 1. ตรงกันเป๊ะๆ
            if (valid === userAnswer) return true;
            // 2. พิมพ์มาเป็นส่วนหนึ่งของเฉลย (เช่น "เยี่ยม" ซ่อนอยู่ใน "เรียกหา เยี่ยมชม")
            // (บังคับว่าต้องพิมพ์มาอย่างน้อย 2 ตัวอักษร เพื่อป้องกันการกดมั่วแค่ตัวอักษรเดียวแล้วฟลุ๊คถูก)
            if (valid.includes(userAnswer) && userAnswer.length >= 2) return true;
            
            return false;
        });

        if (isCorrect) {
            feedbackArea.classList.add('alert-success');
            feedbackArea.innerHTML = '<strong><i class="fas fa-check-circle"></i> ถูกต้อง!</strong>';
            score++;
        } else {
            feedbackArea.classList.add('alert-danger');
            feedbackArea.innerHTML = `
                <strong><i class="fas fa-times-circle"></i> ผิด!</strong><br>
                <div class="mt-2 text-start" style="font-size: 1.1em;">
                    <p class="mb-1 text-dark"><b>ความหมาย:</b> ${currentQ.th_meaning || '-'}</p>
                    <p class="mb-0 text-muted"><b>meaning:</b> ${currentQ.en_meaning || '-'}</p>
                </div>
            `;
        }
    }

    // ฟังก์ชัน: เปลี่ยนไปข้อถัดไป
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

    // ผูกปุ่มเข้ากับฟังก์ชันต่างๆ
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

    // 🪄 เอฟเฟกต์กล่องคำใบ้ (เอาเมาส์ชี้/เอาออก)
    hintBox.addEventListener('mouseenter', function() {
        hintText.style.opacity = '0';  // ซ่อนข้อความ "เอาเมาส์ชี้..."
        jpReading.style.opacity = '1'; // โชว์คำอ่าน
    });

    hintBox.addEventListener('mouseleave', function() {
        hintText.style.opacity = '1';  // โชว์ข้อความ "เอาเมาส์ชี้..." กลับมา
        jpReading.style.opacity = '0'; // ซ่อนคำอ่าน
    });


    // สั่งเริ่มเกมทันทีที่เปิดหน้าเว็บ!
    if (questions.length > 0) {
        loadQuestion();
        setTimeout(playAudio, 500);
    }
});