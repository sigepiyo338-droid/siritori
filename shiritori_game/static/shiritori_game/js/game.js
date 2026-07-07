document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const gameLoading = document.getElementById('game-loading');
    const gamePlayArea = document.getElementById('game-play-area');
    const questionCard = document.getElementById('question-card');
    const currentImage = document.getElementById('current-image');
    const currentReadingElement = document.getElementById('current-reading');
    const nextStartLetterElement = document.getElementById('next-start-letter');
    
    const choicesContainer = document.getElementById('choices-container');
    const errorMessage = document.getElementById('error-message');
    
    const scoreVal = document.getElementById('current-score');
    const comboVal = document.getElementById('current-combo');
    const currentLife = document.getElementById('current-life');
    
    const gameOverScreen = document.getElementById('game-over-screen');
    const gameOverReason = document.getElementById('game-over-reason');
    const finalScore = document.getElementById('final-score');
    const finalCombo = document.getElementById('final-combo');
    const restartBtn = document.getElementById('restart-btn');
    const gameOverHomeBtn = document.getElementById('game-over-home-btn');
    
    const gameClearScreen = document.getElementById('game-clear-screen');
    const clearScore = document.getElementById('clear-score');
    const clearRestartBtn = document.getElementById('clear-restart-btn');
    const gameClearHomeBtn = document.getElementById('game-clear-home-btn');
    
    const historySection = document.getElementById('history-section');
    const historyTimeline = document.getElementById('history-timeline');

    // Menu screen elements
    const gameMenu = document.getElementById('game-menu');
    const startGameBtn = document.getElementById('start-game-btn');
    const abortGameBtn = document.getElementById('abort-game-btn');

    // Game variables
    let allImages = [];         // APIから取得したすべての画像データ
    let usedImageIds = new Set(); // 使用済みの画像ID
    let currentImgData = null;  // 現在のお題画像データ
    let currentWord = '';       // 現在のお題の単語（ひらがな）
    let score = 0;
    let combo = 0;
    let maxCombo = 0;
    let lives = 3;
    let maxLives = 3;
    let correctChoice = null;   // 次の正解となる画像データ
    let correctReading = '';    // 正解の読み方
    let questionLimit = 0;      // 出題上限数（0は無制限）
    let currentQuestionCount = 0; // 現在の問題数（1から開始）
    let karutaMode = false;     // かるたモードフラグ

    // ひらがな平滑化のためのマッピング
    const smallToLarge = {
        'ぁ': 'あ', 'ぃ': 'い', 'ぅ': 'う', 'ぇ': 'え', 'ぉ': 'お',
        'っ': 'つ', 'ゃ': 'や', 'ゅ': 'ゆ', 'ょ': 'よ', 'ゎ': 'わ'
    };
    
    const voicedToClear = {
        'が': 'か', 'ぎ': 'き', 'ぐ': 'く', 'げ': 'け', 'ご': 'こ',
        'ざ': 'さ', 'じ': 'し', 'ず': 'す', 'ぜ': 'せ', 'ぞ': 'そ',
        'だ': 'た', 'ぢ': 'ち', 'づ': 'つ', 'で': 'て', 'ど': 'と',
        'ば': 'は', 'び': 'ひ', 'ぶ': 'ふ', 'べ': 'へ', 'ぼ': 'ほ',
        'ぱ': 'は', 'ぴ': 'ひ', 'ぷ': 'ふ', 'ぺ': 'へ', 'ぽ': 'ほ',
        'ゔ': 'う'
    };

    // 文字の正規化（小文字→大文字、濁音→清音）
    function normalizeLetter(char) {
        if (!char) return '';
        let c = smallToLarge[char] || char;
        c = voicedToClear[c] || c;
        return c;
    }

    // 単語の最後のつなぎ文字を取得
    function getNextRequiredLetter(word) {
        if (!word) return '';
        let lastChar = word.slice(-1);
        if (lastChar === 'ー' && word.length > 1) {
            lastChar = word.slice(-2, -1);
        }
        
        // 「ん」で終わる単語を許可する設定がONの場合、そのまま「ん」を返す
        const allowNn = localStorage.getItem('shiritori_allow_nn') === 'true';
        if (allowNn && normalizeLetter(lastChar) === 'ん') {
            return 'ん';
        }
        
        return normalizeLetter(lastChar);
    }

    // かるたモード用：未使用の画像から次のターゲット文字をランダムで選択する
    function getKarutaNextLetter() {
        const availableLetters = allImages
            .filter(img => !usedImageIds.has(img.id))
            .flatMap(img => img.readings.map(r => normalizeLetter(r.reading.charAt(0))));
        
        const uniqueLetters = [...new Set(availableLetters)];
        if (uniqueLetters.length === 0) return '';
        
        return uniqueLetters[Math.floor(Math.random() * uniqueLetters.length)];
    }

    // 初期データのロード
    async function loadGameData() {
        try {
            // フィルター設定を取得
            const includeUnapproved = localStorage.getItem('shiritori_include_unapproved') === 'true';

            let apiUrl = window.SHIRITORI_API_BASE || '/shiritori/api/images/';
            const params = new URLSearchParams();
            if (includeUnapproved) {
                params.append('include_unapproved_others', 'true');
            }
            
            const response = await fetch(`${apiUrl}?${params.toString()}`);
            if (!response.ok) {
                throw new Error('APIデータの取得に失敗しました');
            }
            allImages = await response.json();
            
            // 画像の差し替え（キャッシュ）対策としてURLにキャッシュバスターを付与
            const cacheBuster = Date.now();
            allImages.forEach(img => {
                if (img.image_url) {
                    img.image_url = `${img.image_url}?cb=${cacheBuster}`;
                }
            });
            
            if (allImages.length === 0) {
                showError('条件に一致する画像が登録されていません。画像を投稿するか、出題設定を変更してください。');
                return;
            }
            
            startGame();
        } catch (error) {
            console.error(error);
            showError('接続エラーが発生しました。リロードしてください。');
        }
    }

    function showError(msg) {
        gameLoading.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="font-size:3rem; color:var(--error-color)"></i><p>${msg}</p>`;
    }

    // ライフ表示の更新
    function renderLives() {
        currentLife.innerHTML = '';
        for (let i = 0; i < maxLives; i++) {
            const heart = document.createElement('i');
            heart.className = 'fa-solid fa-heart life-heart';
            if (i >= lives) {
                heart.classList.add('lost');
            }
            currentLife.appendChild(heart);
        }
    }

    // ゲーム開始
    function startGame() {
        score = 0;
        combo = 0;
        maxCombo = 0;
        
        // ローカルストレージから設定を読み込む
        maxLives = parseInt(localStorage.getItem('shiritori_max_lives') || '3', 10);
        lives = maxLives;
        questionLimit = parseInt(localStorage.getItem('shiritori_question_limit') || '0', 10);
        karutaMode = localStorage.getItem('shiritori_karuta_mode') === 'true';
        currentQuestionCount = 1;
        
        usedImageIds.clear();
        historyTimeline.innerHTML = '';
        
        scoreVal.textContent = score;
        comboVal.textContent = combo;
        renderLives();

        // UI表示の切り替え
        gameLoading.classList.add('hidden');
        gameOverScreen.classList.add('hidden');
        gameClearScreen.classList.add('hidden');
        gamePlayArea.classList.remove('hidden');
        historySection.classList.remove('hidden');

        // 最初のお題をセット（ランダム）
        // 1問目は「ん」で終わらない画像を優先する
        const validStartImages = allImages.filter(img => {
            const firstReadingObj = img.readings[0];
            const firstReading = firstReadingObj ? firstReadingObj.reading : '';
            return firstReading && firstReading.slice(-1) !== 'ん';
        });

        const candidateImages = validStartImages.length > 0 ? validStartImages : allImages;
        const startIndex = Math.floor(Math.random() * candidateImages.length);
        const startImg = candidateImages[startIndex];
        
        setNewQuestion(startImg, startImg.readings[0]);
    }

    // 新しいお題を画面にセット
    function setNewQuestion(imgData, readingObj) {
        currentImgData = imgData;
        currentWord = readingObj.reading;
        usedImageIds.add(imgData.id);

        const displayName = readingObj.display_name || readingObj.reading;

        // フェードアウトしてから画像切り替えするアニメーション
        questionCard.style.opacity = 0;
        
        setTimeout(() => {
            currentImage.src = imgData.image_url;
            currentImage.alt = displayName;
            currentReadingElement.textContent = displayName;
            
            // かるたモードならランダム、通常モードなら語尾を取得
            const nextLetter = karutaMode ? getKarutaNextLetter() : getNextRequiredLetter(readingObj.reading);
            nextStartLetterElement.textContent = nextLetter.toUpperCase();
            
            questionCard.style.opacity = 1;
            errorMessage.textContent = '';
            
            // 次の選択肢を生成
            generateChoices(nextLetter);

            // 履歴に追加
            addHistoryItem(imgData, readingObj, nextLetter);
        }, 150);
    }

    // 選択肢の生成
    function generateChoices(nextLetter) {
        choicesContainer.innerHTML = '';
        
        // 1. 正解となる画像を未使用の中から探す
        const correctCandidates = allImages.filter(img => 
            !usedImageIds.has(img.id) &&
            img.readings.some(r => normalizeLetter(r.reading.charAt(0)) === nextLetter)
        );

        // 正解候補がない場合はゲームクリア！
        if (correctCandidates.length === 0) {
            endGame(true);
            return;
        }

        // 正解を1つ選出
        correctChoice = correctCandidates[Math.floor(Math.random() * correctCandidates.length)];
        
        // 正解となる読み方オブジェクトを特定（つなぎ文字から始まるもの）
        correctReadingObj = correctChoice.readings.find(r => normalizeLetter(r.reading.charAt(0)) === nextLetter);
        correctReading = correctReadingObj;

        // 2. ダミーの選択肢（正解以外の画像）を最大3つ選ぶ
        // ダミーの条件: 正解画像ではなく、かつ現在のお題のつなぎ文字から始まらないもの（使用済み画像もダミーに含める）
        const dummyCandidates = allImages.filter(img => 
            img.id !== correctChoice.id &&
            !img.readings.some(r => normalizeLetter(r.reading.charAt(0)) === nextLetter)
        );

        // ランダムにシャッフルして最大8つ（3x3マス用）選ぶ
        const shuffledDummies = shuffleArray([...dummyCandidates]);
        // 候補が8つ未満の場合はある分だけすべて使う
        const dummyCount = Math.min(8, shuffledDummies.length);
        const dummies = shuffledDummies.slice(0, dummyCount);

        // 3. 正解とダミーを結合してシャッフル
        const choiceList = shuffleArray([correctChoice, ...dummies]);

        // 4. 画面上に描画
        choiceList.forEach(imgData => {
            const card = document.createElement('div');
            card.className = 'choice-card';
            card.innerHTML = `<img src="${imgData.image_url}" alt="選択肢">`;
            
            card.addEventListener('click', () => handleChoiceClick(imgData));
            choicesContainer.appendChild(card);
        });
    }

    // 配列のランダムシャッフル
    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    // 選択肢クリック時の処理
    function handleChoiceClick(clickedImgData) {
        if (!correctChoice) return;

        if (clickedImgData.id === correctChoice.id) {
            // 正解の場合
            combo++;
            if (combo > maxCombo) {
                maxCombo = combo;
            }
            score += 100 + (combo * 10);
            
            scoreVal.textContent = score;
            comboVal.textContent = combo;

            // スコア加算時の演出
            const scoreBox = document.getElementById('score-box');
            scoreBox.style.transform = 'scale(1.1)';
            setTimeout(() => scoreBox.style.transform = 'scale(1)', 200);

            // しりとりルール：「ん」で終わる単語を選んでしまった場合はゲームオーバー（許可設定OFFのときのみ）
            const lastLetter = correctReading.reading.slice(-1);
            const resolvedName = correctReading.display_name || correctReading.reading;
            const allowNn = localStorage.getItem('shiritori_allow_nn') === 'true';
            if (lastLetter === 'ん' && !allowNn) {
                setTimeout(() => {
                    endGame(false, `「${resolvedName}」の最後が「ん」で終わってしまいました！`);
                }, 300);
                return;
            }

            // 出題上限に達しているか判定
            const isFinal = questionLimit > 0 && currentQuestionCount >= questionLimit;

            // 正解ポップアップを表示
            showCorrectAnswerPopup(correctChoice, correctReading, isFinal);
        } else {
            // 不正解（お手つき）の場合
            combo = 0;
            comboVal.textContent = combo;
            lives--;
            renderLives();

            errorMessage.textContent = 'ちがう画像だよ！もういちど選んでね。';

            // お手つき時の画面揺れアニメーション
            gamePlayArea.classList.add('shake');
            setTimeout(() => {
                gamePlayArea.classList.remove('shake');
            }, 400);

            // ライフが0になったらゲームオーバー
            if (lives <= 0) {
                setTimeout(() => {
                    endGame(false, 'ライフがなくなってしまいました！');
                }, 300);
            }
        }
    }

    // 正解ポップアップの表示と次の問題への進行
    function showCorrectAnswerPopup(imgData, readingObj, isFinal = false) {
        const popup = document.getElementById('correct-answer-popup');
        const overlay = document.getElementById('popup-overlay');
        const popupImg = document.getElementById('popup-image');
        const popupReading = document.getElementById('popup-reading');
        const popupSubmitter = document.getElementById('popup-submitter');
        const popupRemarks = document.getElementById('popup-remarks');
        const popupOkBtn = document.getElementById('popup-ok-btn');

        const resolvedName = readingObj.display_name || readingObj.reading;

        if (!popup) {
            // もしポップアップ要素がなければそのまま次へ進む
            if (isFinal) {
                endGame(true);
            } else {
                currentQuestionCount++;
                setNewQuestion(imgData, readingObj);
            }
            return;
        }

        popupImg.src = imgData.image_url;
        popupReading.textContent = resolvedName;
        if (popupSubmitter && imgData.submitter_name) {
            popupSubmitter.textContent = "投稿者: " + imgData.submitter_name + " さん";
        } else if (popupSubmitter) {
            popupSubmitter.textContent = "";
        }
        
        if (imgData.remarks) {
            popupRemarks.textContent = imgData.remarks;
            popupRemarks.style.display = 'block';
        } else {
            popupRemarks.textContent = '';
            popupRemarks.style.display = 'none';
        }

        popup.classList.remove('hidden');
        overlay.classList.remove('hidden');

        const handleOkClick = () => {
            popup.classList.add('hidden');
            overlay.classList.add('hidden');
            popupOkBtn.removeEventListener('click', handleOkClick);
            if (isFinal) {
                endGame(true);
            } else {
                currentQuestionCount++;
                setNewQuestion(imgData, readingObj);
            }
        };
        
        popupOkBtn.addEventListener('click', handleOkClick);
    }

    // 履歴アイテムの作成
    function addHistoryItem(imgData, readingObj, nextLetter) {
        const item = document.createElement('div');
        item.className = 'history-item';
        
        const resolvedName = readingObj.display_name || readingObj.reading;
        
        item.innerHTML = `
            <div class="history-left">
                <div class="history-img-wrapper">
                    <img src="${imgData.image_url}" alt="${resolvedName}">
                </div>
                <div class="history-word-info">
                    <span class="history-kana">${resolvedName}</span>
                </div>
            </div>
            <div class="history-right">
                → ${nextLetter.toUpperCase()}
            </div>
        `;
        
        historyTimeline.insertBefore(item, historyTimeline.firstChild);
    }

    // ゲーム終了（ゲームオーバーまたはクリア）
    function endGame(isClear, reason = '') {
        gamePlayArea.classList.add('hidden');
        
        if (isClear) {
            gameClearScreen.classList.remove('hidden');
            clearScore.textContent = score;
        } else {
            gameOverScreen.classList.remove('hidden');
            gameOverReason.textContent = reason;
            finalScore.textContent = score;
            finalCombo.textContent = maxCombo;
        }
    }

    // ボタンイベント
    restartBtn.addEventListener('click', startGame);
    clearRestartBtn.addEventListener('click', startGame);
    
    // トップに戻る・中止機能
    function returnToHome() {
        gamePlayArea.classList.add('hidden');
        gameOverScreen.classList.add('hidden');
        gameClearScreen.classList.add('hidden');
        historySection.classList.add('hidden');
        gameMenu.classList.remove('hidden');
    }
    
    abortGameBtn.addEventListener('click', returnToHome);
    gameOverHomeBtn.addEventListener('click', returnToHome);
    gameClearHomeBtn.addEventListener('click', returnToHome);

    // ゲーム開始ボタンのクリックイベント
    startGameBtn.addEventListener('click', () => {
        gameMenu.classList.add('hidden');
        gameLoading.classList.remove('hidden');
        loadGameData();
    });
});
