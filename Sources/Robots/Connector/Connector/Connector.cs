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

    [Parameter("Environment", Group = "Connection Management", DefaultValue = EnvironmentType.Quant)]
    public EnvironmentType Environment { get; set; }

    [Parameter("Database", Group = "Connection Management", DefaultValue = DatabaseType.Auto)]
    public DatabaseType Database { get; set; }

    [Parameter("Accuracy", Group = "Accuracy Management", DefaultValue = AccuracyMode.Auto)]
    public AccuracyMode Accuracy { get; set; }

    [Parameter("Verification", Group = "Accuracy Management", DefaultValue = VerificationMode.Auto)]
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

    [Parameter("Universe Buffering", Group = "Universe Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode UniverseBuffering { get; set; }

    [Parameter("Universe Batch", Group = "Universe Management", DefaultValue = 1, MinValue = 0)]
    public int UniverseBatch { get; set; }

    [Parameter("Universe Interval", Group = "Universe Management", DefaultValue = 0.0, MinValue = 0.0)]
    public double UniverseInterval { get; set; }

    [Parameter("Universe Workers", Group = "Universe Management", DefaultValue = 1, MinValue = 1)]
    public int UniverseWorkers { get; set; }

    [Parameter("Universe Maxsize", Group = "Universe Management", DefaultValue = 64, MinValue = 0)]
    public int UniverseMaxsize { get; set; }

    [Parameter("Market Buffering", Group = "Market Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode MarketBuffering { get; set; }

    [Parameter("Market Batch", Group = "Market Management", DefaultValue = 100, MinValue = 0)]
    public int MarketBatch { get; set; }

    [Parameter("Market Interval", Group = "Market Management", DefaultValue = 60.0, MinValue = 0.0)]
    public double MarketInterval { get; set; }

    [Parameter("Market Workers", Group = "Market Management", DefaultValue = 8, MinValue = 1)]
    public int MarketWorkers { get; set; }

    [Parameter("Market Maxsize", Group = "Market Management", DefaultValue = 64, MinValue = 0)]
    public int MarketMaxsize { get; set; }

    [Parameter("Portfolio Buffering", Group = "Portfolio Management", DefaultValue = BufferingMode.Auto)]
    public BufferingMode PortfolioBuffering { get; set; }

    [Parameter("Portfolio Batch", Group = "Portfolio Management", DefaultValue = 100, MinValue = 0)]
    public int PortfolioBatch { get; set; }

    [Parameter("Portfolio Interval", Group = "Portfolio Management", DefaultValue = 60.0, MinValue = 0.0)]
    public double PortfolioInterval { get; set; }

    [Parameter("Portfolio Workers", Group = "Portfolio Management", DefaultValue = 1, MinValue = 1)]
    public int PortfolioWorkers { get; set; }

    [Parameter("Portfolio Maxsize", Group = "Portfolio Management", DefaultValue = 64, MinValue = 0)]
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
        int verification = Verification switch
        {
            VerificationMode.Off => 0,
            VerificationMode.Manual => VerificationCount,
            _ => 1,
        };
        _robot_api_ = new RobotAPI(this, Console, File, Strategy, Environment, Database, verification, Accuracy,
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