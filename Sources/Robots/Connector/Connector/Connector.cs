using System;
using cAlgo.API;
using cAlgo.API.Collections;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace Connector;

[Robot(AccessRights = AccessRights.FullAccess, AddIndicators = true)]
public class Connector : Robot
{
    [Parameter("Strategy", Group = "Strategy Management", DefaultValue = StrategyType.Download)]
    public StrategyType Strategy { get; set; }

    [Parameter("Environment", Group = "Connection Management", DefaultValue = EnvironmentType.Quant)]
    public EnvironmentType Environment { get; set; }

    [Parameter("Database", Group = "Connection Management", DefaultValue = DatabaseType.Auto)]
    public DatabaseType Database { get; set; }

    [Parameter("Accuracy Mode", Group = "Accuracy Management", DefaultValue = AccuracyMode.Auto)]
    public AccuracyMode Accuracy { get; set; }

    [Parameter("Verification Mode", Group = "Accuracy Management", DefaultValue = VerificationMode.Auto)]
    public VerificationMode Verification { get; set; }

    [Parameter("Verification Count", Group = "Accuracy Management", DefaultValue = 1, MinValue = 1)]
    public int VerificationCount { get; set; }

    [Parameter("Tick Stream", Group = "Streaming Management", DefaultValue = TickStreamMode.Auto)]
    public TickStreamMode TickStream { get; set; }

    [Parameter("Bar Stream", Group = "Streaming Management", DefaultValue = BarStreamMode.Auto)]
    public BarStreamMode BarStream { get; set; }

    [Parameter("Order Stream", Group = "Streaming Management", DefaultValue = OrderStreamMode.Auto)]
    public OrderStreamMode OrderStream { get; set; }

    [Parameter("Position Stream", Group = "Streaming Management", DefaultValue = PositionStreamMode.Auto)]
    public PositionStreamMode PositionStream { get; set; }

    [Parameter("Trade Stream", Group = "Streaming Management", DefaultValue = TradeStreamMode.Auto)]
    public TradeStreamMode TradeStream { get; set; }

    [Parameter("Buffering Mode", Group = "Universe Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode UniverseBuffering { get; set; }

    [Parameter("Batch", Group = "Universe Management", DefaultValue = 1, MinValue = 0)]
    public int UniverseBatch { get; set; }

    [Parameter("Interval", Group = "Universe Management", DefaultValue = 0.0, MinValue = 0.0)]
    public double UniverseInterval { get; set; }

    [Parameter("Workers", Group = "Universe Management", DefaultValue = 1, MinValue = 1)]
    public int UniverseWorkers { get; set; }

    [Parameter("Maxsize", Group = "Universe Management", DefaultValue = 64, MinValue = 0)]
    public int UniverseMaxsize { get; set; }

    [Parameter("Buffering Mode", Group = "Market Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode MarketBuffering { get; set; }

    [Parameter("Batch", Group = "Market Management", DefaultValue = 100, MinValue = 0)]
    public int MarketBatch { get; set; }

    [Parameter("Interval", Group = "Market Management", DefaultValue = 60.0, MinValue = 0.0)]
    public double MarketInterval { get; set; }

    [Parameter("Workers", Group = "Market Management", DefaultValue = 8, MinValue = 1)]
    public int MarketWorkers { get; set; }

    [Parameter("Maxsize", Group = "Market Management", DefaultValue = 64, MinValue = 0)]
    public int MarketMaxsize { get; set; }

    [Parameter("Buffering Mode", Group = "Portfolio Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode PortfolioBuffering { get; set; }

    [Parameter("Batch", Group = "Portfolio Management", DefaultValue = 100, MinValue = 0)]
    public int PortfolioBatch { get; set; }

    [Parameter("Interval", Group = "Portfolio Management", DefaultValue = 60.0, MinValue = 0.0)]
    public double PortfolioInterval { get; set; }

    [Parameter("Workers", Group = "Portfolio Management", DefaultValue = 1, MinValue = 1)]
    public int PortfolioWorkers { get; set; }

    [Parameter("Maxsize", Group = "Portfolio Management", DefaultValue = 64, MinValue = 0)]
    public int PortfolioMaxsize { get; set; }

    [Parameter("Tick Delay Mode", Group = "Delay Management", DefaultValue = DelayMode.Auto)]
    public DelayMode TickDelayMode { get; set; }

    [Parameter("Tick Delay Count", Group = "Delay Management", DefaultValue = 1, MinValue = 1)]
    public int TickDelayCount { get; set; }

    [Parameter("Bar Delay Mode", Group = "Delay Management", DefaultValue = DelayMode.Auto)]
    public DelayMode BarDelayMode { get; set; }

    [Parameter("Bar Delay Count", Group = "Delay Management", DefaultValue = 1, MinValue = 1)]
    public int BarDelayCount { get; set; }

    [Parameter("Order Delay Mode", Group = "Delay Management", DefaultValue = DelayMode.Auto)]
    public DelayMode OrderDelayMode { get; set; }

    [Parameter("Order Delay Count", Group = "Delay Management", DefaultValue = 1, MinValue = 1)]
    public int OrderDelayCount { get; set; }

    [Parameter("Position Delay Mode", Group = "Delay Management", DefaultValue = DelayMode.Auto)]
    public DelayMode PositionDelayMode { get; set; }

    [Parameter("Position Delay Count", Group = "Delay Management", DefaultValue = 1, MinValue = 1)]
    public int PositionDelayCount { get; set; }

    [Parameter("Trade Delay Mode", Group = "Delay Management", DefaultValue = DelayMode.Auto)]
    public DelayMode TradeDelayMode { get; set; }

    [Parameter("Trade Delay Count", Group = "Delay Management", DefaultValue = 1, MinValue = 1)]
    public int TradeDelayCount { get; set; }

    [Parameter("Console", Group = "Logging Management", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel Console { get; set; }

    [Parameter("File", Group = "Logging Management", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel File { get; set; }

    [Parameter("Storage", Group = "Logging Management", DefaultValue = VerboseLevel.Warning)]
    public VerboseLevel Storage { get; set; }

    [Parameter("Profile", Group = "Logging Management", DefaultValue = false)]
    public bool Profile { get; set; }

    [Parameter("Benchmark", Group = "Analysis Management", DefaultValue = false)]
    public bool Benchmark { get; set; }

    [Parameter("Benchmark Tickers", Group = "Analysis Management", DefaultValue = "")]
    public string BenchmarkTickers { get; set; }

    [Parameter("Report", Group = "Reporting Management", DefaultValue = true)]
    public bool Report { get; set; }

    [Parameter("Export", Group = "Reporting Management", DefaultValue = true)]
    public bool Export { get; set; }

    [Parameter("Plot", Group = "Reporting Management", DefaultValue = false)]
    public bool Plot { get; set; }

    [Parameter("Description", Group = "Reporting Management", DefaultValue = "")]
    public string Description { get; set; }

    private RobotAPI _robot_api_;

    protected override void OnStart()
    {
        int verification = Verification switch
        {
            VerificationMode.Off => 0,
            VerificationMode.Manual => VerificationCount,
            _ => 1,
        };
        _robot_api_ = new RobotAPI(this, Console, File, Storage, Strategy, Environment, Database, verification, Accuracy,
            TickStream, BarStream, OrderStream, PositionStream, TradeStream,
            TickDelayMode, TickDelayCount, BarDelayMode, BarDelayCount, OrderDelayMode, OrderDelayCount,
            PositionDelayMode, PositionDelayCount, TradeDelayMode, TradeDelayCount,
            UniverseBuffering, UniverseBatch, UniverseInterval, UniverseWorkers, UniverseMaxsize,
            MarketBuffering, MarketBatch, MarketInterval, MarketWorkers, MarketMaxsize,
            PortfolioBuffering, PortfolioBatch, PortfolioInterval, PortfolioWorkers, PortfolioMaxsize,
            Benchmark, BenchmarkTickers, Report, Export, Plot, Profile, Description);
    }

    protected override void OnStop()
    {
        _robot_api_?.OnShutdown();
        _robot_api_?.Dispose();
    }

    protected override void OnException(Exception exception)
    {
        _robot_api_?.OnException(exception);
        base.OnException(exception);
    }

    protected override void OnError(Error error)
    {
        _robot_api_?.OnError(error);
    }
}