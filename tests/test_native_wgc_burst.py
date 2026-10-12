"""Exercise the native burst's actual C++ freshness/background/coverage policy without a game."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/native_wgc'

HARNESS = r'''
#include "burst_window_capture.h"
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
using namespace NativeWgcBurst;
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
WindowState baseline() {
    WindowState s;
    s.hwnd = 789; s.pid = 123; s.threadId = 77; s.creationTime = 456;
    s.processLive = s.windowValid = s.visible = s.geometryValid = true;
    s.foregroundHwnd = 42; s.foregroundPid = 43;
    s.client = {10,20,74,68}; s.frame = {2,2,82,76};
    s.extendedStyle = 0x08000000U;
    return s;
}
int64_t realClock100ns() {
    return std::chrono::duration_cast<std::chrono::duration<int64_t,std::ratio<1,10000000>>>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
int main(int argc, char** argv) {
    try {
        require(argc == 2, "scenario required");
        const std::string scenario = argv[1];
        CaptureOptions options{1000,180,100,200};
        const int64_t request = 1000000, end = 11000000;
        if (scenario == "freshness") {
            FrameTimeline t(request, end, options);
            require(!t.assess(request,request).valid(), "equal request accepted");
            require(!t.assess(request-1,request).valid(), "pre-request accepted");
            require(!t.assess(request+1,request).valid(), "future timestamp accepted");
            require(!t.assess(request+1,request+2000002).valid(), "old delivery accepted");
            require(!t.assess(end+1,end+2).valid(), "outside planned interval accepted");
            require(t.assess(request+10,request+11).valid(), "fresh frame rejected");
            t.accept(request+10);
            require(!t.assess(request+10,request+11).valid(), "duplicate accepted");
            require(!t.assess(request+9,request+11).valid(), "nonmonotonic accepted");
            require(t.assess(request+11,request+12).valid(), "next fresh frame rejected");
        } else if (scenario == "future_wait_real_clock") {
            const auto now = realClock100ns(), frame = now + 20000, deadline = now + 1000000;
            FrameTimeline timeline(now,deadline,options);
            const auto initial = timeline.assess(frame,now);
            require(initial.error == "frame_timestamp_in_future", "future frame accepted without waiting");
            FutureTimestampWait wait(frame,now,deadline,initial);
            require(wait.requested() && !wait.eligible(now), "future wait did not retain strict eligibility");
            auto observed = realClock100ns();
            while (wait.shouldWait(observed)) {
                std::this_thread::sleep_for(std::chrono::microseconds(100));
                observed = realClock100ns();
            }
            require(wait.eligible(observed) && timeline.assess(frame,observed).valid(),
                    "real clock never made the frame eligible inside the wait budget");
        } else if (scenario == "future_wait_bounds") {
            FrameTimeline timeline(request,end,options);
            const auto large = request + FutureTimestampWaitLimit100ns + 1;
            require(!FutureTimestampWait(large,request,end,timeline.assess(large,request)).requested(),
                    "large future offset received a wait allowance");
            require(!FutureTimestampWait(end+1,end,end,timeline.assess(end+1,end)).requested(),
                    "future wait extended the capture interval");
            FutureTimestampWait tail(end,end-10,end,timeline.assess(end,end-10));
            require(tail.deadline() == end && tail.eligible(end) && !tail.eligible(end+1),
                    "wait accepted an observation after the planned deadline");
            const auto frame = request + 1000001;
            FutureTimestampWait head(frame,frame-1,end,timeline.assess(frame,frame-1));
            require(head.eligible(frame), "small offset incorrectly blocked");
            require(timeline.assess(frame,frame).gapExceeded, "waiting concealed the startup gap");
            timeline.accept(frame);
            for (int64_t time = frame + 500000; time < end; time += 500000) timeline.accept(time);
            require(!timeline.complete(true,false), "waited frame made an uncovered interval complete");
        } else if (scenario == "background") {
            const WindowBinding binding{789,123,456};
            const auto first = baseline();
            auto current = first;
            require(windowFailure(binding,current,&first).empty(), "valid binding rejected");
            current.foregroundHwnd = 99; current.foregroundPid = 100;
            require(windowFailure(binding,current,&first).empty(), "other application switch rejected");
            current.foregroundPid = binding.pid;
            require(windowFailure(binding,current,&first) == "owned_process_became_foreground", "foreground accepted");
            current = first; current.minimized = true;
            require(!windowFailure(binding,current,&first).empty(), "minimized accepted");
            current = first; current.visible = false;
            require(!windowFailure(binding,current,&first).empty(), "hidden accepted");
            current = first; current.cloaked = true;
            require(!windowFailure(binding,current,&first).empty(), "cloaked accepted");
            current = first; current.extendedStyle = 0;
            require(windowFailure(binding,current,&first) == "window_missing_noactivate_style", "noactivate change accepted");
            require(windowFailure(binding,current) == "window_missing_noactivate_style", "missing initial noactivate accepted");
        } else if (scenario == "rejected_frame_guard") {
            const WindowBinding binding{789,123,456};
            const auto first = baseline();
            FrameTimeline timeline(request,end,options);
            const auto rejected = timeline.assess(request,request+1);
            require(rejected.error == "frame_not_after_request", "expected timestamp rejection");
            require(guardedFrameFailure(binding,first,first,rejected.error) == rejected.error,
                    "safe rejected frame changed its diagnosis");
            for (auto fault : {0,1,2,3}) {
                auto changed = first;
                if (fault == 0) changed.foregroundPid = binding.pid;
                if (fault == 1) changed.extendedStyle = 0;
                if (fault == 2) changed.creationTime++;
                if (fault == 3) changed.client.right++;
                const auto failure = guardedFrameFailure(binding,changed,first,rejected.error);
                require(failure == windowFailure(binding,changed,&first) && failure != rejected.error,
                        "timestamp rejection suppressed a transient window guard violation");
                require(guardedFrameFailure(binding,first,first,failure) == failure,
                        "restored window erased the prior terminal failure");
            }
        } else if (scenario == "identity_geometry") {
            const WindowBinding binding{789,123,456};
            const auto first = baseline();
            auto current = first;
            current.creationTime = 457;
            require(!windowFailure(binding,current,&first).empty(), "PID reuse accepted");
            current = first; current.processLive = false;
            require(!windowFailure(binding,current,&first).empty(), "dead process accepted");
            current = first; current.pid = 124;
            require(!windowFailure(binding,current,&first).empty(), "different window owner accepted");
            current = first; current.hwnd = 788;
            require(!windowFailure(binding,current,&first).empty(), "different HWND accepted");
            current = first; current.threadId = 78;
            require(!windowFailure(binding,current,&first).empty(), "window thread change accepted");
            current = first; ++current.client.right;
            require(!windowFailure(binding,current,&first).empty(), "resize accepted");
            current = first; ++current.frame.left;
            require(!windowFailure(binding,current,&first).empty(), "DWM geometry change accepted");
            current = first; current.geometryValid = false;
            require(!windowFailure(binding,current,&first).empty(), "unknown crop accepted");
        } else if (scenario == "gaps") {
            FrameTimeline good(request,end,options);
            for (int64_t time = request + 500000; time < end; time += 500000) {
                require(!good.assess(time,time+1).gapExceeded, "50ms gap flagged");
                good.accept(time);
            }
            require(good.complete(true,false), "covered interval rejected");
            require(!good.complete(false,false), "early frame cap accepted as complete");
            require(!good.complete(true,true), "terminal failure accepted as complete");
            FrameTimeline middle(request,end,options);
            middle.accept(request+1);
            require(middle.assess(request+1000002,request+1000003).gapExceeded, "interior gap not flagged");
            middle.accept(request+1000002);
            for (int64_t time = request+1500002; time < end; time+=500000) middle.accept(time);
            require(!middle.complete(true,false), "interior gap accepted");
            FrameTimeline head(request,end,options);
            require(head.assess(request+1000001,request+1000002).gapExceeded, "startup gap not flagged");
            head.accept(request+1000001);
            for (int64_t time = request+1500001; time < end; time+=500000) head.accept(time);
            require(!head.complete(true,false), "startup gap accepted");
            FrameTimeline tail(request,end,options);
            for (int64_t time = request+500000; time < end-1000000; time+=500000) tail.accept(time);
            require(tail.tailGap() > 1000000 && !tail.complete(true,false), "tail gap accepted");
            FrameTimeline empty(request,end,options);
            require(!empty.complete(true,false), "empty interval accepted");
        } else if (scenario == "bounds") {
            require(validOptions(options), "ordinary plan rejected");
            for (auto field : {0,1,2,3}) {
                auto invalid = options;
                if (field == 0) invalid.durationMs = 60001;
                if (field == 1) invalid.maxFrames = 1801;
                if (field == 2) invalid.maxGapMs = 0;
                if (field == 3) invalid.maxFrameAgeMs = 5001;
                require(!validOptions(invalid), "unbounded plan accepted");
            }
        } else throw std::runtime_error("unknown scenario");
        std::cout << scenario << ":passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
'''


class NativeBurstContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('g++') or shutil.which('clang++')
        if compiler is None:
            raise unittest.SkipTest('A C++20 compiler is required for native burst contract tests')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        directory = Path(cls.temporary.name)
        source = directory / 'burst_contract.cpp'
        source.write_text(HARNESS, encoding='ascii')
        cls.executable = directory / 'burst_contract.exe'
        subprocess.run([compiler, '-std=c++20', '-I', str(SOURCE), str(source), '-o', str(cls.executable)],
                       capture_output=True, text=True, timeout=60, check=True)

    def scenario(self, name):
        result = subprocess.run([str(self.executable), name], capture_output=True, text=True,
                                timeout=10, check=True)
        self.assertEqual(name + ':passed', result.stdout.strip())

    def test_equal_duplicate_old_future_and_nonmonotonic_frames_are_rejected(self):
        self.scenario('freshness')

    def test_future_frame_requires_actual_clock_progress_before_eligibility(self):
        self.scenario('future_wait_real_clock')

    def test_future_wait_rejects_large_offsets_deadline_overrun_and_uncovered_gaps(self):
        self.scenario('future_wait_bounds')

    def test_owned_foreground_minimize_cloak_and_noactivate_change_fail(self):
        self.scenario('background')

    def test_process_creation_window_owner_and_client_geometry_are_bound(self):
        self.scenario('identity_geometry')

    def test_rejected_timestamp_cannot_mask_a_transient_window_guard_failure(self):
        self.scenario('rejected_frame_guard')

    def test_start_middle_tail_gaps_and_early_cap_cannot_be_complete(self):
        self.scenario('gaps')

    def test_duration_frame_cap_and_temporal_thresholds_are_bounded(self):
        self.scenario('bounds')


if __name__ == '__main__':
    unittest.main()
