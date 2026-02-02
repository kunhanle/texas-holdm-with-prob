/**
 * Texas Hold'em Web Game - Frontend JavaScript
 * 德州撲克教學版 - 前端遊戲邏輯
 */

class PokerGame {
    constructor() {
        this.gameId = null;
        this.settings = {
            opponents: 4,
            difficulty: 'medium'
        };

        this.init();
    }

    init() {
        // 設定選項按鈕
        document.querySelectorAll('.btn-option[data-opponents]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.btn-option[data-opponents]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.settings.opponents = parseInt(btn.dataset.opponents);
            });
        });

        document.querySelectorAll('.btn-option[data-difficulty]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.btn-option[data-difficulty]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.settings.difficulty = btn.dataset.difficulty;
            });
        });

        // 開始按鈕
        document.getElementById('btn-start').addEventListener('click', () => this.startGame());

        // 動作按鈕
        document.querySelectorAll('.btn-action').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (action === 'raise' || action === 'bet') {
                    this.currentBetAction = action;
                    this.showRaiseModal();
                } else {
                    this.doAction(action);
                }
            });
        });

        // 加注 Modal
        document.getElementById('raise-slider').addEventListener('input', (e) => {
            document.getElementById('raise-amount').textContent = e.target.value;
        });
        document.getElementById('raise-cancel').addEventListener('click', () => this.hideModal('raise-modal'));
        document.getElementById('raise-confirm').addEventListener('click', () => {
            const amount = parseInt(document.getElementById('raise-slider').value);
            this.hideModal('raise-modal');
            this.doAction(this.currentBetAction || 'raise', amount);
        });

        // 下一局
        document.getElementById('next-hand').addEventListener('click', () => {
            this.hideModal('result-modal');
            this.startHand();
        });

        // 重新開始
        document.getElementById('restart-game').addEventListener('click', () => {
            this.hideModal('gameover-modal');
            document.getElementById('game-screen').classList.remove('active');
            document.getElementById('start-screen').classList.add('active');
        });

        // 鍵盤快捷鍵 (Tab 切換面板)
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Tab') {
                e.preventDefault();
                this.toggleAnalysisPanel();
            }
        });

        // 顯示面板開關提示
        this.addToggleHint();
    }

    addToggleHint() {
        const hint = document.createElement('div');
        hint.className = 'panel-toggle-hint';
        hint.textContent = '按 Tab 切換分析面板';
        document.body.appendChild(hint);
    }

    toggleAnalysisPanel() {
        const panel = document.querySelector('.analysis-panel');
        panel.classList.toggle('hidden');
    }

    async startGame() {
        try {
            const res = await fetch('/api/game/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.settings)
            });
            const data = await res.json();

            if (data.success) {
                this.gameId = data.game_id;
                document.getElementById('start-screen').classList.remove('active');
                document.getElementById('game-screen').classList.add('active');
                this.startHand();
            }
        } catch (err) {
            console.error('Failed to start game:', err);
        }
    }

    async startHand() {
        try {
            const res = await fetch('/api/game/start', { method: 'POST' });
            const state = await res.json();
            this.updateUI(state);
        } catch (err) {
            console.error('Failed to start hand:', err);
        }
    }

    async doAction(action, amount = 0) {
        try {
            const res = await fetch('/api/game/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, amount })
            });
            const state = await res.json();
            this.updateUI(state);
        } catch (err) {
            console.error('Action failed:', err);
        }
    }

    updateUI(state) {
        if (!state) return;

        // Check for error (e.g. session expired)
        if (state.error) {
            console.error('Game error:', state.error);
            if (state.error.includes('No active game')) {
                alert('遊戲連線已中斷，請重新開始');
                location.reload();
            }
            return;
        }

        // 基本資訊

        document.getElementById('hand-num').textContent = state.hand_number;
        document.getElementById('stage').textContent = this.translateStage(state.stage);

        // Handle pot display
        const potValue = (state.pot !== undefined && state.pot !== null) ? state.pot : 0;
        document.getElementById('pot').textContent = `$${potValue}`;

        // 公共牌
        this.renderCommunityCards(state.community_cards);

        // 對手
        this.renderOpponents(state.players.filter(p => !p.is_human));

        // 玩家
        const human = state.players.find(p => p.is_human);
        if (human) {
            this.renderPlayerCards(human.cards);
            document.getElementById('player-chips').textContent = `$${human.chips}`;
        }

        // 當前手牌
        document.getElementById('current-hand').textContent = state.current_hand || '';

        // 可用動作
        this.updateActions(state.available_actions);

        // 機率分析
        this.updateAnalysis(state.analysis);

        // 教學建議
        this.updateAdvice(state.advice);

        // 訊息
        this.renderMessages(state.messages);

        // 本局結果
        if (state.hand_result) {
            this.showHandResult(state.hand_result);
        }

        // 遊戲結束
        if (state.is_game_over) {
            this.showGameOver(human.chips);
        }
    }

    translateStage(stage) {
        const stages = {
            'WAITING': '等待中',
            'PRE_FLOP': '翻牌前',
            'FLOP': '翻牌',
            'TURN': '轉牌',
            'RIVER': '河牌',
            'SHOWDOWN': '攤牌',
            'FINISHED': '結束'
        };
        return stages[stage] || stage;
    }

    renderCommunityCards(cards) {
        const container = document.getElementById('community-cards');
        let html = '';

        for (let i = 0; i < 5; i++) {
            if (i < cards.length) {
                const card = cards[i];
                const isRed = card.suit === '♥' || card.suit === '♦';
                html += `
                    <div class="card face ${isRed ? 'red' : ''}">
                        <span class="rank">${card.rank}</span>
                        <span class="suit-symbol">${card.suit}</span>
                    </div>
                `;
            } else {
                html += '<div class="card placeholder"></div>';
            }
        }

        container.innerHTML = html;
    }

    renderOpponents(opponents) {
        const container = document.getElementById('opponents');

        // 設定佈局類別
        container.className = `opponents layout-${opponents.length}`;

        let html = '';

        for (let i = 0; i < opponents.length; i++) {
            const opp = opponents[i];
            const classes = ['opponent'];

            // 根據總人數和索引分配位置類別
            let posClass = 'pos-top';
            if (opponents.length === 3) {
                if (i === 0) posClass = 'pos-left';
                if (i === 1) posClass = 'pos-right';
            } else if (opponents.length === 4) {
                if (i === 0) posClass = 'pos-left';
                if (i === 1) posClass = 'pos-top';
                if (i === 2) posClass = 'pos-right';
            } else if (opponents.length === 5) {
                if (i === 0) posClass = 'pos-left';
                if (i === 1) posClass = 'pos-top-left';
                if (i === 2) posClass = 'pos-top-right';
                if (i === 3) posClass = 'pos-right';
            }
            classes.push(posClass);

            if (opp.is_current) classes.push('current');
            if (opp.is_current && opp.bet > 0) classes.push('acting');
            if (!opp.is_active) classes.push('folded');

            // 決定顯示的行動文字
            let actionText = '';
            const actionMap = {
                'fold': '棄牌',
                'check': '過牌',
                'call': '跟注',
                'bet': '下注',
                'raise': '加注',
                'all_in': 'ALL IN'
            };

            if (opp.last_action && opp.last_action !== 'fold') {
                actionText = actionMap[opp.last_action] || opp.last_action;
                // 如果是下注相關，加上金額
                if (['bet', 'call', 'raise', 'all_in'].includes(opp.last_action) && opp.current_bet > 0) {
                    actionText += ` $${opp.current_bet}`;
                }
            } else if (opp.bet > 0 && opp.is_current) {
                // 如果沒有 last_action 但正在下注（兼容舊狀態）
                actionText = `下注 $${opp.bet}`;
            }

            html += `
                <div class="${classes.join(' ')}">
                    <div class="action-indicator" style="${actionText ? 'opacity:1;transform:translateY(-50%)' : ''}">${actionText}</div>
                    <div class="name">
                        ${opp.name}
                        ${opp.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
                    </div>
                    <div class="chips">$${opp.chips}</div>
                    ${opp.bet > 0 ? `<div class="bet">下注: $${opp.bet}</div>` : ''}
                    <div class="cards">
                        ${this.renderSmallCards(opp.cards, !opp.is_active)}
                    </div>
                    ${!opp.is_active ? '<div class="status">已棄牌</div>' : ''}
                    ${opp.is_all_in ? '<div class="status" style="color:var(--accent-orange)">ALL-IN</div>' : ''}
                </div>
            `;
        }

        container.innerHTML = html;
    }

    renderSmallCards(cards, folded = false) {
        if (!cards || folded) {
            return `
                <div class="card small hidden"></div>
                <div class="card small hidden"></div>
            `;
        }

        let html = '';
        for (const card of cards) {
            const isRed = card.suit === '♥' || card.suit === '♦';
            html += `
                <div class="card small face ${isRed ? 'red' : ''}">
                    <span class="rank">${card.rank}</span>
                    <span class="suit-symbol">${card.suit}</span>
                </div>
            `;
        }
        return html;
    }

    renderPlayerCards(cards) {
        const container = document.getElementById('player-cards');
        if (!cards || cards.length === 0) {
            container.innerHTML = '';
            return;
        }

        let html = '';
        for (const card of cards) {
            const isRed = card.suit === '♥' || card.suit === '♦';
            html += `
                <div class="card face ${isRed ? 'red' : ''}">
                    <span class="rank">${card.rank}</span>
                    <span class="suit-symbol">${card.suit}</span>
                </div>
            `;
        }
        container.innerHTML = html;
    }

    updateActions(actions) {
        const allActions = ['fold', 'check', 'bet', 'call', 'raise', 'all_in'];

        for (const action of allActions) {
            const btn = document.querySelector(`.btn-action[data-action="${action}"]`);
            if (!btn) continue;

            const available = actions.find(a => a.action === action);
            btn.disabled = !available;

            if (action === 'call' && available) {
                btn.textContent = `跟注 $${available.amount}`;
            }
            if (action === 'bet' && available) {
                btn.textContent = `下注 $${available.amount}`;
            }
        }

        // 設定加注/下注滑桿範圍
        const raiseAction = actions.find(a => a.action === 'raise');
        const betAction = actions.find(a => a.action === 'bet');
        const sliderAction = raiseAction || betAction;

        if (sliderAction) {
            const slider = document.getElementById('raise-slider');
            slider.min = sliderAction.amount;
            slider.value = sliderAction.amount;
            document.getElementById('raise-amount').textContent = sliderAction.amount;
        }
    }

    updateAnalysis(analysis) {
        if (!analysis) {
            document.getElementById('win-rate').textContent = '--';
            document.getElementById('pot-odds').textContent = '--';
            document.getElementById('ev').textContent = '--';
            document.getElementById('outs-section').innerHTML = '';
            return;
        }

        // 勝率
        const winRate = (analysis.win_rate * 100).toFixed(1);
        document.getElementById('win-rate').textContent = `${winRate}%`;

        // 底池賠率
        const potOdds = (analysis.pot_odds * 100).toFixed(1);
        document.getElementById('pot-odds').textContent = `${potOdds}%`;

        // 期望值
        const evEl = document.getElementById('ev');
        const ev = analysis.ev;
        evEl.textContent = ev >= 0 ? `+$${ev.toFixed(0)}` : `-$${Math.abs(ev).toFixed(0)}`;
        evEl.className = `value ${ev >= 0 ? 'positive' : 'negative'}`;

        // Outs
        const outsSection = document.getElementById('outs-section');
        if (analysis.outs && analysis.outs.length > 0) {
            let outsHtml = '<div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;">聽牌:</div>';
            for (const out of analysis.outs) {
                const prob = (out.probability * 100).toFixed(0);
                outsHtml += `
                    <div class="out-item">
                        <span>${out.name}</span>
                        <span class="count">${out.count} outs (${prob}%)</span>
                    </div>
                `;
            }
            outsSection.innerHTML = outsHtml;
        } else {
            outsSection.innerHTML = '';
        }
    }

    updateAdvice(advice) {
        if (!advice) {
            document.getElementById('advice-action').textContent = '等待行動...';
            document.getElementById('advice-action').className = 'advice-action';
            document.getElementById('advice-reason').textContent = '';
            document.getElementById('teaching-points').innerHTML = '';
            return;
        }

        const actionEl = document.getElementById('advice-action');
        const actionText = {
            'strong_bet': '🔥 強烈建議加注',
            'bet': '↑ 建議加注',
            'call': '→ 建議跟注',
            'check_call': '→ 過牌/跟注',
            'check_fold': '↓ 過牌/棄牌',
            'fold': '✕ 建議棄牌'
        };
        actionEl.textContent = actionText[advice.action] || advice.action;
        actionEl.className = `advice-action ${advice.action}`;

        document.getElementById('advice-reason').textContent = advice.reasoning;

        const pointsEl = document.getElementById('teaching-points');
        let pointsHtml = '';
        for (const point of advice.teaching_points || []) {
            pointsHtml += `<li>${point}</li>`;
        }
        pointsEl.innerHTML = pointsHtml;
    }

    renderMessages(messages) {
        const container = document.getElementById('messages');
        let html = '';
        for (const msg of messages || []) {
            html += `<div class="message">${msg}</div>`;
        }
        container.innerHTML = html;
    }

    showHandResult(result) {
        const winnerNames = result.winners.join(', ');
        document.getElementById('result-title').textContent = result.winners.includes('玩家') ? '🎉 你贏了！' : '本局結束';
        document.getElementById('winner-info').textContent = `${winnerNames} 贏得 $${result.pot}`;

        // 顯示各玩家手牌
        let handsHtml = '';
        for (const hand of result.hands || []) {
            handsHtml += `
                <div class="hand-reveal">
                    <div class="player-name">${hand.name}</div>
                    <div class="cards" style="display:flex;gap:4px;justify-content:center;margin:8px 0;">
                        ${this.renderSmallCards(hand.cards)}
                    </div>
                    <div class="hand-type">${hand.hand}</div>
                </div>
            `;
        }
        document.getElementById('hands-reveal').innerHTML = handsHtml;

        this.showModal('result-modal');
    }

    showGameOver(chips) {
        const msg = chips <= 0
            ? '你的籌碼已用完！繼續練習，你一定會進步的！'
            : '🎉 恭喜！你擊敗了所有對手！';
        document.getElementById('gameover-message').textContent = msg;
        this.showModal('gameover-modal');
    }

    showRaiseModal() {
        this.showModal('raise-modal');
    }

    showModal(id) {
        document.getElementById(id).classList.add('active');
    }

    hideModal(id) {
        document.getElementById(id).classList.remove('active');
    }
}

// Initialize game
document.addEventListener('DOMContentLoaded', () => {
    window.pokerGame = new PokerGame();
});
