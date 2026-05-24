using NetMQ;
using System;
using cAlgo.API;
using System.Diagnostics;
using NetMQ.Sockets;
using Newtonsoft.Json;
using cAlgo.API.Internals;

namespace cAlgo.Robots;

public class SystemAPI : IDisposable
{
    private readonly Logging _console_;
    private readonly PairSocket _socket_;
    private bool _disposed_;
    private Process _peer_;
    private volatile bool _peer_dead_;
    private static readonly TimeSpan _poll_interval_ = TimeSpan.FromMilliseconds(100);

    public SystemAPI(Robot robot, VerboseLevel console, string host = "localhost", int port = 5555)
    {
        _console_ = new Logging(robot, "API", console);
        _socket_ = new PairSocket();
        _socket_.Options.SendHighWatermark = 0;
        _socket_.Options.Linger = TimeSpan.Zero;
        _socket_.Connect($"tcp://{host}:{port}");
        _console_.Info($"ZMQ PAIR Socket connected to tcp://{host}:{port}");
    }

    public void SetPeer(Process peer)
    {
        _peer_ = peer;
        if (peer == null) return;
        System.Threading.Tasks.Task.Run(() =>
        {
            try { peer.WaitForExit(); }
            catch (Exception e) { _console_.Warning($"Peer watch failed: {e.Message}"); }
            OnPeerExited();
        });
    }

    private void OnPeerExited()
    {
        _peer_dead_ = true;
        _console_.Warning($"Python process exited (code {_peer_?.ExitCode}); receive/send loops will unblock");
    }

    public void Connect()
    {
        _console_.Info("ZMQ Ready for communication");
    }

    public void Disconnect()
    {
        if (_disposed_) return;
        try { _socket_.Close(); } catch (Exception e) { _console_.Warning($"Socket close: {e.Message}"); }
        _console_.Info("Disconnected");
    }

    public void Dispose()
    {
        if (_disposed_) return;
        _disposed_ = true;
        try { _socket_.Dispose(); } catch (Exception e) { _console_.Warning($"Socket dispose: {e.Message}"); }
    }

    private void SendUpdate(object payload)
    {
        if (_peer_dead_) throw new InvalidOperationException("Python process exited; cannot send");
        var json = JsonConvert.SerializeObject(payload);
        while (!_socket_.TrySendFrame(_poll_interval_, json))
        {
            if (_peer_dead_) throw new InvalidOperationException("Python process exited during send");
        }
    }

    public void SendUpdateComplete()
    {
        SendUpdate(new { UpdateID = (int)UpdateID.Complete });
    }

    public void SendUpdateAccount(IAccount account)
    {
        SendUpdate(new
        {
            UpdateID = (int)UpdateID.Account,
            AccountType = (int)account.AccountType,
            AssetType = account.Asset.Name,
            Balance = account.Balance,
            Equity = account.Equity,
            Credit = account.Credit,
            Leverage = account.PreciseLeverage,
            MarginUsed = account.Margin,
            MarginFree = account.FreeMargin,
            MarginLevel = account.MarginLevel,
            MarginStopLevel = account.StopOutLevel,
            MarginMode = (int)account.TotalMarginCalculationType
        });
    }

    public void SendUpdateSymbol(Symbol symbol)
    {
        SendUpdate(new
        {
            UpdateID = (int)UpdateID.Security,
            BaseAssetType = symbol.BaseAsset.Name,
            QuoteAssetType = symbol.QuoteAsset.Name,
            Digits = symbol.Digits,
            PointSize = symbol.TickSize,
            PipSize = symbol.PipSize,
            LotSize = symbol.LotSize,
            VolumeInUnitsMin = symbol.VolumeInUnitsMin,
            VolumeInUnitsMax = symbol.VolumeInUnitsMax,
            VolumeInUnitsStep = symbol.VolumeInUnitsStep,
            Commission = symbol.Commission,
            CommissionMode = (int)symbol.CommissionType,
            SwapLong = symbol.SwapLong,
            SwapShort = symbol.SwapShort,
            SwapMode = (int)symbol.SwapCalculationType,
            SwapExtraDay = symbol.Swap3DaysRollover != null ? (int)symbol.Swap3DaysRollover : 0
        });
    }

    public void SendUpdatePosition(UpdateID update_id, Position position)
    {
        SendUpdate(new
        {
            UpdateID = (int)update_id,
            PositionID = position.Id,
            PositionType = position.Comment,
            TradeType = (int)position.TradeType,
            EntryTimestamp = ((DateTimeOffset)position.EntryTime).ToUnixTimeMilliseconds(),
            EntryPrice = position.EntryPrice,
            StopLoss = position.StopLoss,
            TakeProfit = position.TakeProfit,
            Volume = position.VolumeInUnits,
            Quantity = position.Quantity,
            GrossPnL = position.GrossProfit,
            CommissionPnL = position.Commissions,
            SwapPnL = position.Swap,
            NetPnL = position.NetProfit,
            UsedMargin = position.Margin
        });
    }

    public void SendUpdateTrade(UpdateID update_id, HistoricalTrade trade)
    {
        SendUpdate(new
        {
            UpdateID = (int)update_id,
            PositionID = trade.PositionId,
            TradeID = trade.ClosingDealId,
            PositionType = trade.Comment,
            TradeType = (int)trade.TradeType,
            EntryTimestamp = ((DateTimeOffset)trade.EntryTime).ToUnixTimeMilliseconds(),
            ExitTimestamp = ((DateTimeOffset)trade.ClosingTime).ToUnixTimeMilliseconds(),
            EntryPrice = trade.EntryPrice,
            ExitPrice = trade.ClosingPrice,
            Volume = trade.VolumeInUnits,
            Quantity = trade.Quantity,
            GrossPnL = trade.GrossProfit,
            CommissionPnL = trade.Commissions,
            SwapPnL = trade.Swap,
            NetPnL = trade.NetProfit
        });
    }
    
    public void SendUpdateBarClosed(RobotAPI.xBar bar)
    {
        SendUpdate(new
        {
            UpdateID = (int)UpdateID.BarClosed,
            Timestamp = ((DateTimeOffset)bar.Timestamp).ToUnixTimeMilliseconds(),
            GapAsk = bar.GapTick.Ask, GapBid = bar.GapTick.Bid,
            GapTimestamp = ((DateTimeOffset)bar.GapTick.Timestamp).ToUnixTimeMilliseconds(),
            GapVolume = bar.GapTick.Volume,
            GapAskBaseConversion = bar.GapTick.AskBaseConversion, GapBidBaseConversion = bar.GapTick.BidBaseConversion,
            GapAskQuoteConversion = bar.GapTick.AskQuoteConversion, GapBidQuoteConversion = bar.GapTick.BidQuoteConversion,
            OpenAsk = bar.OpenTick.Ask, OpenBid = bar.OpenTick.Bid,
            OpenTimestamp = ((DateTimeOffset)bar.OpenTick.Timestamp).ToUnixTimeMilliseconds(),
            OpenVolume = bar.OpenTick.Volume,
            OpenAskBaseConversion = bar.OpenTick.AskBaseConversion, OpenBidBaseConversion = bar.OpenTick.BidBaseConversion,
            OpenAskQuoteConversion = bar.OpenTick.AskQuoteConversion, OpenBidQuoteConversion = bar.OpenTick.BidQuoteConversion,
            HighAsk = bar.HighTick.Ask, HighBid = bar.HighTick.Bid,
            HighTimestamp = ((DateTimeOffset)bar.HighTick.Timestamp).ToUnixTimeMilliseconds(),
            HighVolume = bar.HighTick.Volume,
            HighAskBaseConversion = bar.HighTick.AskBaseConversion, HighBidBaseConversion = bar.HighTick.BidBaseConversion,
            HighAskQuoteConversion = bar.HighTick.AskQuoteConversion, HighBidQuoteConversion = bar.HighTick.BidQuoteConversion,
            LowAsk = bar.LowTick.Ask, LowBid = bar.LowTick.Bid,
            LowTimestamp = ((DateTimeOffset)bar.LowTick.Timestamp).ToUnixTimeMilliseconds(),
            LowVolume = bar.LowTick.Volume,
            LowAskBaseConversion = bar.LowTick.AskBaseConversion, LowBidBaseConversion = bar.LowTick.BidBaseConversion,
            LowAskQuoteConversion = bar.LowTick.AskQuoteConversion, LowBidQuoteConversion = bar.LowTick.BidQuoteConversion,
            CloseAsk = bar.CloseTick.Ask, CloseBid = bar.CloseTick.Bid,
            CloseTimestamp = ((DateTimeOffset)bar.CloseTick.Timestamp).ToUnixTimeMilliseconds(),
            CloseVolume = bar.CloseTick.Volume,
            CloseAskBaseConversion = bar.CloseTick.AskBaseConversion, CloseBidBaseConversion = bar.CloseTick.BidBaseConversion,
            CloseAskQuoteConversion = bar.CloseTick.AskQuoteConversion, CloseBidQuoteConversion = bar.CloseTick.BidQuoteConversion,
            Volume = bar.Volume
        });
    }

    public void SendUpdateTarget(UpdateID update_id, RobotAPI.xTick tick)
    {
        SendUpdate(new
        {
            UpdateID = (int)update_id,
            Timestamp = ((DateTimeOffset)tick.Timestamp).ToUnixTimeMilliseconds(),
            Ask = tick.Ask,
            Bid = tick.Bid,
            AskBaseConversion = tick.AskBaseConversion,
            BidBaseConversion = tick.BidBaseConversion,
            AskQuoteConversion = tick.AskQuoteConversion,
            BidQuoteConversion = tick.BidQuoteConversion,
            Volume = tick.Volume
        });
    }

    public void SendUpdateShutdown()
    {
        SendUpdate(new { UpdateID = (int)UpdateID.Shutdown });
    }

    public string ReceiveAction()
    {
        while (true)
        {
            if (_peer_dead_) throw new InvalidOperationException("Python process exited; cannot receive");
            if (_socket_.TryReceiveFrameString(_poll_interval_, out var json)) return json;
        }
    }
}