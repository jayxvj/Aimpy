"use strict";

(() => {
    const API_BASE_URL = "http://127.0.0.1:5000";

    async function request(endpoint, options = {}) {
        let response;

        try {
            response = await fetch(`${API_BASE_URL}${endpoint}`, {
                ...options,
                headers: {
                    Accept: "application/json",
                    ...(options.body
                        ? { "Content-Type": "application/json" }
                        : {}),
                    ...options.headers
                }
            });
        } catch (error) {
            throw new Error(
                "Backend connection failed. Please start your Flask server."
            );
        }

        let data;

        try {
            data = await response.json();
        } catch {
            throw new Error(
                `Invalid server response. HTTP ${response.status}`
            );
        }

        if (!response.ok) {
            throw new Error(
                data.error ||
                data.message ||
                `Request failed. HTTP ${response.status}`
            );
        }

        return data;
    }

    async function getApiStatus() {
        return request("/");
    }

    async function getModelFeatures() {
        const data = await request("/features");

        if (Array.isArray(data)) {
            return data;
        }

        if (Array.isArray(data.features)) {
            return data.features;
        }

        throw new Error("Invalid feature response from backend.");
    }

    async function getModelSchema() {
        return request("/schema");
    }

    async function predictStudentPerformance(studentData) {
        if (
            !studentData ||
            typeof studentData !== "object" ||
            Array.isArray(studentData)
        ) {
            throw new Error("Please enter valid student details.");
        }

        return request("/predict", {
            method: "POST",
            body: JSON.stringify(studentData)
        });
    }

    window.EduPredictAPI = Object.freeze({
        API_BASE_URL,
        request,
        getApiStatus,
        getModelFeatures,
        getModelSchema,
        predictStudentPerformance
    });
})();