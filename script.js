// Get session token
const sessionToken = document.getElementById('session-token').value;

// 3D Animation Background (Ultimate Extreme: Interactive Nebula with Mouse Parallax & Glow)
function init3DBackground() {
    const container = document.getElementById('background-canvas');
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    // Enhanced particles (20k for density)
    const particles = 20000;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particles * 3);
    const colors = new Float32Array(particles * 3);
    const sizes = new Float32Array(particles);

    for (let i = 0; i < particles; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 2500;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 2500;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 2500;

        // Dynamic colors: Neon cyan/white/blue mix
        const colorChoice = Math.random();
        if (colorChoice < 0.4) {
            colors[i * 3] = 1; colors[i * 3 + 1] = 1; colors[i * 3 + 2] = 1; // White
        } else if (colorChoice < 0.7) {
            colors[i * 3] = 0; colors[i * 3 + 1] = 1; colors[i * 3 + 2] = 1; // Cyan
        } else {
            colors[i * 3] = 0.039; colors[i * 3 + 1] = 0.145; colors[i * 3 + 2] = 0.251; // Deep blue
        }
        sizes[i] = Math.random() * 3 + 1; // Variable size for depth
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const material = new THREE.PointsMaterial({
        size: 3,
        vertexColors: true,
        blending: THREE.AdditiveBlending,
        transparent: true,
        depthTest: false,
        sizeAttenuation: true // Perspective sizing
    });

    const starField = new THREE.Points(geometry, material);
    scene.add(starField);

    camera.position.z = 600;

    let mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
    });

    // Animation loop: Rotation + parallax
    function animate() {
        requestAnimationFrame(animate);
        starField.rotation.y += 0.0003;
        starField.rotation.x += 0.00015;
        camera.position.x += (mouseX * 50 - camera.position.x) * 0.01; // Parallax
        camera.position.y += (mouseY * 50 - camera.position.y) * 0.01;
        camera.lookAt(scene.position);
        renderer.render(scene, camera);
    }
    animate();

    // Resize
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

// Theme Toggle (Saves to localStorage)
function toggleTheme() {
    document.body.classList.toggle('dark');
    const isDark = document.body.classList.contains('dark');
    document.getElementById('theme-toggle').textContent = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// Load theme on start
if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark');
    document.getElementById('theme-toggle').textContent = '☀️ Light Mode';
}

init3DBackground();

// Auto-draft save (Extreme: Every 30s to localStorage)
setInterval(() => {
    const inputs = ['chat-prompt', 'memory-title', 'memory-content', 'project-name', 'code-input', 'seo-description', 'git-path'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.value) localStorage.setId = id; localStorage.setItem(id, el.value);
    });
}, 30000);

// Load drafts
window.addEventListener('load', () => {
    const inputs = ['chat-prompt', 'memory-title', 'memory-content', 'project-name', 'code-input', 'seo-description', 'git-path'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = localStorage.getItem(id) || '';
    });
});

// Enhanced API Handlers (With progress, smooth scroll to response)
async function apiPost(endpoint, data) {
    const responseDiv = data.responseSelector ? document.querySelector(data.responseSelector) : null;
    if (responseDiv) responseDiv.innerHTML = '<p class="loading">🔄 Processing... (Extreme Mode)</p>';
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...data.body, session_token: sessionToken })
        });
        if (!response.ok) throw new Error(await response.text());
        const result = await response.json();
        if (responseDiv) {
            responseDiv.innerHTML = `<p class="success">✅ ${result[Object.keys(result)[0]]}</p>`;
            responseDiv.scrollIntoView({ behavior: 'smooth' });
        }
        return result;
    } catch (error) {
        if (responseDiv) responseDiv.innerHTML = `<p class="error">❌ Error: ${error.message}</p>`;
        throw error;
    }
}

async function apiGet(endpoint, responseSelector) {
    const responseDiv = document.querySelector(responseSelector);
    if (responseDiv) responseDiv.innerHTML = '<p class="loading">🔄 Loading...</p>';
    
    try {
        const response = await fetch(`\( {endpoint}?session_token= \){sessionToken}`);
        if (!response.ok) throw new Error(await response.text());
        const result = await response.json();
        if (responseDiv) {
            responseDiv.innerHTML = result.memory ? 
                result.memory.map(m => `<div class="memory-item"><strong>\( {m.title}</strong><br> \){m.content}</div>`).join('') : 
                JSON.stringify(result, null, 2);
            responseDiv.scrollIntoView({ behavior: 'smooth' });
        }
        return result;
    } catch (error) {
        if (responseDiv) responseDiv.innerHTML = `<p class="error">❌ Error: ${error.message}</p>`;
        throw error;
    }
}

// Handlers (Updated with new structure)
async function handleChat() {
    const prompt = document.getElementById('chat-prompt').value;
    await apiPost('/chat', { body: { prompt }, responseSelector: '#chat-response' });
}

async function handleSaveMemory() {
    const title = document.getElementById('memory-title').value;
    const content = document.getElementById('memory-content').value;
    await apiPost('/save-memory', { body: { title, content }, responseSelector: '#save-memory-response' });
}

async function handleGetMemory() {
    await apiGet('/memory', '#memory-list');
}

async function handleCreateProject() {
    const name = document.getElementById('project-name').value;
    await apiPost('/create-project', { body: { name }, responseSelector: '#create-project-response' });
}

async function handleCodeReview() {
    const code = document.getElementById('code-input').value;
    await apiPost('/review-code', { body: { code }, responseSelector: '#code-review-response' });
}

async function handleGenerateSEO() {
    const description = document.getElementById('seo-description').value;
    await apiPost('/generate-seo', { body: { description }, responseSelector: '#seo-response' });
}

async function handleGitInit() {
    const path = document.getElementById('git-path').value;
    await apiPost('/init-git', { body: { path }, responseSelector: '#git-init-response' });
}

// Add CSS rule for memory-item
const style = document.createElement('style');
style.textContent = `
    .memory-item {
        margin-bottom: 15px;
        padding: 10px;
        background: rgba(0, 191, 255, 0.1);
        border-radius: 8px;
        border-left: 3px solid #00BFFF;
    }
    body.dark .memory-item { background: rgba(0, 255, 255, 0.1); }
`;
document.head.appendChild(style);
