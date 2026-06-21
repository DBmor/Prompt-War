// ==========================================================================
// STATE MANAGEMENT & CONFIGS
// ==========================================================================

window.onerror = function(message, source, lineno, colno, error) {
    const div = document.createElement('div');
    div.style.position = 'fixed';
    div.style.bottom = '10px';
    div.style.left = '10px';
    div.style.background = 'rgba(239, 68, 68, 0.95)';
    div.style.color = 'white';
    div.style.padding = '15px';
    div.style.borderRadius = '8px';
    div.style.zIndex = '999999';
    div.style.fontFamily = 'monospace';
    div.style.fontSize = '12px';
    div.style.maxWidth = '90%';
    div.style.whiteSpace = 'pre-wrap';
    div.innerHTML = `<strong>JS Diagnostic Error:</strong> ${message}<br>at ${source}:${lineno}:${colno}`;
    document.body.appendChild(div);
    console.error(error);
    return false;
};

let currentUser = null;
let currentTab = 'auth';
let hasB2CAssessment = false;
let hasB2BAssessment = false;
let activeArticleId = null;
let articleTimer = null;
let articleTimeRemaining = 30;

// Card selection parameters for B2C Form
let selectedB2CInputs = {
    sex: 'female',
    body_composition: 'normal',
    dietary_preference: 'vegan',
    transit_mode: 'private_vehicle',
    fuel_type: 'petrol',
    monthly_distance: 2000
};

// Chart references to prevent duplication errors on re-rendering
let chartCompRef = null;
let chartBreakdownRef = null;

// On Page Load
document.addEventListener('DOMContentLoaded', () => {
    checkSession();
    initNeuralBackground();
});

function initNeuralBackground() {
    const canvas = document.getElementById('neural-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;
    
    // Resize handler
    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });
    
    // Parallax mouse position
    let mouse = { x: null, y: null, tx: 0, ty: 0 };
    window.addEventListener('mousemove', (e) => {
        mouse.tx = (e.clientX - width / 2) * 0.05;
        mouse.ty = (e.clientY - height / 2) * 0.05;
    });
    
    window.addEventListener('mouseleave', () => {
        mouse.tx = 0;
        mouse.ty = 0;
    });
    
    // Floating particles config
    const particleCount = Math.min(80, Math.floor((width * height) / 18000));
    const particles = [];
    const colors = [
        'rgba(52, 211, 153, 0.95)',  // Vibrant emerald green
        'rgba(16, 185, 129, 0.9)',   // Sea green
        'rgba(34, 211, 238, 0.95)',  // Brilliant teal / Cyan
        'rgba(96, 165, 250, 0.85)'   // Glowing blue
    ];
    
    // Initialize particles
    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.4,
            vy: (Math.random() - 0.5) * 0.4,
            radius: Math.random() * 2.5 + 1.5,
            color: colors[Math.floor(Math.random() * colors.length)]
        });
    }
    
    let px = 0;
    let py = 0;
    
    function animate() {
        requestAnimationFrame(animate);
        
        // Clear canvas with dark black base
        ctx.fillStyle = '#0b0f19';
        ctx.fillRect(0, 0, width, height);
        
        // Dynamic grid lines to look like gamified eco-blueprint
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.02)';
        ctx.lineWidth = 1;
        const gridSize = 80;
        for (let x = 0; x < width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        for (let y = 0; y < height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        
        // Soft mouse parallax interpolation
        px += (mouse.tx - px) * 0.08;
        py += (mouse.ty - py) * 0.08;
        
        // Update & draw particles
        particles.forEach((p) => {
            p.x += p.vx;
            p.y += p.vy;
            
            if (p.x < 0) p.x = width;
            if (p.x > width) p.x = 0;
            if (p.y < 0) p.y = height;
            if (p.y > height) p.y = 0;
            
            ctx.beginPath();
            ctx.arc(p.x + px, p.y + py, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.shadowBlur = 15;
            ctx.shadowColor = p.color;
            ctx.fill();
            ctx.shadowBlur = 0;
        });
        
        // Draw interconnected lines
        ctx.lineWidth = 0.8;
        for (let i = 0; i < particleCount; i++) {
            for (let j = i + 1; j < particleCount; j++) {
                const p1 = particles[i];
                const p2 = particles[j];
                
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist < 150) {
                    const alpha = (1 - dist / 150) * 0.22;
                    ctx.strokeStyle = `rgba(16, 185, 129, ${alpha})`;
                    ctx.beginPath();
                    ctx.moveTo(p1.x + px, p1.y + py);
                    ctx.lineTo(p2.x + px, p2.y + py);
                    ctx.stroke();
                }
            }
        }
    }
    
    animate();
}

// ==========================================================================
// SESSION & AUTHENTICATION HANDLERS
// ==========================================================================

// Tree Animation State Variables
let treeInterval = null;
let treeAnimationTimeout = null;

async function checkSession() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.status === 200) {
            currentUser = await res.json();
            onLoginSuccess(false);
        } else {
            showAuthScreen('login');
        }
    } catch (e) {
        showAuthScreen('login');
    }
}

function showAuthScreen(tab) {
    currentUser = null;
    const sidebar = document.getElementById('sidebar-container');
    const topBar = document.getElementById('top-bar-container');
    if (sidebar) sidebar.style.display = 'none';
    if (topBar) topBar.style.display = 'none';
    document.getElementById('points-container').style.display = 'none';
    document.getElementById('auth-buttons').style.display = 'block';
    
    switchView('view-auth');
    toggleAuthTab(tab);
}

function toggleAuthTab(type) {
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const formLogin = document.getElementById('form-login');
    const formRegister = document.getElementById('form-register');

    if (type === 'login') {
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
        formLogin.style.display = 'block';
        formRegister.style.display = 'none';
    } else {
        tabLogin.classList.remove('active');
        tabRegister.classList.add('active');
        formLogin.style.display = 'none';
        formRegister.style.display = 'block';
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    let originalText = "";
    if (submitBtn) {
        submitBtn.disabled = true;
        originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Signing In...';
    }

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (res.status === 200) {
            currentUser = data.user;
            onLoginSuccess(true);
            showNotification("Successfully logged in! Welcome back.", "success");
        } else {
            showNotification(data.error || "Login failed.", "danger");
        }
    } catch (err) {
        showNotification("Failed to connect to authentication server.", "danger");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    let originalText = "";
    if (submitBtn) {
        submitBtn.disabled = true;
        originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Creating Account...';
    }

    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const role = document.getElementById('reg-role').value;

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, role })
        });
        const data = await res.json();

        if (res.status === 210) {
            const loginRes = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if (loginRes.status === 200) {
                const loginData = await loginRes.json();
                currentUser = loginData.user;
                onLoginSuccess(true);
                showNotification("Registration successful! Welcome to BioLedger.", "success");
            }
        } else {
            showNotification(data.error || "Registration failed.", "danger");
        }
    } catch (err) {
        showNotification("Failed to connect to registration server.", "danger");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
}

async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        currentUser = null;
        showNotification("Logged out successfully.", "success");
        showAuthScreen('login');
    } catch (e) {
        showAuthScreen('login');
    }
}

function onLoginSuccess(playIntro = false) {
    document.getElementById('auth-buttons').style.display = 'none';
    
    // Fill the sidebar user profile metadata
    const avatarBadge = document.getElementById('user-avatar-badge');
    const displayFullname = document.getElementById('user-display-name');
    const displayRole = document.getElementById('user-display-role');
    
    if (currentUser) {
        displayFullname.textContent = currentUser.username;
        displayRole.textContent = currentUser.role === 'industrial' ? 'Industrial Owner' : currentUser.role === 'admin' ? 'Administrator' : 'Common User';
        avatarBadge.textContent = currentUser.username.substring(0, 2).toUpperCase();
    }
    
    // Update points display & points visibility (common users only)
    document.getElementById('points-val').textContent = currentUser.total_points;
    if (currentUser.role === 'common') {
        document.querySelectorAll('.common-only').forEach(el => el.style.display = 'flex');
        document.getElementById('points-container').style.display = 'flex';
    } else {
        document.querySelectorAll('.common-only').forEach(el => el.style.display = 'none');
        document.getElementById('points-container').style.display = 'none';
    }
    
    // Setup Navigation Sidebar and Topbar
    const sidebarContainer = document.getElementById('sidebar-container');
    const topBarContainer = document.getElementById('top-bar-container');
    if (sidebarContainer) sidebarContainer.style.display = 'flex';
    if (topBarContainer) topBarContainer.style.display = 'flex';
    
    // Display admin link if appropriate
    const adminLink = document.getElementById('nav-admin-panel');
    if (currentUser.role === 'admin') {
        if (adminLink) adminLink.style.display = 'flex';
    } else {
        if (adminLink) adminLink.style.display = 'none';
    }

    // Configure calculator forms depending on user role
    const calcB2c = document.getElementById('calc-b2c-wrapper');
    const calcB2b = document.getElementById('calc-b2b-wrapper');
    if (currentUser.role === 'industrial') {
        if (calcB2c) calcB2c.style.display = 'none';
        if (calcB2b) calcB2b.style.display = 'block';
    } else {
        if (calcB2c) calcB2c.style.display = 'block';
        if (calcB2b) calcB2b.style.display = 'none';
    }

    if (playIntro) {
        startTreeTransition();
    } else {
        switchTab('dashboard');
    }
}



// Tree shedding transition animations
function startTreeTransition() {
    const overlay = document.getElementById('login-tree-overlay');
    overlay.style.display = 'flex';
    overlay.classList.remove('fade-out');

    // Reset tree leaves
    const leaves = document.querySelectorAll('.transition-leaf');
    leaves.forEach(leaf => {
        leaf.classList.remove('wither', 'fall');
        leaf.setAttribute('fill', '#10B981');
    });

    // Clear any previous CO2 floats
    document.getElementById('co2-spawn-area').innerHTML = '';

    const statusEl = document.getElementById('tree-transition-status');
    statusEl.textContent = 'Auditing regional carbon load and forest canopy integrity...';

    let leafIndex = 0;
    const leafArray = Array.from(leaves);
    // Shuffle the leaves array so they fall in a random natural order
    leafArray.sort(() => Math.random() - 0.5);

    const totalLeaves = leafArray.length;

    if (treeInterval) clearInterval(treeInterval);
    if (treeAnimationTimeout) clearTimeout(treeAnimationTimeout);

    treeInterval = setInterval(() => {
        if (leafIndex >= totalLeaves) {
            clearInterval(treeInterval);
            treeInterval = null;
            statusEl.textContent = 'Canopy audit complete. High greenhouse gas levels detected!';
            
            treeAnimationTimeout = setTimeout(() => {
                endTreeTransition();
            }, 1200);
            return;
        }

        const leaf = leafArray[leafIndex];
        
        // 1. Wither: leaf turns brown
        leaf.classList.add('wither');
        
        // 2. Spawn floating CO2 indicator
        spawnCO2Bubble(leaf);
        
        // 3. Fall: leaf falls down
        setTimeout(() => {
            leaf.classList.add('fall');
        }, 150);

        // Update status text dynamically based on count
        const percentLost = Math.round(((leafIndex + 1) / totalLeaves) * 100);
        statusEl.textContent = `Canopy Integrity: -${percentLost}% (Releasing CO₂...)`;

        leafIndex++;
    }, 200);
}

function spawnCO2Bubble(leaf) {
    const area = document.getElementById('co2-spawn-area');
    const bubble = document.createElement('div');
    bubble.className = 'co2-bubble';
    bubble.textContent = 'CO₂';
    
    // Get the leaf coordinates from the SVG attributes
    const cx = parseFloat(leaf.getAttribute('cx'));
    const cy = parseFloat(leaf.getAttribute('cy'));
    
    // Convert coordinate percents to absolute positioning relative to container (SVG is viewBox 0 0 400 400)
    // tree-container width/height is 320px
    const scale = 320 / 400;
    const posX = cx * scale - 15; // center offset
    const posY = cy * scale - 10;
    
    bubble.style.left = `${posX}px`;
    bubble.style.top = `${posY}px`;
    
    area.appendChild(bubble);
    
    // Clean up bubble element after animation ends
    setTimeout(() => {
        bubble.remove();
    }, 2500);
}

function endTreeTransition() {
    const overlay = document.getElementById('login-tree-overlay');
    overlay.classList.add('fade-out');
    
    setTimeout(() => {
        overlay.style.display = 'none';
        switchTab('dashboard');
    }, 800);
}

function skipTreeIntro() {
    if (treeInterval) {
        clearInterval(treeInterval);
        treeInterval = null;
    }
    if (treeAnimationTimeout) {
        clearTimeout(treeAnimationTimeout);
        treeAnimationTimeout = null;
    }
    const overlay = document.getElementById('login-tree-overlay');
    overlay.classList.add('fade-out');
    setTimeout(() => {
        overlay.style.display = 'none';
        switchTab('dashboard');
    }, 200);
}

// ==========================================
// SPA NAVIGATION SYSTEM
// ==========================================

function checkCalculatorStatusAndRender() {
    const calcB2cWrapper = document.getElementById('calc-b2c-wrapper');
    const calcB2bWrapper = document.getElementById('calc-b2b-wrapper');
    const calcResultsContainer = document.getElementById('calc-results-container');
    
    // Set default fallbacks immediately to prevent blank screens
    const userRole = (currentUser && currentUser.role) ? currentUser.role : 'common';
    if (userRole === 'industrial') {
        if (calcB2bWrapper) calcB2bWrapper.style.display = 'block';
        if (calcB2cWrapper) calcB2cWrapper.style.display = 'none';
    } else {
        if (calcB2cWrapper) calcB2cWrapper.style.display = 'block';
        if (calcB2bWrapper) calcB2bWrapper.style.display = 'none';
    }
    if (calcResultsContainer) calcResultsContainer.style.display = 'none';
}

function switchTab(tabName) {
    currentTab = tabName;
    
    // Update sidebar links active class
    const links = document.querySelectorAll('.sidebar-link');
    links.forEach(link => {
        if (link.id === `nav-${tabName}`) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // Handle view switches and data loads
    if (tabName === 'dashboard') {
        switchView('view-dashboard');
        loadDashboardData();
    } else if (tabName === 'calculator') {
        switchView('view-calculator');
        checkCalculatorStatusAndRender();
    } else if (tabName === 'leaderboard') {
        if (currentUser.role !== 'common') {
            switchTab('dashboard');
            return;
        }
        switchView('view-leaderboard');
        loadLeaderboard();
    } else if (tabName === 'blogs') {
        switchView('view-blogs');
        loadBlogsFeed();
    } else if (tabName === 'articles') {
        switchView('view-articles');
        loadArticlesList();
    } else if (tabName === 'ai-coach') {
        if (currentUser.role !== 'common') {
            switchTab('dashboard');
            return;
        }
        switchView('view-ai-coach');
    } else if (tabName === 'admin-panel') {
        if (currentUser.role !== 'admin') {
            switchTab('dashboard');
            return;
        }
        switchView('view-admin-panel');
        loadAdminPanelData();
    }
}

function switchView(viewId) {
    const views = ['view-auth', 'view-dashboard', 'view-calculator', 'view-blogs', 'view-articles', 'view-admin-panel', 'view-leaderboard', 'view-ai-coach'];
    views.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (id === viewId) {
                el.style.display = 'block';
            } else {
                el.style.display = 'none';
            }
        }
    });
}

// ==========================================
// DASHBOARD DATA & CHARTING LOGIC
// ==========================================

async function loadDashboardData() {
    // 1. Sync User info for fresh points
    try {
        const userRes = await fetch('/api/auth/me');
        if (userRes.status === 200) {
            currentUser = await userRes.json();
            document.getElementById('points-val').textContent = currentUser.total_points;
        }
    } catch (e) {}

    // Toggle Role Dashboard Views
    const commonDash = document.getElementById('common-dashboard-view');
    const indDash = document.getElementById('industrial-dashboard-view');
    
    if (currentUser.role === 'industrial') {
        if (commonDash) commonDash.style.display = 'none';
        if (indDash) indDash.style.display = 'block';
    } else {
        if (commonDash) commonDash.style.display = 'block';
        if (indDash) indDash.style.display = 'none';
    }

    // 2. Set dashboard text greeting/title if they exist
    const heading = document.getElementById('dashboard-heading');
    const subheading = document.getElementById('dashboard-subheading');
    
    if (heading && subheading) {
        if (currentUser.role === 'admin') {
            heading.textContent = "Admin Control Panel";
            subheading.textContent = "Review carbon footprints, system audits, and moderate community green blogs.";
        } else if (currentUser.role === 'industrial') {
            heading.textContent = "Industrial Compliance Hub";
            subheading.textContent = "Manage heavy carbon intensity metrics, verification checks under India's BEE caps, and credits trade.";
        } else {
            heading.textContent = "Personal Sustainability Ledger";
            subheading.textContent = "Track your dietary choices, transport mileage, home energy usage, and grow your Eco Ledger.";
        }
    }

    // 3. Load Calculator History & Update Gauge / Industrial Metrics
    try {
        const res = await fetch('/api/calculator/history');
        if (res.status === 200) {
            const data = await res.json();
            renderHistoryLog(data);
            
            const statusBadge = document.getElementById('gauge-status-txt');
            const footprintValue = document.getElementById('gauge-footprint-value');
            const footprintUnit = document.getElementById('gauge-footprint-unit');
            const chartsCard = document.getElementById('analytics-charts-card');

            if (currentUser.role === 'industrial') {
                hasB2BAssessment = data.b2b.length > 0;
                // Update B2B Retake button text
                const retakeBtn = document.getElementById('btn-retake-compliance');
                if (retakeBtn) {
                    retakeBtn.innerHTML = hasB2BAssessment ? `🧮 Update Compliance Audit` : `🧮 Start Compliance Audit`;
                }

                if (data.b2b.length > 0) {
                    const latestB2B = data.b2b[0];
                    
                    // Update Industrial Dashboard DOM elements
                    document.getElementById('ind-dash-intensity').textContent = latestB2B.emission_intensity.toFixed(3);
                    document.getElementById('ind-dash-intensity-unit').textContent = latestB2B.sector === 'power' ? 'tCO₂e / MWh' : 'tCO₂e / unit output';
                    
                    const statusText = latestB2B.is_compliant ? 'COMPLIANT' : 'NON-COMPLIANT';
                    const statusEl = document.getElementById('ind-dash-status');
                    statusEl.textContent = statusText;
                    statusEl.style.color = latestB2B.is_compliant ? 'var(--mint-green)' : 'var(--crimson-alert)';
                    document.getElementById('ind-dash-cap').textContent = `Regulatory Cap: ${latestB2B.regulatory_cap.toFixed(2)}`;
                    
                    document.getElementById('ind-dash-credits').textContent = latestB2B.credits_earned.toFixed(2);
                    document.getElementById('ind-dash-scope1').textContent = latestB2B.scope1.toFixed(2) + ' t';
                    document.getElementById('ind-dash-scope2').textContent = latestB2B.scope2.toFixed(4) + ' t';

                    // Fetch Industrial Recommendations directly for Dashboard
                    try {
                        const mitRes = await fetch(`/api/calculator/b2b/${latestB2B.id}/mitigation`);
                        if (mitRes.status === 200) {
                            const mitData = await mitRes.json();
                            document.getElementById('ind-rec-easy').textContent = mitData.recommendations.easy;
                            document.getElementById('ind-rec-medium').textContent = mitData.recommendations.medium;
                            document.getElementById('ind-rec-hard').textContent = mitData.recommendations.hard;
                            document.getElementById('ind-mitigation-card').style.display = 'block';
                        }
                    } catch (e) {
                        document.getElementById('ind-mitigation-card').style.display = 'none';
                    }
                } else {
                    document.getElementById('ind-dash-intensity').textContent = '--';
                    document.getElementById('ind-dash-status').textContent = 'NO AUDIT';
                    document.getElementById('ind-dash-status').style.color = 'var(--text-secondary)';
                    document.getElementById('ind-dash-cap').textContent = 'Regulatory Cap: --';
                    document.getElementById('ind-dash-credits').textContent = '0.00';
                    document.getElementById('ind-dash-scope1').textContent = '0.00 t';
                    document.getElementById('ind-dash-scope2').textContent = '0.00 t';
                    document.getElementById('ind-mitigation-card').style.display = 'none';
                }
            } else {
                hasB2CAssessment = data.b2c.length > 0;
                // Update B2C Start button text and quick action labels
                const startBtn = document.getElementById('btn-start-assessment');
                if (startBtn) {
                    startBtn.innerHTML = hasB2CAssessment ? `<span class="btn-icon">🧮</span> Update Assessment` : `<span class="btn-icon">▶</span> Start Assessment`;
                }
                const qaTitle = document.getElementById('qa-calc-title');
                const qaDesc = document.getElementById('qa-calc-desc');
                if (qaTitle) {
                    qaTitle.textContent = hasB2CAssessment ? "Update Assessment" : "Start Assessment";
                }
                if (qaDesc) {
                    qaDesc.textContent = hasB2CAssessment ? "Retake your lifestyle calculator to adjust your baseline." : "Input your lifestyle parameters to calculate your footprint.";
                }

                // Common user dashboard footprint gauge
                if (footprintUnit) footprintUnit.textContent = 'KG CO₂ / YEAR';
                if (data.b2c.length > 0) {
                    const latestB2C = data.b2c[0];
                    if (footprintValue) footprintValue.textContent = Math.round(latestB2C.total_footprint).toLocaleString();
                    if (statusBadge) {
                        statusBadge.textContent = 'AUDITED';
                        statusBadge.className = 'badge';
                    }
                    
                    if (chartsCard) chartsCard.style.display = 'block';
                    renderB2CCharts(latestB2C);
                    loadMitigationAdvice('b2c', latestB2C.id);
                } else {
                    if (footprintValue) footprintValue.textContent = '--';
                    if (statusBadge) {
                        statusBadge.textContent = 'NO ASSESSMENT';
                        statusBadge.className = 'badge';
                    }
                    if (chartsCard) chartsCard.style.display = 'none';
                    const mitigationPanel = document.getElementById('mitigation-panel');
                    if (mitigationPanel) mitigationPanel.style.display = 'none';
                }

                // Load B2C dynamic points and offset logging statistics
                loadOffsetStats();
            }
        }
    } catch (err) {
        console.error("Failed to load calculation history log.", err);
    }
}

function renderHistoryLog(data) {
    const list = document.getElementById('history-log-list');
    if (!list) return; // Guard against missing container on dashboard
    list.innerHTML = '';
    
    if (currentUser.role === 'industrial') {
        if (data.b2b.length === 0) {
            list.innerHTML = '<p class="text-muted">No assessments logged yet.</p>';
            return;
        }
        data.b2b.forEach(item => {
            const date = new Date(item.recorded_at).toLocaleDateString();
            const badgeClass = item.is_compliant ? 'badge' : 'badge btn-danger';
            const complianceText = item.is_compliant ? 'Compliant' : 'Non-Compliant';

            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `
                <div class="history-item-header">
                    <span class="history-date">${date} - ${item.company_name}</span>
                    <span class="${badgeClass}">${complianceText}</span>
                </div>
                <div class="history-details">
                    <div>Intensity: <strong class="history-val">${item.emission_intensity.toFixed(3)}</strong> t/t</div>
                    <div>Credits: <strong>${item.credits_earned.toFixed(1)}</strong> CCCs</div>
                </div>
            `;
            list.appendChild(div);
        });
    } else {
        if (data.b2c.length === 0) {
            list.innerHTML = '<p class="text-muted">No assessments logged yet.</p>';
            return;
        }
        data.b2c.forEach(item => {
            const date = new Date(item.recorded_at).toLocaleDateString();
            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `
                <div class="history-item-header">
                    <span class="history-date">${date}</span>
                    <span class="history-val">${item.total_footprint.toFixed(1)} kg CO2e</span>
                </div>
                <div class="history-details">
                    <div>Diet: ${item.diet_footprint.toFixed(0)} kg</div>
                    <div>Transport: ${item.transport_footprint.toFixed(0)} kg</div>
                    <div>Energy: ${item.energy_footprint.toFixed(0)} kg</div>
                </div>
            `;
            list.appendChild(div);
        });
    }
}

// 4. Charting Renderers
async function renderB2CCharts(latestB2C) {
    try {
        const res = await fetch(`/api/analytics/b2c/${latestB2C.id}`);
        if (res.status !== 200) return;
        const data = await res.json();

        // Destroy previous chart contexts if they exist to avoid hover glitches
        if (chartCompRef) chartCompRef.destroy();
        if (chartBreakdownRef) chartBreakdownRef.destroy();

        // Chart 1: Comparison Bar Graph
        const ctxComp = document.getElementById('chartComparative').getContext('2d');
        chartCompRef = new Chart(ctxComp, {
            type: 'bar',
            data: {
                labels: ['Your Footprint', 'Global Target', 'India Baseline'],
                datasets: [{
                    label: 'Annual Emissions (kg CO2e)',
                    data: [
                        data.comparative_trend.user_actual,
                        data.comparative_trend.global_sustainable_average,
                        data.comparative_trend.national_indian_baseline
                    ],
                    backgroundColor: ['#10B981', '#06B6D4', '#f59e0b'],
                    borderColor: ['#047857', '#0891b2', '#d97706'],
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: 'Comparative Annual Footprint', color: '#f3f4f6' }
                },
                scales: {
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                    x: { ticks: { color: '#9ca3af' } }
                }
            }
        });

        // Chart 2: Slices Pie Chart
        const ctxBreak = document.getElementById('chartBreakdown').getContext('2d');
        chartBreakdownRef = new Chart(ctxBreak, {
            type: 'pie',
            data: {
                labels: ['Diet', 'Transport', 'Energy'],
                datasets: [{
                    data: [
                        data.categorical_breakdown['Diet & Food'],
                        data.categorical_breakdown['Transport'],
                        data.categorical_breakdown['Heating & Energy']
                    ],
                    backgroundColor: ['#ef4444', '#06b6d4', '#10b981'],
                    borderWidth: 1,
                    borderColor: '#111827'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Emissions Slices', color: '#f3f4f6' },
                    legend: { labels: { color: '#9ca3af' } }
                }
            }
        });
    } catch (e) {
        console.error(e);
    }
}

async function renderB2BCharts(latestB2B) {
    try {
        const res = await fetch(`/api/analytics/b2b/${latestB2B.id}`);
        if (res.status !== 200) return;
        const data = await res.json();

        if (chartCompRef) chartCompRef.destroy();
        if (chartBreakdownRef) chartBreakdownRef.destroy();

        // Chart 1: Actual vs Regulatory Cap
        const ctxComp = document.getElementById('chartComparative').getContext('2d');
        chartCompRef = new Chart(ctxComp, {
            type: 'bar',
            data: {
                labels: ['Actual Intensity', 'BEE Target Cap'],
                datasets: [{
                    label: 'Intensity (tonnes CO2e/tonne)',
                    data: [
                        data.intensity_vs_cap.user_intensity,
                        data.intensity_vs_cap.regulatory_cap
                    ],
                    backgroundColor: [
                        data.intensity_vs_cap.user_intensity <= data.intensity_vs_cap.regulatory_cap ? '#10B981' : '#EF4444',
                        '#06B6D4'
                    ],
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: `Intensity vs Cap (${data.sector.toUpperCase()})`, color: '#f3f4f6' }
                },
                scales: {
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                    x: { ticks: { color: '#9ca3af' } }
                }
            }
        });

        // Chart 2: Scope 1 vs Scope 2 breakdown
        const ctxBreak = document.getElementById('chartBreakdown').getContext('2d');
        chartBreakdownRef = new Chart(ctxBreak, {
            type: 'pie',
            data: {
                labels: ['Scope 1 (Direct)', 'Scope 2 (Indirect)'],
                datasets: [{
                    data: [
                        data.scopes_breakdown['Scope 1 (Direct)'],
                        data.scopes_breakdown['Scope 2 (Indirect)']
                    ],
                    backgroundColor: ['#f59e0b', '#10b981'],
                    borderWidth: 1,
                    borderColor: '#111827'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Scope 1 vs Scope 2 (tCO2e)', color: '#f3f4f6' },
                    legend: { labels: { color: '#9ca3af' } }
                }
            }
        });
    } catch (e) {
        console.error(e);
    }
}

// 5. Dynamic Recommendations Engine
async function loadMitigationAdvice(type, resultId) {
    try {
        const res = await fetch(`/api/calculator/${type}/${resultId}/mitigation`);
        if (res.status === 200) {
            const data = await res.json();
            
            document.getElementById('mitigation-panel').style.display = 'block';
            
            const badge = document.getElementById('highest-emitter-badge');
            if (type === 'b2c') {
                badge.textContent = `Highest Source: ${data.highest_emitting_category}`;
                badge.style.display = 'inline-block';
            } else {
                badge.textContent = `Status: ${data.compliance_status}`;
                badge.style.display = 'inline-block';
                // Adjust warning color depending on compliance
                if (data.compliance_status.includes("Non-Compliant")) {
                    badge.className = "badge btn-danger";
                } else {
                    badge.className = "badge";
                }
            }

            document.getElementById('rec-easy-txt').textContent = data.recommendations.easy;
            document.getElementById('rec-medium-txt').textContent = data.recommendations.medium;
            document.getElementById('rec-hard-txt').textContent = data.recommendations.hard;
        }
    } catch (e) {
        console.error(e);
    }
}

// ==========================================
// CALCULATOR SUBMISSIONS
// ==========================================

// Multi-step transitions for B2C Form
function nextB2CStep(stepNum) {
    const panels = ['b2c-step-1', 'b2c-step-2', 'b2c-step-3'];
    panels.forEach((id, idx) => {
        const panel = document.getElementById(id);
        if (idx === (stepNum - 1)) {
            panel.style.display = 'block';
        } else {
            panel.style.display = 'none';
        }
    });

    const indicators = ['step-ind-1', 'step-ind-2', 'step-ind-3'];
    indicators.forEach((id, idx) => {
        const ind = document.getElementById(id);
        if (idx === (stepNum - 1)) {
            ind.classList.add('active');
        } else {
            ind.classList.remove('active');
        }
    });
}

function selectCard(category, value, element) {
    const container = element.parentElement;
    const cards = container.querySelectorAll('.selector-card');
    cards.forEach(card => card.classList.remove('active'));
    
    element.classList.add('active');
    selectedB2CInputs[category] = value;
}

function toggleFuelRow(visible) {
    document.getElementById('fuel-type-container').style.display = visible ? 'block' : 'none';
    document.getElementById('distance-slider-container').style.display = visible || selectedB2CInputs.transit_mode === 'public_transit' ? 'block' : 'none';
}

function updateSliderDisplay(value) {
    document.getElementById('distance-val-display').textContent = Number(value).toLocaleString() + ' km';
    selectedB2CInputs.monthly_distance = parseFloat(value);
}

async function loadLeaderboard() {
    const box = document.getElementById('leaderboard-list-box');
    const podiumEl = document.getElementById('leaderboard-podium');
    const tableBodyEl = document.getElementById('leaderboard-table-body');
    
    try {
        const res = await fetch('/api/leaderboard');
        if (res.status === 200) {
            const list = await res.json();
            
            // A. Populate Homepage Sidebar List
            if (box) {
                box.innerHTML = '';
                if (list.length === 0) {
                    box.innerHTML = '<p class="text-muted" style="font-size: 0.85rem;">No registered user points ledger entries.</p>';
                } else {
                    list.forEach((user, idx) => {
                        const item = document.createElement('div');
                        item.className = 'leaderboard-item';
                        item.innerHTML = `
                            <div class="leaderboard-rank-user">
                                <span class="leaderboard-rank">${idx + 1}</span>
                                <span class="leaderboard-name">${user.username} <span style="font-size: 0.7rem; color: var(--text-secondary);">(${user.role})</span></span>
                            </div>
                            <span class="leaderboard-points">${user.total_points} <span>pts</span></span>
                        `;
                        box.appendChild(item);
                    });
                }
            }

            // B. Populate Dedicated Leaderboard page
            if (podiumEl && tableBodyEl) {
                podiumEl.innerHTML = '';
                tableBodyEl.innerHTML = '';

                if (list.length === 0) {
                    podiumEl.innerHTML = '<p class="text-muted text-center" style="grid-column: span 3; font-size: 0.9rem; padding: 2rem;">No registered user points ledger entries.</p>';
                    tableBodyEl.innerHTML = '<tr><td colspan="4" class="text-center text-muted" style="padding: 2rem;">No entries found.</td></tr>';
                    return;
                }

                // Gather ranks
                const top3 = list.slice(0, 3);
                const rest = list.slice(3);

                // Scaffold Podium (Top 3)
                // Order: 2nd place (left), 1st place (center), 3rd place (right)
                const user1 = top3[0] || { username: 'Empty', role: 'common', total_points: 0 };
                const user2 = top3[1] || { username: 'Empty', role: 'common', total_points: 0 };
                const user3 = top3[2] || { username: 'Empty', role: 'common', total_points: 0 };

                // 2nd Place Column
                const col2 = document.createElement('div');
                col2.className = 'podium-col rank-2';
                col2.innerHTML = `
                    <div class="podium-badge">🥈</div>
                    <div class="podium-card glass-card">
                        <span class="podium-name">${user2.username}</span>
                        <span style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.2rem; text-transform: capitalize;">${user2.role}</span>
                        <span class="podium-pts">${user2.total_points} pts</span>
                        <div class="podium-bar"></div>
                    </div>
                `;
                podiumEl.appendChild(col2);

                // 1st Place Column
                const col1 = document.createElement('div');
                col1.className = 'podium-col rank-1';
                col1.innerHTML = `
                    <div class="podium-badge">👑</div>
                    <div class="podium-card glass-card" style="border-color: rgba(245, 158, 11, 0.25);">
                        <span class="podium-name" style="color: var(--warning-gold); font-size: 1.25rem;">${user1.username}</span>
                        <span style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.2rem; text-transform: capitalize;">${user1.role}</span>
                        <span class="podium-pts" style="font-size: 1.05rem; font-weight: 700;">${user1.total_points} pts</span>
                        <div class="podium-bar"></div>
                    </div>
                `;
                podiumEl.appendChild(col1);

                // 3rd Place Column
                const col3 = document.createElement('div');
                col3.className = 'podium-col rank-3';
                col3.innerHTML = `
                    <div class="podium-badge">🥉</div>
                    <div class="podium-card glass-card">
                        <span class="podium-name">${user3.username}</span>
                        <span style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.2rem; text-transform: capitalize;">${user3.role}</span>
                        <span class="podium-pts">${user3.total_points} pts</span>
                        <div class="podium-bar"></div>
                    </div>
                `;
                podiumEl.appendChild(col3);

                // Populate Rest (Ranks 4-10) in table
                if (rest.length === 0) {
                    tableBodyEl.innerHTML = '<tr><td colspan="4" class="text-center text-muted" style="padding: 1.5rem 0;">No further rankings registered.</td></tr>';
                } else {
                    rest.forEach((user, idx) => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td style="padding-left: 2rem; font-weight: 700; color: var(--text-secondary);">${idx + 4}</td>
                            <td style="font-weight: 600;">${user.username}</td>
                            <td class="text-muted" style="text-transform: capitalize;">${user.role}</td>
                            <td style="padding-right: 2rem; text-align: right; font-weight: 700; color: var(--mint-green);">${user.total_points} <span style="font-size: 0.75rem; font-weight: normal; color: var(--text-secondary);">pts</span></td>
                        `;
                        tableBodyEl.appendChild(tr);
                    });
                }
            }
        }
    } catch (e) {
        if (box) box.innerHTML = '<p class="text-muted" style="font-size: 0.85rem;">Failed to fetch leaderboard.</p>';
        if (podiumEl) podiumEl.innerHTML = '<p class="text-muted text-center" style="grid-column: span 3; padding: 2rem;">Failed to load leaderboard standings.</p>';
    }
}

async function submitB2C(e) {
    e.preventDefault();
    const payload = {
        sex: selectedB2CInputs.sex,
        body_composition: selectedB2CInputs.body_composition,
        dietary_preference: selectedB2CInputs.dietary_preference,
        transit_mode: selectedB2CInputs.transit_mode,
        fuel_type: selectedB2CInputs.transit_mode === 'private_vehicle' ? selectedB2CInputs.fuel_type : 'none',
        monthly_distance: selectedB2CInputs.transit_mode === 'walk_bicycle' ? 0.0 : selectedB2CInputs.monthly_distance,
        monthly_kwh: parseFloat(document.getElementById('b2c-kwh').value) || 0.0
    };

    try {
        const res = await fetch('/api/calculator/b2c', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (res.status === 201) {
            showNotification(`Lifestyle footprint calculation complete! You earned +${data.points_earned} points.`, "success");
            nextB2CStep(1);
            document.getElementById('form-calc-b2c').reset();
            
            // Reset selection state
            selectedB2CInputs = {
                sex: 'female',
                body_composition: 'normal',
                dietary_preference: 'vegan',
                transit_mode: 'private_vehicle',
                fuel_type: 'petrol',
                monthly_distance: 2000
            };
            
            // Switch back to dashboard to display new charts
            switchTab('dashboard');
        } else {
            showNotification(data.error || "Failed to submit calculation.", "danger");
        }
    } catch (err) {
        showNotification("Failed to submit calculation.", "danger");
    }
}

async function submitB2B(e) {
    e.preventDefault();
    const payload = {
        company_name: document.getElementById('b2b-company').value,
        sector: document.getElementById('b2b-sector').value,
        coal_tonnes: parseFloat(document.getElementById('b2b-coal').value) || 0,
        diesel_liters: parseFloat(document.getElementById('b2b-diesel').value) || 0,
        process_emissions: parseFloat(document.getElementById('b2b-process').value) || 0,
        grid_kwh: parseFloat(document.getElementById('b2b-grid').value) || 0,
        production_output: parseFloat(document.getElementById('b2b-output').value) || 0
    };

    try {
        const res = await fetch('/api/calculator/b2b', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.status === 201) {
            const result = data.result;
            
            // Populate Modal Fields
            document.getElementById('b2b-modal-intensity').textContent = result.emission_intensity.toFixed(3);
            document.getElementById('b2b-modal-cap').textContent = result.regulatory_cap.toFixed(2);
            document.getElementById('b2b-modal-scope1').textContent = result.scope1.toFixed(2);
            document.getElementById('b2b-modal-scope2').textContent = result.scope2.toFixed(4);
            
            const banner = document.getElementById('b2b-modal-status-banner');
            const statusTitle = document.getElementById('b2b-modal-status-title');
            const statusDesc = document.getElementById('b2b-modal-status-desc');
            const creditsDesc = document.getElementById('b2b-modal-credits-desc');
            
            if (result.is_compliant) {
                banner.className = 'compliance-banner compliant';
                statusTitle.textContent = 'STATUS: COMPLIANT';
                statusDesc.textContent = `Excellent! Your facility's carbon intensity (${result.emission_intensity.toFixed(3)} tCO₂e/tonne) complies with the regulatory cap of ${result.regulatory_cap} tCO₂e/tonne.`;
                creditsDesc.textContent = `SUCCESS: Earned +${result.credits_earned.toFixed(1)} Carbon Credit Certificates (CCCs) for trading under CCTS rules.`;
                creditsDesc.style.color = 'var(--mint-green)';
            } else {
                banner.className = 'compliance-banner non-compliant';
                statusTitle.textContent = 'STATUS: NON-COMPLIANT';
                statusDesc.textContent = `Warning! Your carbon intensity (${result.emission_intensity.toFixed(3)} tCO₂e/tonne) exceeds the regulatory cap of ${result.regulatory_cap} tCO₂e/tonne.`;
                creditsDesc.textContent = `WARNING: Subject to National Green Tribunal (NGT) / CCTS financial penalty structures.`;
                creditsDesc.style.color = 'var(--crimson-alert)';
            }
            
            // Fetch B2B solutions directly from the backend API
            try {
                const mitRes = await fetch(`/api/calculator/b2b/${result.id}/mitigation`);
                if (mitRes.status === 200) {
                    const mitData = await mitRes.json();
                    document.getElementById('b2b-modal-rec-easy').textContent = mitData.recommendations.easy;
                    document.getElementById('b2b-modal-rec-medium').textContent = mitData.recommendations.medium;
                    document.getElementById('b2b-modal-rec-hard').textContent = mitData.recommendations.hard;
                }
            } catch (err) {
                document.getElementById('b2b-modal-rec-easy').textContent = "Conduct HVAC energy audits to optimize heating loops.";
                document.getElementById('b2b-modal-rec-medium').textContent = "Implement waste heat recovery on exhaust chambers.";
                document.getElementById('b2b-modal-rec-hard').textContent = "Transition boilers to biomass or green hydrogen.";
            }

            showNotification("Industrial compliance audit completed successfully!", "success");
            document.getElementById('form-calc-b2b').reset();
            
            // Open the Modal
            document.getElementById('b2b-result-modal').style.display = 'flex';
        } else {
            showNotification(data.error || "Failed to log B2B audit data.", "danger");
        }
    } catch (err) {
        showNotification("Connection error submitting industrial parameters.", "danger");
    }
}

function closeB2BResultModal() {
    document.getElementById('b2b-result-modal').style.display = 'none';
    switchTab('dashboard');
}

// ==========================================
// AWARENESS ENGINE & READING MODAL TIMER
// ==========================================

async function loadArticlesList() {
    const deck = document.getElementById('articles-deck');
    deck.innerHTML = '<p class="text-muted">Loading awareness library...</p>';

    try {
        const res = await fetch('/api/articles');
        if (res.status === 200) {
            const list = await res.json();
            deck.innerHTML = '';
            
            if (list.length === 0) {
                deck.innerHTML = '<p class="text-muted">No awareness articles seeded.</p>';
                return;
            }

            list.forEach(art => {
                const card = document.createElement('div');
                card.className = 'glass-card article-card';
                card.innerHTML = `
                    <div class="article-card-body-wrapper">
                        <div class="article-card-header">
                            <h3>${art.title}</h3>
                        </div>
                        <div class="article-card-body">
                            ${art.content}
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="openArticle(${art.id}, '${art.title.replace(/'/g, "\\'")}', '${art.content.replace(/'/g, "\\'")}')">Read Article & Earn +10 Pts</button>
                `;
                deck.appendChild(card);
            });
        }
    } catch (e) {
        deck.innerHTML = '<p class="text-muted">Failed to load articles.</p>';
    }
}

async function openArticle(id, title, content) {
    activeArticleId = id;
    document.getElementById('modal-article-title').textContent = title;
    document.getElementById('modal-article-body').textContent = content;
    
    // Reset timer progress variables
    articleTimeRemaining = 30;
    document.getElementById('timer-progress-fill-element').style.width = '0%';
    document.getElementById('timer-label-text').textContent = `Verifying engagement: 30s remaining`;
    document.getElementById('btn-claim-points').disabled = true;
    document.getElementById('timer-box').style.display = 'flex';

    // Show modal overlay
    document.getElementById('article-reader-modal').style.display = 'flex';

    // Call start-read API
    try {
        await fetch(`/api/articles/${id}/start-read`, { method: 'POST' });
    } catch (e) {}

    // Clear any active timers
    if (articleTimer) clearInterval(articleTimer);

    // Launch countdown progress
    articleTimer = setInterval(() => {
        articleTimeRemaining--;
        let percentage = ((30 - articleTimeRemaining) / 30) * 100;
        document.getElementById('timer-progress-fill-element').style.width = `${percentage}%`;
        
        if (articleTimeRemaining > 0) {
            document.getElementById('timer-label-text').textContent = `Verifying engagement: ${articleTimeRemaining}s remaining`;
        } else {
            clearInterval(articleTimer);
            document.getElementById('timer-label-text').textContent = "Engagement Verified! You can now claim your points.";
            document.getElementById('btn-claim-points').disabled = false;
        }
    }, 1000);
}

function closeArticleModal() {
    if (articleTimer) clearInterval(articleTimer);
    document.getElementById('article-reader-modal').style.display = 'none';
    activeArticleId = null;
}

async function claimArticlePoints() {
    if (!activeArticleId) return;
    
    try {
        const res = await fetch(`/api/articles/${activeArticleId}/complete-read`, { method: 'POST' });
        const data = await res.json();
        
        if (res.status === 200) {
            if (data.points_earned > 0) {
                showNotification(`Read verified! +${data.points_earned} points credited.`, "success");
            } else {
                showNotification("Read verified! Points had already been claimed for this article.", "success");
            }
            // Update points val on UI
            document.getElementById('points-val').textContent = data.total_points;
            closeArticleModal();
        } else {
            showNotification(data.error || "Timer check failed. Points not awarded.", "danger");
        }
    } catch (e) {
        showNotification("Failed to finalize reading validation.", "danger");
    }
}

// ==========================================
// COMMUNITY BLOGGING PORTAL
// ==========================================

async function loadBlogsFeed() {
    const list = document.getElementById('blogs-feed-list');
    list.innerHTML = '<p class="text-muted">Loading community feed...</p>';

    try {
        const res = await fetch('/api/blogs');
        if (res.status === 200) {
            const blogs = await res.json();
            list.innerHTML = '';
            
            if (blogs.length === 0) {
                list.innerHTML = '<p class="text-muted">No approved blogs published yet. Be the first to submit a draft!</p>';
                return;
            }

            // Fetch list of user comments/likes for rendering
            blogs.forEach(b => {
                const date = new Date(b.created_at).toLocaleDateString();
                const card = document.createElement('div');
                card.className = 'glass-card blog-post-card';
                card.id = `blog-post-${b.id}`;
                card.innerHTML = `
                    <div class="blog-post-header">
                        <span class="blog-author-meta">By <strong>${b.author}</strong> on ${date}</span>
                    </div>
                    <h3 class="blog-post-title">${b.title}</h3>
                    <div class="blog-body-text">${b.content}</div>
                    
                    <div class="blog-actions-bar">
                        <button class="action-btn-like" onclick="likeBlogPost(${b.id})">
                            ❤ <span id="like-count-${b.id}">${b.likes_count}</span> Likes
                        </button>
                        <span class="comment-count-meta">💬 ${b.comments_count} Comments</span>
                    </div>
                    
                    <div class="comments-thread">
                        <div class="comments-list-box" id="comments-box-${b.id}">
                            <p class="text-muted" style="font-size: 0.8rem;">Loading comments...</p>
                        </div>
                        <form class="comment-input-row" onsubmit="postComment(event, ${b.id})">
                            <input type="text" placeholder="Write a comment..." required id="comment-input-${b.id}">
                            <button type="submit" class="btn btn-primary btn-sm">Comment (+5 Pts)</button>
                        </form>
                    </div>
                `;
                list.appendChild(card);
                loadBlogComments(b.id);
            });
        }
    } catch (e) {
        list.innerHTML = '<p class="text-muted">Failed to load blogs feed.</p>';
    }
}

async function loadBlogComments(blogId) {
    const box = document.getElementById(`comments-box-${blogId}`);
    try {
        const res = await fetch('/api/blogs');
        if (res.status === 200) {
            const blogs = await res.json();
            const matching = blogs.find(x => x.id === blogId);
            box.innerHTML = '';
            
            if (matching && matching.comments && matching.comments.length > 0) {
                matching.comments.forEach(c => {
                    const bubble = document.createElement('div');
                    bubble.className = 'comment-bubble';
                    bubble.innerHTML = `<span class="comment-author">${c.author}:</span> ${c.content}`;
                    box.appendChild(bubble);
                });
            } else {
                box.innerHTML = '<p class="text-muted" style="font-size: 0.8rem;">No comments yet.</p>';
            }
        }
    } catch (e) {
        box.innerHTML = '<p class="text-muted" style="font-size: 0.8rem;">Failed to load comments.</p>';
    }
}

async function likeBlogPost(blogId) {
    try {
        const res = await fetch(`/api/routes/blogs/${blogId}/like`, { method: 'POST' }); // wait, URL is /api/blogs/<id>/like
        // Let's double check route URL: routes_bp prefix is '/api'.
        // So the endpoint is `/api/blogs/<id>/like`.
        const likesRes = await fetch(`/api/blogs/${blogId}/like`, { method: 'POST' });
        const data = await likesRes.json();
        
        if (likesRes.status === 200) {
            document.getElementById(`like-count-${blogId}`).textContent = data.likes_count;
        }
    } catch (e) {
        console.error(e);
    }
}

async function postComment(e, blogId) {
    e.preventDefault();
    const input = document.getElementById(`comment-input-${blogId}`);
    const content = input.value;

    try {
        const res = await fetch(`/api/blogs/${blogId}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
        const data = await res.json();

        if (res.status === 201) {
            input.value = '';
            showNotification(`Comment posted successfully! +5 points awarded.`, "success");
            
            // Update points val on UI
            document.getElementById('points-val').textContent = data.total_points;
            
            // Reload blogs to display new comment
            loadBlogsFeed();
        } else {
            showNotification(data.error || "Failed to post comment.", "danger");
        }
    } catch (err) {
        showNotification("Failed to post comment.", "danger");
    }
}

async function submitBlog(e) {
    e.preventDefault();
    const title = document.getElementById('blog-title').value;
    const content = document.getElementById('blog-content').value;

    try {
        const res = await fetch('/api/blogs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content })
        });
        const data = await res.json();

        if (res.status === 201) {
            showNotification("Green Log submitted for review! Check back soon for admin approval (+100 Points).", "success");
            document.getElementById('form-create-blog').reset();
            // Reload blogs queue (if we are admin) or feed
            loadBlogsFeed();
        } else {
            showNotification(data.error || "Failed to submit blog draft.", "danger");
        }
    } catch (err) {
        showNotification("Failed to submit blog draft.", "danger");
    }
}

// ==========================================
// ADMIN WORKFLOWS
// ==========================================

async function loadAdminPanelData() {
    const tableBody = document.getElementById('admin-pending-table-body');
    tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Loading verification queue...</td></tr>';

    try {
        const res = await fetch('/api/admin/blogs/pending');
        if (res.status === 200) {
            const list = await res.json();
            tableBody.innerHTML = '';
            
            if (list.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No pending blogs in the verification queue.</td></tr>';
                return;
            }

            list.forEach(b => {
                const tr = document.createElement('tr');
                tr.id = `admin-row-${b.id}`;
                tr.innerHTML = `
                    <td><strong>${b.author}</strong></td>
                    <td>${b.title}</td>
                    <td class="text-muted"><em>${b.content.substring(0, 50)}...</em></td>
                    <td class="actions-cell">
                        <button class="btn btn-success btn-sm" onclick="moderateBlog(${b.id}, 'approve')">Approve (+100)</button>
                        <button class="btn btn-danger btn-sm" onclick="moderateBlog(${b.id}, 'reject')">Reject</button>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        }
    } catch (e) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Failed to load moderation queues.</td></tr>';
    }
}

async function moderateBlog(id, action) {
    try {
        const res = await fetch(`/api/admin/blogs/${id}/${action}`, { method: 'POST' });
        const data = await res.json();
        
        if (res.status === 200) {
            showNotification(`Blog draft successfully ${action}ed!`, "success");
            // Remove row from table
            const row = document.getElementById(`admin-row-${id}`);
            if (row) row.remove();
            
            // If table is now empty, reset message
            const tableBody = document.getElementById('admin-pending-table-body');
            if (tableBody.children.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No pending blogs in the verification queue.</td></tr>';
            }
        } else {
            showNotification(data.error || `Failed to ${action} blog.`, "danger");
        }
    } catch (e) {
        showNotification("Failed to contact moderation endpoints.", "danger");
    }
}

// ==========================================
// NOTIFICATIONS BANNER UTILS
// ==========================================

function showNotification(msg, type) {
    const banner = document.getElementById('notification-banner');
    const txt = document.getElementById('notification-msg');
    
    txt.textContent = msg;
    banner.className = `notification ${type}`;
    banner.style.display = 'flex';
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        banner.style.display = 'none';
    }, 5000);
}

function closeNotification() {
    document.getElementById('notification-banner').style.display = 'none';
}

// ==========================================
// DYNAMIC OFFSET LOGGING & AI COACH ENGINE
// ==========================================

let chatHistory = [];

async function loadOffsetStats() {
    try {
        const res = await fetch('/api/actions/stats');
        if (res.status === 200) {
            const data = await res.json();
            
            // Populate metrics-row
            const baselineEl = document.getElementById('metric-baseline');
            const monthlyEl = document.getElementById('metric-monthly');
            const totalEl = document.getElementById('metric-total-offset');
            const milestonesEl = document.getElementById('metric-milestones');

            if (baselineEl) {
                baselineEl.textContent = data.baseline > 0 ? `${Math.round(data.baseline).toLocaleString()} kg` : 'Take assessment';
            }
            if (monthlyEl) {
                monthlyEl.textContent = `${data.monthly_progress.toFixed(1)} kg`;
            }
            if (totalEl) {
                totalEl.textContent = `${data.total_offset.toFixed(1)} kg`;
            }
            if (milestonesEl) {
                milestonesEl.textContent = data.milestones;
            }
        }
    } catch (e) {
        console.error("Failed to load offset stats", e);
    }
}

async function handleLogAction(category, actionName, co2Saved, pointsEarned) {
    if (currentUser.role !== 'common') {
        showNotification("Points action is only available for common users.", "danger");
        return;
    }
    
    try {
        const res = await fetch('/api/actions/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: category,
                action_name: actionName,
                co2_saved: co2Saved,
                points_earned: pointsEarned
            })
        });
        const data = await res.json();
        
        if (res.status === 201) {
            showNotification(`Logged Action: ${actionName}! +${pointsEarned} points.`, "success");
            // Update points val on top bar
            document.getElementById('points-val').textContent = data.total_points;
            // Refresh stats on dashboard
            loadOffsetStats();
        } else {
            showNotification(data.error || "Failed to log action.", "danger");
        }
    } catch (e) {
        showNotification("Network error while logging action.", "danger");
    }
}

// AI Coach Chat handlers
async function handleSendCoachMessage(e) {
    if (e) e.preventDefault();
    
    const inputEl = document.getElementById('coach-message-input');
    const msg = inputEl.value.trim();
    if (!msg) return;
    
    inputEl.value = '';
    
    // Add user message to UI
    appendCoachMessage('user', msg);
    
    // Add loading indicator bubble
    const messagesBox = document.getElementById('chat-messages');
    const loadingBubble = document.createElement('div');
    loadingBubble.className = 'chat-bubble coach loading';
    loadingBubble.id = 'coach-loading-bubble';
    loadingBubble.innerHTML = `<p>Coach is writing...</p>`;
    messagesBox.appendChild(loadingBubble);
    messagesBox.scrollTop = messagesBox.scrollHeight;
    
    try {
        const res = await fetch('/api/ai/coach', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                history: chatHistory
            })
        });
        const data = await res.json();
        
        // Remove loading bubble
        const bubble = document.getElementById('coach-loading-bubble');
        if (bubble) bubble.remove();
        
        if (res.status === 200) {
            appendCoachMessage('model', data.reply);
            
            // Update local conversation history
            chatHistory.push({ role: 'user', text: msg });
            chatHistory.push({ role: 'model', text: data.reply });
        } else {
            appendCoachMessage('model', `Sorry, I encountered an error: ${data.error || 'Server error'}`);
        }
    } catch (err) {
        const bubble = document.getElementById('coach-loading-bubble');
        if (bubble) bubble.remove();
        appendCoachMessage('model', "Sorry, I am unable to connect to the Sustainability Coach right now.");
    }
}

function sendStarterMessage(text) {
    const inputEl = document.getElementById('coach-message-input');
    inputEl.value = text;
    handleSendCoachMessage();
}

function appendCoachMessage(role, text) {
    const messagesBox = document.getElementById('chat-messages');
    if (!messagesBox) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role === 'user' ? 'user' : 'coach'}`;
    
    // Simple markdown replacement for bold/headers in replies
    let formattedText = text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');

    bubble.innerHTML = `<p>${formattedText}</p>`;
    messagesBox.appendChild(bubble);
    messagesBox.scrollTop = messagesBox.scrollHeight;
}

