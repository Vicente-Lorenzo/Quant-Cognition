using System;
using System.IO;
using System.Diagnostics;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using cAlgo.API;

namespace Connector;

public class RobotAPI : IDisposable
{
    private class LastPositionData
    {
        public double LastVolume { get; set; }
        public double? LastStopLoss { get; set; }
        public double? LastTakeProfit { get; set; }
    }

    private class LastOrderData
    {
        public double LastVolume { get; set; }
        public double LastTargetPrice { get; set; }
        public double? LastStopLoss { get; set; }
        public double? LastTakeProfit { get; set; }
    }

    public class xTick
    {
        public DateTime Timestamp { get; init; }
        public double Ask { get; init; }
        public double Bid { get; init; }
        public double AskBaseConversion { get; init; }
        public double BidBaseConversion { get; init; }
        public double AskQuoteConversion { get; init; }
        public double BidQuoteConversion { get; init; }
        public double Volume { get; init; }
    }

    public class xBar
    {
        public DateTime Timestamp { get; set; }
        public xTick GapTick { get; set; }
        public xTick OpenTick { get; set; }
        public xTick HighTick { get; set; }
        public xTick LowTick { get; set; }
        public xTick CloseTick { get; set; }
        public double Volume { get; set; }
    }

    private readonly Robot _robot_;
    private readonly Logging _log_;
    private readonly SystemAPI _system_;

    private readonly VerboseLevel _console_;
    private readonly VerboseLevel _file_;
    private readonly StrategyType _strategy_;

    private readonly EnvironmentType _environment_;
    private readonly DatabaseType _database_;
    private readonly int _verification_;
    private readonly AccuracyMode _accuracy_;
    private bool _persist_market_ = true;
    private readonly TickStreamMode _tick_stream_;
    private readonly BarStreamMode _bar_stream_;
    private readonly OrderStreamMode _order_stream_;
    private readonly PositionStreamMode _position_stream_;
    private readonly TradeStreamMode _trade_stream_;
    private readonly DelayMode _tick_delay_mode_;
    private readonly int _tick_delay_count_;
    private readonly DelayMode _bar_delay_mode_;
    private readonly int _bar_delay_count_;
    private readonly DelayMode _order_delay_mode_;
    private readonly int _order_delay_count_;
    private readonly DelayMode _position_delay_mode_;
    private readonly int _position_delay_count_;
    private readonly DelayMode _trade_delay_mode_;
    private readonly int _trade_delay_count_;
    private DelayMode _tick_delay_;
    private DelayMode _bar_delay_;
    private DelayMode _order_delay_;
    private DelayMode _position_delay_;
    private DelayMode _trade_delay_;
    private readonly Queue<byte[]> _tick_queue_ = new Queue<byte[]>();
    private readonly Queue<byte[]> _bar_queue_ = new Queue<byte[]>();
    private readonly Queue<byte[]> _order_queue_ = new Queue<byte[]>();
    private readonly Queue<byte[]> _position_queue_ = new Queue<byte[]>();
    private readonly Queue<byte[]> _trade_queue_ = new Queue<byte[]>();
    private Stream _streams_ = Stream.Tick | Stream.BarOpened | Stream.BarClosed | Stream.Order | Stream.Position | Stream.Trade;
    private readonly BufferingMode _universe_buffering_;
    private readonly int _universe_batch_;
    private readonly double _universe_interval_;
    private readonly int _universe_workers_;
    private readonly int _universe_maxsize_;
    private readonly BufferingMode _market_buffering_;
    private readonly int _market_batch_;
    private readonly double _market_interval_;
    private readonly int _market_workers_;
    private readonly int _market_maxsize_;
    private readonly BufferingMode _portfolio_buffering_;
    private readonly int _portfolio_batch_;
    private readonly double _portfolio_interval_;
    private readonly int _portfolio_workers_;
    private readonly int _portfolio_maxsize_;
    private readonly bool _benchmark_;
    private readonly string _benchmark_tickers_;
    private readonly bool _report_;
    private readonly bool _export_;
    private readonly bool _plot_;
    private readonly bool _profile_;
    private readonly SystemMode _system_mode_;

    private readonly Dictionary<int, LastPositionData> _positions_;
    private readonly Dictionary<int, LastOrderData> _orders_;

    private double? _ask_above_target_;
    private double? _ask_below_target_;
    private double? _bid_above_target_;
    private double? _bid_below_target_;

    private readonly Func<double> _ask_base_conversion_;
    private readonly Func<double> _bid_base_conversion_;
    private readonly Func<double> _ask_quote_conversion_;
    private readonly Func<double> _bid_quote_conversion_;

    private readonly xBar _bar_;

    private readonly List<xBar> _verification_buffer_;
    private int _observed_bars_;
    private int _degraded_bars_;
    private bool _verified_;
    private bool _primed_;

    private long _ticks_sent_;
    private long _bars_sent_;
    private long _orders_sent_;
    private long _positions_sent_;
    private long _trades_sent_;
    private long _actions_received_;

    public RobotAPI(Robot algo, VerboseLevel console, VerboseLevel file, StrategyType strategy,
                    EnvironmentType environment, DatabaseType database, int verification, AccuracyMode accuracy,
                    TickStreamMode tick_stream, BarStreamMode bar_stream, OrderStreamMode order_stream,
                    PositionStreamMode position_stream, TradeStreamMode trade_stream,
                    DelayMode tick_delay_mode, int tick_delay_count, DelayMode bar_delay_mode, int bar_delay_count,
                    DelayMode order_delay_mode, int order_delay_count, DelayMode position_delay_mode, int position_delay_count,
                    DelayMode trade_delay_mode, int trade_delay_count,
                    BufferingMode universe_buffering, int universe_batch, double universe_interval, int universe_workers, int universe_maxsize,
                    BufferingMode market_buffering, int market_batch, double market_interval, int market_workers, int market_maxsize,
                    BufferingMode portfolio_buffering, int portfolio_batch, double portfolio_interval, int portfolio_workers, int portfolio_maxsize,
                    bool benchmark, string benchmark_tickers, bool report, bool export, bool plot, bool profile)
    {
        _robot_ = algo;
        _console_ = console;
        _file_ = file;
        _strategy_ = strategy;

        _log_ = new Logging(_robot_, "Strategy", console);
        _log_.Info("Start Operation: Starting");

        _system_mode_ = ResolveSystemMode(_robot_.RunningMode);
        _environment_ = environment;
        _database_ = ResolveDatabase(database);
        _verification_ = verification;
        _accuracy_ = accuracy;
        _tick_stream_ = tick_stream;
        _bar_stream_ = bar_stream;
        _order_stream_ = order_stream;
        _position_stream_ = position_stream;
        _trade_stream_ = trade_stream;
        _tick_delay_mode_ = tick_delay_mode;
        _tick_delay_count_ = tick_delay_count;
        _bar_delay_mode_ = bar_delay_mode;
        _bar_delay_count_ = bar_delay_count;
        _order_delay_mode_ = order_delay_mode;
        _order_delay_count_ = order_delay_count;
        _position_delay_mode_ = position_delay_mode;
        _position_delay_count_ = position_delay_count;
        _trade_delay_mode_ = trade_delay_mode;
        _trade_delay_count_ = trade_delay_count;
        _universe_buffering_ = universe_buffering;
        _universe_batch_ = universe_batch;
        _universe_interval_ = universe_interval;
        _universe_workers_ = universe_workers;
        _universe_maxsize_ = universe_maxsize;
        _market_buffering_ = market_buffering;
        _market_batch_ = market_batch;
        _market_interval_ = market_interval;
        _market_workers_ = market_workers;
        _market_maxsize_ = market_maxsize;
        _portfolio_buffering_ = portfolio_buffering;
        _portfolio_batch_ = portfolio_batch;
        _portfolio_interval_ = portfolio_interval;
        _portfolio_workers_ = portfolio_workers;
        _portfolio_maxsize_ = portfolio_maxsize;
        _benchmark_ = benchmark;
        _benchmark_tickers_ = benchmark_tickers;
        _report_ = report;
        _export_ = export;
        _plot_ = plot;
        _profile_ = profile;

        _log_.Debug($"Streams: Tick {_tick_stream_} · Bar {_bar_stream_} · Order {_order_stream_} · Position {_position_stream_} · Trade {_trade_stream_}");

        var base_conversions = FindConversions(_robot_.Symbol.BaseAsset, _robot_.Account.Asset);
        _ask_base_conversion_ = base_conversions.Ask;
        _bid_base_conversion_ = base_conversions.Bid;
        var quote_conversions = FindConversions(_robot_.Symbol.QuoteAsset, _robot_.Account.Asset);
        _ask_quote_conversion_ = quote_conversions.Ask;
        _bid_quote_conversion_ = quote_conversions.Bid;
        var tick = CurrentTick();
        _bar_ = new xBar
        {
            Timestamp = tick.Timestamp,
            GapTick = tick,
            OpenTick = tick,
            HighTick = tick,
            LowTick = tick,
            CloseTick = tick,
            Volume = 0.0
        };
        _positions_ = new Dictionary<int, LastPositionData>();
        _orders_ = new Dictionary<int, LastOrderData>();
        _verification_buffer_ = new List<xBar>();

        _robot_.Positions.Opened += OnPositionOpened;
        _robot_.Positions.Modified += OnPositionModified;
        _robot_.Positions.Closed += OnPositionClosed;
        _robot_.PendingOrders.Created += OnOrderCreated;
        _robot_.PendingOrders.Modified += OnOrderModified;
        _robot_.PendingOrders.Cancelled += OnOrderCancelled;
        _robot_.PendingOrders.Filled += OnOrderFilled;
        _robot_.Bars.BarClosed += OnBarClosed;
        _robot_.Bars.BarOpened += OnBarOpened;
        _robot_.Symbol.Tick += OnTick;

        _system_ = new SystemAPI(_robot_, console, _robot_.InstanceId);

        if (_system_mode_ == SystemMode.Live)
        {
            _verified_ = true;
            Activate();
        }
        else
        {
            _log_.Info($"Activation Operation: Verifying Accuracy ({_verification_} Bars)");
        }
    }

    public void Dispose()
    {
        _system_?.Dispose();
    }

    private bool EmitTickAll => _tick_stream_ == TickStreamMode.Auto ? (_streams_ & Stream.Tick) != 0 : _tick_stream_ == TickStreamMode.All;

    private bool EmitBarOpened => _bar_stream_ == BarStreamMode.Auto ? (_streams_ & Stream.BarOpened) != 0 : _bar_stream_ == BarStreamMode.All;

    private bool EmitBarClosed => _bar_stream_ == BarStreamMode.Auto ? (_streams_ & Stream.BarClosed) != 0 : _bar_stream_ == BarStreamMode.All;

    private bool EmitOrder => _order_stream_ == OrderStreamMode.Auto ? (_streams_ & Stream.Order) != 0 : _order_stream_ == OrderStreamMode.All;

    private bool EmitPosition => _position_stream_ == PositionStreamMode.Auto ? (_streams_ & Stream.Position) != 0 : _position_stream_ == PositionStreamMode.All;

    private bool EmitTrade => _trade_stream_ == TradeStreamMode.Auto ? (_streams_ & Stream.Trade) != 0 : _trade_stream_ == TradeStreamMode.All;

    private static SystemMode ResolveSystemMode(RunningMode mode)
    {
        switch (mode)
        {
            case RunningMode.RealTime: return SystemMode.Live;
            case RunningMode.VisualBacktesting: return SystemMode.Simulation;
            case RunningMode.SilentBacktesting: return SystemMode.Simulation;
            case RunningMode.Optimization: return SystemMode.Testing;
            default: throw new ArgumentOutOfRangeException($"Unsupported RunningMode: {mode}");
        }
    }

    private static DatabaseType ResolveDatabase(DatabaseType chosen)
    {
        if (chosen != DatabaseType.Auto) return chosen;
        return DatabaseType.Quant;
    }

    private DelayMode Resolve(DelayMode mode)
    {
        bool isDownload = _strategy_ == StrategyType.Download;
        return mode == DelayMode.Auto ? (isDownload ? DelayMode.Full : DelayMode.Off) : mode;
    }

    private void ResolveDelays()
    {
        _tick_delay_ = Resolve(_tick_delay_mode_);
        _bar_delay_ = Resolve(_bar_delay_mode_);
        _order_delay_ = Resolve(_order_delay_mode_);
        _position_delay_ = Resolve(_position_delay_mode_);
        _trade_delay_ = Resolve(_trade_delay_mode_);
        _log_.Debug($"Delay: Tick {_tick_delay_}/{_tick_delay_count_} · Bar {_bar_delay_}/{_bar_delay_count_} · Order {_order_delay_}/{_order_delay_count_} · Position {_position_delay_}/{_position_delay_count_} · Trade {_trade_delay_}/{_trade_delay_count_}");
    }

    private static string BufferingArgs(string group, BufferingMode mode, int batch, double interval, int workers, int maxsize)
    {
        switch (mode)
        {
            case BufferingMode.Auto: return "";
            case BufferingMode.Off: return $" --{group}-batch 0 --{group}-interval 0";
            case BufferingMode.Full: return $" --{group}-batch -1 --{group}-interval 0";
            default: return $" --{group}-batch {batch} --{group}-interval {interval.ToString(System.Globalization.CultureInfo.InvariantCulture)} --{group}-workers {workers} --{group}-maxsize {maxsize}";
        }
    }

    private void Activate()
    {
        var base_directory = new DirectoryInfo(Environment.CurrentDirectory).Parent?.Parent?.Parent?.FullName;
        var database_arg = _database_ == DatabaseType.Off ? "" : $" --database \"{_database_}\"";
        var universe_args = BufferingArgs("universe", _universe_buffering_, _universe_batch_, _universe_interval_, _universe_workers_, _universe_maxsize_);
        var market_args = !_persist_market_ ? " --market-batch 0 --market-interval 0" : BufferingArgs("market", _market_buffering_, _market_batch_, _market_interval_, _market_workers_, _market_maxsize_);
        var portfolio_args = BufferingArgs("portfolio", _portfolio_buffering_, _portfolio_batch_, _portfolio_interval_, _portfolio_workers_, _portfolio_maxsize_);
        var benchmark_tickers = _benchmark_tickers_ == null ? "" : _benchmark_tickers_.Trim();
        var benchmark_arg = !_benchmark_ ? "" : benchmark_tickers.Length == 0 ? " --benchmark" : $" --benchmark \"{benchmark_tickers}\"";
        var report_arg = _report_ ? " --report" : "";
        var export_arg = _export_ ? " --export" : "";
        var plot_arg = _plot_ ? " --plot" : "";
        var profile_arg = _profile_ ? " --profile" : "";
        var script_args = $"{_system_mode_} --console \"{_console_}\" --file \"{_file_}\" --strategy \"{_strategy_}\" --provider \"{_robot_.Account.BrokerName}\" --ticker \"{_robot_.Symbol.Name}\" --timeframe \"{_robot_.TimeFrame.Name}\" --iid \"{_robot_.InstanceId}\"{database_arg}{benchmark_arg}{universe_args}{market_args}{portfolio_args}{report_arg}{export_arg}{plot_arg}{profile_arg}";
        var inner_cmd = $"cd /d \"{base_directory}\" && conda run --no-capture-output -n {_environment_} python -m Library.System.Main {script_args}";
        _log_.Debug($"Activation Operation: Launching Python · {_environment_} · {script_args}");
        SpawnTerminal(inner_cmd);
        try
        {
            _system_.SendUpdateInit(Process.GetCurrentProcess().Id);
            _system_.SendUpdateAccount(_robot_.Account);
            _system_.SendUpdateSymbol(_robot_.Symbol);
            _system_.SendUpdateComplete();
            _log_.Debug("Handshake Operation: Sent · Awaiting Python Actions");
            ReceiveAndProcessActions();
            ResolveDelays();
            _log_.Info("Activation Operation: Activated · Python Ready");
        }
        catch (Exception e)
        {
            _log_.Exception($"Activation Operation: Failed · {e.Message}");
            _robot_.Stop();
        }
    }

    private const int BatchCapacity = 4092;
    private const int FlushThreshold = 16;

    private void ReleaseSingle(byte[] record)
    {
        _system_.SendRecord(record);
        _system_.SendUpdateComplete();
        ReceiveAndProcessActions();
    }

    private void FlushBatch(Queue<byte[]> queue)
    {
        using var ms = new MemoryStream();
        ms.WriteByte((byte)UpdateID.Batch);
        while (queue.Count > 0)
        {
            var record = queue.Peek();
            if (3 + record.Length > BatchCapacity) { queue.Dequeue(); ReleaseSingle(record); continue; }
            if (ms.Length + 2 + record.Length > BatchCapacity) break;
            ms.Write(BitConverter.GetBytes((ushort)record.Length), 0, 2);
            ms.Write(record, 0, record.Length);
            queue.Dequeue();
        }
        if (ms.Length > 1) _system_.SendBatch(ms.ToArray());
    }

    private void Emit(Queue<byte[]> queue, DelayMode mode, int count, byte[] record)
    {
        try
        {
            if (mode == DelayMode.Off) { ReleaseSingle(record); return; }
            queue.Enqueue(record);
            if (mode == DelayMode.Manual)
            {
                while (queue.Count > count) ReleaseSingle(queue.Dequeue());
            }
            else if (mode == DelayMode.Full && queue.Count >= FlushThreshold)
            {
                FlushBatch(queue);
            }
        }
        catch (PeerExitException) { _robot_.Stop(); }
    }

    private void DrainQueue(Queue<byte[]> queue)
    {
        while (queue.Count > 0) FlushBatch(queue);
    }

    private void DrainBatched()
    {
        DrainQueue(_tick_queue_);
        DrainQueue(_bar_queue_);
        DrainQueue(_order_queue_);
        DrainQueue(_position_queue_);
        DrainQueue(_trade_queue_);
    }

    private void SpawnTerminal(string inner_cmd)
    {
        try
        {
            var wt_info = new ProcessStartInfo
            {
                FileName = "wt.exe",
                Arguments = $"-w cAlgo new-tab --title \"{_robot_.InstanceId}\" cmd.exe /k \"{inner_cmd}\"",
                UseShellExecute = true
            };
            Process.Start(wt_info);
        }
        catch (Exception)
        {
            var cmd_info = new ProcessStartInfo
            {
                FileName = "cmd.exe",
                Arguments = $"/k \"{inner_cmd}\"",
                UseShellExecute = true
            };
            Process.Start(cmd_info);
        }
    }

    private (Func<double> Ask, Func<double> Bid) FindConversions(Asset from_asset, Asset to_asset)
    {
        if (from_asset == to_asset) return (Ask: () => 1.0, Bid: () => 1.0);
        var primary = _robot_.Symbol;
        if (primary.BaseAsset == from_asset && primary.QuoteAsset == to_asset) return (Ask: () => primary.Ask, Bid: () => primary.Bid);
        if (primary.QuoteAsset == from_asset && primary.BaseAsset == to_asset) return (Ask: () => 1.0 / primary.Bid, Bid: () => 1.0 / primary.Ask);
        foreach (var name in new[] { $"{from_asset.Name}{to_asset.Name}", $"{to_asset.Name}{from_asset.Name}" })
        {
            if (!_robot_.Symbols.Exists(name)) continue;
            try
            {
                var symbol = _robot_.Symbols.GetSymbol(name);
                if (symbol?.BaseAsset == null || symbol.QuoteAsset == null) continue;
                if (symbol.BaseAsset == from_asset && symbol.QuoteAsset == to_asset) return (Ask: () => symbol.Ask, Bid: () => symbol.Bid);
                if (symbol.QuoteAsset == from_asset && symbol.BaseAsset == to_asset) return (Ask: () => 1.0 / symbol.Bid, Bid: () => 1.0 / symbol.Ask);
            }
            catch (Exception e) { _log_.Debug($"Conversion Probe: Skipped · {name} · {e.Message}"); }
        }
        _log_.Warning($"Conversion Operation: Unavailable · {from_asset.Name} → {to_asset.Name} · Defaulting to 1.0");
        return (Ask: () => 1.0, Bid: () => 1.0);
    }

    private xTick CurrentTick()
    {
        return new xTick
        {
            Timestamp = _robot_.Server.Time,
            Ask = _robot_.Symbol.Ask,
            Bid = _robot_.Symbol.Bid,
            AskBaseConversion = _ask_base_conversion_(),
            BidBaseConversion = _bid_base_conversion_(),
            AskQuoteConversion = _ask_quote_conversion_(),
            BidQuoteConversion = _bid_quote_conversion_(),
            Volume = 1.0
        };
    }

    private bool IsPositionFromRobot(Position position)
    {
        return string.Equals(position.Label, _robot_.InstanceId);
    }

    private Position[] FindPositions()
    {
        return _robot_.Positions.FindAll(_robot_.InstanceId);
    }

    private Position FindPosition(int position_id)
    {
        return FindPositions().FirstOrDefault(p => p.Id == position_id);
    }

    private HistoricalTrade[] FindTrades()
    {
        return _robot_.History.FindAll(_robot_.InstanceId);
    }

    private HistoricalTrade FindTrade(int position_id)
    {
        return FindTrades().Where(t => t.PositionId == position_id).OrderByDescending(t => t.ClosingTime).FirstOrDefault();
    }

    private bool IsOrderFromRobot(PendingOrder order)
    {
        return string.Equals(order.Label, _robot_.InstanceId);
    }

    private PendingOrder FindOrder(int order_id)
    {
        return _robot_.PendingOrders.FirstOrDefault(o => o.Id == order_id);
    }

    private UpdateID ResolveOrderUpdateID(PendingOrder order, string action)
    {
        bool isBuy = order.TradeType == TradeType.Buy;
        switch (order.OrderType)
        {
            case PendingOrderType.Stop:
                if (action == "Opened") return isBuy ? UpdateID.OpenedBuyStopOrder : UpdateID.OpenedSellStopOrder;
                if (action == "ModifiedVolume") return isBuy ? UpdateID.ModifiedBuyStopOrderVolume : UpdateID.ModifiedSellStopOrderVolume;
                if (action == "ModifiedTargetPrice") return isBuy ? UpdateID.ModifiedBuyStopOrderStopPrice : UpdateID.ModifiedSellStopOrderStopPrice;
                if (action == "ModifiedStopLoss") return isBuy ? UpdateID.ModifiedBuyStopOrderStopLoss : UpdateID.ModifiedSellStopOrderStopLoss;
                if (action == "ModifiedTakeProfit") return isBuy ? UpdateID.ModifiedBuyStopOrderTakeProfit : UpdateID.ModifiedSellStopOrderTakeProfit;
                if (action == "Closed") return isBuy ? UpdateID.ClosedBuyStopOrder : UpdateID.ClosedSellStopOrder;
                if (action == "Filled") return isBuy ? UpdateID.FilledBuyStopOrder : UpdateID.FilledSellStopOrder;
                if (action == "Expired") return isBuy ? UpdateID.ExpiredBuyStopOrder : UpdateID.ExpiredSellStopOrder;
                break;
            case PendingOrderType.Limit:
                if (action == "Opened") return isBuy ? UpdateID.OpenedBuyLimitOrder : UpdateID.OpenedSellLimitOrder;
                if (action == "ModifiedVolume") return isBuy ? UpdateID.ModifiedBuyLimitOrderVolume : UpdateID.ModifiedSellLimitOrderVolume;
                if (action == "ModifiedTargetPrice") return isBuy ? UpdateID.ModifiedBuyLimitOrderLimitPrice : UpdateID.ModifiedSellLimitOrderLimitPrice;
                if (action == "ModifiedStopLoss") return isBuy ? UpdateID.ModifiedBuyLimitOrderStopLoss : UpdateID.ModifiedSellLimitOrderStopLoss;
                if (action == "ModifiedTakeProfit") return isBuy ? UpdateID.ModifiedBuyLimitOrderTakeProfit : UpdateID.ModifiedSellLimitOrderTakeProfit;
                if (action == "Closed") return isBuy ? UpdateID.ClosedBuyLimitOrder : UpdateID.ClosedSellLimitOrder;
                if (action == "Filled") return isBuy ? UpdateID.FilledBuyLimitOrder : UpdateID.FilledSellLimitOrder;
                if (action == "Expired") return isBuy ? UpdateID.ExpiredBuyLimitOrder : UpdateID.ExpiredSellLimitOrder;
                break;
            case PendingOrderType.StopLimit:
                if (action == "Opened") return isBuy ? UpdateID.OpenedBuyStopLimitOrder : UpdateID.OpenedSellStopLimitOrder;
                if (action == "ModifiedVolume") return isBuy ? UpdateID.ModifiedBuyStopLimitOrderVolume : UpdateID.ModifiedSellStopLimitOrderVolume;
                if (action == "ModifiedTargetPrice") return isBuy ? UpdateID.ModifiedBuyStopLimitOrderStopPrice : UpdateID.ModifiedSellStopLimitOrderStopPrice;
                if (action == "ModifiedStopLoss") return isBuy ? UpdateID.ModifiedBuyStopLimitOrderStopLoss : UpdateID.ModifiedSellStopLimitOrderStopLoss;
                if (action == "ModifiedTakeProfit") return isBuy ? UpdateID.ModifiedBuyStopLimitOrderTakeProfit : UpdateID.ModifiedSellStopLimitOrderTakeProfit;
                if (action == "Closed") return isBuy ? UpdateID.ClosedBuyStopLimitOrder : UpdateID.ClosedSellStopLimitOrder;
                if (action == "Filled") return isBuy ? UpdateID.FilledBuyStopLimitOrder : UpdateID.FilledSellStopLimitOrder;
                if (action == "Expired") return isBuy ? UpdateID.ExpiredBuyStopLimitOrder : UpdateID.ExpiredSellStopLimitOrder;
                break;
        }
        throw new ArgumentException($"Unknown action {action} for {order.OrderType}");
    }

    private static UpdateID ResolvePositionCloseUpdateID(Position position, PositionCloseReason reason)
    {
        bool isBuy = position.TradeType == TradeType.Buy;
        switch (reason)
        {
            case PositionCloseReason.StopLoss: return isBuy ? UpdateID.StopLossBuyPosition : UpdateID.StopLossSellPosition;
            case PositionCloseReason.TakeProfit: return isBuy ? UpdateID.TakeProfitBuyPosition : UpdateID.TakeProfitSellPosition;
            case PositionCloseReason.StopOut: return isBuy ? UpdateID.MarginCallBuyPosition : UpdateID.MarginCallSellPosition;
            default: return isBuy ? UpdateID.ClosedBuyPosition : UpdateID.ClosedSellPosition;
        }
    }

    private void OnOrderCreated(PendingOrderCreatedEventArgs args)
    {
        if (!IsOrderFromRobot(args.PendingOrder)) return;
        if (!_verified_) return;
        var order_data = new LastOrderData { LastVolume = args.PendingOrder.VolumeInUnits, LastTargetPrice = args.PendingOrder.TargetPrice, LastStopLoss = args.PendingOrder.StopLoss, LastTakeProfit = args.PendingOrder.TakeProfit };
        _orders_.Add(args.PendingOrder.Id, order_data);
        if (!EmitOrder) return;
        _orders_sent_++;
        Emit(_order_queue_, _order_delay_, _order_delay_count_, _system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "Opened"), _bar_, args.PendingOrder));
    }

    private void OnOrderModified(PendingOrderModifiedEventArgs args)
    {
        if (!IsOrderFromRobot(args.PendingOrder)) return;
        if (!_verified_) return;
        var order_data = _orders_[args.PendingOrder.Id];
        if (Math.Abs(args.PendingOrder.VolumeInUnits - order_data.LastVolume) > double.Epsilon)
        {
            order_data.LastVolume = args.PendingOrder.VolumeInUnits;
            if (!EmitOrder) return;
            _orders_sent_++;
            Emit(_order_queue_, _order_delay_, _order_delay_count_, _system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "ModifiedVolume"), _bar_, args.PendingOrder));
            return;
        }
        if (Math.Abs(args.PendingOrder.TargetPrice - order_data.LastTargetPrice) > double.Epsilon)
        {
            order_data.LastTargetPrice = args.PendingOrder.TargetPrice;
            if (!EmitOrder) return;
            _orders_sent_++;
            Emit(_order_queue_, _order_delay_, _order_delay_count_, _system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "ModifiedTargetPrice"), _bar_, args.PendingOrder));
            return;
        }
        if ((order_data.LastStopLoss == null && args.PendingOrder.StopLoss != null) || (order_data.LastStopLoss != null && args.PendingOrder.StopLoss == null) || (order_data.LastStopLoss != null && args.PendingOrder.StopLoss != null && Math.Abs((double)args.PendingOrder.StopLoss - (double)order_data.LastStopLoss) > double.Epsilon))
        {
            order_data.LastStopLoss = args.PendingOrder.StopLoss;
            if (!EmitOrder) return;
            _orders_sent_++;
            Emit(_order_queue_, _order_delay_, _order_delay_count_, _system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "ModifiedStopLoss"), _bar_, args.PendingOrder));
            return;
        }
        if ((order_data.LastTakeProfit == null && args.PendingOrder.TakeProfit != null) || (order_data.LastTakeProfit != null && args.PendingOrder.TakeProfit == null) || (order_data.LastTakeProfit != null && args.PendingOrder.TakeProfit != null && Math.Abs((double)args.PendingOrder.TakeProfit - (double)order_data.LastTakeProfit) > double.Epsilon))
        {
            order_data.LastTakeProfit = args.PendingOrder.TakeProfit;
            if (!EmitOrder) return;
            _orders_sent_++;
            Emit(_order_queue_, _order_delay_, _order_delay_count_, _system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "ModifiedTakeProfit"), _bar_, args.PendingOrder));
        }
    }

    private void OnOrderCancelled(PendingOrderCancelledEventArgs args)
    {
        if (!IsOrderFromRobot(args.PendingOrder)) return;
        if (!_verified_) return;
        _orders_.Remove(args.PendingOrder.Id);
        if (!EmitOrder) return;
        _orders_sent_++;
        Emit(_order_queue_, _order_delay_, _order_delay_count_, _system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "Closed"), _bar_, args.PendingOrder));
    }

    private void OnOrderFilled(PendingOrderFilledEventArgs args)
    {
        if (!IsOrderFromRobot(args.PendingOrder)) return;
        if (!_verified_) return;
        _orders_.Remove(args.PendingOrder.Id);
        if (!EmitOrder) return;
        _orders_sent_++;
        Emit(_order_queue_, _order_delay_, _order_delay_count_, _system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "Filled"), _bar_, args.PendingOrder));
    }

    private void OnPositionOpened(PositionOpenedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_verified_) return;
        var position_data = new LastPositionData { LastVolume = args.Position.VolumeInUnits, LastStopLoss = args.Position.StopLoss, LastTakeProfit = args.Position.TakeProfit };
        _positions_.Add(args.Position.Id, position_data);
        if (!EmitPosition) return;
        UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.OpenedBuyPosition : UpdateID.OpenedSellPosition;
        _positions_sent_++;
        Emit(_position_queue_, _position_delay_, _position_delay_count_, _system_.BuildUpdatePosition(update_id, _bar_, args.Position));
    }

    private void OnPositionModified(PositionModifiedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_verified_) return;
        var position_data = _positions_[args.Position.Id];
        if (Math.Abs(args.Position.VolumeInUnits - position_data.LastVolume) > double.Epsilon)
        {
            bool increased = args.Position.VolumeInUnits > position_data.LastVolume;
            position_data.LastVolume = args.Position.VolumeInUnits;
            if (increased)
            {
                if (!EmitPosition) return;
                UpdateID increase_id = args.Position.TradeType == TradeType.Buy ? UpdateID.IncreasedBuyPositionVolume : UpdateID.IncreasedSellPositionVolume;
                _positions_sent_++;
                Emit(_position_queue_, _position_delay_, _position_delay_count_, _system_.BuildUpdatePosition(increase_id, _bar_, args.Position));
                return;
            }
            if (!EmitTrade) return;
            var trade = FindTrade(args.Position.Id);
            UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.DecreasedBuyPositionVolume : UpdateID.DecreasedSellPositionVolume;
            _trades_sent_++;
            Emit(_trade_queue_, _trade_delay_, _trade_delay_count_, _system_.BuildUpdatePositionTrade(update_id, _bar_, args.Position, trade));
            return;
        }
        if ((position_data.LastStopLoss == null && args.Position.StopLoss != null) || (position_data.LastStopLoss != null && args.Position.StopLoss == null) || (position_data.LastStopLoss != null && args.Position.StopLoss != null && Math.Abs((double)args.Position.StopLoss - (double)position_data.LastStopLoss) > double.Epsilon))
        {
            position_data.LastStopLoss = args.Position.StopLoss;
            if (!EmitPosition) return;
            UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.ModifiedBuyPositionStopLoss : UpdateID.ModifiedSellPositionStopLoss;
            _positions_sent_++;
            Emit(_position_queue_, _position_delay_, _position_delay_count_, _system_.BuildUpdatePosition(update_id, _bar_, args.Position));
            return;
        }
        if ((position_data.LastTakeProfit == null && args.Position.TakeProfit != null) || (position_data.LastTakeProfit != null && args.Position.TakeProfit == null) || (position_data.LastTakeProfit != null && args.Position.TakeProfit != null && Math.Abs((double)args.Position.TakeProfit - (double)position_data.LastTakeProfit) > double.Epsilon))
        {
            position_data.LastTakeProfit = args.Position.TakeProfit;
            if (!EmitPosition) return;
            UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.ModifiedBuyPositionTakeProfit : UpdateID.ModifiedSellPositionTakeProfit;
            _positions_sent_++;
            Emit(_position_queue_, _position_delay_, _position_delay_count_, _system_.BuildUpdatePosition(update_id, _bar_, args.Position));
        }
    }

    private void OnPositionClosed(PositionClosedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_verified_) return;
        _positions_.Remove(args.Position.Id);
        if (!EmitTrade) return;
        var trade = FindTrade(args.Position.Id);
        UpdateID update_id = ResolvePositionCloseUpdateID(args.Position, args.Reason);
        _trades_sent_++;
        Emit(_trade_queue_, _trade_delay_, _trade_delay_count_, _system_.BuildUpdatePositionTrade(update_id, _bar_, args.Position, trade));
    }

    private void OnTick(SymbolTickEventArgs args)
    {
        var tick = CurrentTick();
        if (tick.Bid > _bar_.HighTick.Bid) _bar_.HighTick = tick;
        if (tick.Bid < _bar_.LowTick.Bid) _bar_.LowTick = tick;
        _bar_.CloseTick = tick;
        if (!_verified_) return;
        if (EmitTickAll)
        {
            _ticks_sent_++;
            Emit(_tick_queue_, _tick_delay_, _tick_delay_count_, _system_.BuildUpdateTick(UpdateID.Tick, tick));
        }
        if (_ask_above_target_ != null && tick.Ask >= _ask_above_target_)
        {
            _ticks_sent_++;
            Emit(_tick_queue_, _tick_delay_, _tick_delay_count_, _system_.BuildUpdateTick(UpdateID.AskAboveTarget, tick));
        }
        if (_ask_below_target_ != null && tick.Ask <= _ask_below_target_)
        {
            _ticks_sent_++;
            Emit(_tick_queue_, _tick_delay_, _tick_delay_count_, _system_.BuildUpdateTick(UpdateID.AskBelowTarget, tick));
        }
        if (_bid_above_target_ != null && tick.Bid >= _bid_above_target_)
        {
            _ticks_sent_++;
            Emit(_tick_queue_, _tick_delay_, _tick_delay_count_, _system_.BuildUpdateTick(UpdateID.BidAboveTarget, tick));
        }
        if (_bid_below_target_ != null && tick.Bid <= _bid_below_target_)
        {
            _ticks_sent_++;
            Emit(_tick_queue_, _tick_delay_, _tick_delay_count_, _system_.BuildUpdateTick(UpdateID.BidBelowTarget, tick));
        }
    }

    private void OnBarOpened(BarOpenedEventArgs args)
    {
        var tick = CurrentTick();
        _bar_.OpenTick = tick;
        _bar_.HighTick = tick;
        _bar_.LowTick = tick;
        _bar_.CloseTick = tick;
        _bar_.Volume = 0.0;
        if (!_verified_) return;
        if (!EmitBarOpened) return;
        _bars_sent_++;
        Emit(_bar_queue_, _bar_delay_, _bar_delay_count_, _system_.BuildUpdateBar(UpdateID.BarOpened, _bar_));
    }

    private void OnBarClosed(BarClosedEventArgs args)
    {
        var last_bar = _robot_.Bars.LastBar;
        _bar_.Volume = last_bar.TickVolume;
        if (!_primed_)
        {
            _primed_ = true;
            _bar_.Timestamp = last_bar.OpenTime;
            _bar_.GapTick = _bar_.CloseTick;
            return;
        }
        if (!_verified_)
        {
            _observed_bars_++;
            var bar_ticks = new[] { _bar_.GapTick, _bar_.OpenTick, _bar_.HighTick, _bar_.LowTick, _bar_.CloseTick };
            var ts_set = new HashSet<DateTime>(bar_ticks.Select(t => t.Timestamp));
            bool sub_minute = bar_ticks.Any(t => t.Timestamp.Second != 0 || t.Timestamp.Millisecond != 0);
            if (!(ts_set.Count > 2 && sub_minute)) _degraded_bars_++;
            _verification_buffer_.Add(new xBar { Timestamp = _bar_.Timestamp, GapTick = _bar_.GapTick, OpenTick = _bar_.OpenTick, HighTick = _bar_.HighTick, LowTick = _bar_.LowTick, CloseTick = _bar_.CloseTick, Volume = _bar_.Volume });
            if (_observed_bars_ >= _verification_)
            {
                bool degraded = _degraded_bars_ >= _verification_;
                if (_accuracy_ == AccuracyMode.Tick && degraded)
                {
                    _log_.Exception("Activation Operation: Failed · Accuracy = Tick but non-Tick Data detected · Set Data to 'Tick data from Server' or set Accuracy = Auto/Bar");
                    _robot_.Stop();
                    return;
                }
                if (_accuracy_ == AccuracyMode.Bar && !degraded)
                {
                    _log_.Exception("Activation Operation: Failed · Accuracy = Bar but Tick Data detected · Set Data to Bars or set Accuracy = Auto/Tick");
                    _robot_.Stop();
                    return;
                }
                _verified_ = true;
                _persist_market_ = _accuracy_ == AccuracyMode.Tick || (_accuracy_ == AccuracyMode.Auto && !degraded);
                if (!_persist_market_) _log_.Warning($"Activation Operation: Bar Mode ({_degraded_bars_}/{_verification_} non-Tick) · Market Persistence Disabled");
                _log_.Info($"Activation Operation: Accuracy {(_persist_market_ ? "Tick" : "Bar")} ({_verification_ - _degraded_bars_}/{_verification_}) · Activating");
                Activate();
                if (EmitBarClosed)
                {
                    foreach (var buffered in _verification_buffer_)
                    {
                        _ticks_sent_ += 5;
                        _bars_sent_++;
                        ReleaseSingle(_system_.BuildUpdateBar(UpdateID.BarClosed, buffered));
                    }
                    _log_.Debug($"Warmup Operation: Replayed Buffer ({_verification_buffer_.Count} Bars) · Total Sent {_bars_sent_} Bars");
                }
                _verification_buffer_.Clear();
            }
        }
        else if (EmitBarClosed)
        {
            _ticks_sent_ += 5;
            _bars_sent_++;
            Emit(_bar_queue_, _bar_delay_, _bar_delay_count_, _system_.BuildUpdateBar(UpdateID.BarClosed, _bar_));
        }
        _bar_.Timestamp = last_bar.OpenTime;
        _bar_.GapTick = _bar_.CloseTick;
    }

    public void OnError(Error error)
    {
        _log_.Error($"Execution Operation: Failed · Unexpected Error · {error.TradeResult}");
    }

    public void OnException(Exception exception)
    {
        _log_.Exception($"Execution Operation: Failed · {exception.Message}");
        _log_.Exception($"Execution Operation: Failed · {exception}");
        _robot_.Stop();
    }

    public void OnShutdown()
    {
        _log_.Info("Shutdown Operation: Safely Terminating");
        _log_.Info($"Summary: Ticks {_ticks_sent_} · Bars {_bars_sent_} · Orders {_orders_sent_} · Positions {_positions_sent_} · Trades {_trades_sent_} · Actions {_actions_received_}");
        try
        {
            if (_verified_)
            {
                bool pending = _tick_queue_.Count > 0 || _bar_queue_.Count > 0 || _order_queue_.Count > 0 || _position_queue_.Count > 0 || _trade_queue_.Count > 0;
                DrainBatched();
                if (pending) { _system_.SendUpdateComplete(); ReceiveAndProcessActions(); }
                _system_.SendUpdateShutdown();
                ReceiveAndProcessActions();
            }
        }
        catch (Exception e) { _log_.Warning($"Shutdown Operation: Failed · {e.Message}"); }
    }

    private static double? NullIfNan(double value)
    {
        return double.IsNaN(value) ? null : value;
    }

    private static int ReadInt32(byte[] data, int offset)
    {
        return BitConverter.ToInt32(data, offset);
    }

    private static double ReadDouble(byte[] data, int offset)
    {
        return BitConverter.ToDouble(data, offset);
    }

    private static string ReadString(byte[] data, ref int offset)
    {
        ushort len = BitConverter.ToUInt16(data, offset);
        offset += 2;
        if (len == 0) return null;
        string s = Encoding.UTF8.GetString(data, offset, len);
        offset += len;
        return s;
    }

    private bool ProcessActionOpenPosition(TradeType trade_type, string pos_type, double volume, double? sl_pips, double? tp_pips)
    {
        var result = _robot_.ExecuteMarketOrder(trade_type, _robot_.Symbol.Name, volume, _robot_.InstanceId, sl_pips, tp_pips, pos_type, false, StopTriggerMethod.Trade);
        return result.IsSuccessful;
    }

    private bool ProcessActionModifyVolume(int position_id, double volume, int intent)
    {
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning("Modify Volume Operation: Failed · Position Not Found"); return true; }
        double current = position.VolumeInUnits;
        if (Math.Abs(volume - current) <= double.Epsilon) return true;
        if (intent > 0 && volume < current) { _log_.Warning($"Increase Volume Operation: Failed · Target Below Current ({volume} < {current})"); return true; }
        if (intent < 0 && volume > current) { _log_.Warning($"Decrease Volume Operation: Failed · Target Above Current ({volume} > {current})"); return true; }
        var result = position.ModifyVolume(volume);
        return result.IsSuccessful;
    }

    private bool ProcessActionModifyStopLoss(int position_id, double? sl_price)
    {
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning("Modify Stop Loss Operation: Failed · Position Not Found"); return true; }
        var result = position.ModifyStopLossPrice(sl_price);
        return result.IsSuccessful;
    }

    private bool ProcessActionModifyTakeProfit(int position_id, double? tp_price)
    {
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning("Modify Take Profit Operation: Failed · Position Not Found"); return true; }
        var result = position.ModifyTakeProfitPrice(tp_price);
        return result.IsSuccessful;
    }

    private bool ProcessActionClosePosition(int position_id)
    {
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning("Close Position Operation: Failed · Position Not Found"); return true; }
        return _robot_.ClosePosition(position).IsSuccessful;
    }


    private bool ProcessActionOpenStopOrder(TradeType trade_type, double volume, double target_price, double? sl_price, double? tp_price)
    {
        var result = _robot_.PlaceStopOrder(trade_type, _robot_.Symbol.Name, volume, target_price, _robot_.InstanceId, stopLoss: sl_price, takeProfit: tp_price, protectionType: null);
        return result.IsSuccessful;
    }

    private bool ProcessActionOpenLimitOrder(TradeType trade_type, double volume, double target_price, double? sl_price, double? tp_price)
    {
        var result = _robot_.PlaceLimitOrder(trade_type, _robot_.Symbol.Name, volume, target_price, _robot_.InstanceId, stopLoss: sl_price, takeProfit: tp_price, protectionType: null);
        return result.IsSuccessful;
    }

    private bool ProcessActionOpenStopLimitOrder(TradeType trade_type, double volume, double stop_price, double limit_price, double? sl_price, double? tp_price)
    {
        double range_pips = Math.Abs(limit_price - stop_price) / _robot_.Symbol.PipSize;
        var result = _robot_.PlaceStopLimitOrder(trade_type, _robot_.Symbol.Name, volume, stop_price, range_pips, _robot_.InstanceId, stopLoss: sl_price, takeProfit: tp_price, protectionType: null);
        return result.IsSuccessful;
    }

    private bool ProcessActionModifyOrderVolume(int order_id, double volume)
    {
        var order = FindOrder(order_id);
        if (order == null) { _log_.Warning("Modify Order Volume Operation: Failed · Order Not Found"); return true; }
        return order.ModifyVolume(volume).IsSuccessful;
    }

    private bool ProcessActionModifyOrderPrice(int order_id, double price)
    {
        var order = FindOrder(order_id);
        if (order == null) { _log_.Warning("Modify Order Price Operation: Failed · Order Not Found"); return true; }
        return order.ModifyTargetPrice(price).IsSuccessful;
    }

    private bool ProcessActionModifyOrderLimitPrice(int order_id, double limit_price)
    {
        var order = FindOrder(order_id);
        if (order == null) { _log_.Warning("Modify Order Limit Price Operation: Failed · Order Not Found"); return true; }
        double range_pips = Math.Abs(limit_price - order.TargetPrice) / _robot_.Symbol.PipSize;
        return order.ModifyStopLimitRange(range_pips).IsSuccessful;
    }

    private bool ProcessActionModifyOrderStopLoss(int order_id, double? sl_price)
    {
        var order = FindOrder(order_id);
        if (order == null) { _log_.Warning("Modify Order Stop Loss Operation: Failed · Order Not Found"); return true; }
        return order.ModifyStopLossPrice(sl_price).IsSuccessful;
    }

    private bool ProcessActionModifyOrderTakeProfit(int order_id, double? tp_price)
    {
        var order = FindOrder(order_id);
        if (order == null) { _log_.Warning("Modify Order Take Profit Operation: Failed · Order Not Found"); return true; }
        return order.ModifyTakeProfitPrice(tp_price).IsSuccessful;
    }

    private bool ProcessActionCloseOrder(int order_id)
    {
        var order = FindOrder(order_id);
        if (order == null) { _log_.Warning("Close Order Operation: Failed · Order Not Found"); return true; }
        return _robot_.CancelPendingOrder(order).IsSuccessful;
    }

    private void ReceiveAndProcessActions()
    {
        ActionID action_id;
        var go_live = false;
        do
        {
            byte[] data;
            try { data = _system_.Receive(); }
            catch (PeerExitException)
            {
                _robot_.Stop();
                return;
            }
            catch (Exception e)
            {
                _log_.Exception($"Receive Operation: Failed · {e.Message}");
                _robot_.Stop();
                return;
            }
            action_id = (ActionID)data[0];
            if (action_id != ActionID.Complete) _actions_received_++;
            switch (action_id)
            {
                case ActionID.Complete: break;
                case ActionID.Shutdown: _robot_.Stop(); break;
                case ActionID.Execution: go_live = true; break;
                case ActionID.Subscribe: _streams_ |= (Stream)data[1]; break;
                case ActionID.Unsubscribe: _streams_ &= ~(Stream)data[1]; break;
                case ActionID.Init:
                    int python_pid = ReadInt32(data, 1);
                    _log_.Debug($"Handshake Operation: Completed (pid {python_pid})");
                    try { _system_.Watchdog(Process.GetProcessById(python_pid)); }
                    catch (Exception e) { _log_.Warning($"Handshake Operation: Failed · Could Not Open Python Process {python_pid} · {e.Message}"); }
                    break;
                case ActionID.OpenBuyPosition:
                case ActionID.OpenSellPosition:
                    int offset = 1;
                    string posType = ReadString(data, ref offset);
                    double vol = ReadDouble(data, offset);
                    double? sl = NullIfNan(ReadDouble(data, offset + 8));
                    double? tp = NullIfNan(ReadDouble(data, offset + 16));
                    if (!ProcessActionOpenPosition(action_id == ActionID.OpenBuyPosition ? TradeType.Buy : TradeType.Sell, posType, vol, sl, tp)) _robot_.Stop();
                    break;
                case ActionID.IncreaseBuyPositionVolume:
                case ActionID.IncreaseSellPositionVolume:
                    if (!ProcessActionModifyVolume(ReadInt32(data, 1), ReadDouble(data, 5), 1)) _robot_.Stop();
                    break;
                case ActionID.DecreaseBuyPositionVolume:
                case ActionID.DecreaseSellPositionVolume:
                    if (!ProcessActionModifyVolume(ReadInt32(data, 1), ReadDouble(data, 5), -1)) _robot_.Stop();
                    break;
                case ActionID.ModifyBuyPositionVolume:
                case ActionID.ModifySellPositionVolume:
                    if (!ProcessActionModifyVolume(ReadInt32(data, 1), ReadDouble(data, 5), 0)) _robot_.Stop();
                    break;
                case ActionID.ModifyBuyPositionStopLoss:
                case ActionID.ModifySellPositionStopLoss:
                    if (!ProcessActionModifyStopLoss(ReadInt32(data, 1), NullIfNan(ReadDouble(data, 5)))) _robot_.Stop();
                    break;
                case ActionID.ModifyBuyPositionTakeProfit:
                case ActionID.ModifySellPositionTakeProfit:
                    if (!ProcessActionModifyTakeProfit(ReadInt32(data, 1), NullIfNan(ReadDouble(data, 5)))) _robot_.Stop();
                    break;
                case ActionID.CloseBuyPosition:

                case ActionID.CloseSellPosition:
                    if (!ProcessActionClosePosition(ReadInt32(data, 1))) _robot_.Stop();
                    break;
                case ActionID.OpenBuyStopOrder:
                case ActionID.OpenSellStopOrder:
                    if (!ProcessActionOpenStopOrder(action_id == ActionID.OpenBuyStopOrder ? TradeType.Buy : TradeType.Sell, ReadDouble(data, 1), ReadDouble(data, 9), NullIfNan(ReadDouble(data, 17)), NullIfNan(ReadDouble(data, 25)))) _robot_.Stop();
                    break;
                case ActionID.OpenBuyLimitOrder:
                case ActionID.OpenSellLimitOrder:
                    if (!ProcessActionOpenLimitOrder(action_id == ActionID.OpenBuyLimitOrder ? TradeType.Buy : TradeType.Sell, ReadDouble(data, 1), ReadDouble(data, 9), NullIfNan(ReadDouble(data, 17)), NullIfNan(ReadDouble(data, 25)))) _robot_.Stop();
                    break;
                case ActionID.OpenBuyStopLimitOrder:
                case ActionID.OpenSellStopLimitOrder:
                    if (!ProcessActionOpenStopLimitOrder(action_id == ActionID.OpenBuyStopLimitOrder ? TradeType.Buy : TradeType.Sell, ReadDouble(data, 1), ReadDouble(data, 9), ReadDouble(data, 17), NullIfNan(ReadDouble(data, 25)), NullIfNan(ReadDouble(data, 33)))) _robot_.Stop();
                    break;
                case ActionID.ModifyBuyStopOrderVolume:
                case ActionID.ModifySellStopOrderVolume:
                case ActionID.ModifyBuyLimitOrderVolume:
                case ActionID.ModifySellLimitOrderVolume:
                case ActionID.ModifyBuyStopLimitOrderVolume:
                case ActionID.ModifySellStopLimitOrderVolume:
                    if (!ProcessActionModifyOrderVolume(ReadInt32(data, 1), ReadDouble(data, 5))) _robot_.Stop();
                    break;
                case ActionID.ModifyBuyStopOrderStopPrice:
                case ActionID.ModifySellStopOrderStopPrice:
                case ActionID.ModifyBuyLimitOrderLimitPrice:
                case ActionID.ModifySellLimitOrderLimitPrice:
                case ActionID.ModifyBuyStopLimitOrderStopPrice:
                case ActionID.ModifySellStopLimitOrderStopPrice:
                    if (!ProcessActionModifyOrderPrice(ReadInt32(data, 1), ReadDouble(data, 5))) _robot_.Stop();
                    break;
                case ActionID.ModifyBuyStopLimitOrderLimitPrice:
                case ActionID.ModifySellStopLimitOrderLimitPrice:
                    if (!ProcessActionModifyOrderLimitPrice(ReadInt32(data, 1), ReadDouble(data, 5))) _robot_.Stop();
                    break;
                case ActionID.ModifyBuyStopOrderStopLoss:
                case ActionID.ModifySellStopOrderStopLoss:
                case ActionID.ModifyBuyLimitOrderStopLoss:
                case ActionID.ModifySellLimitOrderStopLoss:
                case ActionID.ModifyBuyStopLimitOrderStopLoss:
                case ActionID.ModifySellStopLimitOrderStopLoss:
                    if (!ProcessActionModifyOrderStopLoss(ReadInt32(data, 1), NullIfNan(ReadDouble(data, 5)))) _robot_.Stop();
                    break;
                case ActionID.ModifyBuyStopOrderTakeProfit:
                case ActionID.ModifySellStopOrderTakeProfit:
                case ActionID.ModifyBuyLimitOrderTakeProfit:
                case ActionID.ModifySellLimitOrderTakeProfit:
                case ActionID.ModifyBuyStopLimitOrderTakeProfit:
                case ActionID.ModifySellStopLimitOrderTakeProfit:
                    if (!ProcessActionModifyOrderTakeProfit(ReadInt32(data, 1), NullIfNan(ReadDouble(data, 5)))) _robot_.Stop();
                    break;
                case ActionID.CloseBuyStopOrder:
                case ActionID.CloseSellStopOrder:
                case ActionID.CloseBuyLimitOrder:
                case ActionID.CloseSellLimitOrder:
                case ActionID.CloseBuyStopLimitOrder:
                case ActionID.CloseSellStopLimitOrder:
                    if (!ProcessActionCloseOrder(ReadInt32(data, 1))) _robot_.Stop();
                    break;
                case ActionID.AskAboveTarget: _ask_above_target_ = NullIfNan(ReadDouble(data, 1)); break;
                case ActionID.AskBelowTarget: _ask_below_target_ = NullIfNan(ReadDouble(data, 1)); break;
                case ActionID.BidAboveTarget: _bid_above_target_ = NullIfNan(ReadDouble(data, 1)); break;
                case ActionID.BidBelowTarget: _bid_below_target_ = NullIfNan(ReadDouble(data, 1)); break;
                default: _log_.Exception($"Receive Operation: Failed · Invalid Action ID {action_id}"); throw new ArgumentOutOfRangeException();
            }
        } while (action_id != ActionID.Complete && action_id != ActionID.Shutdown);
        if (go_live)
        {
            _system_.SendUpdateExecution();
            _system_.SendUpdateComplete();
            _log_.Info("Execution Operation: Trading Enabled · Python Warmed Up");
            ReceiveAndProcessActions();
        }
    }
}
