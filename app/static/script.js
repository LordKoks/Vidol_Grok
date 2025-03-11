async function fetchCsrfToken() {
    try {
        console.log('Fetching CSRF token...');
        const response = await fetch('/api/csrf-token', {
            method: 'GET',
            credentials: 'include'
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        console.log('CSRF token received:', data.csrf_token);
        localStorage.setItem('csrfToken', data.csrf_token);
        return data.csrf_token;
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        alert('Ошибка получения CSRF-токена');
        return null;
    }
}

async function initApp() {
    console.log('Initializing app...');
    const token = await fetchCsrfToken();
    if (!token) {
        console.error('Failed to fetch CSRF token, stopping initialization');
        return;
    }
    console.log('Using CSRF token:', token);

    initializeUI();
    initializeAnimation();
    if (!localStorage.getItem('isAuthenticated')) {
        showAuthModal();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, calling initApp');
    initApp();
});

// Остальной код остается без изменений (initializeUI, login, register и т.д.)
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, calling initApp');
    initApp();
});

// Остальной код (включая login, register и т.д.) остается без изменений
function initializeUI() {
    console.log('Initializing UI...');
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;
    const savedTheme = localStorage.getItem('theme') || 'dark-theme';
    body.classList.add(savedTheme);

    if (themeToggle && body) {
        themeToggle.addEventListener('click', () => {
            if (body.classList.contains('dark-theme')) {
                body.classList.replace('dark-theme', 'light-theme');
                localStorage.setItem('theme', 'light-theme');
            } else {
                body.classList.replace('light-theme', 'dark-theme');
                localStorage.setItem('theme', 'dark-theme');
            }
            console.log('Theme toggled');
        });
    } else {
        console.error('Theme toggle or body not found');
    }

    window.showAuthModal = () => {
        const modal = document.getElementById('authModal');
        if (modal) {
            modal.style.display = 'block';
            console.log('Auth modal shown');
        } else {
            console.error('Auth modal not found');
        }
    };

    window.showBotCreationModal = () => {
        const modal = document.getElementById('botCreationModal');
        if (modal) {
            modal.style.display = 'block';
            console.log('Bot creation modal shown');
        } else {
            console.error('Bot creation modal not found');
        }
    };

    window.showRegistrationModal = () => {
        closeModal('authModal');
        const modal = document.getElementById('registrationModal');
        if (modal) {
            modal.style.display = 'block';
            console.log('Registration modal shown');
        } else {
            console.error('Registration modal not found');
        }
    };

    window.closeModal = (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            console.log(`${modalId} modal closed`);
        } else {
            console.error(`${modalId} not found`);
        }
    };

    window.login = async () => {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const csrfToken = localStorage.getItem('csrfToken');
        const usernameError = document.getElementById('usernameError');
        const passwordError = document.getElementById('passwordError');

        usernameError.textContent = '';
        passwordError.textContent = '';

        if (!username || !password) {
            if (!username) usernameError.textContent = 'Логин обязателен';
            if (!password) passwordError.textContent = 'Пароль обязателен';
            return;
        }

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'include',
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            if (response.ok) {
                console.log('Login successful:', data.message);
                localStorage.setItem('isAuthenticated', 'true');
                localStorage.setItem('userRole', data.role);
                closeModal('authModal');
                showAuthenticatedUI();
                if (data.role === 'admin') {
                    console.log('Admin privileges granted');
                }
            } else {
                if (response.status === 401) {
                    passwordError.textContent = data.detail || 'Неверный логин или пароль';
                } else if (response.status === 403) {
                    passwordError.textContent = 'Неверный CSRF-токен. Перезагрузите страницу.';
                } else {
                    passwordError.textContent = data.detail || 'Ошибка входа';
                }
            }
        } catch (error) {
            console.error('Login error:', error);
            passwordError.textContent = 'Ошибка сервера';
        }
    };

    window.createBot = async () => {
        const botName = document.getElementById('botName').value;
        const botToken = document.getElementById('botToken').value;
        const csrfToken = localStorage.getItem('csrfToken');
        const botNameError = document.getElementById('botNameError');
        const botTokenError = document.getElementById('botTokenError');

        botNameError.textContent = '';
        botTokenError.textContent = '';

        if (!botName || !botToken) {
            if (!botName) botNameError.textContent = 'Имя бота обязательно';
            if (!botToken) botTokenError.textContent = 'Токен бота обязателен';
            return;
        }

        try {
            const response = await fetch('/api/create-bot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'include',
                body: JSON.stringify({ name: botName, token: botToken })
            });

            const data = await response.json();
            if (response.ok) {
                console.log('Bot created:', data.message);
                closeModal('botCreationModal');
            } else {
                if (response.status === 403) {
                    botNameError.textContent = 'Неверный CSRF-токен. Перезагрузите страницу.';
                } else {
                    botNameError.textContent = data.detail || 'Ошибка создания бота';
                }
            }
        } catch (error) {
            console.error('Bot creation error:', error);
            botNameError.textContent = 'Ошибка сервера';
        }
    };

    window.register = async () => {
        let csrfToken = localStorage.getItem('csrfToken');
        if (!csrfToken) {
            csrfToken = await fetchCsrfToken();
            if (csrfToken) localStorage.setItem('csrfToken', csrfToken);
        }

        const username = document.getElementById('regUsername').value;
        const password = document.getElementById('regPassword').value;
        const email = document.getElementById('regEmail').value;
        const regEmailError = document.getElementById('regEmailError');

        regEmailError.textContent = '';
        console.log('Register attempt:', { username, password, email, csrfToken });

        if (!username || !password || !email) {
            regEmailError.textContent = 'Все поля обязательны';
            return;
        }
        if (!csrfToken) {
            regEmailError.textContent = 'CSRF-токен не получен. Перезагрузите страницу.';
            return;
        }

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken
                },
                credentials: 'include',
                body: JSON.stringify({ username, password, email })
            });

            const data = await response.json();
            console.log('Register response:', data);
            if (response.ok) {
                console.log('Registration successful:', data.message);
                closeModal('registrationModal');
                document.getElementById('verifyModal').style.display = 'block';
            } else {
                regEmailError.textContent = data.detail || 'Ошибка регистрации';
            }
        } catch (error) {
            console.error('Registration error:', error);
            regEmailError.textContent = 'Ошибка сервера';
        }
    };

    window.verifyEmail = async () => {
        const code = document.getElementById('verificationCode').value;
        const username = document.getElementById('regUsername').value;
        const csrfToken = localStorage.getItem('csrfToken');
        const verificationCodeError = document.getElementById('verificationCodeError');

        verificationCodeError.textContent = '';

        if (!code) {
            verificationCodeError.textContent = 'Код обязателен';
            return;
        }

        try {
            const response = await fetch('/api/verify-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'include',
                body: JSON.stringify({ username, code })
            });

            const data = await response.json();
            if (response.ok) {
                console.log('Email verified:', data.message);
                closeModal('verifyModal');
                alert('Регистрация завершена! Теперь вы можете войти.');
                showAuthModal();
            } else {
                verificationCodeError.textContent = data.detail || 'Неверный код';
            }
        } catch (error) {
            console.error('Verification error:', error);
            verificationCodeError.textContent = 'Ошибка сервера';
        }
    };

    window.generateNodeWithAI = () => {
        console.log('Generate node with AI clicked');
    };

    window.addNode = () => {
        console.log('Add node clicked');
    };

    window.configureAI = () => {
        console.log('Configure AI clicked');
    };

    window.toggleCustomAIFields = () => {
        const aiProvider = document.getElementById('aiProvider').value;
        const customAIFields = document.getElementById('customAIFields');
        if (aiProvider === 'custom') {
            customAIFields.style.display = 'block';
        } else {
            customAIFields.style.display = 'none';
        }
    };

    showAuthenticatedUI();
}

function showAuthenticatedUI() {
    const isAuthenticated = localStorage.getItem('isAuthenticated');
    const buttonGroup = document.querySelector('.button-group');
    if (isAuthenticated) {
        buttonGroup.style.display = 'flex';
        buttonGroup.classList.add('fade-in');
    } else {
        buttonGroup.style.display = 'none';
    }
}

function initializeAnimation() {
    console.log('Initializing animation...');
    if (typeof window.initScene === 'function') {
        window.initScene();
    } else {
        console.error('initScene function not found');
    }
}

document.addEventListener('DOMContentLoaded', initApp);
