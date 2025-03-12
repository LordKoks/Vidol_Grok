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
    document.getElementById('createBotButton').addEventListener('click', () => showModal('createBotModal'));
    document.getElementById('checkStatusButton').addEventListener('click', () => showModal('checkStatusModal'));
    document.getElementById('exportAPKButton').addEventListener('click', () => showModal('exportAPKModal'));
    document.getElementById('previewButton').addEventListener('click', () => showModal('previewModal'));
    document.getElementById('docsButton').addEventListener('click', () => showModal('docsModal'));
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

function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    if (modalId === 'previewModal') {
        initializePreview();
        loadBotStructure();
    }
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
    const botName = document.getElementById('createBotName').value;
    const botToken = document.getElementById('createBotToken').value;
    const botType = document.getElementById('botType').value;
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
            body: JSON.stringify({ name: botName, token: botToken, type: botType })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${botName}_bot.py`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            console.log('Bot created:', botName);
            closeModal('createBotModal');
            alert('Бот создан и скачан!');
            localStorage.setItem('botToken', botToken);
            localStorage.setItem('botName', botName);
        } else {
            const data = await response.json();
            document.getElementById('createBotError').textContent = data.detail;
            console.error('Bot creation failed:', data.detail);
        }
    } catch (error) {
        console.error('Bot creation error:', error);
        alert('Ошибка создания бота');
    }
}

async function checkBotStatus() {
    const botName = localStorage.getItem('botName') || "TestBot";
    const botToken = localStorage.getItem('botToken');
    const botType = document.getElementById('checkBotType').value;
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
            body: JSON.stringify({ name: botName, token: botToken, type: botType })
        });

        const data = await response.json();
        if (response.ok) {
            console.log('Bot status:', data);
            document.getElementById('statusResult').innerHTML = `
                Статус: ${data.status}<br>
                Информация: ${JSON.stringify(data.bot_info || data.error)}<br>
                Статистика: ${data.stats ? JSON.stringify(data.stats) : 'Недоступно'}
            `;
        } else {
            console.error('Bot status check failed:', data.detail);
            document.getElementById('statusResult').textContent = 'Ошибка: ' + data.detail;
        }
    } catch (error) {
        console.error('Bot status check error:', error);
        document.getElementById('statusResult').textContent = 'Ошибка проверки статуса';
    }
}

async function exportAPK() {
    const botName = localStorage.getItem('botName') || "TestBot";
    const botToken = localStorage.getItem('botToken');
    const uiTitle = document.getElementById('apkUITitle').value;
    const uiColor = document.getElementById('apkUIColor').value;
    const csrfToken = localStorage.getItem('csrfToken');

    if (!botToken) {
        alert('Сначала создайте бота!');
        return;
    }
    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }

    const uiConfig = { title: uiTitle || "Bot Control", color: uiColor || "#007bff" };
    try {
        const response = await fetch('/api/export-apk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ name: botName, token: botToken, ui_config: uiConfig })
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
            closeModal('exportAPKModal');
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
    const botName = localStorage.getItem('botName') || "TestBot";
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
            body: JSON.stringify({ name: botName, token: botToken, structure: null })
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
        sphere.userData = node;
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

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let selectedNode = null;

    previewRenderer.domElement.addEventListener('mousemove', (event) => {
        mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(event.clientY / 600) * 2 + 1;
        raycaster.setFromCamera(mouse, previewCamera);
        const intersects = raycaster.intersectObjects(previewScene.children);
        if (intersects.length > 0) {
            selectedNode = intersects[0].object;
            selectedNode.material.color.set(0x00ff00);
        } else if (selectedNode) {
            selectedNode.material.color.set(0xff0000);
            selectedNode = null;
        }
    });

    previewRenderer.domElement.addEventListener('click', () => {
        if (selectedNode) {
            const newCommand = prompt('Введите новую команду:', selectedNode.userData.command);
            if (newCommand) {
                selectedNode.userData.command = newCommand;
                updateBotStructure(structure);
            }
        }
    });
}

async function updateBotStructure(structure) {
    const botName = localStorage.getItem('botName') || "TestBot";
    const botToken = localStorage.getItem('botToken');
    const csrfToken = localStorage.getItem('csrfToken');

    try {
        const response = await fetch('/api/bot-structure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ name: botName, token: botToken, structure })
        });

        const data = await response.json();
        if (response.ok) {
            console.log('Structure updated:', data);
        } else {
            console.error('Structure update failed:', data.detail);
        }
    } catch (error) {
        console.error('Structure update error:', error);
    }
}

async function generateDocs() {
    const botName = localStorage.getItem('botName') || "TestBot";
    const botToken = localStorage.getItem('botToken');
    const commands = document.getElementById('docCommands').value.split(',').map(c => c.trim());
    const examples = document.getElementById('docExamples').value.split(',').map(e => e.trim());
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
