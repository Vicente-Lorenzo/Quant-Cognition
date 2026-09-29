using System;
using cAlgo.API;

namespace Connector;

[Robot(AccessRights = AccessRights.FullAccess, AddIndicators = true)]
public class Connector : Robot
{
    [Parameter("Strategy", Group = "Strategy Management", DefaultValue = StrategyType.Trend)]
    public StrategyType Strategy { get; set; }

    [Parameter("Environment", Group = "Connection Management", DefaultValue = EnvironmentType.Quant)]
    public EnvironmentType Environment { get; set; }

    [Parameter("Console", Group = "Logging Management", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel Console { get; set; }

    [Parameter("File", Group = "Logging Management", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel File { get; set; }

    [Parameter("Benchmark", Group = "Analysis Management", DefaultValue = false)]
    public bool Benchmark { get; set; }

    [Parameter("Benchmark Tickers", Group = "Analysis Management", DefaultValue = "")]
    public string BenchmarkTickers { get; set; }

    [Parameter("Profile", Group = "Reporting Management", DefaultValue = false)]
    public bool Profile { get; set; }

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
        _robot_api_ = new RobotAPI(this, Console, File, Strategy, Environment, Benchmark, BenchmarkTickers, Report, Export, Plot, Profile, Description);
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