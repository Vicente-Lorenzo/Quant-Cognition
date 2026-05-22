using System;
using cAlgo.API;
using cAlgo.API.Collections;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots;

[Robot(AccessRights = AccessRights.None, AddIndicators = true)]
public class Connector : Robot
{
    [Parameter("Strategy", Group = "Strategy Management", DefaultValue = StrategyType.Download)]
    public StrategyType Strategy { get; set; }

    [Parameter("Console", Group = "Logging Management", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel Console { get; set; }

    [Parameter("File", Group = "Logging Management", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel File { get; set; }

    private RobotAPI _robot_api_;

    protected override void OnStart()
    {
        _robot_api_ = new RobotAPI(this, Console, File, Strategy);
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