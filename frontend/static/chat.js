/**
 * SkyAssist chat client.
 * Чистый ванильный JS, без сборки.
 *
 * Состояние:
 *   currentSessionId — id открытой сессии (null при стартовом welcome-экране)
 *
 * API:
 *   GET    /api/sessions
 *   POST   /api/sessions
 *   PATCH  /api/sessions/:id
 *   DELETE /api/sessions/:id
 *   GET    /api/sessions/:id/messages
 *   POST   /api/sessions/:id/messages
 */

// ===== Состояние =====

let currentSessionId = null;
let isWaitingForResponse = false;
let renameSessionId = null;

// ===== DOM-элементы =====

const sessionsList = document.getElementById('sessionsList');
const sessionTitleEl = document.getElementById('sessionTitle');
const messagesEl = document.getElementById('messages');
const welcomeEl = document.getElementById('welcome');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const renameModal = document.getElementById('renameModal');
const renameInput = document.getElementById('renameInput');
const renameCancelBtn = document.getElementById('renameCancel');
const renameConfirmBtn = document.getElementById('renameConfirm');

// ===== API-обёртки =====

async function api(method, path, body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body !== null) {
        opts.body = JSON.stringify(body);
    }
    const response = await fetch(path, opts);
    if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(`${response.status} ${response.statusText}: ${text}`);
    }
    if (response.status === 204) return null;
    return response.json();
}

// ===== Сессии =====

async function loadSessions() {
    try {
        const sessions = await api('GET', '/api/sessions');
        renderSessions(sessions);
    } catch (err) {
        console.error('Ошибка загрузки сессий:', err);
    }
}

function renderSessions(sessions) {
    sessionsList.innerHTML = '';
    sessions.forEach(s => {
        const item = document.createElement('div');
        item.className = 'session-item';
        if (s.id === currentSessionId) item.classList.add('active');
        item.dataset.id = s.id;

        const titleSpan = document.createElement('span');
        titleSpan.className = 'session-title-text';
        titleSpan.textContent = s.title;
        item.appendChild(titleSpan);

        const actions = document.createElement('div');
        actions.className = 'session-actions';

        // Иконка переименовать (карандаш)
        const renameBtn = document.createElement('button');
        renameBtn.className = 'session-icon-btn';
        renameBtn.title = 'Переименовать';
        renameBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>';
        renameBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openRenameModal(s.id, s.title);
        });

        // Иконка удалить (корзина)
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'session-icon-btn danger';
        deleteBtn.title = 'Удалить';
        deleteBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSession(s.id, s.title);
        });

        actions.appendChild(renameBtn);
        actions.appendChild(deleteBtn);
        item.appendChild(actions);

        item.addEventListener('click', () => openSession(s.id));

        sessionsList.appendChild(item);
    });
}

async function openSession(sessionId) {
    if (currentSessionId === sessionId) return;
    currentSessionId = sessionId;

    try {
        const [session, messages] = await Promise.all([
            api('GET', `/api/sessions/${sessionId}`),
            api('GET', `/api/sessions/${sessionId}/messages`),
        ]);

        sessionTitleEl.textContent = session.title;
        renderMessages(messages);
        markActiveSession(sessionId);
    } catch (err) {
        console.error('Ошибка открытия сессии:', err);
        alert('Не удалось открыть чат: ' + err.message);
    }
}

function markActiveSession(sessionId) {
    sessionsList.querySelectorAll('.session-item').forEach(el => {
        el.classList.toggle('active', el.dataset.id === sessionId);
    });
}

async function startNewChat() {
    currentSessionId = null;
    sessionTitleEl.textContent = 'Новый чат';
    messagesEl.innerHTML = '';
    messagesEl.appendChild(welcomeEl);
    welcomeEl.style.display = '';
    markActiveSession(null);
    messageInput.focus();
}

async function deleteSession(sessionId, title) {
    if (!confirm(`Удалить чат «${title}»?`)) return;
    try {
        await api('DELETE', `/api/sessions/${sessionId}`);
        if (currentSessionId === sessionId) {
            startNewChat();
        }
        await loadSessions();
    } catch (err) {
        console.error('Ошибка удаления:', err);
        alert('Не удалось удалить: ' + err.message);
    }
}

// ===== Рендер сообщений =====

function renderMessages(messages) {
    messagesEl.innerHTML = '';
    welcomeEl.style.display = 'none';
    messages.forEach(m => appendMessage(m.role, m.content));
    scrollToBottom();
}

function appendMessage(role, content) {
    welcomeEl.style.display = 'none';

    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'Я' : 'AL';

    const wrap = document.createElement('div');
    wrap.className = 'message-content';

    const roleEl = document.createElement('div');
    roleEl.className = 'message-role';
    roleEl.textContent = role === 'user' ? 'Вы' : 'SkyAssist';

    const textEl = document.createElement('div');
    textEl.className = 'message-text';
    if (role === 'assistant') {
        // Markdown с защитой от XSS — отключаем HTML, разрешаем только основной markdown
        textEl.innerHTML = marked.parse(content, { breaks: true, gfm: true });
    } else {
        // Пользовательские сообщения — просто текст с переносами
        textEl.textContent = content;
    }

    wrap.appendChild(roleEl);
    wrap.appendChild(textEl);
    msg.appendChild(avatar);
    msg.appendChild(wrap);

    messagesEl.appendChild(msg);
    scrollToBottom();

    return msg;
}

function appendTypingIndicator() {
    const msg = document.createElement('div');
    msg.className = 'message assistant';
    msg.id = 'typing-indicator';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AL';

    const wrap = document.createElement('div');
    wrap.className = 'message-content';

    const roleEl = document.createElement('div');
    roleEl.className = 'message-role';
    roleEl.textContent = 'SkyAssist';

    const textEl = document.createElement('div');
    textEl.className = 'message-text';
    textEl.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';

    wrap.appendChild(roleEl);
    wrap.appendChild(textEl);
    msg.appendChild(avatar);
    msg.appendChild(wrap);

    messagesEl.appendChild(msg);
    scrollToBottom();
}

function removeTypingIndicator() {
    const t = document.getElementById('typing-indicator');
    if (t) t.remove();
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ===== Отправка сообщения =====

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isWaitingForResponse) return;

    isWaitingForResponse = true;
    updateSendButtonState();

    // Если нет открытой сессии — создаём новую перед отправкой
    if (currentSessionId === null) {
        try {
            const newSession = await api('POST', '/api/sessions', {});
            currentSessionId = newSession.id;
            sessionTitleEl.textContent = newSession.title;
        } catch (err) {
            console.error('Ошибка создания сессии:', err);
            alert('Не удалось создать чат: ' + err.message);
            isWaitingForResponse = false;
            updateSendButtonState();
            return;
        }
    }

    // Показываем сообщение пользователя сразу (оптимистичный UI)
    appendMessage('user', text);
    messageInput.value = '';
    autoResizeInput();
    appendTypingIndicator();

    try {
        const result = await api(
            'POST',
            `/api/sessions/${currentSessionId}/messages`,
            { content: text }
        );

        removeTypingIndicator();
        appendMessage('assistant', result.assistant_message.content);

        // Обновляем title в шапке (мог измениться после первого сообщения)
        sessionTitleEl.textContent = result.session.title;

        // Перезагружаем список сессий — новый чат поднимется наверх
        await loadSessions();
    } catch (err) {
        removeTypingIndicator();
        console.error('Ошибка отправки:', err);
        appendMessage('assistant', `⚠️ Ошибка: ${err.message}`);
    } finally {
        isWaitingForResponse = false;
        updateSendButtonState();
        messageInput.focus();
    }
}

function updateSendButtonState() {
    const hasText = messageInput.value.trim().length > 0;
    sendBtn.disabled = !hasText || isWaitingForResponse;
}

// ===== Авторесайз textarea =====

function autoResizeInput() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
}

// ===== Модалка переименования =====

function openRenameModal(sessionId, currentTitle) {
    renameSessionId = sessionId;
    renameInput.value = currentTitle;
    renameModal.hidden = false;
    setTimeout(() => {
        renameInput.focus();
        renameInput.select();
    }, 50);
}

function closeRenameModal() {
    renameSessionId = null;
    renameModal.hidden = true;
}

async function confirmRename() {
    const title = renameInput.value.trim();
    if (!title || !renameSessionId) {
        closeRenameModal();
        return;
    }
    try {
        await api('PATCH', `/api/sessions/${renameSessionId}`, { title });
        if (currentSessionId === renameSessionId) {
            sessionTitleEl.textContent = title;
        }
        await loadSessions();
    } catch (err) {
        console.error('Ошибка переименования:', err);
        alert('Не удалось переименовать: ' + err.message);
    }
    closeRenameModal();
}

// ===== Обработчики событий =====

newChatBtn.addEventListener('click', startNewChat);

sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('input', () => {
    autoResizeInput();
    updateSendButtonState();
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Подсказки на стартовом экране
document.querySelectorAll('.suggestion').forEach(btn => {
    btn.addEventListener('click', () => {
        messageInput.value = btn.dataset.prompt;
        autoResizeInput();
        updateSendButtonState();
        sendMessage();
    });
});

// Модалка переименования
renameCancelBtn.addEventListener('click', closeRenameModal);
renameConfirmBtn.addEventListener('click', confirmRename);
renameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') confirmRename();
    if (e.key === 'Escape') closeRenameModal();
});
renameModal.addEventListener('click', (e) => {
    if (e.target === renameModal) closeRenameModal();
});

// ===== Инициализация =====

loadSessions();
messageInput.focus();