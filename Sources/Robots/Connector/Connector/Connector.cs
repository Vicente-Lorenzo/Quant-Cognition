using System;
using cAlgo.API;
using cAlgo.API.Collections;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots;

[Robot(AccessRights = AccessRights.None, AddIndicators = true)]
public class Connector : Robot
{
    [Parameter("Strategy Name", DefaultValue = StrategyType.Download)]
    public StrategyType StrategyName { get; set; }

    [Parameter("Console Logging", DefaultValue = VerboseLevel.Debug)]
    public VerboseLevel ConsoleLogging { get; set; }

    private RobotAPI _robot_api_;

    protected override void OnStart()
    {
        _robot_api_ = new RobotAPI(this, ConsoleLogging, StrategyName);
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