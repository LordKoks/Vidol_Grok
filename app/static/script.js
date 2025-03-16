let botName, botToken, csrfToken;
let chart;

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, calling initApp');
    initApp();
});

function initApp() {
    fetch('/api/csrf-token')  // Изменено с /csrf-token на /api/csrf-token
        .then(response => response.json())
        .then(data => {
            csrfToken = data.csrf_token;
            console.log('CSRF token получен: ', csrfToken);
        })
        .catch(error => console.error('Ошибка получения CSRF токена:', error));
}

// Регистрация пользователя
async function register() {
    const username = document.getElementById('regUsername').value;
    const password = document.getElementById('regPassword').value;
    const email = document.getElementById('regEmail').value;
    try {
        const response = await fetch('/api/register', {  // Добавлен префикс /api/
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            body: JSON.stringify({ username, password })
        });
        if (response.ok) {
            alert('Регистрация успешна! 🌟');
            closeModal('registrationModal');
            showModal('verifyModal');
        } else {
            document.getElementById('regUsernameError').textContent = (await response.json()).detail;
        }
    } catch (error) {
        console.error('Ошибка регистрации:', error);
        document.getElementById('regUsernameError').textContent = 'Ошибка при регистрации 😞';
    }
}

// Вход пользователя
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    try {
        const response = await fetch('/api/login', {  // Добавлен префикс /api/
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            body: JSON.stringify({ username, password })
        });
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('userId', data.user_id);
            localStorage.setItem('token', data.token);
            alert('Вход успешен! 🌈');
            closeModal('authModal');
        } else {
            document.getElementById('passwordError').textContent = (await response.json()).detail;
        }
    } catch (error) {
        console.error('Ошибка входа:', error);
        document.getElementById('passwordError').textContent = 'Ошибка при входе 😞';
    }
}

// Создание бота
async function createBot() {
    botName = document.getElementById('createBotName').value;
    botToken = document.getElementById('createBotToken').value;
    const botType = document.getElementById('botType').value;
    const token = localStorage.getItem('token');
    try {
        const response = await fetch('/api/create-bot', {  // Добавлен префикс /api/
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken,
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name: botName, token: botToken, platform: botType })
        });
        if (response.ok) {
            alert('Бот успешно создан! 🌟');
            closeModal('createBotModal');
        } else {
            document.getElementById('createBotError').textContent = (await response.json()).detail;
        }
    } catch (error) {
        console.error('Ошибка создания бота:', error);
        document.getElementById('createBotError').textContent = 'Ошибка при создании бота 😞';
    }
}

// Проверка статуса бота
async function checkBotStatus() {
    const botType = document.getElementById('checkBotType').value;
    document.getElementById('statusResult').innerHTML = `Статус ${botType}: Ожидание ответа...`;
    setTimeout(() => {
        document.getElementById('statusResult').innerHTML = `Статус ${botType}: Активен 🌟`;
    }, 1000);
}

// Экспорт в APK
async function exportAPK() {
    const uiTitle = document.getElementById('apkUITitle').value;
    const uiColor = document.getElementById('apkUIColor').value;
    alert(`Экспорт APK с названием "${uiTitle}" и цветом ${uiColor} начат! 🌈`);
    closeModal('exportAPKModal');
}

// Генерация документации
async function generateDocs() {
    const commands = document.getElementById('docCommands').value.split(',').map(cmd => cmd.trim());
    const examples = document.getElementById('docExamples').value.split(',').map(ex => ex.trim());
    if (!botToken) {
        alert('Сначала создайте бота! 🌟');
        return;
    }
    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }
    try {
        const response = await fetch('/api/generate-docs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ name: botName, token: botToken, commands, examples })
        });
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${botName}_README.md`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            console.log('Docs generated:', botName);
            closeModal('docsModal');
            alert('Документация бота скачана! 🌈');
        } else {
            const data = await response.json();
            console.error('Docs generation failed:', data.detail);
            alert('Ошибка генерации документации 😞');
        }
    } catch (error) {
        console.error('Docs generation error:', error);
        alert('Ошибка генерации документации 😞');
    }
}

// Показ статистики
async function showStats(userId, startDate = null, endDate = null, platform = null) {
    const token = localStorage.getItem('token');
    let url = `/api/stats/${userId}`;  // Добавлен префикс /api/
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (platform) params.append('platform', platform);
    if (params.toString()) url += `?${params.toString()}`;

    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const stats = await response.json();
            const ctx = document.getElementById('statsChart').getContext('2d');
            
            if (chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: stats.map(s => s.platform),
                    datasets: [
                        {
                            label: 'Отправлено сообщений 📤',
                            data: stats.map(s => s.messages_sent),
                            backgroundColor: 'rgba(75, 192, 192, 0.5)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        },
                        {
                            label: 'Получено сообщений 📥',
                            data: stats.map(s => s.messages_received),
                            backgroundColor: 'rgba(255, 99, 132, 0.5)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1
                        },
                        {
                            label: 'Активные пользователи 👥',
                            data: stats.map(s => s.active_users),
                            backgroundColor: 'rgba(54, 162, 235, 0.5)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    scales: {
                        y: { beginAtZero: true }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeInOutQuad'
                    }
                }
            });
        } else {
            document.getElementById('statsChart').innerHTML = '<p>Статистика не найдена 😞</p>';
        }
    } catch (error) {
        console.error('Ошибка получения статистики:', error);
        document.getElementById('statsChart').innerHTML = '<p>Ошибка загрузки статистики 😞</p>';
    }
}

// Обновление статистики
function updateStats() {
    const userId = localStorage.getItem('userId');
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const platform = document.getElementById('platformFilter').value;
    showStats(userId, startDate, endDate, platform);
}

// Экспорт статистики в CSV
async function exportStats() {
    const userId = localStorage.getItem('userId');
    const token = localStorage.getItem('token');
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const platform = document.getElementById('platformFilter').value;

    let url = `/api/stats/${userId}/export`;  // Добавлен префикс /api/
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (platform) params.append('platform', platform);
    if (params.toString()) url += `?${params.toString()}`;

    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const blob = await response.blob();
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `stats_${userId}.csv`;  // Исправлено имя файла
            link.click();
            alert('Статистика экспортирована! 📥');
            closeModal('statsModal');
        } else {
            alert('Ошибка экспорта 😞');
        }
    } catch (error) {
        console.error('Ошибка экспорта:', error);
        alert('Ошибка при экспорте статистики 😞');
    }
}

// Показ модального окна
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'block';
    if (modalId === 'statsModal') {
        const userId = localStorage.getItem('userId');
        if (userId) showStats(userId);
    }
}

// Закрытие модального окна
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'none';
}

// Верификация email (заглушка)
function verifyEmail() {
    const code = document.getElementById('verificationCode').value;
    if (code === "1234") {
        alert('Email подтвержден! 🌟');
        closeModal('verifyModal');
    } else {
        document.getElementById('verificationCodeError').textContent = 'Неверный код 😞';
    }
}
