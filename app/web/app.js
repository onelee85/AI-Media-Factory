/**
 * AI Media Factory — Web UI Client Logic
 *
 * Handles form submission, progress polling, video preview, and download.
 * Uses vanilla JS with no framework dependencies.
 */
(function () {
    "use strict";

    // --- DOM references ---
    const $prompt = document.getElementById("prompt");
    const $title = document.getElementById("title");
    const $voice = document.getElementById("voice");
    const $charCount = document.getElementById("char-count");
    const $generateBtn = document.getElementById("generate-btn");
    const $btnText = $generateBtn.querySelector(".btn-text");
    const $btnSpinner = $generateBtn.querySelector(".btn-spinner");
    const $errorMessage = document.getElementById("error-message");

    const $inputSection = document.getElementById("input-section");
    const $progressSection = document.getElementById("progress-section");
    const $stageLabel = document.getElementById("stage-label");
    const $progressError = document.getElementById("progress-error");

    const $previewSection = document.getElementById("preview-section");
    const $videoPlayer = document.getElementById("video-player");
    const $videoTitle = document.getElementById("video-title");
    const $videoSize = document.getElementById("video-size");

    const $downloadSection = document.getElementById("download-section");
    const $downloadBtn = document.getElementById("download-btn");

    // --- State ---
    let currentVideoId = null;
    let pollingInterval = null;

    // --- Stage labels ---
    const STAGE_LABELS = {
        script: "Generating script...",
        audio: "Synthesizing voice...",
        subtitles: "Creating subtitles...",
        media: "Matching media...",
        compose: "Rendering video...",
        completed: "Video completed!",
        failed: "Pipeline failed",
    };

    const STAGE_ORDER = ["script", "audio", "subtitles", "media", "compose"];

    // --- Character counter ---
    $prompt.addEventListener("input", function () {
        $charCount.textContent = this.value.length;
    });

    // --- Form submission ---
    $generateBtn.addEventListener("click", async function () {
        const prompt = $prompt.value.trim();

        // Validate
        if (!prompt) {
            showError("Please enter a video topic.");
            return;
        }
        if (prompt.length > 4000) {
            showError("Prompt must be 4000 characters or less.");
            return;
        }

        // Clear previous state
        hideError();
        setLoading(true);

        try {
            const response = await fetch("/api/videos/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt: prompt,
                    title: $title.value.trim() || "",
                    voice: $voice.value,
                }),
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || `Request failed (${response.status})`);
            }

            const data = await response.json();
            currentVideoId = data.video_id;

            // Show progress, start polling
            $progressSection.hidden = false;
            resetStepper();
            startPolling(currentVideoId);

            // Scroll to progress
            $progressSection.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (err) {
            showError(err.message || "Failed to submit request.");
            setLoading(false);
        }
    });

    // --- Polling ---
    function startPolling(videoId) {
        stopPolling(); // Clear any existing interval

        pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/videos/${videoId}/status`);
                if (!response.ok) throw new Error("Status request failed");

                const data = await response.json();
                updateProgress(data.stage, data.error);

                if (data.stage === "completed") {
                    stopPolling();
                    loadVideoPreview(videoId);
                    setLoading(false);
                } else if (data.stage === "failed") {
                    stopPolling();
                    showProgressError(data.error || "Pipeline failed");
                    setLoading(false);
                }
            } catch (err) {
                // Silently retry — network blips are common
                console.warn("Poll error:", err.message);
            }
        }, 2000);
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    // --- Progress UI ---
    function updateProgress(stage, error) {
        const steps = document.querySelectorAll(".step");
        const lines = document.querySelectorAll(".step-line");

        steps.forEach((step, i) => {
            const stepStage = step.dataset.stage;
            step.classList.remove("active", "completed", "failed");

            if (stage === "failed") {
                // Mark the current stage as failed
                if (stepStage === getCurrentFailedStage(i)) {
                    step.classList.add("failed");
                }
            } else {
                const stageIndex = STAGE_ORDER.indexOf(stage);
                const stepIndex = STAGE_ORDER.indexOf(stepStage);

                if (stepIndex < stageIndex) {
                    step.classList.add("completed");
                } else if (stepIndex === stageIndex) {
                    step.classList.add("active");
                }
            }
        });

        // Update lines
        lines.forEach((line, i) => {
            line.classList.remove("completed");
            if (stage !== "failed") {
                const stageIndex = STAGE_ORDER.indexOf(stage);
                if (i < stageIndex) {
                    line.classList.add("completed");
                }
            }
        });

        // Update label
        $stageLabel.textContent = STAGE_LABELS[stage] || stage;
    }

    function getCurrentFailedStage(stepIndex) {
        // Best guess at which step failed
        return STAGE_ORDER[stepIndex] || "compose";
    }

    function resetStepper() {
        document.querySelectorAll(".step").forEach((s) => {
            s.classList.remove("active", "completed", "failed");
        });
        document.querySelectorAll(".step-line").forEach((l) => {
            l.classList.remove("completed");
        });
        $stageLabel.textContent = "Initializing...";
        $progressError.hidden = true;
    }

    // --- Video preview ---
    async function loadVideoPreview(videoId) {
        try {
            // Fetch video details
            const response = await fetch(`/api/videos/${videoId}`);
            if (!response.ok) return;

            const video = await response.json();

            // Set video source
            $videoPlayer.src = `/api/videos/${videoId}/download`;

            // Set info
            $videoTitle.textContent = video.script?.title || "Generated Video";
            if (video.file_size_bytes) {
                $videoSize.textContent = formatFileSize(video.file_size_bytes);
            }

            // Show sections
            $previewSection.hidden = false;
            $downloadSection.hidden = false;

            // Set download link
            $downloadBtn.href = `/api/videos/${videoId}/download`;
            $downloadBtn.textContent = "Download MP4";

            // Scroll to preview
            $previewSection.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (err) {
            console.warn("Preview load error:", err.message);
        }
    }

    // --- Helpers ---
    function setLoading(loading) {
        $generateBtn.disabled = loading;
        $btnText.textContent = loading ? "Generating..." : "Generate Video";
        $btnSpinner.hidden = !loading;
    }

    function showError(message) {
        $errorMessage.textContent = message;
        $errorMessage.hidden = false;
    }

    function hideError() {
        $errorMessage.hidden = true;
    }

    function showProgressError(message) {
        $progressError.textContent = message;
        $progressError.hidden = false;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }
})();
