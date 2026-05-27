using cAlgo.API.Internals;

namespace Connector;

public class Logging
{
    private readonly Algo _algo_;
    private readonly VerboseLevel _verbose_;
    private readonly string _cname_;
    
    private const string _default_exception_log_ = "EXCEPTION";
    private const string _default_error_log_ = "ERROR";
    private const string _default_warning_log_ = "WARNING";
    private const string _default_info_log_ = "INFO";
    private const string _default_debug_log_ = "DEBUG";
    private const string _default_alert_log_ = "ALERT";
    
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

    public void Exception(string message) => LogMessage(VerboseLevel.Exception, _default_exception_log_, message);
    public void Error(string message) => LogMessage(VerboseLevel.Error, _default_error_log_, message);
    public void Warning(string message) => LogMessage(VerboseLevel.Warning, _default_warning_log_, message); 
    public void Alert(string message) => LogMessage(VerboseLevel.Alert, _default_alert_log_, message);
    public void Info(string message) => LogMessage(VerboseLevel.Info, _default_info_log_, message); 
    public void Debug(string message) => LogMessage(VerboseLevel.Debug, _default_debug_log_, message);
}