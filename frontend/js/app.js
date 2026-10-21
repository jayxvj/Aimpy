"use strict";

(() => {
    const HISTORY_KEY = "edupredict_prediction_history";

    // Get an HTML element safely
    function getElement(selector) {
        return document.querySelector(selector);
    }

    // Show notification messages
    function showToast(message, type = "info") {
        let toast = getElement("#eduToast");

        if (!toast) {
            toast = document.createElement("div");
            toast.id = "eduToast";

            Object.assign(toast.style, {
                position: "fixed",
                right: "24px",
                bottom: "24px",
                maxWidth: "360px",
                padding: "14px 20px",
                borderRadius: "12px",
                color: "#ffffff",
                fontSize: "14px",
                fontFamily: "Arial, sans-serif",
                boxShadow: "0 8px 25px rgba(0,0,0,0.15)",
                zIndex: "99999",
                opacity: "0",
                transform: "translateY(12px)",
                transition: "opacity 0.25s ease, transform 0.25s ease"
            });

            document.body.appendChild(toast);
        }

        const backgrounds = {
            success: "#16866a",
            error: "#dc3545",
            warning: "#c78317",
            info: "#183153"
        };

        toast.textContent = message;
        toast.style.background = backgrounds[type] || backgrounds.info;
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";

        clearTimeout(toast.hideTimer);

        toast.hideTimer = setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(12px)";
        }, 3000);
    }

    // Read prediction history from localStorage
    function getPredictionHistory() {
        try {
            const history = JSON.parse(
                localStorage.getItem(HISTORY_KEY) || "[]"
            );

            return Array.isArray(history) ? history : [];
        } catch (error) {
            console.error("Could not read prediction history:", error);
            return [];
        }
    }

    // Save a prediction to localStorage
    function savePrediction(prediction) {
        if (!prediction || typeof prediction !== "object") {
            throw new Error("Invalid prediction data.");
        }

        const history = getPredictionHistory();

        const record = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            date: new Date().toISOString(),
            ...prediction
        };

        history.unshift(record);

        // Keep the latest 100 records
        localStorage.setItem(
            HISTORY_KEY,
            JSON.stringify(history.slice(0, 100))
        );

        return record;
    }

    // Clear prediction history
    function clearPredictionHistory() {
        localStorage.removeItem(HISTORY_KEY);
    }

    // Format date and time
    function formatDate(dateValue) {
        const date = new Date(dateValue);

        if (Number.isNaN(date.getTime())) {
            return "Date unavailable";
        }

        return date.toLocaleString("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        });
    }

    // Format numbers safely
    function formatNumber(value, decimals = 1) {
        const number = Number(value);

        if (!Number.isFinite(number)) {
            return "—";
        }

        return number.toFixed(decimals);
    }

    // Set text without inserting HTML
    function setText(selector, value) {
        const element = getElement(selector);

        if (element) {
            element.textContent = value ?? "";
        }
    }

    // Animate a numeric value
    function animateNumber(element, targetValue, decimals = 0) {
        if (!element || !Number.isFinite(Number(targetValue))) {
            return;
        }

        const target = Number(targetValue);
        const duration = 700;
        const startTime = performance.now();

        function update(currentTime) {
            const progress = Math.min(
                (currentTime - startTime) / duration,
                1
            );

            // Smooth ease-out animation
            const easedProgress = 1 - Math.pow(1 - progress, 3);
            const currentValue = target * easedProgress;

            element.textContent = currentValue.toFixed(decimals);

            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }

        requestAnimationFrame(update);
    }

    // Mobile sidebar toggle, when the page has a sidebar
    function initializeSidebar() {
        const sidebar = getElement(".sidebar");

        if (!sidebar) {
            return;
        }

        let toggleButton = getElement("#sidebarToggle");

        if (!toggleButton) {
            toggleButton = document.createElement("button");
            toggleButton.id = "sidebarToggle";
            toggleButton.type = "button";
            toggleButton.textContent = "☰";
            toggleButton.setAttribute("aria-label", "Toggle navigation");

            Object.assign(toggleButton.style, {
                display: "none",
                border: "0",
                background: "transparent",
                color: "#183153",
                fontSize: "24px",
                cursor: "pointer",
                padding: "8px"
            });

            const topbar = getElement(".topbar");

            if (topbar) {
                topbar.prepend(toggleButton);
            }
        }

        toggleButton.addEventListener("click", () => {
            sidebar.classList.toggle("sidebar-open");
        });

        document.addEventListener("click", (event) => {
            if (
                window.innerWidth <= 768 &&
                sidebar.classList.contains("sidebar-open") &&
                !sidebar.contains(event.target) &&
                !toggleButton.contains(event.target)
            ) {
                sidebar.classList.remove("sidebar-open");
            }
        });

        function updateToggleVisibility() {
            toggleButton.style.display =
                window.innerWidth <= 768 ? "inline-flex" : "none";

            if (window.innerWidth > 768) {
                sidebar.classList.remove("sidebar-open");
            }
        }

        window.addEventListener("resize", updateToggleVisibility);
        updateToggleVisibility();
    }

    // Highlight the current page in the sidebar
    function initializeActiveNavigation() {
        const currentPage = window.location.pathname
            .split("/")
            .pop()
            .toLowerCase();

        document.querySelectorAll(".nav-link").forEach((link) => {
            const href = link.getAttribute("href");

            if (!href) {
                return;
            }

            const linkPage = href.split("/").pop().toLowerCase();

            if (linkPage === currentPage) {
                link.classList.add("active");
                link.setAttribute("aria-current", "page");
            } else {
                link.classList.remove("active");
                link.removeAttribute("aria-current");
            }
        });
    }

    // Run shared page setup
    function initializeApp() {
        initializeSidebar();
        initializeActiveNavigation();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeApp);
    } else {
        initializeApp();
    }

    // Make shared helpers available to other JavaScript files
    window.EduPredictApp = Object.freeze({
        getElement,
        showToast,
        getPredictionHistory,
        savePrediction,
        clearPredictionHistory,
        formatDate,
        formatNumber,
        setText,
        animateNumber,
        HISTORY_KEY
    });
})();