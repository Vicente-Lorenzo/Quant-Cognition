#pragma warning disable CA1416

using System;
using System.IO.MemoryMappedFiles;
using System.Threading;
using cAlgo.API;

namespace Connector;

public class PeerExitException : Exception
{
    public PeerExitException(string message) : base(message) { }
}

public class TransportAPI : IDisposable
{
    private readonly Robot _robot_;
    private readonly Logging _console_;
    private bool _disposed_;
    private volatile bool _peer_dead_;

    private readonly MemoryMappedFile _update_mmf_;
    private readonly MemoryMappedFile _action_mmf_;
    private readonly MemoryMappedViewAccessor _update_view_;
    private readonly MemoryMappedViewAccessor _action_view_;
    private readonly EventWaitHandle _ur_;
    private readonly EventWaitHandle _uc_;
    private readonly EventWaitHandle _ar_;
    private readonly EventWaitHandle _ac_;

    private const int BUF_SIZE = 4096;
    private const int POLL_MS = 500;

    public TransportAPI(Robot robot, VerboseLevel console, string iid)
    {
        _robot_ = robot;
        _console_ = new Logging(robot, "Transport", console);
        var prefix = $"cAlgo_{iid}";
        _update_mmf_ = MemoryMappedFile.CreateOrOpen($"{prefix}_update", BUF_SIZE);
        _action_mmf_ = MemoryMappedFile.CreateOrOpen($"{prefix}_action", BUF_SIZE);
        _update_view_ = _update_mmf_.CreateViewAccessor();
        _action_view_ = _action_mmf_.CreateViewAccessor();
        _ur_ = new EventWaitHandle(false, EventResetMode.AutoReset, $"{prefix}_ur");
        _uc_ = new EventWaitHandle(false, EventResetMode.AutoReset, $"{prefix}_uc");
        _ar_ = new EventWaitHandle(false, EventResetMode.AutoReset, $"{prefix}_ar");
        _ac_ = new EventWaitHandle(false, EventResetMode.AutoReset, $"{prefix}_ac");
        _console_.Debug($"Connect Operation: Created Shared Memory (iid {iid})");
    }

    public bool PeerDead => _peer_dead_;

    public void Watchdog(System.Diagnostics.Process peer)
    {
        if (peer == null) return;
        System.Threading.Tasks.Task.Run(() =>
        {
            try
            {
                peer.WaitForExit();
                int? exitCode = null;
                try { exitCode = peer.ExitCode; } catch (Exception) { }
                _peer_dead_ = true;
                _console_.Warning($"Watchdog Operation: Python Process Exited (code {exitCode?.ToString() ?? "N/A"}) · Transport Will Unblock");
                _robot_.Stop();
            }
            catch (Exception e)
            {
                _console_.Warning($"Watchdog Operation: Failed · {e.Message}");
            }
        });
    }

    private void WriteBuffer(byte[] data)
    {
        _update_view_.Write(0, (uint)data.Length);
        _update_view_.WriteArray(4, data, 0, data.Length);
    }

    private byte[] ReadBuffer()
    {
        uint size = _action_view_.ReadUInt32(0);
        byte[] data = new byte[size];
        _action_view_.ReadArray(4, data, 0, (int)size);
        return data;
    }

    private void WaitFor(EventWaitHandle handle)
    {
        while (true)
        {
            if (_peer_dead_) throw new PeerExitException("Python process exited");
            if (handle.WaitOne(POLL_MS)) return;
        }
    }

    public void Send(byte[] data)
    {
        if (_peer_dead_) throw new PeerExitException("Python process exited");
        WriteBuffer(data);
        _ur_.Set();
        WaitFor(_uc_);
    }

    public byte[] Receive()
    {
        WaitFor(_ar_);
        byte[] data = ReadBuffer();
        _ac_.Set();
        return data;
    }

    public void Dispose()
    {
        if (_disposed_) return;
        _disposed_ = true;
        _update_view_?.Dispose();
        _action_view_?.Dispose();
        _update_mmf_?.Dispose();
        _action_mmf_?.Dispose();
        _ur_?.Dispose();
        _uc_?.Dispose();
        _ar_?.Dispose();
        _ac_?.Dispose();
        _console_.Debug("Disconnect Operation: Disposed Transport");
    }
}
