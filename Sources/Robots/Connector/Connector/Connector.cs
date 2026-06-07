using System;
using cAlgo.API;
using cAlgo.API.Collections;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace Connector;

[Robot(AccessRights = AccessRights.FullAccess, AddIndicators = true)]
public class Connector : Robot
{
    [Parameter("Console", Group = "Logging Management", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel Console { get; set; }

    [Parameter("File", Group = "Logging Management", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel File { get; set; }

    [Parameter("Strategy", Group = "Strategy Management", DefaultValue = StrategyType.Download)]
    public StrategyType Strategy { get; set; }

    [Parameter("Database", Group = "System Management", DefaultValue = DatabaseType.Auto)]
    public DatabaseType Database { get; set; }

    [Parameter("Verification", Group = "System Management", DefaultValue = 1, MinValue = 1)]
    public int Verification { get; set; }

    [Parameter("Accuracy", Group = "System Management", DefaultValue = AccuracyMode.Auto)]
    public AccuracyMode Accuracy { get; set; }

    [Parameter("Tick Stream", Group = "System Management", DefaultValue = TickStreamMode.Auto)]
    public TickStreamMode TickStream { get; set; }

    [Parameter("Bar Stream", Group = "System Management", DefaultValue = BarStreamMode.Auto)]
    public BarStreamMode BarStream { get; set; }

    [Parameter("Order Stream", Group = "System Management", DefaultValue = OrderStreamMode.Auto)]
    public OrderStreamMode OrderStream { get; set; }

    [Parameter("Position Stream", Group = "System Management", DefaultValue = PositionStreamMode.Auto)]
    public PositionStreamMode PositionStream { get; set; }

    [Parameter("Trade Stream", Group = "System Management", DefaultValue = TradeStreamMode.Auto)]
    public TradeStreamMode TradeStream { get; set; }

    [Parameter("Universe Buffering", Group = "Buffering Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode UniverseBuffering { get; set; }

    [Parameter("Universe Batch", Group = "Buffering Management", DefaultValue = 1, MinValue = 0)]
    public int UniverseBatch { get; set; }

    [Parameter("Universe Interval", Group = "Buffering Management", DefaultValue = 0.0, MinValue = 0.0)]
    public double UniverseInterval { get; set; }

    [Parameter("Universe Workers", Group = "Buffering Management", DefaultValue = 1, MinValue = 1)]
    public int UniverseWorkers { get; set; }

    [Parameter("Universe Maxsize", Group = "Buffering Management", DefaultValue = 64, MinValue = 0)]
    public int UniverseMaxsize { get; set; }

    [Parameter("Market Buffering", Group = "Buffering Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode MarketBuffering { get; set; }

    [Parameter("Market Batch", Group = "Buffering Management", DefaultValue = 100, MinValue = 0)]
    public int MarketBatch { get; set; }

    [Parameter("Market Interval", Group = "Buffering Management", DefaultValue = 60.0, MinValue = 0.0)]
    public double MarketInterval { get; set; }

    [Parameter("Market Workers", Group = "Buffering Management", DefaultValue = 8, MinValue = 1)]
    public int MarketWorkers { get; set; }

    [Parameter("Market Maxsize", Group = "Buffering Management", DefaultValue = 64, MinValue = 0)]
    public int MarketMaxsize { get; set; }

    [Parameter("Portfolio Buffering", Group = "Buffering Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode PortfolioBuffering { get; set; }

    [Parameter("Portfolio Batch", Group = "Buffering Management", DefaultValue = 100, MinValue = 0)]
    public int PortfolioBatch { get; set; }

    [Parameter("Portfolio Interval", Group = "Buffering Management", DefaultValue = 60.0, MinValue = 0.0)]
    public double PortfolioInterval { get; set; }

    [Parameter("Portfolio Workers", Group = "Buffering Management", DefaultValue = 1, MinValue = 1)]
    public int PortfolioWorkers { get; set; }

    [Parameter("Portfolio Maxsize", Group = "Buffering Management", DefaultValue = 64, MinValue = 0)]
    public int PortfolioMaxsize { get; set; }

    [Parameter("Report", Group = "Reporting Management", DefaultValue = true)]
    public bool Report { get; set; }

    [Parameter("Export", Group = "Reporting Management", DefaultValue = true)]
    public bool Export { get; set; }

    [Parameter("Profile", Group = "Reporting Management", DefaultValue = false)]
    public bool Profile { get; set; }

    private RobotAPI _robot_api_;

    protected override void OnStart()
    {
        _robot_api_ = new RobotAPI(this, Console, File, Strategy, Database, Verification, Accuracy,
            TickStream, BarStream, OrderStream, PositionStream, TradeStream,
            UniverseBuffering, UniverseBatch, UniverseInterval, UniverseWorkers, UniverseMaxsize,
            MarketBuffering, MarketBatch, MarketInterval, MarketWorkers, MarketMaxsize,
            PortfolioBuffering, PortfolioBatch, PortfolioInterval, PortfolioWorkers, PortfolioMaxsize,
            Report, Export, Profile);
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