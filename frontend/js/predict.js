"use strict";

(() => {
    const form = document.getElementById("predictionForm");
    if (!form) return;

    const api = window.EduPredictAPI;
    const app = window.EduPredictApp;

    const predictButton = document.getElementById("predictButton");
    const formError = document.getElementById("formError");
    const featureLoadMessage = document.getElementById("featureLoadMessage");
    const resultPlaceholder = document.getElementById("resultPlaceholder");
    const resultContent = document.getElementById("resultContent");
    const resultScore = document.getElementById("resultScore");
    const scoreFill = document.getElementById("scoreFill");
    const scoreProgress = document.getElementById("scoreProgress");
    const resultCategory = document.getElementById("resultCategory");
    const resultModel = document.getElementById("resultModel");
    const resultModelBadge = document.getElementById("resultModelBadge");
    const resultTime = document.getElementById("resultTime");
    const newPredictionButton = document.getElementById("newPredictionButton");

    let modelFeatures = [];
    let featuresLoaded = false;

    const numericFeatures = [
        "Hours_Studied",
        "Attendance",
        "Sleep_Hours",
        "Previous_Scores",
        "Tutoring_Sessions",
        "Physical_Activity"
    ];

    // Dropdown options
    const categoricalOptions = {
        Parental_Involvement: ["Low", "Medium", "High"],
        Access_to_Resources: ["Low", "Medium", "High"],
        Extracurricular_Activities: ["Yes", "No"],
        Motivation_Level: ["Low", "Medium", "High"],
        Internet_Access: ["Yes", "No"],
        Family_Income: ["Low", "Medium", "High"],
        Teacher_Quality: ["Low", "Medium", "High"],
        School_Type: ["Public", "Private"],
        Peer_Influence: ["Positive", "Neutral", "Negative"],
        Learning_Disabilities: ["Yes", "No"],
        Parental_Education_Level: [
            "High School",
            "College",
            "Postgraduate"
        ],
        Distance_from_Home: ["Near", "Moderate", "Far"],
        Gender: ["Male", "Female"]
    };

    function showError(message) {
        if (formError) {
            formError.textContent = message;
            formError.hidden = false;
            formError.classList.remove("d-none");
        } else if (app) {
            app.showToast(message, "error");
        } else {
            alert(message);
        }
    }

    function clearError() {
        if (formError) {
            formError.textContent = "";
            formError.hidden = true;
            formError.classList.add("d-none");
        }
    }

    function populateDropdowns() {
        Object.entries(categoricalOptions).forEach(([feature, options]) => {
            const select = form.elements.namedItem(feature);

            if (!select || select.tagName !== "SELECT") {
                console.warn(`Dropdown not found: ${feature}`);
                return;
            }

            select.replaceChildren();

            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "Select an option";
            placeholder.disabled = true;
            placeholder.selected = true;

            select.appendChild(placeholder);

            options.forEach(value => {
                const option = document.createElement("option");
                option.value = value;
                option.textContent = value;
                select.appendChild(option);
            });
        });
    }

    function validateForm() {
        const data = {};

        for (const feature of modelFeatures) {
            const field = form.elements.namedItem(feature);

            if (!field) {
                throw new Error(`Form field missing: ${feature}`);
            }

            const value = field.value.trim();

            if (value === "") {
                throw new Error(
                    `Please complete: ${field.labels?.[0]?.textContent?.trim() || feature
                    }`
                );
            }

            if (numericFeatures.includes(feature)) {
                const number = Number(value);

                if (!Number.isFinite(number)) {
                    throw new Error(`${feature} must be a valid number.`);
                }

                if (field.min !== "" && number < Number(field.min)) {
                    throw new Error(`${feature} cannot be less than ${field.min}.`);
                }

                if (field.max !== "" && number > Number(field.max)) {
                    throw new Error(`${feature} cannot be greater than ${field.max}.`);
                }

                if (
                    field.step === "1" &&
                    !Number.isInteger(number)
                ) {
                    throw new Error(`${feature} must be a whole number.`);
                }

                data[feature] = number;
            } else {
                const allowedOptions = categoricalOptions[feature];

                if (allowedOptions && !allowedOptions.includes(value)) {
                    throw new Error(`Please select a valid option for ${feature}.`);
                }

                data[feature] = value;
            }
        }

        return data;
    }

    function setLoading(loading) {
        if (!predictButton) return;

        predictButton.disabled = loading || !featuresLoaded;

        if (loading) {
            predictButton.dataset.originalText = predictButton.textContent;
            predictButton.textContent = "Predicting...";
        } else {
            predictButton.textContent =
                predictButton.dataset.originalText || "Generate prediction →";
        }
    }

    function displayResult(result) {
        const score = Number(result.predicted_score);

        if (!Number.isFinite(score)) {
            throw new Error("The backend returned an invalid prediction score.");
        }

        if (resultScore) resultScore.textContent = score.toFixed(2);

        if (scoreFill) {
            scoreFill.style.width =
                `${Math.max(0, Math.min(100, score))}%`;
        }

        if (scoreProgress) {
            scoreProgress.setAttribute("aria-valuenow", String(score));
        }

        if (resultCategory) {
            resultCategory.textContent =
                result.performance_category || "Prediction complete";
        }

        const modelName = result.model_used || "ML Model";

        if (resultModel) resultModel.textContent = modelName;
        if (resultModelBadge) resultModelBadge.textContent = modelName;

        if (resultTime) {
            resultTime.textContent = new Date().toLocaleString("en-IN");
        }

        if (resultPlaceholder) resultPlaceholder.hidden = true;

        if (resultContent) {
            resultContent.hidden = false;
            resultContent.classList.add("visible");
        }

        if (app) {
            app.showToast("Prediction completed successfully!", "success");

            try {
                app.savePrediction({
                    predicted_score: score,
                    performance_category: result.performance_category || "Unknown",
                    model_used: modelName
                });
            } catch (error) {
                console.error("Could not save prediction history:", error);
            }
        }

        // Refresh stats cards after a new prediction is saved
        loadSummaryStats();
    }

    async function loadSummaryStats() {
        const apiBase = (api && api.API_BASE_URL) || (
            (window.location.protocol === "http:" || window.location.protocol === "https:")
                ? (window.location.port === "5500" || window.location.port === "3000" || window.location.port === "8080"
                    ? "http://127.0.0.1:5000"
                    : window.location.origin)
                : "http://127.0.0.1:5000"
        );

        try {
            const [statusRes, featuresRes, historyRes] = await Promise.all([
                fetch(`${apiBase}/api/health`).catch(() => null),
                fetch(`${apiBase}/features`).catch(() => null),
                fetch(`${apiBase}/history`).catch(() => null)
            ]);

            if (featuresRes && featuresRes.ok) {
                const featData = await featuresRes.json();
                const features = Array.isArray(featData) ? featData : (featData.features || []);
                const count = features.length || featData.total_features || 19;
                const el = document.getElementById("featureCount");
                if (el) el.textContent = count;
            }

            if (statusRes && statusRes.ok) {
                const statusData = await statusRes.json();
                const r2 = statusData.r2 || statusData.r2_score || (statusData.model_metrics && statusData.model_metrics.r2);
                const el = document.getElementById("modelAccuracy");
                if (el) el.textContent = r2 !== undefined ? (r2 * 100).toFixed(1) + "%" : "N/A";
            } else {
                const el = document.getElementById("modelAccuracy");
                if (el && (el.textContent === "—" || el.textContent === "")) el.textContent = "N/A";
            }

            if (historyRes && historyRes.ok) {
                const histData = await historyRes.json();
                const records = Array.isArray(histData.history) ? histData.history : [];
                const elTotal = document.getElementById("totalPredictions");
                if (elTotal) elTotal.textContent = records.length.toLocaleString();

                const scores = records
                    .map(r => Number(r.predicted_score))
                    .filter(s => Number.isFinite(s));
                const elAvg = document.getElementById("averageScore");
                if (elAvg) {
                    if (scores.length > 0) {
                        const avg = scores.reduce((sum, s) => sum + s, 0) / scores.length;
                        elAvg.textContent = avg.toFixed(1);
                    } else {
                        elAvg.textContent = "—";
                    }
                }
            }
        } catch (error) {
            console.warn("Could not load summary statistics:", error);
        }
    }

    async function initialize() {
        // Populate dropdowns immediately, without waiting for the backend.
        populateDropdowns();

        // Load summary cards from backend
        loadSummaryStats();

        if (!api) {
            throw new Error("api.js is not loaded. Check predict.html script tags.");
        }

        const response = await api.getModelFeatures();

        if (!Array.isArray(response) || response.length === 0) {
            throw new Error("Backend returned an invalid feature list.");
        }

        modelFeatures = response;

        const missingFields = modelFeatures.filter(
            feature => !form.elements.namedItem(feature)
        );

        if (missingFields.length > 0) {
            throw new Error(
                "Missing form fields: " + missingFields.join(", ")
            );
        }

        featuresLoaded = true;
        setLoading(false);

        if (featureLoadMessage) {
            featureLoadMessage.textContent =
                `${modelFeatures.length} model input features loaded successfully.`;
        }
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();
        clearError();

        if (!featuresLoaded) {
            showError("Backend is not connected. Start Flask and refresh this page.");
            return;
        }

        try {
            const studentData = validateForm();
            setLoading(true);

            const result = await api.predictStudentPerformance(studentData);
            displayResult(result);
        } catch (error) {
            showError(error.message || "Prediction failed.");
        } finally {
            setLoading(false);
        }
    });

    form.addEventListener("reset", () => {
        setTimeout(() => {
            clearError();

            if (resultContent) {
                resultContent.hidden = true;
                resultContent.classList.remove("visible");
            }

            if (resultPlaceholder) resultPlaceholder.hidden = false;

            populateDropdowns();
        }, 0);
    });

    if (newPredictionButton) {
        newPredictionButton.addEventListener("click", () => {
            form.reset();

            form.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        });
    }

    form.addEventListener("input", clearError);
    form.addEventListener("change", clearError);

    initialize().catch(error => {
        console.error("EduPredict initialization failed:", error);

        // Dropdowns remain usable even if the backend is offline.
        populateDropdowns();
        featuresLoaded = false;
        setLoading(false);

        if (featureLoadMessage) {
            featureLoadMessage.textContent =
                "Dropdowns loaded. Start the Flask backend to enable predictions.";
        }

        showError(error.message || "Could not connect to the backend.");
    });
})();