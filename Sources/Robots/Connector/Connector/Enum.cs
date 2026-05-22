namespace cAlgo.Robots
{
    public enum StrategyType
    {
        Download = 1,
        NNFX = 2,
        DDPG = 3,
    }

    public enum VerboseLevel
    {
        Silent = 0,
        Exception = 1,
        Error = 2,
        Warning = 3,
        Alert = 4,
        Info = 5,
        Debug = 6,
    }
}