/**
 * User Authentication, Social OAuth 2.0 & Encrypted API Key Vault Module
 * Handles local registration, login, Google & GitHub SSO, authenticated JWT session management,
 * and AES-256-GCM encrypted per-user API key vault synchronization.
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
  window.location.replace("/login");
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
  const dockCircle = document.getElementById("dock-avatar-circle");
  const topAuthIcon = document.getElementById("top-auth-icon");

  const tabsContainer = document.querySelector(".auth-tabs");
  const loginForm = document.getElementById("auth-login-form");
  const regForm = document.getElementById("auth-register-form");
  const oauthGroup = document.getElementById("oauth-buttons-group");
  const authDivider = document.getElementById("auth-divider");
  const profileBox = document.getElementById("auth-profile-view");

  const profileAvatar = document.getElementById("profile-avatar-display");
  const profileName = document.getElementById("profile-name-display");
  const profileEmail = document.getElementById("profile-email-display");
  const profileRole = document.getElementById("profile-role-display");
  const profileProvider = document.getElementById("profile-provider-display");

  if (user && token) {
    const initials = getInitials(user.username);
    if (dockName) dockName.textContent = user.username;
    if (dockRole) dockRole.textContent = `Online (${user.role || "Researcher"})`;
    if (dockCircle) {
      if (user.avatar_url) {
        dockCircle.innerHTML = `<img src="${user.avatar_url}" alt="${user.username}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
      } else {
        dockCircle.innerHTML = `<span id="dock-avatar-initials">${initials}</span>`;
      }
    }
    if (topAuthIcon) topAuthIcon.textContent = "👤";

    // Inside modal, show profile & API key vault
    if (tabsContainer) tabsContainer.style.display = "none";
    if (oauthGroup) oauthGroup.style.display = "none";
    if (authDivider) authDivider.style.display = "none";
    if (loginForm) loginForm.style.display = "none";
    if (regForm) regForm.style.display = "none";
    if (profileBox) profileBox.style.display = "flex";

    if (profileAvatar) {
      if (user.avatar_url) {
        profileAvatar.innerHTML = `<img src="${user.avatar_url}" alt="${user.username}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
      } else {
        profileAvatar.textContent = initials;
      }
    }
    if (profileName) profileName.textContent = user.username;
    if (profileEmail) profileEmail.textContent = user.email;
    if (profileRole) profileRole.textContent = `Role: ${user.role || "Researcher"}`;
    if (profileProvider) {
      const prov = (user.oauth_provider || "local").toLowerCase();
      if (prov === "google") {
        profileProvider.textContent = "Google SSO";
      } else if (prov === "github") {
        profileProvider.textContent = "GitHub SSO";
      } else {
        profileProvider.textContent = "Local Account";
      }
    }

    // Automatically synchronize the personal encrypted API key vault status
    loadUserApiKeys();
  } else {
    if (dockName) dockName.textContent = "Guest Researcher";
    if (dockRole) dockRole.textContent = "Sign In / Register";
    if (dockCircle) {
      dockCircle.innerHTML = `<span id="dock-avatar-initials">RF</span>`;
    }
    if (topAuthIcon) topAuthIcon.textContent = "👤";

    if (tabsContainer) tabsContainer.style.display = "flex";
    if (oauthGroup) oauthGroup.style.display = "flex";
    if (authDivider) authDivider.style.display = "flex";
    if (profileBox) profileBox.style.display = "none";
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

export function showVaultAlert(msg, type = "success") {
  const alertEl = document.getElementById("vault-alert");
  if (!alertEl) return;
  alertEl.textContent = msg;
  alertEl.className = `vault-alert ${type}`;
  alertEl.style.display = "block";
  setTimeout(() => {
    if (alertEl && alertEl.textContent === msg) {
      alertEl.style.display = "none";
    }
  }, 5000);
}

export function hideVaultAlert() {
  const alertEl = document.getElementById("vault-alert");
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
  hideVaultAlert();
  modal.style.display = "flex";
  modal.removeAttribute("inert");
}

export function closeAuthModal() {
  const modal = document.getElementById("auth-modal");
  if (!modal) return;
  modal.style.display = "none";
  modal.setAttribute("inert", "");
  hideAuthAlert();
  hideVaultAlert();
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
    window.dispatchEvent(new CustomEvent("workbench:auth_changed", { detail: { user: data.user } }));
  } catch (err) {
    const isUnregistered = (err.message || "").toLowerCase().includes("not registered");
    if (isUnregistered) {
      showAuthAlert(`⚠️ Account Not Registered: ${err.message}`, "error");
      switchAuthTab("register");
    } else {
      showAuthAlert(err.message || "Failed to sign in.", "error");
    }
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
    window.location.replace("/login");
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
      await clearAuthSession();
    }
  } catch (e) {
    updateAuthUI();
  }
}

/**
 * Handles OAuth callback query parameters from Google / GitHub redirect.
 */
export async function checkUrlAuthParams() {
  try {
    const params = new URLSearchParams(window.location.search);
    const authToken = params.get("auth_token");
    const authError = params.get("auth_error");

    if (authError) {
      // Remove query parameters from URL cleanly
      window.history.replaceState({}, document.title, window.location.pathname);
      openAuthModal();
      showAuthAlert(`Sign-in error: ${authError.replace(/_/g, " ")}`, "error");
      return;
    }

    if (authToken) {
      // Store token immediately
      localStorage.setItem(KEY_TOKEN, authToken);
      window.history.replaceState({}, document.title, window.location.pathname);

      // Fetch verified user profile
      const res = await fetch("/api/auth/me", {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (res.ok) {
        const user = await res.json();
        setAuthSession(authToken, user);
        window.dispatchEvent(new CustomEvent("workbench:auth_changed", { detail: { user } }));
      }
    }
  } catch (e) {
    console.warn("Failed checking OAuth URL parameters:", e);
  }
}

/**
 * Encrypted API Key Vault Management
 */
export async function loadUserApiKeys() {
  const token = getAuthToken();
  if (!token) return;

  try {
    const res = await fetch("/api/auth/api-keys", {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;

    const data = await res.json();
    const keys = data.keys || {};

    const providers = ["gemini", "anthropic", "openai", "serpapi"];
    providers.forEach(p => {
      const chip = document.getElementById(`vault-chip-${p}`);
      const input = document.getElementById(`vault-input-${p}`);
      const item = keys[p];

      if (item && item.configured) {
        if (chip) {
          chip.textContent = `Active (${item.hint || "••••"})`;
          chip.className = "vault-chip active";
        }
        if (input) {
          input.value = "";
          input.placeholder = `Encrypted in Vault (${item.hint || "••••"})`;
        }
      } else {
        if (chip) {
          chip.textContent = "Not Configured";
          chip.className = "vault-chip";
        }
        if (input) {
          input.placeholder = `Paste ${p.toUpperCase()} key to encrypt...`;
        }
      }
    });

    // Intelligent provider UI synchronization:
    // If user has OpenAI active in vault but no Gemini key, align default model selectors
    const hasOpenAI = keys.openai && keys.openai.configured;
    const hasGemini = keys.gemini && keys.gemini.configured;
    const hasClaude = keys.anthropic && keys.anthropic.configured;

    const selA2 = document.getElementById('cfg-agent2-model');
    const selA4 = document.getElementById('cfg-agent4-model');
    const modelBadge = document.getElementById('prompt-model-badge');

    if (hasOpenAI && !hasGemini && !hasClaude) {
      if (selA2 && (!selA2.value || selA2.value.startsWith('gemini'))) {
        selA2.value = 'gpt-6.1-sol';
        localStorage.setItem('workbench_agent2_model', 'gpt-6.1-sol');
      }
      if (selA4 && (!selA4.value || selA4.value.startsWith('gemini'))) {
        selA4.value = 'gpt-6-luna';
        localStorage.setItem('workbench_agent4_model', 'gpt-6-luna');
      }
      if (modelBadge && (modelBadge.textContent.includes('Gemini') || !modelBadge.textContent)) {
        modelBadge.textContent = 'GPT-6.1 Sol + SQLite';
      }
    } else if (hasClaude && !hasGemini && !hasOpenAI) {
      if (selA2 && (!selA2.value || selA2.value.startsWith('gemini'))) {
        selA2.value = 'claude-sonnet-5.5';
        localStorage.setItem('workbench_agent2_model', 'claude-sonnet-5.5');
      }
      if (selA4 && (!selA4.value || selA4.value.startsWith('gemini'))) {
        selA4.value = 'claude-haiku-4.5';
        localStorage.setItem('workbench_agent4_model', 'claude-haiku-4.5');
      }
      if (modelBadge && (modelBadge.textContent.includes('Gemini') || !modelBadge.textContent)) {
        modelBadge.textContent = 'Claude Sonnet 5.5 + SQLite';
      }
    }

    const liveStatusBadge = document.getElementById('api-keys-status-badge');
    if (liveStatusBadge && (hasOpenAI || hasGemini || hasClaude)) {
      liveStatusBadge.className = 'badge badge-success';
      liveStatusBadge.textContent = 'Live Keys Active';
    }
  } catch (err) {
    console.warn("Failed to load user API key hints:", err);
  }
}

export async function saveUserApiKey(provider, apiKey) {
  const token = getAuthToken();
  if (!token) {
    showVaultAlert("You must be signed in to store encrypted API keys.", "error");
    return;
  }
  if (!apiKey || !apiKey.trim()) {
    showVaultAlert(`Please enter a valid ${provider} API key.`, "error");
    return;
  }

  try {
    const res = await fetch("/api/auth/api-keys", {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ provider, api_key: apiKey.trim() })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to encrypt and store API key.");
    }
    showVaultAlert(`Successfully encrypted & saved ${provider.toUpperCase()} key (${data.hint})!`, "success");
    const input = document.getElementById(`vault-input-${provider}`);
    if (input) input.value = "";
    await loadUserApiKeys();
  } catch (err) {
    showVaultAlert(err.message || "Failed to store key.", "error");
  }
}

export async function deleteUserApiKey(provider) {
  const token = getAuthToken();
  if (!token) return;

  try {
    const res = await fetch(`/api/auth/api-keys/${provider}`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Failed to remove key.");
    }
    showVaultAlert(`Removed ${provider.toUpperCase()} API key from vault.`, "success");
    await loadUserApiKeys();
  } catch (err) {
    showVaultAlert(err.message || "Failed to remove key.", "error");
  }
}

/**
 * Initializes listeners for OAuth login buttons.
 */
function initOAuthButtons() {
  const googleBtn = document.getElementById("btn-oauth-google");
  if (googleBtn) {
    googleBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/auth/providers");
        const provs = await res.json();
        if (!provs.google) {
          showAuthAlert("Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env, or sign in with email & password.", "error");
          return;
        }
        window.location.href = "/api/auth/google/login";
      } catch (e) {
        window.location.href = "/api/auth/google/login";
      }
    });
  }

  const githubBtn = document.getElementById("btn-oauth-github");
  if (githubBtn) {
    githubBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/auth/providers");
        const provs = await res.json();
        if (!provs.github) {
          showAuthAlert("GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env, or sign in with email & password.", "error");
          return;
        }
        window.location.href = "/api/auth/github/login";
      } catch (e) {
        window.location.href = "/api/auth/github/login";
      }
    });
  }
}

/**
 * Initializes listeners for Encrypted Vault actions.
 */
function initVaultListeners() {
  document.querySelectorAll(".btn-vault-save").forEach(btn => {
    btn.addEventListener("click", () => {
      const provider = btn.getAttribute("data-provider");
      const input = document.getElementById(`vault-input-${provider}`);
      if (provider && input) {
        saveUserApiKey(provider, input.value);
      }
    });
  });

  document.querySelectorAll(".btn-vault-del").forEach(btn => {
    btn.addEventListener("click", () => {
      const provider = btn.getAttribute("data-provider");
      if (provider) {
        deleteUserApiKey(provider);
      }
    });
  });
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

  initOAuthButtons();
  initVaultListeners();

  // Check URL parameters for OAuth redirect callback
  checkUrlAuthParams();

  // Check backend validity on startup
  checkAuthStatus();
}
