using cAlgo.API.Internals;

namespace Connector;

public class Logging
{
    private readonly Algo _algo_;
    private readonly VerboseLevel _verbose_;
    private readonly string _cname_;

    private const string _DEFAULT_EXCEPTION_LOG_ = "EXCEPTION";
    private const string _DEFAULT_ERROR_LOG_ = "ERROR";
    private const string _DEFAULT_WARNING_LOG_ = "WARNING";
    private const string _DEFAULT_INFO_LOG_ = "INFO";
    private const string _DEFAULT_DEBUG_LOG_ = "DEBUG";
    private const string _DEFAULT_ALERT_LOG_ = "ALERT";

    public Logging(Algo algo, string cname, VerboseLevel verbose)
    {
        _algo_ = algo;
        _cname_ = cname;
        _verbose_ = verbose;
    }

    private void LogMessage(VerboseLevel verbose, string default_log, string message)
    {
        if (_verbose_ < verbose) return;
        var log_message = $"{default_log} - {_cname_} - {message}";
        _algo_.Print(log_message);
    }

    public void Exception(string message) => LogMessage(VerboseLevel.Exception, _DEFAULT_EXCEPTION_LOG_, message);
    public void Error(string message) => LogMessage(VerboseLevel.Error, _DEFAULT_ERROR_LOG_, message);
    public void Warning(string message) => LogMessage(VerboseLevel.Warning, _DEFAULT_WARNING_LOG_, message);
    public void Alert(string message) => LogMessage(VerboseLevel.Alert, _DEFAULT_ALERT_LOG_, message);
    public void Info(string message) => LogMessage(VerboseLevel.Info, _DEFAULT_INFO_LOG_, message);
    public void Debug(string message) => LogMessage(VerboseLevel.Debug, _DEFAULT_DEBUG_LOG_, message);
}