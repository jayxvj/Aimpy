/**
 * EduPredict Authentication & Session Guard Module
 * - Handles Register & Login with dedicated backend (http://127.0.0.1:5001)
 * - Inverted Theme: Dark page => Light Modal, Light page => Dark Modal
 * - Page Guard: Blocks viewing any page other than index.html without login
 * - Enforces: "after register user must login"
 */

(function () {
  "use strict";

  // EduPredict API configuration:
  // Primary backend runs on port 5000 (backend/app.py)
  // Standalone auth service can also run on port 5001 (backend/auth_app.py)
  const API_SERVERS = [
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "http://127.0.0.1:5001",
    "http://localhost:5001"
  ];
  let activeApi = "http://127.0.0.1:5000";

  // Resilient multi-endpoint fetch with auto-failover
  async function authFetch(endpoint, options = {}) {
    const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const serversToTry = [
      activeApi,
      ...API_SERVERS.filter((s) => s !== activeApi)
    ];

    let lastError = null;

    for (const base of serversToTry) {
      try {
        const url = `${base}${cleanEndpoint}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 7000);

        const fetchOptions = {
          ...options,
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
          }
        };

        const res = await fetch(url, fetchOptions);
        clearTimeout(timeoutId);

        // Valid HTTP response received; lock in this working endpoint
        activeApi = base;
        return res;
      } catch (err) {
        lastError = err;
        console.warn(`Connection to ${base}${cleanEndpoint} failed:`, err.message);
      }
    }

    // If every candidate server failed to connect:
    throw new Error(
      "Cannot connect to the EduPredict server. Please ensure the backend is running (python backend/app.py on port 5000)."
    );
  }

  // Session Management
  function getLoggedInUser() {
    try {
      const data = localStorage.getItem("ep_user");
      return data ? JSON.parse(data) : null;
    } catch (e) {
      return null;
    }
  }

  function saveUserSession(user) {
    try {
      localStorage.setItem("ep_user", JSON.stringify(user));
      localStorage.setItem("ep_token", "ep_auth_" + (user.unique_id || Date.now()));
    } catch (e) {
      console.warn("Storage quota handling:", e);
      try {
        const safeUser = Object.assign({}, user, { profile_pic: "" });
        localStorage.setItem("ep_user", JSON.stringify(safeUser));
      } catch (err) {}
    }
  }

  function logoutUser() {
    try {
      localStorage.removeItem("ep_user");
      localStorage.removeItem("ep_token");
      sessionStorage.clear();
    } catch (e) {
      console.warn("Storage clear error:", e);
    }

    const current = window.location.pathname.toLowerCase();
    const isHome = current.endsWith("index.html") || current.endsWith("/") || current === "";
    if (isHome) {
      window.location.reload();
    } else {
      window.location.replace("index.html");
    }
  }

  // Detect current page
  const pathname = window.location.pathname.toLowerCase();
  const isLandingPage = pathname.endsWith("index.html") || pathname.endsWith("/") || pathname === "";

  // Inject Modal Markup into DOM
  function injectAuthModal() {
    if (document.getElementById("authModalOverlay")) return;

    const overlay = document.createElement("div");
    overlay.className = "auth-overlay";
    overlay.id = "authModalOverlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");

    overlay.innerHTML = `
      <div class="auth-modal" id="authModalCard">
        <button class="auth-close-btn" id="authCloseBtn" type="button" aria-label="Close modal">✕</button>
        
        <div class="auth-modal-header">
          <h2 id="authModalTitle">Welcome to EduPredict</h2>
          <p id="authModalSubtitle">Please log in with your Admin ID to continue</p>
        </div>

        <div class="auth-tabs" id="authTabs">
          <button class="auth-tab-btn active" id="tabBtnLogin" type="button">Log In</button>
          <button class="auth-tab-btn" id="tabBtnRegister" type="button">Register Admin</button>
        </div>

        <div class="auth-alert" id="authAlert" role="alert"></div>

        <!-- LOGIN FORM -->
        <form id="authLoginForm">
          <div class="auth-form-group">
            <label class="auth-label" for="loginUsername">Admin ID / Username</label>
            <input class="auth-input" id="loginUsername" type="text" placeholder="e.g. admin or username" required autocomplete="username">
          </div>

          <div class="auth-form-group">
            <label class="auth-label" for="loginPassword">Password</label>
            <input class="auth-input" id="loginPassword" type="password" placeholder="Enter your password" required autocomplete="current-password">
          </div>

          <button class="auth-submit-btn" id="loginSubmitBtn" type="submit">
            <i class="fa-solid fa-right-to-bracket"></i>
            <span>Log In</span>
          </button>
        </form>

        <!-- REGISTER FORM -->
        <form id="authRegisterForm" style="display: none;">
          <div class="auth-form-group">
            <label class="auth-label" for="regName">Full Name *</label>
            <input class="auth-input" id="regName" type="text" placeholder="e.g. John Doe" required autocomplete="name">
          </div>

          <div class="auth-form-row">
            <div class="auth-form-group">
              <label class="auth-label" for="regUsername">Admin ID / Username *</label>
              <input class="auth-input" id="regUsername" type="text" placeholder="e.g. admin_john" required autocomplete="username">
            </div>

            <div class="auth-form-group">
              <label class="auth-label" for="regPassword">Password *</label>
              <input class="auth-input" id="regPassword" type="password" placeholder="Min. 4 chars" required autocomplete="new-password">
            </div>
          </div>

          <div class="auth-form-row">
            <div class="auth-form-group">
              <label class="auth-label" for="regCollege">College Name</label>
              <input class="auth-input" id="regCollege" type="text" placeholder="e.g. National Institute of Tech">
            </div>

            <div class="auth-form-group">
              <label class="auth-label" for="regBranch">Branch</label>
              <input class="auth-input" id="regBranch" type="text" placeholder="e.g. Computer Science">
            </div>
          </div>

          <div class="auth-form-row">
            <div class="auth-form-group">
              <label class="auth-label" for="regYear">Academic Year</label>
              <select class="auth-input" id="regYear">
                <option value="1st Year">1st Year</option>
                <option value="2nd Year">2nd Year</option>
                <option value="3rd Year" selected>3rd Year</option>
                <option value="4th Year">4th Year</option>
                <option value="Faculty / Admin">Faculty / Admin</option>
              </select>
            </div>

            <div class="auth-form-group">
              <label class="auth-label" for="regLocation">Location</label>
              <input class="auth-input" id="regLocation" type="text" placeholder="e.g. Mumbai, India">
            </div>
          </div>

          <button class="auth-submit-btn" id="regSubmitBtn" type="submit">
            <i class="fa-solid fa-user-plus"></i>
            <span>Register Admin Account</span>
          </button>
        </form>

        <div style="margin-top: 18px; text-align: center; font-size: 11px; opacity: 0.8;" id="authModalFooter">
          <span>A unique ID will be generated upon registration.</span>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    // Bind Close Button
    const closeBtn = document.getElementById("authCloseBtn");
    closeBtn.addEventListener("click", () => {
      // If on a protected page and not logged in, closing redirects to index.html
      if (!isLandingPage && !getLoggedInUser()) {
        window.location.href = "index.html";
      } else {
        closeAuthModal();
      }
    });

    // Close on overlay background click (only if allowed)
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        if (!isLandingPage && !getLoggedInUser()) {
          window.location.href = "index.html";
        } else {
          closeAuthModal();
        }
      }
    });

    // Tab Switching
    const tabLogin = document.getElementById("tabBtnLogin");
    const tabReg = document.getElementById("tabBtnRegister");
    const loginForm = document.getElementById("authLoginForm");
    const regForm = document.getElementById("authRegisterForm");
    const modalTitle = document.getElementById("authModalTitle");
    const modalSubtitle = document.getElementById("authModalSubtitle");

    tabLogin.addEventListener("click", () => {
      tabLogin.classList.add("active");
      tabReg.classList.remove("active");
      loginForm.style.display = "block";
      regForm.style.display = "none";
      modalTitle.textContent = "Welcome Back";
      modalSubtitle.textContent = "Enter your Admin ID and password to access workspace";
      clearAlert();
    });

    tabReg.addEventListener("click", () => {
      tabReg.classList.add("active");
      tabLogin.classList.remove("active");
      regForm.style.display = "block";
      loginForm.style.display = "none";
      modalTitle.textContent = "Admin Registration";
      modalSubtitle.textContent = "Register credentials. A unique ID will be assigned.";
      clearAlert();
    });

    // Form Submissions
    loginForm.addEventListener("submit", handleLoginSubmit);
    regForm.addEventListener("submit", handleRegisterSubmit);

    // Sync Inverted Theme
    syncModalTheme();
  }

  // Inverted Theme Synchronization
  function syncModalTheme() {
    const card = document.getElementById("authModalCard");
    if (!card) return;
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    if (currentTheme === "dark") {
      card.classList.add("modal-theme-light");
      card.classList.remove("modal-theme-dark");
    } else {
      card.classList.add("modal-theme-dark");
      card.classList.remove("modal-theme-light");
    }
  }

  // Observe theme changes on <html> to maintain inverted contrast
  const themeObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === "attributes" && mutation.attributeName === "data-theme") {
        syncModalTheme();
      }
    });
  });
  themeObserver.observe(document.documentElement, { attributes: true });

  // Open / Close Modal
  function openAuthModal(defaultTab = "login", customMessage = "") {
    injectAuthModal();
    syncModalTheme();

    const overlay = document.getElementById("authModalOverlay");
    const tabLogin = document.getElementById("tabBtnLogin");
    const tabReg = document.getElementById("tabBtnRegister");

    if (defaultTab === "register") {
      if (tabReg) tabReg.click();
    } else {
      if (tabLogin) tabLogin.click();
    }

    if (customMessage) {
      showAlert(customMessage, "error");
    } else {
      clearAlert();
    }

    // Configure close button display
    const closeBtn = document.getElementById("authCloseBtn");
    if (closeBtn) {
      if (!isLandingPage && !getLoggedInUser()) {
        closeBtn.title = "Return to Home";
        closeBtn.innerHTML = '<i class="fa-solid fa-house"></i>';
      } else {
        closeBtn.title = "Close";
        closeBtn.innerHTML = "✕";
      }
    }

    if (overlay) overlay.classList.add("active");
  }

  function closeAuthModal() {
    const overlay = document.getElementById("authModalOverlay");
    if (overlay) overlay.classList.remove("active");
    clearAlert();
  }

  function showAlert(msg, type = "error") {
    const alertBox = document.getElementById("authAlert");
    if (!alertBox) return;
    alertBox.textContent = msg;
    alertBox.className = `auth-alert ${type} visible`;
  }

  function clearAlert() {
    const alertBox = document.getElementById("authAlert");
    if (!alertBox) return;
    alertBox.textContent = "";
    alertBox.className = "auth-alert";
  }

  // Register Handler: Note that after register, user MUST log in.
  async function handleRegisterSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById("regSubmitBtn");
    const name = document.getElementById("regName").value.trim();
    const username = document.getElementById("regUsername").value.trim();
    const password = document.getElementById("regPassword").value;
    const college = document.getElementById("regCollege").value.trim();
    const branch = document.getElementById("regBranch").value.trim();
    const year = document.getElementById("regYear").value;
    const location = document.getElementById("regLocation").value.trim();

    if (!name || !username || !password) {
      showAlert("Please fill in all required fields marked with *");
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Registering...';
    clearAlert();

    try {
      const res = await authFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          name,
          username,
          password,
          college_name: college,
          branch,
          year,
          location
        })
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Registration failed");
      }

      // Clear register form
      document.getElementById("authRegisterForm").reset();

      // Switch to Login Tab and show message (User MUST log in after register!)
      document.getElementById("tabBtnLogin").click();
      document.getElementById("loginUsername").value = username;
      showAlert(
        `✓ Account created! Unique ID: ${data.unique_id}. Please log in with your password to continue.`,
        "success"
      );
      document.getElementById("loginPassword").focus();
    } catch (err) {
      showAlert(err.message || "Failed to register. Please check if backend server is running.");
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> <span>Register Admin Account</span>';
    }
  }

  // Login Handler
  async function handleLoginSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById("loginSubmitBtn");
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;

    if (!username || !password) {
      showAlert("Please enter your Admin ID and password");
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...';
    clearAlert();

    try {
      const res = await authFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password })
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Invalid credentials");
      }

      // Save session
      saveUserSession(data.user);

      // Close modal
      closeAuthModal();

      // Update UI
      updateUIAfterAuth(data.user);

      // If user was on a protected page and locked, reload to initialize page
      if (!isLandingPage) {
        window.location.reload();
      }
    } catch (err) {
      showAlert(err.message || "Authentication failed. Check your password.");
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> <span>Log In</span>';
    }
  }

  // Update Page Navigation elements
  function updateUIAfterAuth(user) {
    // 1. Landing Page Navigation
    const navActions = document.querySelector(".home-nav-actions");
    if (navActions) {
      const existingBtn = navActions.querySelector(".btn-primary");
      let userPill = document.getElementById("navUserPill");
      let signOutBtn = document.getElementById("navSignOutBtn");

      if (user) {
        if (existingBtn) existingBtn.style.display = "none";
        if (!userPill) {
          userPill = document.createElement("a");
          userPill.id = "navUserPill";
          userPill.href = "profile.html";
          userPill.className = "auth-user-pill";
          navActions.insertBefore(userPill, navActions.querySelector(".hamburger-btn"));
        }
        userPill.title = `My Profile (${user.name || user.username})`;
        userPill.setAttribute("aria-label", "View My Profile");
        userPill.innerHTML = `
          <div class="auth-user-avatar">
            ${user.profile_pic ? `<img src="${user.profile_pic}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">` : (user.name ? user.name[0].toUpperCase() : 'U')}
          </div>
        `;

        if (!signOutBtn) {
          signOutBtn = document.createElement("button");
          signOutBtn.id = "navSignOutBtn";
          signOutBtn.type = "button";
          signOutBtn.className = "auth-nav-signout-btn";
          signOutBtn.title = "Sign Out";
          signOutBtn.setAttribute("aria-label", "Sign Out");
          signOutBtn.innerHTML = `<i class="fa-solid fa-arrow-right-from-bracket"></i>`;
          signOutBtn.addEventListener("click", (e) => {
            e.preventDefault();
            logoutUser();
          });
          navActions.insertBefore(signOutBtn, navActions.querySelector(".hamburger-btn"));
        }
      } else {
        if (existingBtn) existingBtn.style.display = "inline-flex";
        if (userPill) userPill.remove();
        if (signOutBtn) signOutBtn.remove();
      }
    }

    // 2. Sidebar Profile Link (for workspace pages: predict, analytics, history, profile)
    const navMenu = document.querySelector(".nav-menu");
    if (navMenu) {
      const existingProfileLinks = navMenu.querySelectorAll("a[href*='profile.html'], #sidebarProfileLink");
      if (existingProfileLinks.length > 1) {
        // Remove duplicates if more than one exists
        for (let i = 1; i < existingProfileLinks.length; i++) {
          existingProfileLinks[i].remove();
        }
      }

      const getSidebarAvatarHtml = (u) => {
        if (u && u.profile_pic) {
          return `<img src="${u.profile_pic}" alt="Profile">`;
        }
        return `<i class="fa-solid fa-circle-user"></i>`;
      };

      if (existingProfileLinks.length === 0) {
        const profileLink = document.createElement("a");
        profileLink.id = "sidebarProfileLink";
        profileLink.className = `nav-link ${pathname.includes("profile.html") ? "active" : ""}`;
        profileLink.href = "profile.html";
        profileLink.innerHTML = `
          <span class="nav-icon" aria-hidden="true">${getSidebarAvatarHtml(user)}</span>
          <span>My Profile</span>
        `;
        navMenu.appendChild(profileLink);
      } else {
        const link = existingProfileLinks[0];
        link.id = "sidebarProfileLink";
        const iconSpan = link.querySelector(".nav-icon");
        if (iconSpan) {
          iconSpan.innerHTML = getSidebarAvatarHtml(user);
        }
        if (pathname.includes("profile.html")) {
          link.classList.add("active");
          link.setAttribute("aria-current", "page");
        }
      }
    }

    // 3. Topbar Profile Icon (for workspace pages)
    const topbarRight = document.querySelector(".topbar-right");
    if (topbarRight) {
      const existingTopIcons = topbarRight.querySelectorAll("#topbarProfileIcon, a[href*='profile.html']");
      if (existingTopIcons.length > 1) {
        for (let i = 1; i < existingTopIcons.length; i++) {
          existingTopIcons[i].remove();
        }
      }

      const getTopbarAvatarHtml = (u) => {
        if (u && u.profile_pic) {
          return `<img src="${u.profile_pic}" alt="Profile">`;
        }
        const initial = (u && u.name) ? u.name[0].toUpperCase() : 'U';
        return `<span style="font-weight:700;font-size:13px;color:#088395;">${initial}</span>`;
      };

      if (existingTopIcons.length === 0) {
        const profBtn = document.createElement("a");
        profBtn.id = "topbarProfileIcon";
        profBtn.href = "profile.html";
        profBtn.className = "topbar-profile-btn";
        profBtn.title = user ? `${user.name} (${user.unique_id})` : "My Profile";
        profBtn.setAttribute("aria-label", "My Profile");
        profBtn.innerHTML = getTopbarAvatarHtml(user);
        topbarRight.insertBefore(profBtn, topbarRight.firstChild);
      } else {
        const profBtn = existingTopIcons[0];
        profBtn.id = "topbarProfileIcon";
        profBtn.className = "topbar-profile-btn";
        profBtn.title = user ? `${user.name} (${user.unique_id})` : "My Profile";
        profBtn.setAttribute("aria-label", "My Profile");
        profBtn.innerHTML = getTopbarAvatarHtml(user);
      }
    }
  }

  // Sync profile directly from backend DB so fresh picture and fields are guaranteed
  async function syncProfileFromDB(user) {
    if (!user || (!user.unique_id && !user.username)) return;
    try {
      const identifier = user.unique_id || user.username;
      const res = await authFetch(`/auth/profile/${encodeURIComponent(identifier)}`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.success && data.user) {
          saveUserSession(data.user);
          updateUIAfterAuth(data.user);
        }
      }
    } catch (e) {
      // Offline fallback: cached user remains in effect
    }
  }

  // Gatekeeper: Protected Page Verification
  function enforceGatekeeper() {
    const user = getLoggedInUser();

    if (!isLandingPage) {
      if (!user) {
        // Unauthenticated access on protected page: Pop up login modal immediately!
        setTimeout(() => {
          openAuthModal("login", "Authentication required. Please log in with your Admin ID to view this page.");
        }, 150);
      } else {
        updateUIAfterAuth(user);
        syncProfileFromDB(user);
      }
    } else {
      // On Landing Page:
      updateUIAfterAuth(user);
      if (user) {
        syncProfileFromDB(user);
      }

      // If user is NOT logged in, clicking workspace links should trigger login popup
      if (!user) {
        document.querySelectorAll("a[href='predict.html'], a[href='analytics.html'], a[href='history.html'], a[href='profile.html']").forEach(link => {
          link.addEventListener("click", (e) => {
            if (!getLoggedInUser()) {
              e.preventDefault();
              openAuthModal("login", "Please log in with your Admin ID to access the EduPredict workspace.");
            }
          });
        });

        // Also intercept "Get Started" buttons
        document.querySelectorAll(".btn-primary").forEach(btn => {
          if (btn.textContent.includes("Get Started") || btn.textContent.includes("Try a Prediction")) {
            btn.addEventListener("click", (e) => {
              if (!getLoggedInUser()) {
                e.preventDefault();
                openAuthModal("login");
              }
            });
          }
        });
      }
    }
  }

  // Initialize on DOM Ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      injectAuthModal();
      enforceGatekeeper();
    });
  } else {
    injectAuthModal();
    enforceGatekeeper();
  }

  // Expose to window for profile page and other buttons
  window.EduPredictAuth = {
    getUser: getLoggedInUser,
    saveUser: saveUserSession,
    logout: logoutUser,
    openModal: openAuthModal,
    closeModal: closeAuthModal,
    get API_URL() {
      return activeApi;
    },
    fetch: authFetch
  };
})();
