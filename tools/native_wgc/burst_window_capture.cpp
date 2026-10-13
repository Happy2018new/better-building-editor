#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "burst_window_capture.h"

#include <atomic>
#include <iomanip>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <vector>
#include <d3d11.h>
#include <dwmapi.h>
#include <wincodec.h>
#include <windows.graphics.capture.interop.h>
#include <windows.graphics.directx.direct3d11.interop.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Graphics.Capture.h>
#include <winrt/Windows.Graphics.DirectX.Direct3D11.h>

namespace NativeWgcBurst {
    namespace {
        using namespace winrt::Windows::Graphics;
        using namespace winrt::Windows::Graphics::Capture;
        using namespace winrt::Windows::Graphics::DirectX;
        using namespace winrt::Windows::Graphics::DirectX::Direct3D11;

        struct Handle {
            HANDLE value = nullptr;
            ~Handle() { if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value); }
        };

        template <typename T> struct CaptureResource {
            T value{nullptr};
            ~CaptureResource() {
                if (value) { try { value.Close(); } catch (...) {} }
            }
        };

        struct Apartment {
            Apartment() { winrt::init_apartment(winrt::apartment_type::multi_threaded); }
            ~Apartment() { winrt::uninit_apartment(); }
        };

        struct DpiContext {
            DPI_AWARENESS_CONTEXT previous = nullptr;
            DpiContext() {
                previous = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
                winrt::check_bool(previous != nullptr);
            }
            ~DpiContext() { if (previous) SetThreadDpiAwarenessContext(previous); }
        };

        struct FrameSignal {
            Handle event{CreateEventW(nullptr, FALSE, FALSE, nullptr)};
            std::atomic<bool> closed{false};
            std::atomic<uint64_t> arrivals{0};
        };

        void keepCaptureModuleLoaded(IUnknown* factory) {
            [[maybe_unused]] static const HMODULE module = [factory] {
                const auto vtable = *reinterpret_cast<const void* const* const*>(factory);
                HMODULE result = nullptr;
                winrt::check_bool(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                    GET_MODULE_HANDLE_EX_FLAG_PIN, reinterpret_cast<LPCWSTR>(vtable), &result));
                return result;
            }();
        }

        int64_t qpcNow(int64_t frequency) {
            LARGE_INTEGER current{};
            winrt::check_bool(QueryPerformanceCounter(&current));
            return static_cast<int64_t>(static_cast<long double>(current.QuadPart) * 10000000.L / frequency);
        }

        Rect rect(const RECT& value) { return {value.left, value.top, value.right, value.bottom}; }

        WindowState observe(const WindowBinding& binding, HANDLE process, int64_t frequency) {
            WindowState result;
            const auto hwnd = reinterpret_cast<HWND>(static_cast<uintptr_t>(binding.hwnd));
            result.hwnd = binding.hwnd;
            result.windowValid = IsWindow(hwnd) != FALSE;
            DWORD windowPid = 0;
            result.threadId = GetWindowThreadProcessId(hwnd, &windowPid);
            result.pid = windowPid;
            result.visible = IsWindowVisible(hwnd) != FALSE;
            result.minimized = IsIconic(hwnd) != FALSE;
            result.extendedStyle = static_cast<uint32_t>(GetWindowLongPtrW(hwnd, GWL_EXSTYLE));
            FILETIME created{}, exited{}, kernel{}, user{};
            result.processLive = process && WaitForSingleObject(process, 0) == WAIT_TIMEOUT &&
                GetProcessTimes(process, &created, &exited, &kernel, &user);
            result.creationTime = (static_cast<uint64_t>(created.dwHighDateTime) << 32) | created.dwLowDateTime;
            const auto foreground = GetForegroundWindow();
            result.foregroundHwnd = reinterpret_cast<uintptr_t>(foreground);
            DWORD foregroundPid = 0;
            if (foreground) GetWindowThreadProcessId(foreground, &foregroundPid);
            result.foregroundPid = foregroundPid;
            DWORD cloaked = 0;
            RECT frame{}, client{};
            POINT origin{};
            const bool dwmKnown = SUCCEEDED(DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, &cloaked, sizeof(cloaked)));
            result.cloaked = !dwmKnown || cloaked != 0;
            result.geometryValid = SUCCEEDED(DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                &frame, sizeof(frame))) && GetClientRect(hwnd, &client) && ClientToScreen(hwnd, &origin);
            result.frame = rect(frame);
            result.client = {origin.x + client.left, origin.y + client.top,
                             origin.x + client.right, origin.y + client.bottom};
            result.observedQpc100ns = qpcNow(frequency);
            return result;
        }

        std::string jsonString(const std::string& value) {
            std::ostringstream result;
            result << '"';
            for (const unsigned char ch : value) {
                if (ch == '"' || ch == '\\') result << '\\' << ch;
                else if (ch < 32) result << "\\u" << std::hex << std::setw(4) <<
                    std::setfill('0') << int(ch) << std::dec;
                else result << ch;
            }
            result << '"';
            return result.str();
        }

        std::string rectJson(const Rect& value) {
            return '[' + std::to_string(value.left) + ',' + std::to_string(value.top) + ',' +
                std::to_string(value.right) + ',' + std::to_string(value.bottom) + ']';
        }

        std::string stateJson(const WindowState& value) {
            std::ostringstream result;
            result << std::boolalpha << "{\"hwnd\":" << value.hwnd << ",\"pid\":" << value.pid
                << ",\"thread_id\":" << value.threadId << ",\"creation_time\":" <<
                jsonString(std::to_string(value.creationTime)) << ",\"process_live\":" << value.processLive
                << ",\"window_valid\":" << value.windowValid << ",\"visible\":" << value.visible
                << ",\"minimized\":" << value.minimized << ",\"cloaked\":" << value.cloaked
                << ",\"geometry_valid\":" << value.geometryValid << ",\"client_rect_screen\":" <<
                rectJson(value.client) << ",\"dwm_frame_rect\":" << rectJson(value.frame)
                << ",\"foreground_hwnd\":" << value.foregroundHwnd << ",\"foreground_pid\":" <<
                value.foregroundPid << ",\"extended_style\":" << value.extendedStyle
                << ",\"background_safe\":" << (value.foregroundPid != value.pid)
                << ",\"window_noactivate_style\":" <<
                ((value.extendedStyle & WS_EX_NOACTIVATE) != 0)
                << ",\"observed_qpc_100ns\":" << value.observedQpc100ns << '}';
            return result.str();
        }

        std::vector<uint8_t> encodePng(IWICImagingFactory* factory, IWICBitmapSource* bitmap,
                                       UINT width, UINT height) {
            winrt::com_ptr<IWICFormatConverter> converter;
            winrt::check_hresult(factory->CreateFormatConverter(converter.put()));
            winrt::check_hresult(converter->Initialize(bitmap, GUID_WICPixelFormat24bppBGR,
                WICBitmapDitherTypeNone, nullptr, 0, WICBitmapPaletteTypeCustom));
            winrt::com_ptr<IStream> stream;
            winrt::check_hresult(CreateStreamOnHGlobal(nullptr, TRUE, stream.put()));
            winrt::com_ptr<IWICBitmapEncoder> encoder;
            winrt::check_hresult(factory->CreateEncoder(GUID_ContainerFormatPng, nullptr, encoder.put()));
            winrt::check_hresult(encoder->Initialize(stream.get(), WICBitmapEncoderNoCache));
            winrt::com_ptr<IWICBitmapFrameEncode> frame;
            winrt::com_ptr<IPropertyBag2> properties;
            winrt::check_hresult(encoder->CreateNewFrame(frame.put(), properties.put()));
            winrt::check_hresult(frame->Initialize(properties.get()));
            winrt::check_hresult(frame->SetSize(width, height));
            WICPixelFormatGUID format = GUID_WICPixelFormat24bppBGR;
            winrt::check_hresult(frame->SetPixelFormat(&format));
            winrt::check_bool(IsEqualGUID(format, GUID_WICPixelFormat24bppBGR));
            winrt::check_hresult(frame->WriteSource(converter.get(), nullptr));
            winrt::check_hresult(frame->Commit());
            winrt::check_hresult(encoder->Commit());
            STATSTG stat{};
            winrt::check_hresult(stream->Stat(&stat, STATFLAG_NONAME));
            winrt::check_bool(stat.cbSize.QuadPart > 0 &&
                              stat.cbSize.QuadPart <= std::numeric_limits<ULONG>::max());
            std::vector<uint8_t> bytes(static_cast<size_t>(stat.cbSize.QuadPart));
            winrt::check_hresult(stream->Seek({}, STREAM_SEEK_SET, nullptr));
            ULONG read = 0;
            winrt::check_hresult(stream->Read(bytes.data(), static_cast<ULONG>(bytes.size()), &read));
            winrt::check_bool(read == bytes.size());
            return bytes;
        }

        winrt::com_ptr<IWICBitmap> copyBitmap(ID3D11Device* device, ID3D11DeviceContext* context,
            IWICImagingFactory* factory, const Direct3D11CaptureFrame& frame, SizeInt32 size,
            const RECT& crop) {
            auto access = frame.Surface().as<::Windows::Graphics::DirectX::Direct3D11::
                IDirect3DDxgiInterfaceAccess>();
            winrt::com_ptr<ID3D11Texture2D> texture;
            winrt::check_hresult(access->GetInterface(__uuidof(ID3D11Texture2D), texture.put_void()));
            D3D11_TEXTURE2D_DESC desc{};
            texture->GetDesc(&desc);
            if (desc.Width < static_cast<UINT>(size.Width) ||
                desc.Height < static_cast<UINT>(size.Height))
                throw std::runtime_error("frame_surface_smaller_than_content");
            desc.Width = static_cast<UINT>(crop.right - crop.left);
            desc.Height = static_cast<UINT>(crop.bottom - crop.top);
            desc.MipLevels = 1;
            desc.ArraySize = 1;
            desc.SampleDesc = {1, 0};
            desc.Usage = D3D11_USAGE_STAGING;
            desc.BindFlags = 0;
            desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
            desc.MiscFlags = 0;
            winrt::com_ptr<ID3D11Texture2D> staging;
            winrt::check_hresult(device->CreateTexture2D(&desc, nullptr, staging.put()));
            const D3D11_BOX box{static_cast<UINT>(crop.left), static_cast<UINT>(crop.top), 0,
                static_cast<UINT>(crop.right), static_cast<UINT>(crop.bottom), 1};
            context->CopySubresourceRegion(staging.get(), 0, 0, 0, 0, texture.get(), 0, &box);
            D3D11_MAPPED_SUBRESOURCE mapped{};
            winrt::check_hresult(context->Map(staging.get(), 0, D3D11_MAP_READ, 0, &mapped));
            struct Unmap {
                ID3D11DeviceContext* context;
                ID3D11Texture2D* texture;
                ~Unmap() { context->Unmap(texture, 0); }
            } unmap{context, staging.get()};
            const uint64_t bytes = static_cast<uint64_t>(mapped.RowPitch) * desc.Height;
            winrt::check_bool(bytes <= std::numeric_limits<UINT>::max());
            winrt::com_ptr<IWICBitmap> bitmap;
            winrt::check_hresult(factory->CreateBitmapFromMemory(desc.Width, desc.Height,
                GUID_WICPixelFormat32bppBGRA, mapped.RowPitch, static_cast<UINT>(bytes),
                static_cast<BYTE*>(mapped.pData), bitmap.put()));
            return bitmap;
        }

        struct Run {
            WindowBinding binding;
            CaptureOptions options;
            std::filesystem::path directory;
            WindowState baseline{}, finalState{};
            int64_t frequency = 0, request = 0, deadline = 0, ended = 0;
            uint32_t attempts = 0, rejected = 0;
            uint64_t arrivals = 0;
            std::string failure, stopReason = "setup_failure";
            std::vector<std::string> records;
            std::unique_ptr<FrameTimeline> timeline;

            std::string manifest() const {
                const bool captureValid = failure.empty() && timeline && timeline->count() > 0;
                const bool complete = timeline &&
                    timeline->complete(stopReason == "duration_elapsed", !failure.empty());
                std::ostringstream out;
                out << std::boolalpha << "{\"schema\":" << (options.allowUserForeground ? 2 : 1)
                    << ",\"backend\":\"Windows.Graphics.Capture\","
                    "\"mode\":\"persistent_burst\",\"clock\":\"compositor_system_relative_qpc_100ns\","
                    "\"background_only\":" << !options.allowUserForeground
                    << ",\"activation_fallback\":false,\"native_resolution\":true,";
                if (options.allowUserForeground)
                    out << "\"foreground_policy\":\"allow_user_foreground\",\"user_foreground_allowed\":true,"
                        "\"agent_activation_allowed\":false,";
                out <<
                    "\"pixel_acceptance\":false,\"ok\":" << (captureValid && complete)
                    << ",\"capture_valid\":" << captureValid << ",\"temporal_complete\":" << complete
                    << ",\"owned_hwnd\":" << binding.hwnd << ",\"owned_pid\":" << binding.pid
                    << ",\"owned_creation_time\":" << jsonString(std::to_string(binding.creationTime))
                    << ",\"planned_duration_ms\":" << options.durationMs << ",\"max_frames\":" << options.maxFrames
                    << ",\"max_gap_ms\":" << options.maxGapMs << ",\"max_frame_age_ms\":" << options.maxFrameAgeMs
                    << ",\"timestamp_policy\":\"strict_after_bounded_qpc_wait\""
                    << ",\"future_timestamp_wait_limit_ms\":" << FutureTimestampWaitLimit100ns / 10000
                    << ",\"future_timestamp_wait_guard_limit\":" << FutureTimestampWaitGuardLimit
                    << ",\"request_qpc_100ns\":" << request << ",\"planned_end_qpc_100ns\":" << deadline
                    << ",\"finished_qpc_100ns\":" << ended << ",\"attempted_frames\":" << attempts
                    << ",\"valid_frames\":" << (timeline ? timeline->count() : 0)
                    << ",\"rejected_frames\":" << rejected
                    << ",\"frame_arrival_events\":" << arrivals
                    << ",\"source_frame_loss_known\":false"
                    << ",\"first_frame_qpc_100ns\":" << (timeline ? timeline->first() : 0)
                    << ",\"last_frame_qpc_100ns\":" << (timeline ? timeline->last() : 0)
                    << ",\"tail_gap_100ns\":" << (timeline ? timeline->tailGap() : 0)
                    << ",\"start_gap_100ns\":" << (timeline ? timeline->startGap() : 0)
                    << ",\"tail_gap_exceeded\":" << (timeline ? timeline->tailGapExceeded() : false)
                    << ",\"maximum_gap_100ns\":" << (timeline ? timeline->maximumGap() : 0)
                    << ",\"stop_reason\":" << jsonString(stopReason) << ",\"error\":" << jsonString(failure)
                    << ",\"baseline\":" << stateJson(baseline)
                    << ",\"final_window_state\":" << stateJson(finalState) << ",\"frames\":[";
                for (size_t i = 0; i < records.size(); ++i)
                    out << (i ? "," : "") << records[i];
                out << "]}";
                return out.str();
            }
        };

        void captureOnWorker(Run& run) {
            Apartment apartment;
            DpiContext dpi;
            LARGE_INTEGER frequency{};
            winrt::check_bool(QueryPerformanceFrequency(&frequency) && frequency.QuadPart > 0);
            run.frequency = frequency.QuadPart;
            Handle process{OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, FALSE, run.binding.pid)};
            run.baseline = observe(run.binding, process.value, run.frequency);
            run.finalState = run.baseline;
            if (const auto error = windowFailure(run.binding, run.baseline, nullptr, run.options.allowUserForeground); !error.empty())
                throw std::runtime_error(error);
            if (!GraphicsCaptureSession::IsSupported()) throw std::runtime_error("wgc_not_supported");
            const auto hwnd = reinterpret_cast<HWND>(static_cast<uintptr_t>(run.binding.hwnd));
            auto interop = winrt::get_activation_factory<GraphicsCaptureItem, IGraphicsCaptureItemInterop>();
            keepCaptureModuleLoaded(interop.get());
            GraphicsCaptureItem item{nullptr};
            winrt::check_hresult(interop->CreateForWindow(hwnd, winrt::guid_of<GraphicsCaptureItem>(),
                winrt::put_abi(item)));
            const auto size = item.Size();
            const auto& bounds = run.baseline.frame;
            if (size.Width <= 0 || size.Height <= 0 ||
                size.Width != bounds.right - bounds.left || size.Height != bounds.bottom - bounds.top ||
                static_cast<int64_t>(size.Width) * size.Height > 33554432)
                throw std::runtime_error("initial_capture_size_mismatch_or_limit");
            const auto& client = run.baseline.client;
            const RECT crop{client.left - bounds.left, client.top - bounds.top,
                            client.right - bounds.left, client.bottom - bounds.top};
            if (crop.left < 0 || crop.top < 0 || crop.right > size.Width || crop.bottom > size.Height)
                throw std::runtime_error("client_crop_outside_capture");
            const UINT width = crop.right - crop.left, height = crop.bottom - crop.top;

            winrt::com_ptr<ID3D11Device> device;
            winrt::com_ptr<ID3D11DeviceContext> context;
            auto hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr,
                D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0, D3D11_SDK_VERSION,
                device.put(), nullptr, context.put());
            if (FAILED(hr)) {
                device = nullptr;
                context = nullptr;
                hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr,
                    D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0, D3D11_SDK_VERSION,
                    device.put(), nullptr, context.put());
            }
            winrt::check_hresult(hr);
            winrt::com_ptr<IInspectable> inspectable;
            winrt::check_hresult(CreateDirect3D11DeviceFromDXGIDevice(
                device.as<IDXGIDevice>().get(), inspectable.put()));
            auto captureDevice = inspectable.as<IDirect3DDevice>();
            auto factory = winrt::create_instance<IWICImagingFactory>(CLSID_WICImagingFactory);
            auto signal = std::make_shared<FrameSignal>();
            winrt::check_bool(signal->event.value != nullptr);
            CaptureResource<Direct3D11CaptureFramePool> pool{
                Direct3D11CaptureFramePool::CreateFreeThreaded(captureDevice,
                    DirectXPixelFormat::B8G8R8A8UIntNormalized, 3, size)};
            CaptureResource<GraphicsCaptureSession> session{pool.value.CreateCaptureSession(item)};
            if (auto cursor = session.value.try_as<IGraphicsCaptureSession2>())
                cursor.IsCursorCaptureEnabled(false);
            auto arrived = pool.value.FrameArrived(
                winrt::auto_revoke, [signal](auto const&, auto const&) {
                    ++signal->arrivals;
                    SetEvent(signal->event.value);
                });
            auto closed = item.Closed(winrt::auto_revoke, [signal](auto const&, auto const&) {
                signal->closed = true;
                SetEvent(signal->event.value);
            });
            run.request = qpcNow(run.frequency);
            run.deadline = run.request + static_cast<int64_t>(run.options.durationMs) * 10000;
            run.timeline = std::make_unique<FrameTimeline>(run.request, run.deadline, run.options);
            session.value.StartCapture();
            uint32_t drainAttempts = 0;
            while (true) {
                const auto before = observe(run.binding, process.value, run.frequency);
                run.finalState = before;
                run.arrivals = signal->arrivals;
                if (const auto error = windowFailure(run.binding, before, &run.baseline, run.options.allowUserForeground); !error.empty())
                    throw std::runtime_error(error);
                if (signal->closed) throw std::runtime_error("capture_item_closed");
                const bool durationElapsed = before.observedQpc100ns >= run.deadline;
                if (run.timeline->count() >= run.options.maxFrames) {
                    run.stopReason = "frame_cap_before_duration";
                    break;
                }
                if (run.attempts >= run.options.maxFrames * 4 + 64) {
                    run.stopReason = "attempt_limit_before_duration";
                    break;
                }
                if (durationElapsed && drainAttempts >= 3) {
                    run.stopReason = "duration_elapsed_drain_limit";
                    break;
                }
                CaptureResource<Direct3D11CaptureFrame> frame{pool.value.TryGetNextFrame()};
                if (!frame.value) {
                    if (durationElapsed) {
                        run.stopReason = "duration_elapsed";
                        break;
                    }
                    const auto remainingMs = (run.deadline - before.observedQpc100ns + 9999) / 10000;
                    const auto wait = WaitForSingleObject(signal->event.value,
                        static_cast<DWORD>(std::min<int64_t>(50, remainingMs)));
                    if (wait == WAIT_FAILED) throw std::runtime_error("frame_event_wait_failed");
                    continue;
                }
                if (durationElapsed) ++drainAttempts;
                ++run.attempts;
                int64_t frameTime = 0, observed = 0, initialObserved = 0, waitDeadline = 0;
                bool timestampAvailable = false;
                FrameAssessment assessment, initialAssessment;
                std::vector<WindowState> waitGuards;
                std::string waitOutcome = "not_requested";
                std::string error;
                std::string pngName;
                WindowState afterRead{}, beforeWrite{}, afterWrite{};
                try {
                    frameTime = frame.value.SystemRelativeTime().count();
                    timestampAvailable = true;
                    observed = qpcNow(run.frequency);
                    initialObserved = observed;
                    initialAssessment = run.timeline->assess(frameTime, observed);
                    assessment = initialAssessment;
                    error = assessment.error;
                    const FutureTimestampWait wait(frameTime, observed, run.deadline, initialAssessment);
                    if (wait.requested()) {
                        waitDeadline = wait.deadline();
                        waitOutcome = "waiting";
                        error.clear();
                        while (wait.shouldWait(observed)) {
                            if (waitGuards.size() >= FutureTimestampWaitGuardLimit) {
                                error = "future_timestamp_wait_guard_limit";
                                waitOutcome = "guard_limit";
                                break;
                            }
                            if (waitDeadline - observed >= 10000) Sleep(1);
                            else SwitchToThread();
                            const auto waiting = observe(run.binding, process.value, run.frequency);
                            waitGuards.push_back(waiting);
                            run.finalState = waiting;
                            observed = waiting.observedQpc100ns;
                            assessment = run.timeline->assess(frameTime, observed);
                            if (observed < initialObserved || waitGuards.size() > 1 &&
                                observed < waitGuards[waitGuards.size() - 2].observedQpc100ns) {
                                error = "future_timestamp_wait_clock_regressed";
                                waitOutcome = "clock_regressed";
                                break;
                            }
                            error = windowFailure(run.binding, waiting, &run.baseline, run.options.allowUserForeground);
                            if (!error.empty()) {
                                waitOutcome = "window_guard_failure";
                                break;
                            }
                            if (signal->closed) {
                                error = "capture_item_closed";
                                waitOutcome = "capture_item_closed";
                                break;
                            }
                        }
                        assessment = run.timeline->assess(frameTime, observed);
                        if (error.empty()) {
                            if (!wait.eligible(observed)) {
                                error = "future_timestamp_wait_budget_exceeded";
                                waitOutcome = "budget_exceeded";
                            } else {
                                error = assessment.error;
                                waitOutcome = error.empty() ? "eligible" : "timestamp_rejected";
                            }
                        }
                    }
                    if (error.empty()) {
                        const auto content = frame.value.ContentSize();
                        if (content.Width != size.Width || content.Height != size.Height)
                            error = "frame_content_size_changed";
                    }
                    if (error.empty()) {
                        auto bitmap = copyBitmap(device.get(), context.get(), factory.get(), frame.value, size, crop);
                        afterRead = observe(run.binding, process.value, run.frequency);
                        run.finalState = afterRead;
                        error = windowFailure(run.binding, afterRead, &run.baseline, run.options.allowUserForeground);
                        if (error.empty()) {
                            auto png = encodePng(factory.get(), bitmap.get(), width, height);
                            beforeWrite = observe(run.binding, process.value, run.frequency);
                            run.finalState = beforeWrite;
                            error = windowFailure(run.binding, beforeWrite, &run.baseline, run.options.allowUserForeground);
                            if (error.empty()) {
                                std::ostringstream name;
                                name << "frame_" << std::setw(6) << std::setfill('0') << run.attempts << ".png";
                                pngName = name.str();
                                writeFreshFile(run.directory / pngName, png.data(), png.size());
                                afterWrite = observe(run.binding, process.value, run.frequency);
                                run.finalState = afterWrite;
                                error = windowFailure(run.binding, afterWrite, &run.baseline, run.options.allowUserForeground);
                            }
                        }
                    }
                } catch (const winrt::hresult_error& problem) {
                    error = "frame_hresult: " + winrt::to_string(problem.message());
                } catch (const std::exception& problem) {
                    error = problem.what();
                }
                if (!error.empty()) {
                    try {
                        run.finalState = observe(run.binding, process.value, run.frequency);
                        error = guardedFrameFailure(run.binding, run.finalState, run.baseline, error,
                                                    run.options.allowUserForeground);
                    } catch (const winrt::hresult_error& problem) {
                        error = "rejected_frame_guard_hresult: " + winrt::to_string(problem.message());
                    } catch (const std::exception& problem) {
                        error = "rejected_frame_guard_failure: " + std::string(problem.what());
                    }
                }
                std::ostringstream receipt;
                receipt << "frame_" << std::setw(6) << std::setfill('0') << run.attempts << ".capture.json";
                std::ostringstream record;
                record << std::boolalpha << "{\"schema\":1,\"sequence\":" << run.attempts
                    << ",\"receipt\":" << jsonString(receipt.str())
                    << ",\"capture_valid\":" << error.empty()
                    << ",\"timestamp_available\":" << timestampAvailable
                    << ",\"request_qpc_100ns\":" << run.request << ",\"frame_qpc_100ns\":" << frameTime
                    << ",\"observed_qpc_100ns\":" << observed << ",\"frame_age_100ns\":" << assessment.age100ns
                    << ",\"initial_timestamp_assessment\":{\"observed_qpc_100ns\":" << initialObserved
                    << ",\"frame_age_100ns\":" << initialAssessment.age100ns
                    << ",\"delta_from_previous_or_request_100ns\":" << initialAssessment.delta100ns
                    << ",\"gap_exceeded\":" << initialAssessment.gapExceeded
                    << ",\"error\":" << jsonString(initialAssessment.error) << '}'
                    << ",\"future_timestamp_wait\":{\"requested\":" << (waitDeadline != 0)
                    << ",\"deadline_qpc_100ns\":" << waitDeadline
                    << ",\"elapsed_100ns\":" << (waitDeadline ? observed - initialObserved : 0)
                    << ",\"outcome\":" << jsonString(waitOutcome) << ",\"guards\":[";
                for (size_t index = 0; index < waitGuards.size(); ++index)
                    record << (index ? "," : "") << stateJson(waitGuards[index]);
                record << "]}"
                    << ",\"delta_from_previous_or_request_100ns\":" << assessment.delta100ns
                    << ",\"gap_exceeded\":" << (error.empty() && assessment.gapExceeded)
                    << ",\"png\":" << (pngName.empty() ? "null" : jsonString(pngName))
                    << ",\"width\":" << width << ",\"height\":" << height
                    << ",\"error\":" << jsonString(error) << ",\"before\":" << stateJson(before)
                    << ",\"after_readback\":" << stateJson(afterRead)
                    << ",\"before_png_write\":" << stateJson(beforeWrite)
                    << ",\"after_png_write\":" << stateJson(afterWrite)
                    << ",\"last_window_state\":" << stateJson(run.finalState) << '}';
                const auto json = record.str();
                try {
                    writeFreshFile(run.directory / receipt.str(),
                                   reinterpret_cast<const uint8_t*>(json.data()), json.size());
                } catch (const std::exception& problem) {
                    run.records.push_back("{\"sequence\":" + std::to_string(run.attempts) +
                        ",\"capture_valid\":false,\"attempt\":" + json +
                        ",\"receipt_write_error\":" + jsonString(problem.what()) + "}");
                    ++run.rejected;
                    throw;
                }
                run.records.push_back(json);
                if (error.empty()) run.timeline->accept(frameTime);
                else {
                    ++run.rejected;
                    if (error != "frame_not_after_request" && error != "frame_not_strictly_monotonic" &&
                        error != "frame_timestamp_in_future" && error != "frame_delivery_too_old" &&
                        error != "frame_after_planned_interval")
                        throw std::runtime_error(error);
                }
                if (error == "frame_after_planned_interval") {
                    run.stopReason = "duration_elapsed";
                    break;
                }
            }
            run.finalState = observe(run.binding, process.value, run.frequency);
            run.arrivals = signal->arrivals;
            if (const auto error = windowFailure(run.binding, run.finalState, &run.baseline, run.options.allowUserForeground); !error.empty())
                throw std::runtime_error(error);
        }
    }

    void writeFreshFile(const std::filesystem::path& path, const uint8_t* bytes, size_t count) {
        if (!count || count > std::numeric_limits<DWORD>::max())
            throw std::runtime_error("output_payload_size_invalid");
        Handle output{CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                                  FILE_ATTRIBUTE_NORMAL, nullptr)};
        if (output.value == INVALID_HANDLE_VALUE)
            throw std::runtime_error("fresh_output_file_creation_failed");
        DWORD written = 0;
        if (!WriteFile(output.value, bytes, static_cast<DWORD>(count), &written, nullptr) ||
            written != count)
            throw std::runtime_error("output_payload_write_incomplete");
    }

    BurstResult captureWindowBurstPng(const WindowBinding& binding, const CaptureOptions& options,
                                      const std::filesystem::path& outputDirectory) {
        Run run{binding, options, outputDirectory};
        std::thread worker([&] {
            try {
                if (!validOptions(options)) throw std::runtime_error("invalid_burst_options");
                captureOnWorker(run);
            } catch (const winrt::hresult_error& error) {
                run.failure = "wgc_hresult: " + winrt::to_string(error.message());
                run.stopReason = "capture_failure";
            } catch (const std::exception& error) {
                run.failure = error.what();
                run.stopReason = "capture_failure";
            }
            if (run.frequency) {
                try { run.ended = qpcNow(run.frequency); } catch (...) {}
            }
        });
        worker.join();
        const bool valid = run.failure.empty() && run.timeline && run.timeline->count() > 0;
        const bool complete = run.timeline &&
            run.timeline->complete(run.stopReason == "duration_elapsed", !run.failure.empty());
        return {valid, complete, run.manifest()};
    }
}
