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
        public xTick HighAskTick { get; set; }
        public xTick HighBidTick { get; set; }
        public xTick HighMidTick { get; set; }
        public xTick LowAskTick { get; set; }
        public xTick LowBidTick { get; set; }
        public xTick LowMidTick { get; set; }
        public xTick CloseTick { get; set; }
        public double Volume { get; set; }

        public void Open(DateTime timestamp, xTick tick)
        {
            Timestamp = timestamp;
            OpenTick = HighAskTick = HighBidTick = HighMidTick = LowAskTick = LowBidTick = LowMidTick = CloseTick = tick;
            Volume = 0.0;
        }
    }

    private readonly Robot _robot_;
    private readonly Logging _log_;
    private readonly SystemAPI _system_;

    private readonly VerboseLevel _console_;
    private readonly VerboseLevel _file_;
    private readonly StrategyType _strategy_;

    private readonly EnvironmentType _environment_;
    private Stream _streams_ = Stream.Tick | Stream.BarOpened | Stream.BarClosed | Stream.Order | Stream.Position | Stream.Trade;
    private string _label_;
    private readonly bool _benchmark_;
    private readonly string _benchmark_tickers_;
    private readonly bool _report_;
    private readonly bool _export_;
    private readonly bool _plot_;
    private readonly bool _profile_;
    private readonly string _description_;
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

    private bool _active_;
    private bool _primed_;
    private double _last_ask_ = double.NaN;
    private double _last_bid_ = double.NaN;

    private long _ticks_sent_;
    private long _bars_sent_;
    private long _orders_sent_;
    private long _positions_sent_;
    private long _trades_sent_;
    private long _actions_received_;

    public RobotAPI(Robot algo, VerboseLevel console, VerboseLevel file, StrategyType strategy, EnvironmentType environment,
                    bool benchmark, string benchmark_tickers, bool report, bool export, bool plot, bool profile, string description)
    {
        _robot_ = algo;
        _console_ = console;
        _file_ = file;
        _strategy_ = strategy;

        _log_ = new Logging(_robot_, "Strategy", console);
        _log_.Info("Start Operation: Starting");

        _system_mode_ = ResolveSystemMode(_robot_.RunningMode);
        _environment_ = environment;
        _benchmark_ = benchmark;
        _benchmark_tickers_ = benchmark_tickers;
        _report_ = report;
        _export_ = export;
        _plot_ = plot;
        _profile_ = profile;
        _description_ = description;

        var base_conversions = FindConversions(_robot_.Symbol.BaseAsset, _robot_.Account.Asset);
        _ask_base_conversion_ = base_conversions.Ask;
        _bid_base_conversion_ = base_conversions.Bid;
        var quote_conversions = FindConversions(_robot_.Symbol.QuoteAsset, _robot_.Account.Asset);
        _ask_quote_conversion_ = quote_conversions.Ask;
        _bid_quote_conversion_ = quote_conversions.Bid;
        var tick = CurrentTick();
        _bar_ = new xBar { GapTick = tick };
        _bar_.Open(_robot_.Bars.LastBar.OpenTime, tick);
        _positions_ = new Dictionary<int, LastPositionData>();
        _orders_ = new Dictionary<int, LastOrderData>();

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
        _label_ = _robot_.InstanceId;

        if (_system_mode_ == SystemMode.Live)
        {
            _active_ = true;
            Activate();
        }
        else
        {
            _log_.Info("Activation Operation: Deferred (First Full Bar)");
        }
    }

    public void Dispose()
    {
        _system_?.Dispose();
    }

    private bool EmitTick => (_streams_ & Stream.Tick) != 0;

    private bool EmitBarOpened => (_streams_ & Stream.BarOpened) != 0;

    private bool EmitBarClosed => (_streams_ & Stream.BarClosed) != 0;

    private bool EmitOrder => (_streams_ & Stream.Order) != 0;

    private bool EmitPosition => (_streams_ & Stream.Position) != 0;

    private bool EmitTrade => (_streams_ & Stream.Trade) != 0;

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

    private void Activate()
    {
        var base_directory = new DirectoryInfo(Environment.CurrentDirectory).Parent?.Parent?.Parent?.FullName;
        var benchmark_tickers = _benchmark_tickers_ == null ? "" : _benchmark_tickers_.Trim();
        var benchmark_arg = !_benchmark_ ? "" : benchmark_tickers.Length == 0 ? " --benchmark" : $" --benchmark \"{benchmark_tickers}\"";
        var report_arg = _report_ ? " --report" : "";
        var export_arg = _export_ ? " --export" : "";
        var plot_arg = _plot_ ? " --plot" : "";
        var profile_arg = _profile_ ? " --profile" : "";
        var description = _description_ == null ? "" : _description_.Trim();
        var description_arg = description.Length == 0 ? "" : $" --description \"{description}\"";
        var script_args = $"{_system_mode_} --console \"{_console_}\" --file \"{_file_}\" --strategy \"{_strategy_}\" --provider \"{_robot_.Account.BrokerName}\" --ticker \"{_robot_.Symbol.Name}\" --timeframe \"{_robot_.TimeFrame.Name}\" --iid \"{_robot_.InstanceId}\"{benchmark_arg}{report_arg}{export_arg}{plot_arg}{profile_arg}{description_arg}";
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
            _log_.Info("Activation Operation: Activated · Python Ready");
        }
        catch (Exception e)
        {
            _log_.Exception($"Activation Operation: Failed · {e.Message}");
            _robot_.Stop();
        }
    }

    private void Emit(byte[] record)
    {
        try
        {
            _system_.SendRecord(record);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
        }
        catch (PeerExitException) { _robot_.Stop(); }
    }

    private void SpawnTerminal(string inner_cmd)
    {
        var escaped_cmd = inner_cmd.Replace("\"", "\\\"");
        try
        {
            var wt_info = new ProcessStartInfo
            {
                FileName = "wt.exe",
                Arguments = $"-w cAlgo new-tab --title \"{_robot_.InstanceId}\" cmd.exe /k \"{escaped_cmd}\"",
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
        var ask = _robot_.Symbol.Ask;
        var bid = _robot_.Symbol.Bid;
        return new xTick
        {
            Timestamp = _robot_.Server.Time,
            Ask = ask,
            Bid = bid,
            AskBaseConversion = _ask_base_conversion_(),
            BidBaseConversion = _bid_base_conversion_(),
            AskQuoteConversion = _ask_quote_conversion_(),
            BidQuoteConversion = _bid_quote_conversion_(),
            Volume = (ask != _last_ask_ ? 1.0 : 0.0) + (bid != _last_bid_ ? 1.0 : 0.0)
        };
    }

    private bool IsPositionFromRobot(Position position)
    {
        return string.Equals(position.Label, _label_);
    }

    private Position[] FindPositions()
    {
        return _robot_.Positions.FindAll(_label_);
    }

    private Position FindPosition(int position_id)
    {
        return FindPositions().FirstOrDefault(p => p.Id == position_id);
    }

    private HistoricalTrade[] FindTrades()
    {
        return _robot_.History.FindAll(_label_);
    }

    private HistoricalTrade FindTrade(int position_id)
    {
        return FindTrades().Where(t => t.PositionId == position_id).OrderByDescending(t => t.ClosingTime).FirstOrDefault();
    }

    private bool IsOrderFromRobot(PendingOrder order)
    {
        return string.Equals(order.Label, _label_);
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
        if (!_active_) return;
        var order_data = new LastOrderData { LastVolume = args.PendingOrder.VolumeInUnits, LastTargetPrice = args.PendingOrder.TargetPrice, LastStopLoss = args.PendingOrder.StopLoss, LastTakeProfit = args.PendingOrder.TakeProfit };
        _orders_.Add(args.PendingOrder.Id, order_data);
        if (!EmitOrder) return;
        _orders_sent_++;
        Emit(_system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "Opened"), _bar_, args.PendingOrder));
    }

    private void OnOrderModified(PendingOrderModifiedEventArgs args)
    {
        if (!IsOrderFromRobot(args.PendingOrder)) return;
        if (!_active_) return;
        var order_data = _orders_[args.PendingOrder.Id];
        if (Math.Abs(args.PendingOrder.VolumeInUnits - order_data.LastVolume) > double.Epsilon)
        {
            order_data.LastVolume = args.PendingOrder.VolumeInUnits;
            if (!EmitOrder) return;
            _orders_sent_++;
            Emit(_system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "ModifiedVolume"), _bar_, args.PendingOrder));
            return;
        }
        if (Math.Abs(args.PendingOrder.TargetPrice - order_data.LastTargetPrice) > double.Epsilon)
        {
            order_data.LastTargetPrice = args.PendingOrder.TargetPrice;
            if (!EmitOrder) return;
            _orders_sent_++;
            Emit(_system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "ModifiedTargetPrice"), _bar_, args.PendingOrder));
            return;
        }
        if (Moved(order_data.LastStopLoss, args.PendingOrder.StopLoss))
        {
            order_data.LastStopLoss = args.PendingOrder.StopLoss;
            if (EmitOrder)
            {
                _orders_sent_++;
                Emit(_system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "ModifiedStopLoss"), _bar_, args.PendingOrder));
            }
        }
        if (Moved(order_data.LastTakeProfit, args.PendingOrder.TakeProfit))
        {
            order_data.LastTakeProfit = args.PendingOrder.TakeProfit;
            if (!EmitOrder) return;
            _orders_sent_++;
            Emit(_system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "ModifiedTakeProfit"), _bar_, args.PendingOrder));
        }
    }

    private void OnOrderCancelled(PendingOrderCancelledEventArgs args)
    {
        if (!IsOrderFromRobot(args.PendingOrder)) return;
        if (!_active_) return;
        _orders_.Remove(args.PendingOrder.Id);
        if (!EmitOrder) return;
        _orders_sent_++;
        Emit(_system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "Closed"), _bar_, args.PendingOrder));
    }

    private void OnOrderFilled(PendingOrderFilledEventArgs args)
    {
        if (!IsOrderFromRobot(args.PendingOrder)) return;
        if (!_active_) return;
        _orders_.Remove(args.PendingOrder.Id);
        if (!EmitOrder) return;
        _orders_sent_++;
        Emit(_system_.BuildUpdateOrder(ResolveOrderUpdateID(args.PendingOrder, "Filled"), _bar_, args.PendingOrder));
    }

    private bool Moved(double? last, double? current)
    {
        if (last == null || current == null) return last != current;
        return Math.Abs((double)current - (double)last) > _robot_.Symbol.TickSize / 2;
    }

    private void OnPositionOpened(PositionOpenedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_active_) return;
        var position_data = new LastPositionData { LastVolume = args.Position.VolumeInUnits, LastStopLoss = args.Position.StopLoss, LastTakeProfit = args.Position.TakeProfit };
        _positions_.Add(args.Position.Id, position_data);
        if (!EmitPosition) return;
        UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.OpenedBuyPosition : UpdateID.OpenedSellPosition;
        _positions_sent_++;
        Emit(_system_.BuildUpdatePosition(update_id, _bar_, args.Position));
    }

    private void OnPositionModified(PositionModifiedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_active_) return;
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
                Emit(_system_.BuildUpdatePosition(increase_id, _bar_, args.Position));
                return;
            }
            if (!EmitTrade) return;
            var trade = FindTrade(args.Position.Id);
            UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.DecreasedBuyPositionVolume : UpdateID.DecreasedSellPositionVolume;
            _trades_sent_++;
            Emit(_system_.BuildUpdatePositionTrade(update_id, _bar_, args.Position, trade));
            return;
        }
        if (Moved(position_data.LastStopLoss, args.Position.StopLoss))
        {
            position_data.LastStopLoss = args.Position.StopLoss;
            if (EmitPosition)
            {
                UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.ModifiedBuyPositionStopLoss : UpdateID.ModifiedSellPositionStopLoss;
                _positions_sent_++;
                Emit(_system_.BuildUpdatePosition(update_id, _bar_, args.Position));
            }
        }
        if (Moved(position_data.LastTakeProfit, args.Position.TakeProfit))
        {
            position_data.LastTakeProfit = args.Position.TakeProfit;
            if (!EmitPosition) return;
            UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.ModifiedBuyPositionTakeProfit : UpdateID.ModifiedSellPositionTakeProfit;
            _positions_sent_++;
            Emit(_system_.BuildUpdatePosition(update_id, _bar_, args.Position));
        }
    }

    private void OnPositionClosed(PositionClosedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_active_) return;
        _positions_.Remove(args.Position.Id);
        if (!EmitTrade) return;
        var trade = FindTrade(args.Position.Id);
        UpdateID update_id = ResolvePositionCloseUpdateID(args.Position, args.Reason);
        _trades_sent_++;
        Emit(_system_.BuildUpdatePositionTrade(update_id, _bar_, args.Position, trade));
    }

    private void OnTick(SymbolTickEventArgs args)
    {
        var tick = CurrentTick();
        _last_ask_ = tick.Ask;
        _last_bid_ = tick.Bid;
        if (tick.Ask > _bar_.HighAskTick.Ask) _bar_.HighAskTick = tick;
        if (tick.Bid > _bar_.HighBidTick.Bid) _bar_.HighBidTick = tick;
        if (tick.Ask + tick.Bid > _bar_.HighMidTick.Ask + _bar_.HighMidTick.Bid) _bar_.HighMidTick = tick;
        if (tick.Ask < _bar_.LowAskTick.Ask) _bar_.LowAskTick = tick;
        if (tick.Bid < _bar_.LowBidTick.Bid) _bar_.LowBidTick = tick;
        if (tick.Ask + tick.Bid < _bar_.LowMidTick.Ask + _bar_.LowMidTick.Bid) _bar_.LowMidTick = tick;
        _bar_.CloseTick = tick;
        if (!_active_) return;
        if (EmitTick)
        {
            _ticks_sent_++;
            Emit(_system_.BuildUpdateTick(UpdateID.Tick, tick));
        }
        if (_ask_above_target_ != null && tick.Ask >= _ask_above_target_)
        {
            _ticks_sent_++;
            Emit(_system_.BuildUpdateTick(UpdateID.AskAboveTarget, tick));
        }
        if (_ask_below_target_ != null && tick.Ask <= _ask_below_target_)
        {
            _ticks_sent_++;
            Emit(_system_.BuildUpdateTick(UpdateID.AskBelowTarget, tick));
        }
        if (_bid_above_target_ != null && tick.Bid >= _bid_above_target_)
        {
            _ticks_sent_++;
            Emit(_system_.BuildUpdateTick(UpdateID.BidAboveTarget, tick));
        }
        if (_bid_below_target_ != null && tick.Bid <= _bid_below_target_)
        {
            _ticks_sent_++;
            Emit(_system_.BuildUpdateTick(UpdateID.BidBelowTarget, tick));
        }
    }

    private void OnBarOpened(BarOpenedEventArgs args)
    {
        _bar_.Open(_robot_.Bars.LastBar.OpenTime, CurrentTick());
        if (!_active_) return;
        if (!EmitBarOpened) return;
        _bars_sent_++;
        Emit(_system_.BuildUpdateBar(UpdateID.BarOpened, _bar_));
    }

    private void OnBarClosed(BarClosedEventArgs args)
    {
        var last_bar = _robot_.Bars.LastBar;
        _bar_.Volume = last_bar.TickVolume;
        _bar_.Timestamp = last_bar.OpenTime;
        if (!_primed_)
        {
            _primed_ = true;
            _bar_.GapTick = _bar_.CloseTick;
            return;
        }
        if (!_active_)
        {
            _active_ = true;
            Activate();
        }
        if (EmitBarClosed)
        {
            _ticks_sent_ += 9;
            _bars_sent_++;
            Emit(_system_.BuildUpdateBar(UpdateID.BarClosed, _bar_));
        }
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
            if (_active_)
            {
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
        var result = _robot_.ExecuteMarketOrder(trade_type, _robot_.Symbol.Name, volume, _label_, sl_pips, tp_pips, pos_type, false, StopTriggerMethod.Trade);
        return result.IsSuccessful;
    }

    private bool ProcessActionModifyVolume(int position_id, double volume, int intent)
    {
        var operation = intent > 0 ? "Increase Volume" : intent < 0 ? "Decrease Volume" : "Modify Volume";
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning($"{operation} Operation: Failed · Position Not Found"); return true; }
        double current = position.VolumeInUnits;
        if (Math.Abs(volume - current) <= double.Epsilon) return true;
        if (intent > 0 && volume < current) { _log_.Warning($"{operation} Operation: Failed · Target Below Current ({volume} < {current})"); return true; }
        if (intent < 0 && volume > current) { _log_.Warning($"{operation} Operation: Failed · Target Above Current ({volume} > {current})"); return true; }
        if (volume <= 0.0) return _robot_.ClosePosition(position).IsSuccessful;
        return position.ModifyVolume(volume).IsSuccessful;
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
        var result = _robot_.PlaceStopOrder(trade_type, _robot_.Symbol.Name, volume, target_price, _label_, stopLoss: sl_price, takeProfit: tp_price, protectionType: null);
        return result.IsSuccessful;
    }

    private bool ProcessActionOpenLimitOrder(TradeType trade_type, double volume, double target_price, double? sl_price, double? tp_price)
    {
        var result = _robot_.PlaceLimitOrder(trade_type, _robot_.Symbol.Name, volume, target_price, _label_, stopLoss: sl_price, takeProfit: tp_price, protectionType: null);
        return result.IsSuccessful;
    }

    private bool ProcessActionOpenStopLimitOrder(TradeType trade_type, double volume, double stop_price, double limit_price, double? sl_price, double? tp_price)
    {
        double range_pips = Math.Abs(limit_price - stop_price) / _robot_.Symbol.PipSize;
        var result = _robot_.PlaceStopLimitOrder(trade_type, _robot_.Symbol.Name, volume, stop_price, range_pips, _label_, stopLoss: sl_price, takeProfit: tp_price, protectionType: null);
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
                    int label_offset = 5;
                    _label_ = ReadString(data, ref label_offset) ?? _robot_.InstanceId;
                    _log_.Debug($"Handshake Operation: Completed (pid {python_pid} · label {_label_})");
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
