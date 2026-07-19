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

    // CSRFトークンをCookieから取得する
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // 正解をサーバーに記録する
    async function recordReadingCompletion(readingId) {
        if (!window.SHIRITORI_USER_ID || window.SHIRITORI_IS_GUEST) {
            // 未ログインまたはゲストユーザーの場合は記録しない
            return;
        }

        try {
            const recordUrl = window.SHIRITORI_RECORD_API || '/shiritori/api/record-correct/';
            const response = await fetch(recordUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ reading_id: readingId })
            });

            if (!response.ok) {
                console.error('正解の記録に失敗しました');
            }
        } catch (error) {
            console.error('記録リクエストエラー:', error);
        }
    }

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
            
            const nextLetter = getNextRequiredLetter(readingObj.reading);
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

        // 2. ダミーの選択肢（正解以外の画像）を最大8つ選ぶ
        // ダミーの条件: 正解画像以外のすべての画像
        // ※ただし「すでに使用済み」かつ「今回の正解の文字から始まる」画像はプレイヤーの罠になるため除外する
        const dummyCandidates = allImages.filter(img => {
            if (img.id === correctChoice.id) return false;
            
            const isUsed = usedImageIds.has(img.id);
            const canConnect = img.readings.some(r => normalizeLetter(r.reading.charAt(0)) === nextLetter);
            
            return !(isUsed && canConnect);
        });

        // ランダムにシャッフルして最大8つ（3x3マス用）選ぶ
        const shuffledDummies = shuffleArray([...dummyCandidates]);
        // 候補が8つ未満の場合はある分だけすべて使う
        const dummyCount = Math.min(8, shuffledDummies.length);
        const dummies = shuffledDummies.slice(0, dummyCount);

        // 3. 正解とダミーを結合してシャッフル
        const choiceList = shuffleArray([correctChoice, ...dummies]);

        // 4. 画面上に描画
        const numpadMap = [7, 8, 9, 4, 5, 6, 1, 2, 3];
        choiceList.forEach((imgData, index) => {
            const card = document.createElement('div');
            card.className = 'choice-card';
            const numKey = numpadMap[index] !== undefined ? numpadMap[index] : (index + 1);
            
            card.innerHTML = `
                <img src="${imgData.image_url}" alt="選択肢">
                <span class="shortcut-key-hint">${numKey}</span>
            `;
            
            card.addEventListener('click', () => handleChoiceClick(imgData));
            choicesContainer.appendChild(card);
        });

        // お助け（自動正解）ボタンの追加
        const hintBtn = document.createElement('div');
        hintBtn.className = 'choice-card hint-btn';
        if (lives <= 1) {
            hintBtn.classList.add('disabled');
        }
        hintBtn.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <span style="font-weight: 700; color: var(--accent-purple); font-size: 1.1rem;"><i class="fa-solid fa-wand-magic-sparkles"></i> お助けパス</span>
                <span style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.2rem;">（ライフを1消費）</span>
            </div>
            <span class="shortcut-key-hint">0</span>
        `;
        hintBtn.addEventListener('click', () => {
            if (lives > 1 && !hintBtn.classList.contains('disabled')) {
                handleHintClick();
            }
        });
        choicesContainer.appendChild(hintBtn);
    }

    // 配列のランダムシャッフル
    function shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    // お助け（自動正解）クリック時の処理
    function handleHintClick() {
        if (lives <= 1 || !correctChoice) return;
        
        // ライフ減少
        lives--;
        renderLives();
        
        // コンボリセット（スコア加算なし）
        combo = 0;
        comboVal.textContent = combo;
        
        // 正解記録を送信
        if (correctReading) {
            recordReadingCompletion(correctReading.id);
        }
        
        // 正解表示へ進む
        const isFinal = questionLimit > 0 && currentQuestionCount >= questionLimit;
        showCorrectAnswerPopup(correctChoice, correctReading, isFinal);
    }

    // 選択肢クリック時の処理
    function handleChoiceClick(clickedImgData) {
        if (!correctChoice) return;

        const nextLetter = getNextRequiredLetter(currentWord);
        const validReadingObj = clickedImgData.readings.find(r => normalizeLetter(r.reading.charAt(0)) === nextLetter);

        if (validReadingObj) {
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
            const lastLetter = validReadingObj.reading.slice(-1);
            const resolvedName = validReadingObj.display_name || validReadingObj.reading;
            const allowNn = localStorage.getItem('shiritori_allow_nn') === 'true';
            if (lastLetter === 'ん' && !allowNn) {
                setTimeout(() => {
                    endGame(false, `「${resolvedName}」の最後が「ん」で終わってしまいました！`);
                }, 300);
                return;
            }

            // 出題上限に達しているか判定
            const isFinal = questionLimit > 0 && currentQuestionCount >= questionLimit;

            // 正解記録を送信
            recordReadingCompletion(validReadingObj.id);

            // 正解ポップアップを表示
            showCorrectAnswerPopup(clickedImgData, validReadingObj, isFinal);
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

    startGameBtn.addEventListener('click', () => {
        gameMenu.classList.add('hidden');
        gameLoading.classList.remove('hidden');
        loadGameData();
    });

    // キーボードショートカット（1〜9キー、テンキー）で選択肢を選ぶ
    document.addEventListener('keydown', (e) => {
        // 入力フォーム等にフォーカスがある場合は無視
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        const popup = document.getElementById('correct-answer-popup');
        
        // ポップアップ表示中の場合
        if (popup && !popup.classList.contains('hidden')) {
            // Enterキーで「OK」ボタンを押したことにする
            if (e.key === 'Enter') {
                const okBtn = document.getElementById('popup-ok-btn');
                if (okBtn) okBtn.click();
            }
            return; // ポップアップ中は他のショートカットを無効化
        }

        // ゲーム画面が非表示の場合は無視
        if (gamePlayArea.classList.contains('hidden')) {
            return;
        }

        const cards = choicesContainer.querySelectorAll('.choice-card:not(.hint-btn)');
        if (cards.length === 0) return;

        let index = -1;
        const key = e.key;
        
        // 「0」またはテンキーの「0」でお助けボタンを発動
        if (key === '0' || e.code === 'Numpad0') {
            const hintBtn = choicesContainer.querySelector('.hint-btn');
            if (hintBtn && !hintBtn.classList.contains('disabled')) {
                hintBtn.click();
            }
            return;
        }

        // テンキーまたは上部の数字キー (1〜9)
        if (['1', '2', '3', '4', '5', '6', '7', '8', '9'].includes(key)) {
            // Numpadの配置に合わせたマッピング
            if (e.code.startsWith('Numpad')) {
                const map = {
                    '7': 0, '8': 1, '9': 2,
                    '4': 3, '5': 4, '6': 5,
                    '1': 6, '2': 7, '3': 8
                };
                index = map[key];
            } else {
                // 上部数字キーの場合は 1〜9 をそのまま 0〜8 のインデックスに
                index = parseInt(key, 10) - 1;
            }
        }
        
        if (index >= 0 && index < cards.length) {
            cards[index].click();
        }
    });
});
