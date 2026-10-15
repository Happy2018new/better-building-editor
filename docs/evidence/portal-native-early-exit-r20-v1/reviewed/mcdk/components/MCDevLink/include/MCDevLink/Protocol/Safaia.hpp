#pragma once

#include "MCDevLink/Endpoint.hpp"
#include "MCDevLink/Event.hpp"

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

namespace MCDevLink {

class Runtime;

namespace Protocol {

namespace SafaiaMessage {
inline constexpr std::int32_t connect = 1;
inline constexpr std::int32_t heartbeat = 2;
inline constexpr std::int32_t config = 3;
inline constexpr std::int32_t message = 4;
inline constexpr std::int32_t leave = 32;
inline constexpr std::int32_t connectSuccess = 48;
inline constexpr std::int32_t connectBlocked = 49;
} // namespace SafaiaMessage

struct SafaiaOptions {
    Endpoint bindEndpoint{"127.0.0.1", 0};
    std::string advertiseAddress{"127.0.0.1"};
    // Empty selects every local IPv4 address. Explicit values disable auto-discovery.
    std::vector<std::string> discoveryTargets;
    std::uint16_t discoveryPortFirst = 26613;
    std::uint16_t discoveryPortCount = 10;
    // Windows only. Zero sends to the full discovery port range.
    std::uint32_t targetProcessId = 0;
    std::chrono::milliseconds discoveryInterval{500};
    std::chrono::milliseconds handshakeTimeout{5000};
    std::chrono::milliseconds idleTimeout{10000};
    std::size_t maxFramePayload = 16U * 1024U * 1024U;
    std::size_t maxPendingWriteBytes = 32U * 1024U * 1024U;
    bool discoveryEnabled = true;
    bool pauseDiscoveryWhileConnected = true;
};

class SafaiaService {
public:
    using LogHandler = std::function<void(const LogEvent&)>;
    using SessionHandler = std::function<void(const SessionEvent&)>;
    using FrameHandler = std::function<void(const ProtocolFrameEvent&)>;
    using DiagnosticHandler = std::function<void(const DiagnosticEvent&)>;

    explicit SafaiaService(Runtime& runtime, SafaiaOptions options = {});
    ~SafaiaService();

    SafaiaService(const SafaiaService&) = delete;
    SafaiaService& operator=(const SafaiaService&) = delete;
    SafaiaService(SafaiaService&&) noexcept;
    SafaiaService& operator=(SafaiaService&&) noexcept;

    // Performs only local socket setup. Network progress and callbacks require Runtime::poll().
    // A service instance is single-use; construct a new one after stop().
    [[nodiscard]] std::error_code start();
    void stop();

    [[nodiscard]] bool isRunning() const noexcept;
    [[nodiscard]] Endpoint localEndpoint() const;
    [[nodiscard]] std::size_t sessionCount() const noexcept;

    // Set handlers before start or from the Runtime::poll() thread.
    void setLogHandler(LogHandler handler);
    void setSessionHandler(SessionHandler handler);
    void setFrameHandler(FrameHandler handler);
    void setDiagnosticHandler(DiagnosticHandler handler);

    // Queues a protocol frame. Call from the Runtime::poll() thread.
    [[nodiscard]] bool send(SessionId sessionId, std::int32_t protocolId,
                            std::span<const std::uint8_t> payload);
    [[nodiscard]] bool send(SessionId sessionId, std::int32_t protocolId,
                            std::string_view payload);

private:
    class Impl;
    std::shared_ptr<Impl> impl_;
};

} // namespace Protocol
} // namespace MCDevLink
