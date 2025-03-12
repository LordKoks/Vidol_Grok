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

function initializeUI() {
    console.log('Initializing UI...');
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('generateAIButton').addEventListener('click', generateNodeWithAI);
}

function initializeAnimation() {
    console.log('Initializing animation...');
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.getElementById('backgroundCanvas').appendChild(renderer.domElement);

    const geometry = new THREE.SphereGeometry(5, 32, 32);
    const material = new THREE.MeshBasicMaterial({ color: 0x00ff00, wireframe: true });
    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);

    camera.position.z = 15;

    const animate = () => {
        requestAnimationFrame(animate);
        TWEEN.update();
        sphere.rotation.x += 0.01;
        sphere.rotation.y += 0.01;
        renderer.render(scene, camera);
    };

    const tween = new TWEEN.Tween(sphere.scale)
        .to({ x: 1.5, y: 1.5, z: 1.5 }, 2000)
        .easing(TWEEN.Easing.Quadratic.InOut)
        .yoyo(true)
        .repeat(Infinity)
        .start();

    animate();

    window.addEventListener('resize', () => {
        renderer.setSize(window.innerWidth, window.innerHeight);
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
    });
}

function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');
    sunIcon.classList.toggle('hidden');
    moonIcon.classList.toggle('hidden');
}

function showAuthModal() {
    document.getElementById('authModal').style.display = 'block';
}

function showRegistrationModal() {
    closeModal('authModal');
    document.getElementById('registrationModal').style.display = 'block';
}

function showBotCreationModal() {
    document.getElementById('botCreationModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const csrfToken = localStorage.getItem('csrfToken');

    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            console.log('Login successful:', data);
            localStorage.setItem('isAuthenticated', 'true');
            localStorage.setItem('role', data.role);
            closeModal('authModal');
            alert('Вход выполнен успешно!');
        } else {
            document.getElementById('passwordError').textContent = data.detail;
            console.error('Login failed:', data.detail);
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Ошибка входа');
    }
}

async function register() {
    const username = document.getElementById('regUsername').value;
    const password = document.getElementById('regPassword').value;
    const email = document.getElementById('regEmail').value;
    const csrfToken = localStorage.getItem('csrfToken');

    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
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
        if (response.ok) {
            console.log('Registration successful:', data);
            closeModal('registrationModal');
            document.getElementById('verifyModal').style.display = 'block';
        } else {
            document.getElementById('regUsernameError').textContent = data.detail;
            console.error('Registration failed:', data.detail);
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('Ошибка регистрации');
    }
}

async function verifyEmail() {
    const username = document.getElementById('regUsername').value;
    const code = document.getElementById('verificationCode').value;
    const csrfToken = localStorage.getItem('csrfToken');

    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }

    try {
        const response = await fetch('/api/verify-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ username, code })
        });

        const data = await response.json();
        if (response.ok) {
            console.log('Email verified:', data);
            closeModal('verifyModal');
            alert('Email подтвержден!');
        } else {
            document.getElementById('verificationCodeError').textContent = data.detail;
            console.error('Verification failed:', data.detail);
        }
    } catch (error) {
        console.error('Verification error:', error);
        alert('Ошибка подтверждения email');
    }
}

async function createBot() {
    const botName = document.getElementById('botName').value;
    const botToken = document.getElementById('botToken').value;
    const csrfToken = localStorage.getItem('csrfToken');

    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }

    try {
        const response = await fetch('/api/create-bot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ name: botName, token: botToken })
        });

        const data = await response.json();
        if (response.ok) {
            console.log('Bot created:', data);
            closeModal('botCreationModal');
            alert('Бот создан успешно!');
        } else {
            document.getElementById('botNameError').textContent = data.detail;
            console.error('Bot creation failed:', data.detail);
        }
    } catch (error) {
        console.error('Bot creation error:', error);
        alert('Ошибка создания бота');
    }
}

function generateNodeWithAI() {
    console.log('Generating node with AI...');
    alert('Генерация узла с помощью AI началась! (Пока это заглушка)');
    // Здесь можно добавить логику вызова API для генерации AI
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, calling initApp');
    initApp();
});
