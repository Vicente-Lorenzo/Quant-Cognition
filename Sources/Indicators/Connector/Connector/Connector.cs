using System;
using cAlgo.API;
using cAlgo.API.Collections;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Indicators;

[Indicator(AccessRights = AccessRights.None)]
public class Connector : Indicator
{
    [Parameter(DefaultValue = "Hello world!")]
    public string Message { get; set; }

    [Output("Main")]
    public IndicatorDataSeries Result { get; set; }

    protected override void Initialize()
    {
        // To learn more about cTrader Algo visit our Help Center:
        // https://help.ctrader.com/ctrader-algo/

        Print(Message);
    }

    public override void Calculate(int index)
    {
        // Calculate value at specified index
        // Result[index] =
    }
}