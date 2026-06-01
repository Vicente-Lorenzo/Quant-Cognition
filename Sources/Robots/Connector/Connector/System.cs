using System;
using System.IO;
using System.Text;
using cAlgo.API;
using cAlgo.API.Internals;

namespace Connector;

public class SystemAPI : IDisposable
{
    private readonly TransportAPI _transport_;

    public SystemAPI(Robot robot, VerboseLevel console, string iid)
    {
        _transport_ = new TransportAPI(robot, console, iid);
    }

    public bool PeerDead => _transport_.PeerDead;

    public void Watchdog(System.Diagnostics.Process peer) => _transport_.Watchdog(peer);

    private void Send(byte[] data) => _transport_.Send(data);

    public byte[] Receive() => _transport_.Receive();

    public void Dispose() => _transport_.Dispose();

    private static void WriteString(MemoryStream ms, string value)
    {
        if (value == null)
        {
            ms.Write(BitConverter.GetBytes((ushort)0), 0, 2);
            return;
        }
        byte[] encoded = Encoding.UTF8.GetBytes(value);
        ms.Write(BitConverter.GetBytes((ushort)encoded.Length), 0, 2);
        ms.Write(encoded, 0, encoded.Length);
    }

    private static double NanIfNull(double? value)
    {
        return value ?? double.NaN;
    }

    private static PositionTypeID ParsePositionType(string comment)
    {
        if (comment == null) return PositionTypeID.Normal;
        if (Enum.TryParse<PositionTypeID>(comment, out var result)) return result;
        return PositionTypeID.Normal;
    }

    private static void WriteAccount(MemoryStream ms, IAccount account)
    {
        WriteString(ms, account.Number.ToString());
        WriteString(ms, account.IsLive ? "Live" : "Demo");
        ms.WriteByte((byte)account.AccountType);
        WriteString(ms, account.Asset.Name);
        ms.Write(BitConverter.GetBytes(account.Balance), 0, 8);
        ms.Write(BitConverter.GetBytes(account.Equity), 0, 8);
        ms.Write(BitConverter.GetBytes(account.Credit), 0, 8);
        ms.Write(BitConverter.GetBytes(account.PreciseLeverage), 0, 8);
        ms.Write(BitConverter.GetBytes(account.Margin), 0, 8);
        ms.Write(BitConverter.GetBytes(account.FreeMargin), 0, 8);
        ms.Write(BitConverter.GetBytes(account.MarginLevel ?? 0.0), 0, 8);
        ms.Write(BitConverter.GetBytes(account.StopOutLevel), 0, 8);
        ms.WriteByte((byte)account.TotalMarginCalculationType);
    }

    private static void WriteSymbol(MemoryStream ms, Symbol symbol)
    {
        WriteString(ms, symbol.BaseAsset.Name);
        WriteString(ms, symbol.QuoteAsset.Name);
        ms.Write(BitConverter.GetBytes(symbol.Digits), 0, 4);
        ms.Write(BitConverter.GetBytes(symbol.TickSize), 0, 8);
        ms.Write(BitConverter.GetBytes(symbol.PipSize), 0, 8);
        ms.Write(BitConverter.GetBytes(symbol.LotSize), 0, 8);
        ms.Write(BitConverter.GetBytes(symbol.VolumeInUnitsMin), 0, 8);
        ms.Write(BitConverter.GetBytes(symbol.VolumeInUnitsMax), 0, 8);
        ms.Write(BitConverter.GetBytes(symbol.VolumeInUnitsStep), 0, 8);
        ms.Write(BitConverter.GetBytes(symbol.Commission), 0, 8);
        ms.WriteByte((byte)symbol.CommissionType);
        ms.Write(BitConverter.GetBytes(symbol.SwapLong), 0, 8);
        ms.Write(BitConverter.GetBytes(symbol.SwapShort), 0, 8);
        ms.WriteByte((byte)symbol.SwapCalculationType);
        ms.Write(BitConverter.GetBytes(symbol.Swap3DaysRollover != null ? (int)symbol.Swap3DaysRollover : 0), 0, 4);
    }

    private static void WriteTick(MemoryStream ms, RobotAPI.xTick tick)
    {
        ms.Write(BitConverter.GetBytes(((DateTimeOffset)tick.Timestamp).ToUnixTimeMilliseconds()), 0, 8);
        ms.Write(BitConverter.GetBytes(tick.Ask), 0, 8);
        ms.Write(BitConverter.GetBytes(tick.Bid), 0, 8);
        ms.Write(BitConverter.GetBytes(tick.AskBaseConversion), 0, 8);
        ms.Write(BitConverter.GetBytes(tick.BidBaseConversion), 0, 8);
        ms.Write(BitConverter.GetBytes(tick.AskQuoteConversion), 0, 8);
        ms.Write(BitConverter.GetBytes(tick.BidQuoteConversion), 0, 8);
        ms.Write(BitConverter.GetBytes(tick.Volume), 0, 8);
    }

    private static void WriteBar(MemoryStream ms, RobotAPI.xBar bar)
    {
        ms.Write(BitConverter.GetBytes(((DateTimeOffset)bar.Timestamp).ToUnixTimeMilliseconds()), 0, 8);
        WriteTick(ms, bar.GapTick);
        WriteTick(ms, bar.OpenTick);
        WriteTick(ms, bar.HighTick);
        WriteTick(ms, bar.LowTick);
        WriteTick(ms, bar.CloseTick);
        ms.Write(BitConverter.GetBytes(bar.Volume), 0, 8);
    }

    private static void WriteOrder(MemoryStream ms, PendingOrder order)
    {
        ms.Write(BitConverter.GetBytes(order.Id), 0, 4);
        ms.WriteByte((byte)order.OrderType);
        ms.WriteByte((byte)order.TradeType);
        ms.Write(BitConverter.GetBytes(order.VolumeInUnits), 0, 8);
        ms.Write(BitConverter.GetBytes(order.TargetPrice), 0, 8);
        ms.Write(BitConverter.GetBytes(NanIfNull(order.StopLoss)), 0, 8);
        ms.Write(BitConverter.GetBytes(NanIfNull(order.TakeProfit)), 0, 8);
        long expMs = order.ExpirationTime.HasValue ? ((DateTimeOffset)order.ExpirationTime.Value).ToUnixTimeMilliseconds() : 0L;
        ms.Write(BitConverter.GetBytes(expMs), 0, 8);
        WriteString(ms, order.Label);
    }

    private static void WritePosition(MemoryStream ms, Position position)
    {
        ms.Write(BitConverter.GetBytes(position.Id), 0, 4);
        ms.WriteByte((byte)ParsePositionType(position.Comment));
        ms.WriteByte((byte)position.TradeType);
        ms.Write(BitConverter.GetBytes(((DateTimeOffset)position.EntryTime).ToUnixTimeMilliseconds()), 0, 8);
        ms.Write(BitConverter.GetBytes(position.EntryPrice), 0, 8);
        ms.Write(BitConverter.GetBytes(position.VolumeInUnits), 0, 8);
        ms.Write(BitConverter.GetBytes(position.Quantity), 0, 8);
        ms.Write(BitConverter.GetBytes(position.GrossProfit), 0, 8);
        ms.Write(BitConverter.GetBytes(position.Commissions), 0, 8);
        ms.Write(BitConverter.GetBytes(position.Swap), 0, 8);
        ms.Write(BitConverter.GetBytes(position.NetProfit), 0, 8);
        ms.Write(BitConverter.GetBytes(position.Margin), 0, 8);
        ms.Write(BitConverter.GetBytes(NanIfNull(position.StopLoss)), 0, 8);
        ms.Write(BitConverter.GetBytes(NanIfNull(position.TakeProfit)), 0, 8);
        WriteString(ms, position.Label);
    }

    private static void WriteTrade(MemoryStream ms, HistoricalTrade trade)
    {
        ms.Write(BitConverter.GetBytes(trade.ClosingDealId), 0, 4);
        ms.Write(BitConverter.GetBytes(trade.PositionId), 0, 4);
        ms.WriteByte((byte)ParsePositionType(trade.Comment));
        ms.WriteByte((byte)trade.TradeType);
        ms.Write(BitConverter.GetBytes(((DateTimeOffset)trade.EntryTime).ToUnixTimeMilliseconds()), 0, 8);
        ms.Write(BitConverter.GetBytes(((DateTimeOffset)trade.ClosingTime).ToUnixTimeMilliseconds()), 0, 8);
        ms.Write(BitConverter.GetBytes(trade.EntryPrice), 0, 8);
        ms.Write(BitConverter.GetBytes(trade.ClosingPrice), 0, 8);
        ms.Write(BitConverter.GetBytes(trade.VolumeInUnits), 0, 8);
        ms.Write(BitConverter.GetBytes(trade.Quantity), 0, 8);
        ms.Write(BitConverter.GetBytes(trade.GrossProfit), 0, 8);
        ms.Write(BitConverter.GetBytes(trade.Commissions), 0, 8);
        ms.Write(BitConverter.GetBytes(trade.Swap), 0, 8);
        ms.Write(BitConverter.GetBytes(trade.NetProfit), 0, 8);
        WriteString(ms, trade.Label);
    }

    public void SendUpdateInitialization(int pid)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)UpdateID.Initialization);
        ms.Write(BitConverter.GetBytes(pid), 0, 4);
        Send(ms.ToArray());
    }

    public void SendUpdateComplete()
    {
        Send(new[] { (byte)UpdateID.Complete });
    }

    public void SendUpdateShutdown()
    {
        Send(new[] { (byte)UpdateID.Shutdown });
    }

    public void SendUpdateAccount(IAccount account)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)UpdateID.Account);
        WriteAccount(ms, account);
        Send(ms.ToArray());
    }

    public void SendUpdateSymbol(Symbol symbol)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)UpdateID.Security);
        WriteSymbol(ms, symbol);
        Send(ms.ToArray());
    }

    public void SendUpdateTick(UpdateID update_id, RobotAPI.xTick tick)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)update_id);
        WriteTick(ms, tick);
        Send(ms.ToArray());
    }

    public void SendUpdateBar(UpdateID update_id, RobotAPI.xBar bar)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)update_id);
        WriteBar(ms, bar);
        Send(ms.ToArray());
    }

    public void SendUpdateOrder(UpdateID update_id, RobotAPI.xBar bar, PendingOrder order)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)update_id);
        WriteBar(ms, bar);
        WriteOrder(ms, order);
        Send(ms.ToArray());
    }

    public void SendUpdatePosition(UpdateID update_id, RobotAPI.xBar bar, Position position)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)update_id);
        WriteBar(ms, bar);
        WritePosition(ms, position);
        Send(ms.ToArray());
    }

    public void SendUpdateTrade(UpdateID update_id, RobotAPI.xBar bar, HistoricalTrade trade)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)update_id);
        WriteBar(ms, bar);
        WriteTrade(ms, trade);
        Send(ms.ToArray());
    }

    public void SendUpdatePositionTrade(UpdateID update_id, RobotAPI.xBar bar, Position position, HistoricalTrade trade)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)update_id);
        WriteBar(ms, bar);
        WritePosition(ms, position);
        WriteTrade(ms, trade);
        Send(ms.ToArray());
    }
}