const API_BASE = 'http://127.0.0.1:8000/api/auth';

const AUTH_PAGES = new Set(['login.html', 'signup.html', 'forgot-password.html', '']);

function getToken() {
    return localStorage.getItem('token');
}

function getUser() {
    const userRaw = localStorage.getItem('user');
    if (!userRaw) return null;
    try {
        return JSON.parse(userRaw);
    } catch (error) {
        return null;
    }
}

function setAuth(data) {
    if (data && data.token) {
        localStorage.setItem('token', data.token);
    }
    if (data && data.user) {
        localStorage.setItem('user', JSON.stringify(data.user));
    }
}

function requireAuthPayload(data) {
    if (!data || !data.token) {
        throw new Error('Login failed: token missing in response');
    }
    return data;
}

async function parseJsonSafe(response) {
    const text = await response.text();
    if (!text) return {};
    try {
        return JSON.parse(text);
    } catch (error) {
        return { message: text };
    }
}

function clearAuth() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

function redirectIfAuthed() {
    const token = getToken();
    const fileName = window.location.pathname.split('/').pop();
    if (token && AUTH_PAGES.has(fileName)) {
        window.location.href = 'index.html';
    }
}

async function validateToken() {
    const token = getToken();
    if (!token) return false;

    try {
        const response = await fetch(`${API_BASE}/validate`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`
            }
        });
        const data = await response.json();
        return Boolean(data && data.valid);
    } catch (error) {
        return false;
    }
}

redirectIfAuthed();

// Password visibility toggles
const passwordToggles = document.querySelectorAll('.password-toggle');
if (passwordToggles.length) {
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const targetId = toggle.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (!input) return;
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            toggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        });
    });
}

const homeSignIn = document.getElementById('homeSignIn');
if (homeSignIn) {
    homeSignIn.addEventListener('click', function (e) {
        e.preventDefault();
        window.location.href = 'login.html';
    });
}

const homeCreateAccount = document.getElementById('homeCreateAccount');
if (homeCreateAccount) {
    homeCreateAccount.addEventListener('click', function (e) {
        e.preventDefault();
        window.location.href = 'signup.html';
    });
}

// Signup
const signupForm = document.getElementById('signupForm');
if (signupForm) {
    signupForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const name = document.getElementById('name').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value.trim();

        if (!name || !email || !password) {
            alert('Please fill all fields');
            return;
        }

        if (password.length < 6) {
            alert('Password must be at least 6 characters');
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            alert('Please enter valid email');
            return;
        }

        fetch(`${API_BASE}/signup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, email, password, confirmPassword: password })
        })
            .then(async response => {
                const data = await parseJsonSafe(response);
                if (!response.ok) {
                    throw new Error(data.message || 'Signup failed');
                }
                return requireAuthPayload(data);
            })
            .then(data => {
                setAuth(data);
                window.location.replace('dashboard.html');
            })
            .catch(error => {
                const message = error && error.message ? error.message : 'Signup failed';
                if (message.toLowerCase().includes('fetch')) {
                    alert('Signup error: Backend not reachable. Start FastAPI on http://127.0.0.1:8000');
                } else {
                    alert('Signup error: ' + message);
                }
            });
    });
}

// Login
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value.trim();

        if (!email || !password) {
            alert('Please fill all fields');
            return;
        }

        fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        })
            .then(async response => {
                const data = await parseJsonSafe(response);
                if (!response.ok) {
                    throw new Error(data.message || 'Login failed');
                }
                return requireAuthPayload(data);
            })
            .then(data => {
                setAuth(data);
                window.location.replace('dashboard.html');
            })
            .catch(error => {
                const message = error && error.message ? error.message : 'Login failed';
                if (message.toLowerCase().includes('fetch')) {
                    alert('Login error: Backend not reachable. Start FastAPI on http://127.0.0.1:8000');
                } else {
                    alert('Login error: ' + message);
                }
            });
    });
}

// Forgot password (UI flow only)
const forgotPasswordForm = document.getElementById('forgotPasswordForm');
if (forgotPasswordForm) {
    forgotPasswordForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const email = document.getElementById('forgotEmail').value.trim();
        if (!email) {
            alert('Please enter your email');
            return;
        }

        alert(`Reset link sent to ${email}`);
        window.location.href = 'login.html';
    });
}

// Dashboard user data
const userNameElement = document.getElementById('userName');
if (userNameElement) {
    const userData = getUser();
    if (!userData || !getToken()) {
        window.location.href = 'login.html';
    } else {
        const safeName = userData.name ? userData.name : 'Learner';
        userNameElement.textContent = 'Hi, ' + safeName;
    }

    validateToken().then(isValid => {
        if (!isValid) {
            clearAuth();
            window.location.href = 'login.html';
        }
    });
}

if (window.location.pathname.endsWith('index.html') && getToken()) {
    validateToken().then(isValid => {
        if (!isValid) {
            clearAuth();
        }
    });
}

// Dashboard logout
const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', function () {
        clearAuth();
        window.location.href = 'login.html';
    });
}

// Profile page user data
const profileName = document.getElementById('profileName');
const profileEmail = document.getElementById('profileEmail');
const profileAvatar = document.getElementById('profileAvatar');
if (profileName && profileEmail && profileAvatar) {
    const userData = getUser();
    if (userData && getToken()) {
        profileName.textContent = userData.name || 'Learner';
        profileEmail.textContent = userData.email || 'Signed in';
        const initials = (userData.name || userData.email || 'U')
            .split(' ')
            .map(part => part[0])
            .join('')
            .slice(0, 2)
            .toUpperCase();
        profileAvatar.textContent = initials;
    } else {
        profileName.textContent = 'Guest User';
        profileEmail.textContent = 'No account connected';
        profileAvatar.textContent = '👤';
    }
}
