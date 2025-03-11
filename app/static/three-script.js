function initScene() {
    try {
        const canvas = document.getElementById('three-canvas');
        if (!canvas) {
            throw new Error('Three.js canvas not found');
        }
        if (!window.THREE) {
            throw new Error('Three.js not loaded');
        }
        if (!window.TWEEN) {
            throw new Error('Tween.js not loaded');
        }

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ canvas, alpha: true });
        renderer.setSize(window.innerWidth, window.innerHeight);

        // Частицы для анимированного фона
        const particleCount = 1000;
        const particles = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        for (let i = 0; i < particleCount * 3; i += 3) {
            positions[i] = (Math.random() - 0.5) * 100;
            positions[i + 1] = (Math.random() - 0.5) * 100;
            positions[i + 2] = (Math.random() - 0.5) * 100;
        }
        particles.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const particleMaterial = new THREE.PointsMaterial({ color: 0xffffff, size: 0.1 });
        const particleSystem = new THREE.Points(particles, particleMaterial);
        scene.add(particleSystem);

        // Основной объект
        const geometry = new THREE.TorusKnotGeometry(1, 0.3, 100, 16);
        const material = new THREE.MeshBasicMaterial({ color: 0x00ff00, wireframe: true });
        const object = new THREE.Mesh(geometry, material);
        scene.add(object);

        camera.position.z = 5;

        const tween = new TWEEN.Tween(object.position)
            .to({ y: 1 }, 2000)
            .easing(TWEEN.Easing.Quadratic.InOut)
            .repeat(Infinity)
            .yoyo(true)
            .start();

        function animate() {
            requestAnimationFrame(animate);
            object.rotation.x += 0.01;
            object.rotation.y += 0.01;
            particleSystem.rotation.y += 0.001;
            TWEEN.update();
            renderer.render(scene, camera);
        }

        function resizeRenderer() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }
        window.addEventListener('resize', resizeRenderer);

        animate();

        const loadingDiv = document.getElementById('three-loading');
        if (loadingDiv) {
            loadingDiv.style.display = 'none';
            console.log('Three.js scene initialized successfully');
        } else {
            console.error('Three loading div not found');
        }
    } catch (error) {
        console.error('Error initializing Three.js scene:', error);
        const loadingDiv = document.getElementById('three-loading');
        if (loadingDiv) {
            loadingDiv.innerHTML = '<p>Ошибка загрузки 3D-сцены.</p>';
        }
    }
}

window.initScene = initScene;
window.addEventListener('load', initScene);
