
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
    document.getElementById('checkBotStatusButton').addEventListener('click', checkBotStatus);
    document.getElementById('exportAPKButton').addEventListener('click', exportAPK);
    document.getElementById('previewButton').addEventListener('click', showPreviewModal);
    document.getElementById('docsButton').addEventListener('click', generateDocs);
}

function initializeAnimation() {
    console.log('Initializing animation...');
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.getElementById('backgroundCanvas').appendChild(renderer.domElement);

    const geometry = new THREE.TorusKnotGeometry(5, 1.5, 100, 16);
    const material = new THREE.MeshBasicMaterial({ color: 0x00ff00, wireframe: true });
    const torusKnot = new THREE.Mesh(geometry, material);
    scene.add(torusKnot);

    camera.position.z = 15;

    const animate = () => {
        requestAnimationFrame(animate);
        TWEEN.update();
        torusKnot.rotation.x += 0.01;
        torusKnot.rotation.y += 0.01;
        renderer.render(scene, camera);
    };

    const tween = new TWEEN.Tween(torusKnot.scale)
        .to({ x: 1.2, y: 1.2, z: 1.2 }, 2000)
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

let previewScene, previewCamera, previewRenderer;
function initializePreview() {
    previewScene = new THREE.Scene();
    previewCamera = new THREE.PerspectiveCamera(75, window.innerWidth / 600, 0.1, 1000);
    previewRenderer = new THREE.WebGLRenderer({ alpha: true });
    previewRenderer.setSize(window.innerWidth, 600);
    document.getElementById('previewCanvas').appendChild(previewRenderer.domElement);

    previewCamera.position.z = 20;

    const animatePreview = () => {
        requestAnimationFrame(animatePreview);
        previewRenderer.render(previewScene, previewCamera);
    };
    animatePreview();
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

function showPreviewModal() {
    document.getElementById('previewModal').style.display = 'block';
    initializePreview();
    loadBotStructure();
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
            localStorage.setItem('botToken', data.token);
        } else {
            document.getElementById('botNameError').textContent = data.detail;
            console.error('Bot creation failed:', data.detail);
        }
    } catch (error) {
        console.error('Bot creation error:', error);
        alert('Ошибка создания бота');
    }
}

async function checkBotStatus() {
    const botName = document.getElementById('botName').value || "TestBot";
    const botToken = localStorage.getItem('botToken');
    const csrfToken = localStorage.getItem('csrfToken');

    if (!botToken) {
        alert('Сначала создайте бота!');
        return;
    }
    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }

    try {
        const response = await fetch('/api/check-bot-status', {
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
            console.log('Bot status:', data);
            alert(`Статус бота: ${data.status}\nИнформация: ${JSON.stringify(data.bot_info || data.error)}`);
        } else {
            console.error('Bot status check failed:', data.detail);
            alert('Ошибка проверки статуса бота');
        }
    } catch (error) {
        console.error('Bot status check error:', error);
        alert('Ошибка проверки статуса бота');
    }
}

async function exportAPK() {
    const botName = document.getElementById('botName').value || "TestBot";
    const botToken = localStorage.getItem('botToken');
    const csrfToken = localStorage.getItem('csrfToken');

    if (!botToken) {
        alert('Сначала создайте бота!');
        return;
    }
    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }

    try {
        const response = await fetch('/api/export-apk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ name: botName, token: botToken })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${botName}_bot.apk`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            console.log('APK exported:', botName);
            alert('APK бота скачан!');
        } else {
            const data = await response.json();
            console.error('APK export failed:', data.detail);
            alert('Ошибка экспорта APK');
        }
    } catch (error) {
        console.error('APK export error:', error);
        alert('Ошибка экспорта APK');
    }
}

async function loadBotStructure() {
    const botName = document.getElementById('botName').value || "TestBot";
    const botToken = localStorage.getItem('botToken');
    const csrfToken = localStorage.getItem('csrfToken');

    if (!botToken) {
        alert('Сначала создайте бота!');
        return;
    }
    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }

    try {
        const response = await fetch('/api/bot-structure', {
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
            console.log('Bot structure loaded:', data);
            renderBotStructure(data.structure);
        } else {
            console.error('Structure load failed:', data.detail);
            alert('Ошибка загрузки структуры бота');
        }
    } catch (error) {
        console.error('Structure load error:', error);
        alert('Ошибка загрузки структуры бота');
    }
}

function renderBotStructure(structure) {
    previewScene.clear();
    structure.nodes.forEach(node => {
        const geometry = new THREE.SphereGeometry(1, 32, 32);
        const material = new THREE.MeshBasicMaterial({ color: 0xff0000 });
        const sphere = new THREE.Mesh(geometry, material);
        sphere.position.set(node.x, node.y, node.z);
        previewScene.add(sphere);
    });
    structure.edges.forEach(edge => {
        const fromNode = structure.nodes.find(n => n.id === edge.from);
        const toNode = structure.nodes.find(n => n.id === edge.to);
        const geometry = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(fromNode.x, fromNode.y, fromNode.z),
            new THREE.Vector3(toNode.x, toNode.y, toNode.z)
        ]);
        const material = new THREE.LineBasicMaterial({ color: 0xffffff });
        const line = new THREE.Line(geometry, material);
        previewScene.add(line);
    });
}

async function generateDocs() {
    const botName = document.getElementById('botName').value || "TestBot";
    const botToken = localStorage.getItem('botToken');
    const commands = prompt('Введите команды бота через запятую (например, /start, /help):')?.split(',').map(c => c.trim()) || ['/start'];
    const csrfToken = localStorage.getItem('csrfToken');

    if (!botToken) {
        alert('Сначала создайте бота!');
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
            body: JSON.stringify({ name: botName, token: botToken, commands })
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
            alert('Документация бота скачана!');
        } else {
            const data = await response.json();
            console.error('Docs generation failed:', data.detail);
            alert('Ошибка генерации документации');
        }
    } catch (error) {
        console.error('Docs generation error:', error);
        alert('Ошибка генерации документации');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, calling initApp');
    initApp();
});
