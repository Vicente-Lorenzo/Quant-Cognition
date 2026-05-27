namespace Connector;

public enum DatabaseType
{
    Auto = 0,
    Quant = 1,
    Tests = 2,
    Off = 3,
}

public enum BufferingMode
{
    Auto = 0,
    Manual = 1,
}

public enum TickStreamMode
{
    Auto = 0,
    All = 1,
    Target = 2,
    Off = 3,
}

public enum BarStreamMode
{
    Auto = 0,
    All = 1,
    Off = 2,
}

public enum OrderStreamMode
{
    Auto = 0,
    All = 1,
    Off = 2,
}

public enum PositionStreamMode
{
    Auto = 0,
    All = 1,
    Off = 2,
}

public enum TradeStreamMode
{
    Auto = 0,
    All = 1,
    Off = 2,
}