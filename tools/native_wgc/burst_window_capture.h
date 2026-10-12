#pragma once

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <string>

namespace NativeWgcBurst {
    struct Rect {
        int32_t left = 0, top = 0, right = 0, bottom = 0;
        bool operator==(const Rect&) const = default;
    };

    struct WindowBinding {
        uint64_t hwnd = 0;
        uint32_t pid = 0;
        uint64_t creationTime = 0;
    };

    struct WindowState {
        uint64_t hwnd = 0;
        uint32_t pid = 0, threadId = 0;
        uint64_t creationTime = 0;
        bool processLive = false, windowValid = false, visible = false;
        bool minimized = false, cloaked = false, geometryValid = false;
        uint64_t foregroundHwnd = 0;
        uint32_t foregroundPid = 0, extendedStyle = 0;
        Rect client{}, frame{};
        int64_t observedQpc100ns = 0;
    };

    inline std::string windowFailure(const WindowBinding& expected, const WindowState& current,
                                     const WindowState* baseline = nullptr) {
        if (!current.processLive || current.creationTime != expected.creationTime)
            return "process_identity_changed";
        if (!current.windowValid || current.hwnd != expected.hwnd || current.pid != expected.pid)
            return "window_identity_changed";
        if (current.foregroundPid == expected.pid) return "owned_process_became_foreground";
        if (!(current.extendedStyle & 0x08000000U)) return "window_missing_noactivate_style";
        if (!current.visible || current.minimized || current.cloaked) return "window_not_capturable_in_background";
        if (!current.geometryValid || current.client.right <= current.client.left ||
            current.client.bottom <= current.client.top) return "client_geometry_unavailable";
        if (baseline && (current.threadId != baseline->threadId || current.client != baseline->client ||
                         current.frame != baseline->frame)) return "window_geometry_or_thread_changed";
        return {};
    }

    inline std::string guardedFrameFailure(const WindowBinding& expected, const WindowState& current,
                                           const WindowState& baseline, const std::string& frameError) {
        const auto guardError = windowFailure(expected, current, &baseline);
        return guardError.empty() ? frameError : guardError;
    }

    struct CaptureOptions {
        uint32_t durationMs = 1000;
        uint32_t maxFrames = 180;
        uint32_t maxGapMs = 150;
        uint32_t maxFrameAgeMs = 1000;
    };

    inline bool validOptions(const CaptureOptions& options) {
        return options.durationMs >= 50 && options.durationMs <= 60000 &&
               options.maxFrames >= 1 && options.maxFrames <= 1800 &&
               options.maxGapMs >= 1 && options.maxGapMs <= 5000 &&
               options.maxFrameAgeMs >= 1 && options.maxFrameAgeMs <= 5000;
    }

    struct FrameAssessment {
        std::string error;
        int64_t delta100ns = 0, age100ns = 0;
        bool gapExceeded = false;
        bool valid() const { return error.empty(); }
    };

    constexpr int64_t FutureTimestampWaitLimit100ns = 50 * 10000;
    constexpr uint32_t FutureTimestampWaitGuardLimit = 128;

    class FutureTimestampWait {
    public:
        FutureTimestampWait(int64_t frame, int64_t observed, int64_t deadline,
                            const FrameAssessment& initial) : frame_(frame) {
            if (initial.error == "frame_timestamp_in_future" && frame > observed &&
                frame <= deadline && frame - observed <= FutureTimestampWaitLimit100ns)
                deadline_ = observed + std::min(FutureTimestampWaitLimit100ns, deadline - observed);
        }
        bool requested() const { return deadline_ != 0; }
        int64_t deadline() const { return deadline_; }
        bool shouldWait(int64_t observed) const {
            return requested() && observed < frame_ && observed < deadline_;
        }
        bool eligible(int64_t observed) const {
            return requested() && observed >= frame_ && observed <= deadline_;
        }
    private:
        int64_t frame_, deadline_ = 0;
    };

    // This policy is shared with the host-only tests; it never reads a game clock.
    class FrameTimeline {
    public:
        FrameTimeline(int64_t requested, int64_t deadline, const CaptureOptions& options)
            : requested_(requested), deadline_(deadline), maxGap_(int64_t(options.maxGapMs) * 10000),
              maxAge_(int64_t(options.maxFrameAgeMs) * 10000) {}

        FrameAssessment assess(int64_t frame, int64_t observed) const {
            FrameAssessment result;
            result.age100ns = observed - frame;
            if (frame <= requested_) result.error = "frame_not_after_request";
            else if (frame <= last_) result.error = "frame_not_strictly_monotonic";
            else if (frame > observed) result.error = "frame_timestamp_in_future";
            else if (result.age100ns > maxAge_) result.error = "frame_delivery_too_old";
            else if (frame > deadline_) result.error = "frame_after_planned_interval";
            result.delta100ns = frame - (last_ ? last_ : requested_);
            result.gapExceeded = result.valid() && result.delta100ns > maxGap_;
            return result;
        }

        void accept(int64_t frame) {
            const auto gap = frame - (last_ ? last_ : requested_);
            maxObservedGap_ = std::max(maxObservedGap_, gap);
            gapExceeded_ = gapExceeded_ || gap > maxGap_;
            if (!first_) first_ = frame;
            last_ = frame;
            ++count_;
        }

        int64_t tailGap() const { return deadline_ - (last_ ? last_ : requested_); }
        int64_t maximumGap() const { return std::max(maxObservedGap_, tailGap()); }
        bool complete(bool reachedDeadline, bool terminalFailure) const {
            return reachedDeadline && !terminalFailure && count_ >= 2 && !gapExceeded_ && tailGap() <= maxGap_;
        }
        uint32_t count() const { return count_; }
        int64_t first() const { return first_; }
        int64_t last() const { return last_; }
        int64_t startGap() const { return first_ ? first_ - requested_ : deadline_ - requested_; }
        bool tailGapExceeded() const { return tailGap() > maxGap_; }

    private:
        int64_t requested_, deadline_, maxGap_, maxAge_;
        int64_t first_ = 0, last_ = 0, maxObservedGap_ = 0;
        uint32_t count_ = 0;
        bool gapExceeded_ = false;
    };

    struct BurstResult {
        bool captureValid = false, temporalComplete = false;
        std::string manifestJson;
    };

    BurstResult captureWindowBurstPng(const WindowBinding& binding, const CaptureOptions& options,
                                     const std::filesystem::path& outputDirectory);
    void writeFreshFile(const std::filesystem::path& path, const uint8_t* bytes, size_t count);
}
