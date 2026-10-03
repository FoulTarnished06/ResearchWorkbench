/**
 * User Authentication & Session Management Module (AUTH-01)
 * Handles registration, login, JWT storage, auth headers, and UI state synchronization.
 */

const KEY_TOKEN = "workbench_auth_token";
const KEY_USER = "workbench_auth_user";

export function getAuthToken() {
  try {
    return localStorage.getItem(KEY_TOKEN) || "";
  } catch (e) {
    return "";
  }
}

export function getCurrentUser() {
  try {
    const raw = localStorage.getItem(KEY_USER);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export function getAuthHeaders(customHeaders = {}) {
  const token = getAuthToken();
  const headers = { ...customHeaders };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export function setAuthSession(token, user) {
  try {
    if (token) localStorage.setItem(KEY_TOKEN, token);
    if (user) localStorage.setItem(KEY_USER, JSON.stringify(user));
  } catch (e) {
    console.warn("Failed to write auth session to localStorage", e);
  }
  updateAuthUI();
}

export async function clearAuthSession() {
  try {
    localStorage.removeItem(KEY_TOKEN);
    localStorage.removeItem(KEY_USER);
  } catch (e) {
    console.warn("Failed to clear auth session from localStorage", e);
  }
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch (e) {
    // Non-blocking logout network error
  }
  updateAuthUI();
}

export function getInitials(name) {
  if (!name) return "RF";
  const parts = name.trim().split(/[\s_\-]+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export function updateAuthUI() {
  const user = getCurrentUser();
  const token = getAuthToken();

  const dockName = document.getElementById("dock-user-name");
  const dockRole = document.getElementById("dock-user-role");
  const dockInitials = document.getElementById("dock-avatar-initials");
  const topAuthIcon = document.getElementById("top-auth-icon");

  const loginTab = document.getElementById("auth-tab-login");
  const regTab = document.getElementById("auth-tab-register");
  const tabsContainer = document.querySelector(".auth-tabs");
  const loginForm = document.getElementById("auth-login-form");
  const regForm = document.getElementById("auth-register-form");
  const profileBox = document.getElementById("auth-profile-view");

  const profileAvatar = document.getElementById("profile-avatar-display");
  const profileName = document.getElementById("profile-name-display");
  const profileEmail = document.getElementById("profile-email-display");
  const profileRole = document.getElementById("profile-role-display");

  if (user && token) {
    const initials = getInitials(user.username);
    if (dockName) dockName.textContent = user.username;
    if (dockRole) dockRole.textContent = `Online (${user.role || "Researcher"})`;
    if (dockInitials) dockInitials.textContent = initials;
    if (topAuthIcon) topAuthIcon.textContent = "👤";

    // Inside modal, show profile box
    if (tabsContainer) tabsContainer.style.display = "none";
    if (loginForm) loginForm.style.display = "none";
    if (regForm) regForm.style.display = "none";
    if (profileBox) profileBox.style.display = "flex";

    if (profileAvatar) profileAvatar.textContent = initials;
    if (profileName) profileName.textContent = user.username;
    if (profileEmail) profileEmail.textContent = user.email;
    if (profileRole) profileRole.textContent = `Role: ${user.role || "Researcher"}`;
  } else {
    if (dockName) dockName.textContent = "Guest Researcher";
    if (dockRole) dockRole.textContent = "Sign In / Register";
    if (dockInitials) dockInitials.textContent = "RF";
    if (topAuthIcon) topAuthIcon.textContent = "👤";

    if (tabsContainer) tabsContainer.style.display = "flex";
    if (profileBox) profileBox.style.display = "none";
    // Default to login tab
    switchAuthTab("login");
  }
}

export function showAuthAlert(msg, type = "error") {
  const alertEl = document.getElementById("auth-alert");
  if (!alertEl) return;
  alertEl.textContent = msg;
  alertEl.className = `auth-alert ${type}`;
  alertEl.style.display = "block";
}

export function hideAuthAlert() {
  const alertEl = document.getElementById("auth-alert");
  if (alertEl) alertEl.style.display = "none";
}

export function switchAuthTab(tab) {
  const loginTab = document.getElementById("auth-tab-login");
  const regTab = document.getElementById("auth-tab-register");
  const loginForm = document.getElementById("auth-login-form");
  const regForm = document.getElementById("auth-register-form");
  hideAuthAlert();

  if (tab === "register") {
    if (loginTab) {
      loginTab.classList.remove("active");
      loginTab.setAttribute("aria-selected", "false");
    }
    if (regTab) {
      regTab.classList.add("active");
      regTab.setAttribute("aria-selected", "true");
    }
    if (loginForm) loginForm.style.display = "none";
    if (regForm) regForm.style.display = "flex";
  } else {
    if (regTab) {
      regTab.classList.remove("active");
      regTab.setAttribute("aria-selected", "false");
    }
    if (loginTab) {
      loginTab.classList.add("active");
      loginTab.setAttribute("aria-selected", "true");
    }
    if (regForm) regForm.style.display = "none";
    if (loginForm) loginForm.style.display = "flex";
  }
}

export function openAuthModal(defaultTab = "login") {
  const modal = document.getElementById("auth-modal");
  if (!modal) return;
  updateAuthUI();
  if (!getCurrentUser()) {
    switchAuthTab(defaultTab);
  }
  hideAuthAlert();
  modal.style.display = "flex";
  modal.removeAttribute("inert");
}

export function closeAuthModal() {
  const modal = document.getElementById("auth-modal");
  if (!modal) return;
  modal.style.display = "none";
  modal.setAttribute("inert", "");
  hideAuthAlert();
}

export async function loginUser(username, password) {
  hideAuthAlert();
  const btn = document.getElementById("btn-submit-login");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Authentication failed.");
    }
    setAuthSession(data.access_token, data.user);
    closeAuthModal();
    // Dispatch custom event for modules to refresh their history / sessions
    window.dispatchEvent(new CustomEvent("workbench:auth_changed", { detail: { user: data.user } }));
  } catch (err) {
    showAuthAlert(err.message || "Failed to sign in.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

export async function registerUser(username, email, password) {
  hideAuthAlert();
  const btn = document.getElementById("btn-submit-register");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Account creation failed.");
    }
    setAuthSession(data.access_token, data.user);
    closeAuthModal();
    window.dispatchEvent(new CustomEvent("workbench:auth_changed", { detail: { user: data.user } }));
  } catch (err) {
    showAuthAlert(err.message || "Failed to create account.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

export async function checkAuthStatus() {
  const token = getAuthToken();
  if (!token) {
    updateAuthUI();
    return;
  }

  try {
    const res = await fetch("/api/auth/me", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (res.ok) {
      const user = await res.json();
      setAuthSession(token, user);
    } else {
      // Token expired or invalid
      await clearAuthSession();
    }
  } catch (e) {
    // Network offline; keep local session
    updateAuthUI();
  }
}

export function initAuth() {
  const dockBtn = document.getElementById("dock-auth-btn");
  if (dockBtn) {
    dockBtn.addEventListener("click", () => openAuthModal());
  }

  const topAuthBtn = document.getElementById("btn-top-auth");
  if (topAuthBtn) {
    topAuthBtn.addEventListener("click", () => openAuthModal());
  }

  const closeBtn = document.getElementById("btn-close-auth-modal");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => closeAuthModal());
  }

  const modal = document.getElementById("auth-modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeAuthModal();
    });
  }

  const loginTab = document.getElementById("auth-tab-login");
  if (loginTab) {
    loginTab.addEventListener("click", () => switchAuthTab("login"));
  }

  const regTab = document.getElementById("auth-tab-register");
  if (regTab) {
    regTab.addEventListener("click", () => switchAuthTab("register"));
  }

  const loginForm = document.getElementById("auth-login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const u = document.getElementById("login-username")?.value || "";
      const p = document.getElementById("login-password")?.value || "";
      if (u && p) loginUser(u, p);
    });
  }

  const regForm = document.getElementById("auth-register-form");
  if (regForm) {
    regForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const u = document.getElementById("reg-username")?.value || "";
      const em = document.getElementById("reg-email")?.value || "";
      const p = document.getElementById("reg-password")?.value || "";
      if (u && em && p) registerUser(u, em, p);
    });
  }

  const logoutBtn = document.getElementById("btn-auth-logout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      await clearAuthSession();
      closeAuthModal();
      window.dispatchEvent(new CustomEvent("workbench:auth_changed", { detail: { user: null } }));
    });
  }

  // Check backend validity on startup
  checkAuthStatus();
}
