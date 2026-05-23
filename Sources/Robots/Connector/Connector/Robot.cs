using System;
using System.IO;
using System.Diagnostics;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using Newtonsoft.Json.Linq;

namespace cAlgo.Robots;

public class RobotAPI : IDisposable
{
    private class LastPositionData
    {
        public double LastVolume { get; set; }
        public double? LastStopLoss { get; set; }
        public double? LastTakeProfit { get; set; }
    }

    public class xTick
    {
        public DateTime Timestamp { get; set; }
        public double Ask { get; set; }
        public double Bid { get; set; }
        public double AskBaseConversion { get; set; }
        public double BidBaseConversion { get; set; }
        public double AskQuoteConversion { get; set; }
        public double BidQuoteConversion { get; set; }
        public double Volume { get; set; }
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

    private readonly DatabaseType _database_;
    private readonly int _verification_;
    private readonly TickStreamMode _tick_stream_;
    private readonly BarStreamMode _bar_stream_;
    private readonly OrderStreamMode _order_stream_;
    private readonly PositionStreamMode _position_stream_;
    private readonly TradeStreamMode _trade_stream_;
    private readonly BufferingMode _market_buffering_;
    private readonly int _market_batch_;
    private readonly double _market_interval_;
    private readonly BufferingMode _portfolio_buffering_;
    private readonly int _portfolio_batch_;
    private readonly double _portfolio_interval_;
    private readonly SystemMode _system_mode_;

    private readonly Dictionary<int, LastPositionData> _positions_;

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

    public RobotAPI(Robot algo, VerboseLevel console, VerboseLevel file, StrategyType strategy,
                    DatabaseType database, int verification,
                    TickStreamMode tick_stream, BarStreamMode bar_stream, OrderStreamMode order_stream,
                    PositionStreamMode position_stream, TradeStreamMode trade_stream,
                    BufferingMode market_buffering, int market_batch, double market_interval,
                    BufferingMode portfolio_buffering, int portfolio_batch, double portfolio_interval,
                    string host = "localhost", int port = 5555)
    {
        _robot_ = algo;
        _console_ = console;
        _file_ = file;
        _strategy_ = strategy;
        _verification_ = verification;

        _log_ = new Logging(_robot_, "Strategy", console);
        _log_.Info("Starting");

        _system_mode_ = ResolveSystemMode(_robot_.RunningMode);
        _database_ = ResolveDatabase(_system_mode_, strategy, database);
        _tick_stream_ = tick_stream == TickStreamMode.Auto ? TickStreamMode.Target : tick_stream;
        _bar_stream_ = bar_stream == BarStreamMode.Auto ? BarStreamMode.All : bar_stream;
        _order_stream_ = order_stream == OrderStreamMode.Auto ? OrderStreamMode.All : order_stream;
        _position_stream_ = position_stream == PositionStreamMode.Auto ? PositionStreamMode.All : position_stream;
        _trade_stream_ = trade_stream == TradeStreamMode.Auto ? TradeStreamMode.All : trade_stream;
        _market_buffering_ = market_buffering;
        _market_batch_ = market_batch;
        _market_interval_ = market_interval;
        _portfolio_buffering_ = portfolio_buffering;
        _portfolio_batch_ = portfolio_batch;
        _portfolio_interval_ = portfolio_interval;

        if (_tick_stream_ == TickStreamMode.All) _log_.Warning("Tick Stream=All not implemented, using Target");
        _log_.Debug($"Streams: tick={_tick_stream_}, bar={_bar_stream_}, order={_order_stream_}, position={_position_stream_}, trade={_trade_stream_}");

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
        _verification_buffer_ = new List<xBar>();

        _robot_.Positions.Opened += OnPositionOpened;
        _robot_.Positions.Modified += OnPositionModified;
        _robot_.Positions.Closed += OnPositionClosed;
        _robot_.Bars.BarClosed += OnBarClosed;
        _robot_.Bars.BarOpened += OnBarOpened;
        _robot_.Symbol.Tick += OnTick;

        _system_ = new SystemAPI(_robot_, console, host, port);

        if (_system_mode_ == SystemMode.Live)
        {
            _verified_ = true;
            Activate();
        }
        else
        {
            _log_.Info($"Verifying data accuracy ({_verification_} bars)");
        }
    }

    public void Dispose()
    {
        _system_?.Dispose();
    }

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

    private static DatabaseType ResolveDatabase(SystemMode system, StrategyType strat, DatabaseType chosen)
    {
        if (chosen != DatabaseType.Auto) return chosen;
        if (system == SystemMode.Live) return DatabaseType.Quant;
        if (strat == StrategyType.Download) return DatabaseType.Quant;
        return DatabaseType.Tests;
    }

    private void Activate()
    {
        var base_directory = new DirectoryInfo(Environment.CurrentDirectory).Parent?.Parent?.Parent?.FullName;
        var database_arg = _database_ == DatabaseType.Off ? "" : $" --database \"{_database_}\"";
        var market_batch_arg = _market_buffering_ == BufferingMode.Auto ? "" : $" --market-batch {_market_batch_}";
        var market_interval_arg = _market_buffering_ == BufferingMode.Auto ? "" : $" --market-interval {_market_interval_.ToString(System.Globalization.CultureInfo.InvariantCulture)}";
        var portfolio_batch_arg = _portfolio_buffering_ == BufferingMode.Auto ? "" : $" --portfolio-batch {_portfolio_batch_}";
        var portfolio_interval_arg = _portfolio_buffering_ == BufferingMode.Auto ? "" : $" --portfolio-interval {_portfolio_interval_.ToString(System.Globalization.CultureInfo.InvariantCulture)}";
        var script_args = $"{_system_mode_} --console \"{_console_}\" --file \"{_file_}\" --strategy \"{_strategy_}\" --provider \"{_robot_.Account.BrokerName}\" --ticker \"{_robot_.Symbol.Name}\" --timeframe \"{_robot_.TimeFrame.Name}\" --iid \"{_robot_.InstanceId}\"{database_arg}{market_batch_arg}{market_interval_arg}{portfolio_batch_arg}{portfolio_interval_arg}";
        var process_info = new ProcessStartInfo
        {
            FileName = "cmd.exe",
            Arguments = $"/c \"cd {base_directory} && conda run --no-capture-output -n Quant python -m Library.System.Main {script_args}\"",
            UseShellExecute = true
        };
        _log_.Debug($"Activating: {script_args}");
        Process.Start(process_info);
        _system_.Connect();
        _system_.SendUpdateAccount(_robot_.Account);
        _system_.SendUpdateSymbol(_robot_.Symbol);
        _system_.SendUpdateComplete();
        ReceiveAndProcessActions();
    }

    private (Func<double> Ask, Func<double> Bid) FindConversions(Asset from_asset, Asset to_asset)
    {
        if (from_asset == to_asset) return (Ask: () => 1.0, Bid: () => 1.0);
        var primary = _robot_.Symbol;
        if (primary.BaseAsset == from_asset && primary.QuoteAsset == to_asset) return (Ask: () => primary.Ask, Bid: () => primary.Bid);
        if (primary.QuoteAsset == from_asset && primary.BaseAsset == to_asset) return (Ask: () => 1.0 / primary.Bid, Bid: () => 1.0 / primary.Ask);
        foreach (var symbol_name in _robot_.Symbols)
        {
            try
            {
                if (!_robot_.Symbols.Exists(symbol_name)) continue;
                var symbol = _robot_.Symbols.GetSymbol(symbol_name);
                if (symbol.BaseAsset == null || symbol.QuoteAsset == null) continue;
                if (symbol.BaseAsset == from_asset && symbol.QuoteAsset == to_asset) return (Ask: () => symbol.Ask, Bid: () => symbol.Bid);
                if (symbol.QuoteAsset == from_asset && symbol.BaseAsset == to_asset) return (Ask: () => 1.0 / symbol.Bid, Bid: () => 1.0 / symbol.Ask);
            }
            catch (Exception e) { _log_.Warning(e.Message); }
        }
        throw new Exception($"No conversion symbol found for {from_asset} -> {to_asset}");
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
        return FindTrades().FirstOrDefault(t => t.PositionId == position_id);
    }

    private void OnPositionOpened(PositionOpenedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_verified_) return;
        var position_data = new LastPositionData
        {
            LastVolume = args.Position.VolumeInUnits,
            LastStopLoss = args.Position.StopLoss,
            LastTakeProfit = args.Position.TakeProfit
        };
        _positions_.Add(args.Position.Id, position_data);
        if (_position_stream_ == PositionStreamMode.Off) return;
        UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.OpenedBuyPosition : UpdateID.OpenedSellPosition;
        _system_.SendUpdatePosition(update_id, args.Position);
        _system_.SendUpdateComplete();
        ReceiveAndProcessActions();
    }

    private void OnPositionModified(PositionModifiedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_verified_) return;
        var position_data = _positions_[args.Position.Id];
        if (Math.Abs(args.Position.VolumeInUnits - position_data.LastVolume) > double.Epsilon)
        {
            position_data.LastVolume = args.Position.VolumeInUnits;
            if (_trade_stream_ == TradeStreamMode.Off) return;
            var trade = FindTrade(args.Position.Id);
            UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.ModifiedBuyPositionVolume : UpdateID.ModifiedSellPositionVolume;
            _system_.SendUpdateTrade(update_id, trade);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
            return;
        }
        if ((position_data.LastStopLoss == null && args.Position.StopLoss != null) ||
            (position_data.LastStopLoss != null && args.Position.StopLoss == null) ||
            (position_data.LastStopLoss != null && args.Position.StopLoss != null && Math.Abs((double)args.Position.StopLoss - (double)position_data.LastStopLoss) > double.Epsilon))
        {
            position_data.LastStopLoss = args.Position.StopLoss;
            if (_position_stream_ == PositionStreamMode.Off) return;
            UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.ModifiedBuyPositionStopLoss : UpdateID.ModifiedSellPositionStopLoss;
            _system_.SendUpdatePosition(update_id, args.Position);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
            return;
        }
        if ((position_data.LastTakeProfit == null && args.Position.TakeProfit != null) ||
            (position_data.LastTakeProfit != null && args.Position.TakeProfit == null) ||
            (position_data.LastTakeProfit != null && args.Position.TakeProfit != null && Math.Abs((double)args.Position.TakeProfit - (double)position_data.LastTakeProfit) > double.Epsilon))
        {
            position_data.LastTakeProfit = args.Position.TakeProfit;
            if (_position_stream_ == PositionStreamMode.Off) return;
            UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.ModifiedBuyPositionTakeProfit : UpdateID.ModifiedSellPositionTakeProfit;
            _system_.SendUpdatePosition(update_id, args.Position);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
        }
    }

    private void OnPositionClosed(PositionClosedEventArgs args)
    {
        if (!IsPositionFromRobot(args.Position)) return;
        if (!_verified_) return;
        _positions_.Remove(args.Position.Id);
        if (_trade_stream_ == TradeStreamMode.Off) return;
        var trade = FindTrade(args.Position.Id);
        UpdateID update_id = args.Position.TradeType == TradeType.Buy ? UpdateID.ClosedBuyPosition : UpdateID.ClosedSellPosition;
        _system_.SendUpdateTrade(update_id, trade);
        _system_.SendUpdateComplete();
        ReceiveAndProcessActions();
    }

    private void OnBarClosed(BarClosedEventArgs args)
    {
        var last_bar = _robot_.Bars.LastBar;
        _bar_.Volume = last_bar.TickVolume;

        if (!_verified_)
        {
            _observed_bars_++;
            var ts_set = new HashSet<DateTime> {
                _bar_.GapTick.Timestamp, _bar_.OpenTick.Timestamp,
                _bar_.HighTick.Timestamp, _bar_.LowTick.Timestamp, _bar_.CloseTick.Timestamp
            };
            if (ts_set.Count <= 2) _degraded_bars_++;
            _verification_buffer_.Add(new xBar
            {
                Timestamp = _bar_.Timestamp,
                GapTick = _bar_.GapTick,
                OpenTick = _bar_.OpenTick,
                HighTick = _bar_.HighTick,
                LowTick = _bar_.LowTick,
                CloseTick = _bar_.CloseTick,
                Volume = _bar_.Volume
            });
            if (_observed_bars_ >= _verification_)
            {
                if (_degraded_bars_ >= _verification_)
                {
                    _log_.Exception("Accuracy check failed: set Data='Tick data from Server', tick 'Download historical data' and 'Apply commission automatically', restart");
                    _robot_.Stop();
                    return;
                }
                _verified_ = true;
                _log_.Info($"Accuracy verified ({_verification_ - _degraded_bars_}/{_verification_}), activating");
                Activate();
                if (_bar_stream_ != BarStreamMode.Off)
                {
                    foreach (var buffered in _verification_buffer_)
                    {
                        _system_.SendUpdateBarClosed(buffered);
                        _system_.SendUpdateComplete();
                        ReceiveAndProcessActions();
                    }
                }
                _verification_buffer_.Clear();
            }
        }
        else if (_bar_stream_ != BarStreamMode.Off)
        {
            _system_.SendUpdateBarClosed(_bar_);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
        }

        _bar_.Timestamp = last_bar.OpenTime;
        _bar_.GapTick = _bar_.CloseTick;
    }

    private void OnBarOpened(BarOpenedEventArgs args)
    {
        var tick = CurrentTick();
        _bar_.OpenTick = tick;
        _bar_.HighTick = tick;
        _bar_.LowTick = tick;
        _bar_.CloseTick = tick;
    }

    private void OnTick(SymbolTickEventArgs args)
    {
        var tick = CurrentTick();
        if (tick.Bid > _bar_.HighTick.Bid) _bar_.HighTick = tick;
        if (tick.Bid < _bar_.LowTick.Bid) _bar_.LowTick = tick;
        _bar_.CloseTick = tick;
        if (!_verified_) return;
        if (_tick_stream_ == TickStreamMode.Off) return;
        if (_ask_above_target_ != null && tick.Ask >= _ask_above_target_)
        {
            _system_.SendUpdateTarget(UpdateID.AskAboveTarget, tick);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
        }
        if (_ask_below_target_ != null && tick.Ask <= _ask_below_target_)
        {
            _system_.SendUpdateTarget(UpdateID.AskBelowTarget, tick);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
        }
        if (_bid_above_target_ != null && tick.Bid >= _bid_above_target_)
        {
            _system_.SendUpdateTarget(UpdateID.BidAboveTarget, tick);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
        }
        if (_bid_below_target_ != null && tick.Bid <= _bid_below_target_)
        {
            _system_.SendUpdateTarget(UpdateID.BidBelowTarget, tick);
            _system_.SendUpdateComplete();
            ReceiveAndProcessActions();
        }
    }

    public void OnError(Error error)
    {
        _log_.Error("An unexpected error occurred in the robot execution");
        _log_.Error(error.TradeResult.ToString());
    }

    public void OnException(Exception exception)
    {
        _log_.Error("An unexpected exception occurred in the robot execution");
        _log_.Error(exception.ToString());
    }

    public void OnShutdown()
    {
        _log_.Warning("Shutdown strategy and safely terminate operations");
        if (!_verified_) { _system_.Disconnect(); return; }
        _system_.SendUpdateShutdown();
        ReceiveAndProcessActions();
        _system_.Disconnect();
    }

    private bool ProcessActionOpenPosition(TradeType trade_type, string pos_type, double volume, double? sl_pips, double? tp_pips)
    {
        var result = _robot_.ExecuteMarketOrder(trade_type, _robot_.Symbol.Name, volume, _robot_.InstanceId, sl_pips, tp_pips, pos_type, false, StopTriggerMethod.Trade);
        return result.IsSuccessful;
    }

    private bool ProcessActionModifyVolume(int position_id, double volume)
    {
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning("Modify Volume did not find the position"); return true; }
        if (Math.Abs(position.VolumeInUnits - volume) < _robot_.Symbol.VolumeInUnitsMin) _log_.Warning("Modified Volume to the same value causing unexpected behaviour");
        var result = position.ModifyVolume(volume);
        return result.IsSuccessful;
    }

    private bool ProcessActionModifyStopLoss(int position_id, double? sl_price)
    {
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning("Modify Stop Loss did not find the position"); return true;}
        if (position.StopLoss != null && sl_price != null && Math.Abs((double)position.StopLoss - (double)sl_price) < _robot_.Symbol.TickSize) _log_.Warning("Modified Stop-Loss to the same value causing unexpected behaviour");
        var result = position.ModifyStopLossPrice(sl_price);
        return result.IsSuccessful;
    }

    private bool ProcessActionModifyTakeProfit(int position_id, double? tp_price)
    {
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning("Modify Take Profit did not find the position"); return true; }
        if (position.TakeProfit != null && tp_price != null && Math.Abs((double)position.TakeProfit - (double)tp_price) < _robot_.Symbol.TickSize) _log_.Warning("Modified Take-Profit to the same value causing unexpected behaviour");
        var result = position.ModifyTakeProfitPrice(tp_price);
        return result.IsSuccessful;
    }

    private bool ProcessActionClosePosition(int position_id)
    {
        var position = FindPosition(position_id);
        if (position == null) { _log_.Warning("Close Position did not find the position"); return true; }
        return _robot_.ClosePosition(position).IsSuccessful;
    }

    private void ReceiveAndProcessActions()
    {
        ActionID action_id;
        do
        {
            var json = _system_.ReceiveAction();
            var action = JObject.Parse(json);
            action_id = (ActionID)action["ActionID"]!.Value<int>();
            switch (action_id)
            {
                case ActionID.Complete: break;
                case ActionID.OpenBuyPosition: if (!ProcessActionOpenPosition(TradeType.Buy, action["PositionType"]!.Value<string>()!, action["Volume"]!.Value<double>(), action["StopLoss"]?.Value<double?>(), action["TakeProfit"]?.Value<double?>())) _robot_.Stop(); break;
                case ActionID.OpenSellPosition: if (!ProcessActionOpenPosition(TradeType.Sell, action["PositionType"]!.Value<string>()!, action["Volume"]!.Value<double>(), action["StopLoss"]?.Value<double?>(), action["TakeProfit"]?.Value<double?>())) _robot_.Stop(); break;
                case ActionID.ModifyBuyPositionVolume:
                case ActionID.ModifySellPositionVolume: if (!ProcessActionModifyVolume(action["PositionID"]!.Value<int>(), action["Volume"]!.Value<double>())) _robot_.Stop(); break;
                case ActionID.ModifyBuyPositionStopLoss:
                case ActionID.ModifySellPositionStopLoss: if (!ProcessActionModifyStopLoss(action["PositionID"]!.Value<int>(), action["StopLoss"]?.Value<double?>())) _robot_.Stop(); break;
                case ActionID.ModifyBuyPositionTakeProfit:
                case ActionID.ModifySellPositionTakeProfit: if (!ProcessActionModifyTakeProfit(action["PositionID"]!.Value<int>(), action["TakeProfit"]?.Value<double?>())) _robot_.Stop(); break;
                case ActionID.CloseBuyPosition:
                case ActionID.CloseSellPosition: if (!ProcessActionClosePosition(action["PositionID"]!.Value<int>())) _robot_.Stop(); break;
                case ActionID.AskAboveTarget: _ask_above_target_ = action["Ask"]?.Value<double?>(); break;
                case ActionID.AskBelowTarget: _ask_below_target_ = action["Ask"]?.Value<double?>(); break;
                case ActionID.BidAboveTarget: _bid_above_target_ = action["Bid"]?.Value<double?>(); break;
                case ActionID.BidBelowTarget: _bid_below_target_ = action["Bid"]?.Value<double?>(); break;
                default: _log_.Exception($"Received invalid action ID: {action_id}"); throw new ArgumentOutOfRangeException();
            }
        } while (action_id != ActionID.Complete);
    }
}