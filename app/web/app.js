/**
 * AI Media Factory — Web UI Client Logic
 *
 * Handles form submission, progress polling, video preview, and download.
 * Uses vanilla JS with no framework dependencies.
 */
(function () {
    "use strict";

    // --- Flow Completion Tracker ---
    const flowTracker = {
        steps: { input: false, submit: false, progress: false, preview: false, download: false },
        startTime: null,
        mark(step) {
            if (this.steps[step]) return; // Already marked
            this.steps[step] = true;
            if (!this.startTime) this.startTime = Date.now();
            console.log(`[Flow] Step completed: ${step}`, this.completionSummary());
            this._updateDebugPanel();
        },
        completionSummary() {
            const completed = Object.values(this.steps).filter(Boolean).length;
            const total = Object.keys(this.steps).length;
            return { completed, total, rate: Math.round((completed / total) * 100), steps: { ...this.steps } };
        },
        getDropOff() {
            return Object.entries(this.steps).filter(([_, v]) => !v).map(([k]) => k);
        },
        getElapsed() {
            if (!this.startTime) return 0;
            return Math.round((Date.now() - this.startTime) / 1000);
        },
        _updateDebugPanel() {
            const panel = document.getElementById("debug-panel");
            if (!panel) return;
            const summary = this.completionSummary();
            const dropOff = this.getDropOff();
            const elapsed = this.getElapsed();
            panel.innerHTML = `
                <strong>Flow Debug</strong><br>
                Steps: ${summary.completed}/${summary.total} (${summary.rate}%)<br>
                Elapsed: ${elapsed}s<br>
                Drop-off: ${dropOff.length > 0 ? dropOff.join(", ") : "none"}<br>
                ${Object.entries(this.steps).map(([k, v]) => `${v ? "✓" : "○"} ${k}`).join("<br>")}
            `;
        }
    };
    window.flowTracker = flowTracker;

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
    let pollFailureCount = 0;
    let elapsedTimer = null;
    let generationStartTime = null;
    const MAX_POLL_RETRIES = 3;
    const POLL_TIMEOUT_MS = 300000; // 5 minutes

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

    const STAGE_LABELS_CN = {
        script: "脚本生成",
        audio: "语音合成",
        subtitles: "字幕生成",
        media: "素材匹配",
        compose: "视频合成",
        completed: "已完成",
        failed: "生成失败",
    };

    const STAGE_ORDER = ["script", "audio", "subtitles", "media", "compose"];

    let _currentStage = "script";

    // --- Character counter + input tracking ---
    $prompt.addEventListener("input", function () {
        $charCount.textContent = this.value.length;
        if (this.value.trim().length > 0) {
            flowTracker.mark("input");
        }
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
        flowTracker.mark("submit");

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
            showError(err.message || "无法连接服务器，请检查网络后重试");
            setLoading(false);
        }
    });

    // --- Polling ---
    function startPolling(videoId) {
        stopPolling(); // Clear any existing interval
        pollFailureCount = 0;
        generationStartTime = Date.now();

        // Start elapsed time timer
        elapsedTimer = setInterval(updateElapsedTime, 1000);

        pollingInterval = setInterval(async () => {
            // Check timeout
            if (Date.now() - generationStartTime > POLL_TIMEOUT_MS) {
                stopPolling();
                showTimeoutOptions();
                return;
            }

            try {
                const response = await fetch(`/api/videos/${videoId}/status`);
                if (!response.ok) throw new Error("Status request failed");

                pollFailureCount = 0; // Reset on success
                const data = await response.json();
                updateProgress(data.stage, data.error);
                flowTracker.mark("progress");

                if (data.stage === "completed") {
                    stopPolling();
                    loadVideoPreview(videoId);
                    setLoading(false);
                } else if (data.stage === "failed") {
                    stopPolling();
                    showPipelineError(data.error || "Pipeline failed");
                    setLoading(false);
                }
            } catch (err) {
                pollFailureCount++;
                console.warn(`Poll error (${pollFailureCount}/${MAX_POLL_RETRIES}):`, err.message);

                if (pollFailureCount >= MAX_POLL_RETRIES) {
                    stopPolling();
                    showConnectionLost();
                }
            }
        }, 2000);
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
        if (elapsedTimer) {
            clearInterval(elapsedTimer);
            elapsedTimer = null;
        }
    }

    function updateElapsedTime() {
        if (!generationStartTime) return;
        const elapsed = Math.floor((Date.now() - generationStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        const timeStr = `${minutes}:${seconds.toString().padStart(2, "0")}`;
        $stageLabel.textContent = `${STAGE_LABELS[_currentStage] || "Processing..."} (已用时间: ${timeStr})`;
    }

    function showConnectionLost() {
        const errorDiv = $progressError;
        errorDiv.innerHTML = "连接中断 — 网络请求失败3次";
        const retryBtn = document.createElement("button");
        retryBtn.textContent = "重新连接";
        retryBtn.className = "btn btn-primary";
        retryBtn.style.marginTop = "0.5rem";
        retryBtn.addEventListener("click", function () {
            errorDiv.hidden = true;
            if (currentVideoId) startPolling(currentVideoId);
        });
        errorDiv.appendChild(retryBtn);
        errorDiv.hidden = false;
        setLoading(false);
    }

    function showPipelineError(errorMsg) {
        const errorDiv = $progressError;
        errorDiv.innerHTML = `生成失败: ${errorMsg}`;
        const retryBtn = document.createElement("button");
        retryBtn.textContent = "重新生成";
        retryBtn.className = "btn btn-primary";
        retryBtn.style.marginTop = "0.5rem";
        retryBtn.addEventListener("click", resetForm);
        errorDiv.appendChild(retryBtn);
        errorDiv.hidden = false;
    }

    function showTimeoutOptions() {
        const errorDiv = $progressError;
        errorDiv.innerHTML = "生成超时 — 已超过5分钟";
        const btnContainer = document.createElement("div");
        btnContainer.style.cssText = "display:flex;gap:0.5rem;margin-top:0.5rem;";

        const waitBtn = document.createElement("button");
        waitBtn.textContent = "继续等待";
        waitBtn.className = "btn btn-primary";
        waitBtn.addEventListener("click", function () {
            errorDiv.hidden = true;
            generationStartTime = Date.now(); // Reset timeout
            if (currentVideoId) startPolling(currentVideoId);
        });

        const cancelBtn = document.createElement("button");
        cancelBtn.textContent = "取消";
        cancelBtn.className = "btn btn-success";
        cancelBtn.addEventListener("click", resetForm);

        btnContainer.appendChild(waitBtn);
        btnContainer.appendChild(cancelBtn);
        errorDiv.appendChild(btnContainer);
        errorDiv.hidden = false;
        setLoading(false);
    }

    function resetForm() {
        stopPolling();
        currentVideoId = null;
        generationStartTime = null;
        pollFailureCount = 0;
        _currentStage = "script";
        setLoading(false);
        $progressSection.hidden = true;
        $previewSection.hidden = true;
        $downloadSection.hidden = true;
        $progressError.hidden = true;
        $prompt.value = "";
        $charCount.textContent = "0";
        resetStepper();
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // --- Progress UI ---
    function updateProgress(stage, error) {
        _currentStage = stage;
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

            // Update step labels with Chinese checkmarks
            const labelEl = step.querySelector(".step-label");
            if (labelEl && STAGE_LABELS_CN[stepStage]) {
                const isCompleted = step.classList.contains("completed");
                labelEl.textContent = (isCompleted ? "✓ " : "") + STAGE_LABELS_CN[stepStage];
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
        const cnLabel = STAGE_LABELS_CN[stage] || stage;
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
            flowTracker.mark("preview");

            // Set download link
            $downloadBtn.href = `/api/videos/${videoId}/download`;
            $downloadBtn.textContent = "Download MP4";
            $downloadBtn.addEventListener("click", function () {
                flowTracker.mark("download");
            });

            // Add "Generate New Video" button if not exists
            if (!document.getElementById("new-video-btn")) {
                const newBtn = document.createElement("button");
                newBtn.id = "new-video-btn";
                newBtn.className = "btn btn-primary";
                newBtn.textContent = "生成新视频";
                newBtn.style.marginTop = "0.75rem";
                newBtn.addEventListener("click", resetForm);
                $downloadSection.appendChild(newBtn);
            }

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
