import polars as pl
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Contract import ContractAPI, PayoffType
from Library.Universe.Security import SecurityAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Universe.Provider import Provider, Platform, ProviderAPI
def populate(db):
    by = "Population"
    categories_data = [
        {CategoryAPI.ID.UID: "Forex (Major)", CategoryAPI.ID.Primary: "Forex", CategoryAPI.ID.Secondary: "Major", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Forex (Minor)", CategoryAPI.ID.Primary: "Forex", CategoryAPI.ID.Secondary: "Minor", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Forex (Exotic)", CategoryAPI.ID.Primary: "Forex", CategoryAPI.ID.Secondary: "Exotic", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Index (AMER) Equity", CategoryAPI.ID.Primary: "Index", CategoryAPI.ID.Secondary: "AMER", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Index (EMEA) Equity", CategoryAPI.ID.Primary: "Index", CategoryAPI.ID.Secondary: "EMEA", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Index (APAC) Equity", CategoryAPI.ID.Primary: "Index", CategoryAPI.ID.Secondary: "APAC", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Index (AMER) Currency", CategoryAPI.ID.Primary: "Index", CategoryAPI.ID.Secondary: "AMER", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Index (EMEA) Currency", CategoryAPI.ID.Primary: "Index", CategoryAPI.ID.Secondary: "EMEA", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Index (APAC) Currency", CategoryAPI.ID.Primary: "Index", CategoryAPI.ID.Secondary: "APAC", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Crypto (Major)", CategoryAPI.ID.Primary: "Crypto", CategoryAPI.ID.Secondary: "Major", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Crypto (Minor)", CategoryAPI.ID.Primary: "Crypto", CategoryAPI.ID.Secondary: "Minor", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Crypto (Exotic)", CategoryAPI.ID.Primary: "Crypto", CategoryAPI.ID.Secondary: "Exotic", CategoryAPI.ID.Alternative: "Currency"},
        {CategoryAPI.ID.UID: "Metal (Major)", CategoryAPI.ID.Primary: "Metal", CategoryAPI.ID.Secondary: "Major", CategoryAPI.ID.Alternative: "Commodity"},
        {CategoryAPI.ID.UID: "Metal (Minor)", CategoryAPI.ID.Primary: "Metal", CategoryAPI.ID.Secondary: "Minor", CategoryAPI.ID.Alternative: "Commodity"},
        {CategoryAPI.ID.UID: "Energy (Major)", CategoryAPI.ID.Primary: "Energy", CategoryAPI.ID.Secondary: "Major", CategoryAPI.ID.Alternative: "Commodity"},
        {CategoryAPI.ID.UID: "Energy (Minor)", CategoryAPI.ID.Primary: "Energy", CategoryAPI.ID.Secondary: "Minor", CategoryAPI.ID.Alternative: "Commodity"},
        {CategoryAPI.ID.UID: "Stock (US)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "United States", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "ETF (US)", CategoryAPI.ID.Primary: "ETF", CategoryAPI.ID.Secondary: "United States", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (AU)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Australia", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "ETF (AU)", CategoryAPI.ID.Primary: "ETF", CategoryAPI.ID.Secondary: "Australia", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (GB)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Great Britain", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "ETF (GB)", CategoryAPI.ID.Primary: "ETF", CategoryAPI.ID.Secondary: "Great Britain", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (DE)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Germany", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (HK)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Hong Kong", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (CH)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Switzerland", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (DK)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Denmark", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (NO)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Norway", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (SE)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Sweden", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (FI)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Finland", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (IE)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Ireland", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (BE)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Belgium", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (FR)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "France", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (PT)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Portugal", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (ES)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Spain", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (AT)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Austria", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (JP)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Japan", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (NL)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Netherlands", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (IT)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Italy", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (CA)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Canada", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (IN)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "India", CategoryAPI.ID.Alternative: "Equity"},
        {CategoryAPI.ID.UID: "Stock (SG)", CategoryAPI.ID.Primary: "Stock", CategoryAPI.ID.Secondary: "Singapore", CategoryAPI.ID.Alternative: "Equity"}
    ]
    UniverseAPI.push_categories(db, pl.DataFrame(categories_data))
    provider_map = {
        Provider.Spotware: ("Spotware Systems", Platform.cTrader),
        Provider.Pepperstone: ("Pepperstone Europe", Platform.cTrader),
        Provider.ICMarkets: ("IC Markets EU Ltd", Platform.cTrader),
        Provider.Bloomberg: ("Bloomberg", Platform.API),
        Provider.Yahoo: ("Yahoo Finance", Platform.API)
    }
    providers_data = []
    for p in Provider:
        name, plat = provider_map[p]
        providers_data.append({
            ProviderAPI.ID.UID: f"{p.name} ({plat.name})",
            ProviderAPI.ID.Platform: plat.name,
            ProviderAPI.ID.Name: name,
            ProviderAPI.ID.Abbreviation: p.name
        })
    UniverseAPI.push_providers(db, pl.DataFrame(providers_data))
    forex_data = [
        ("EURUSD", "Forex (Major)", "EUR", "Euro", "USD", "US Dollar", "Euro vs US Dollar"),
        ("USDJPY", "Forex (Major)", "USD", "US Dollar", "JPY", "Japanese Yen", "US Dollar vs Japanese Yen"),
        ("GBPUSD", "Forex (Major)", "GBP", "British Pound", "USD", "US Dollar", "British Pound vs US Dollar"),
        ("USDCHF", "Forex (Major)", "USD", "US Dollar", "CHF", "Swiss Franc", "US Dollar vs Swiss Franc"),
        ("AUDUSD", "Forex (Major)", "AUD", "Australian Dollar", "USD", "US Dollar", "Australian Dollar vs US Dollar"),
        ("USDCAD", "Forex (Major)", "USD", "US Dollar", "CAD", "Canadian Dollar", "US Dollar vs Canadian Dollar"),
        ("NZDUSD", "Forex (Major)", "NZD", "New Zealand Dollar", "USD", "US Dollar", "New Zealand Dollar vs US Dollar"),
        ("EURGBP", "Forex (Minor)", "EUR", "Euro", "GBP", "British Pound", "Euro vs British Pound"),
        ("EURJPY", "Forex (Minor)", "EUR", "Euro", "JPY", "Japanese Yen", "Euro vs Japanese Yen"),
        ("EURCHF", "Forex (Minor)", "EUR", "Euro", "CHF", "Swiss Franc", "Euro vs Swiss Franc"),
        ("EURAUD", "Forex (Minor)", "EUR", "Euro", "AUD", "Australian Dollar", "Euro vs Australian Dollar"),
        ("EURCAD", "Forex (Minor)", "EUR", "Euro", "CAD", "Canadian Dollar", "Euro vs Canadian Dollar"),
        ("EURNZD", "Forex (Minor)", "EUR", "Euro", "NZD", "New Zealand Dollar", "Euro vs New Zealand Dollar"),
        ("GBPJPY", "Forex (Minor)", "GBP", "British Pound", "JPY", "Japanese Yen", "British Pound vs Japanese Yen"),
        ("GBPCHF", "Forex (Minor)", "GBP", "British Pound", "CHF", "Swiss Franc", "British Pound vs Swiss Franc"),
        ("GBPAUD", "Forex (Minor)", "GBP", "British Pound", "AUD", "Australian Dollar", "British Pound vs Australian Dollar"),
        ("GBPCAD", "Forex (Minor)", "GBP", "British Pound", "CAD", "Canadian Dollar", "British Pound vs Canadian Dollar"),
        ("GBPNZD", "Forex (Minor)", "GBP", "British Pound", "NZD", "New Zealand Dollar", "British Pound vs New Zealand Dollar"),
        ("CHFJPY", "Forex (Minor)", "CHF", "Swiss Franc", "JPY", "Japanese Yen", "Swiss Franc vs Japanese Yen"),
        ("AUDJPY", "Forex (Minor)", "AUD", "Australian Dollar", "JPY", "Japanese Yen", "Australian Dollar vs Japanese Yen"),
        ("AUDCHF", "Forex (Minor)", "AUD", "Australian Dollar", "CHF", "Swiss Franc", "Australian Dollar vs Swiss Franc"),
        ("AUDCAD", "Forex (Minor)", "AUD", "Australian Dollar", "CAD", "Canadian Dollar", "Australian Dollar vs Canadian Dollar"),
        ("AUDNZD", "Forex (Minor)", "AUD", "Australian Dollar", "NZD", "New Zealand Dollar", "Australian Dollar vs New Zealand Dollar"),
        ("CADJPY", "Forex (Minor)", "CAD", "Canadian Dollar", "JPY", "Japanese Yen", "Canadian Dollar vs Japanese Yen"),
        ("CADCHF", "Forex (Minor)", "CAD", "Canadian Dollar", "CHF", "Swiss Franc", "Canadian Dollar vs Swiss Franc"),
        ("NZDJPY", "Forex (Minor)", "NZD", "New Zealand Dollar", "JPY", "Japanese Yen", "New Zealand Dollar vs Japanese Yen"),
        ("NZDCHF", "Forex (Minor)", "NZD", "New Zealand Dollar", "CHF", "Swiss Franc", "New Zealand Dollar vs Swiss Franc"),
        ("NZDCAD", "Forex (Minor)", "NZD", "New Zealand Dollar", "CAD", "Canadian Dollar", "New Zealand Dollar vs Canadian Dollar"),
        ("USDHKD", "Forex (Exotic)", "USD", "US Dollar", "HKD", "Hong Kong Dollar", "US Dollar vs Hong Kong Dollar"),
        ("USDSGD", "Forex (Exotic)", "USD", "US Dollar", "SGD", "Singapore Dollar", "US Dollar vs Singapore Dollar"),
        ("USDTRY", "Forex (Exotic)", "USD", "US Dollar", "TRY", "Turkish Lira", "US Dollar vs Turkish Lira"),
        ("USDMXN", "Forex (Exotic)", "USD", "US Dollar", "MXN", "Mexican Peso", "US Dollar vs Mexican Peso"),
        ("USDZAR", "Forex (Exotic)", "USD", "US Dollar", "ZAR", "South African Rand", "US Dollar vs South African Rand"),
        ("USDSEK", "Forex (Exotic)", "USD", "US Dollar", "SEK", "Swedish Krona", "US Dollar vs Swedish Krona"),
        ("USDNOK", "Forex (Exotic)", "USD", "US Dollar", "NOK", "Norwegian Krone", "US Dollar vs Norwegian Krone"),
        ("USDDKK", "Forex (Exotic)", "USD", "US Dollar", "DKK", "Danish Krone", "US Dollar vs Danish Krone"),
        ("USDCNH", "Forex (Exotic)", "USD", "US Dollar", "CNH", "Offshore Chinese Yuan", "US Dollar vs Offshore Chinese Yuan"),
        ("USDTHB", "Forex (Exotic)", "USD", "US Dollar", "THB", "Thai Baht", "US Dollar vs Thai Baht"),
        ("USDRUB", "Forex (Exotic)", "USD", "US Dollar", "RUB", "Russian Ruble", "US Dollar vs Russian Ruble"),
        ("USDPLN", "Forex (Exotic)", "USD", "US Dollar", "PLN", "Polish Zloty", "US Dollar vs Polish Zloty"),
        ("USDHUF", "Forex (Exotic)", "USD", "US Dollar", "HUF", "Hungarian Forint", "US Dollar vs Hungarian Forint"),
        ("USDSAR", "Forex (Exotic)", "USD", "US Dollar", "SAR", "Saudi Riyal", "US Dollar vs Saudi Riyal"),
        ("USDILS", "Forex (Exotic)", "USD", "US Dollar", "ILS", "Israeli New Shekel", "US Dollar vs Israeli New Shekel"),
        ("EURTRY", "Forex (Exotic)", "EUR", "Euro", "TRY", "Turkish Lira", "Euro vs Turkish Lira"),
        ("EURSEK", "Forex (Exotic)", "EUR", "Euro", "SEK", "Swedish Krona", "Euro vs Swedish Krona"),
        ("EURNOK", "Forex (Exotic)", "EUR", "Euro", "NOK", "Norwegian Krone", "Euro vs Norwegian Krone"),
        ("EURZAR", "Forex (Exotic)", "EUR", "Euro", "ZAR", "South African Rand", "Euro vs South African Rand"),
        ("EURHUF", "Forex (Exotic)", "EUR", "Euro", "HUF", "Hungarian Forint", "Euro vs Hungarian Forint"),
        ("EURPLN", "Forex (Exotic)", "EUR", "Euro", "PLN", "Polish Zloty", "Euro vs Polish Zloty"),
        ("GBPMXN", "Forex (Exotic)", "GBP", "British Pound", "MXN", "Mexican Peso", "British Pound vs Mexican Peso"),
        ("SGDJPY", "Forex (Exotic)", "SGD", "Singapore Dollar", "JPY", "Japanese Yen", "Singapore Dollar vs Japanese Yen"),
        ("NOKJPY", "Forex (Exotic)", "NOK", "Norwegian Krone", "JPY", "Japanese Yen", "Norwegian Krone vs Japanese Yen"),
        ("SEKJPY", "Forex (Exotic)", "SEK", "Swedish Krona", "JPY", "Japanese Yen", "Swedish Krona vs Japanese Yen"),
        ("GBPZAR", "Forex (Exotic)", "GBP", "British Pound", "ZAR", "South African Rand", "British Pound vs South African Rand"),
        ("EURMXN", "Forex (Exotic)", "EUR", "Euro", "MXN", "Mexican Peso", "Euro vs Mexican Peso"),
        ("EURDKK", "Forex (Exotic)", "EUR", "Euro", "DKK", "Danish Krone", "Euro vs Danish Krone"),
        ("EURHKD", "Forex (Exotic)", "EUR", "Euro", "HKD", "Hong Kong Dollar", "Euro vs Hong Kong Dollar"),
        ("GBPNOK", "Forex (Exotic)", "GBP", "British Pound", "NOK", "Norwegian Krone", "British Pound vs Norwegian Krone"),
        ("EURCZK", "Forex (Exotic)", "EUR", "Euro", "CZK", "Czech Koruna", "Euro vs Czech Koruna"),
        ("NZDSGD", "Forex (Exotic)", "NZD", "New Zealand Dollar", "SGD", "Singapore Dollar", "New Zealand Dollar vs Singapore Dollar"),
        ("USDCZK", "Forex (Exotic)", "USD", "US Dollar", "CZK", "Czech Koruna", "US Dollar vs Czech Koruna"),
        ("GBPSGD", "Forex (Exotic)", "GBP", "British Pound", "SGD", "Singapore Dollar", "British Pound vs Singapore Dollar"),
        ("AUDSGD", "Forex (Exotic)", "AUD", "Australian Dollar", "SGD", "Singapore Dollar", "Australian Dollar vs Singapore Dollar"),
        ("AUDZAR", "Forex (Exotic)", "AUD", "Australian Dollar", "ZAR", "South African Rand", "Australian Dollar vs South African Rand"),
        ("CADMXN", "Forex (Exotic)", "CAD", "Canadian Dollar", "MXN", "Mexican Peso", "Canadian Dollar vs Mexican Peso"),
        ("CHFSGD", "Forex (Exotic)", "CHF", "Swiss Franc", "SGD", "Singapore Dollar", "Swiss Franc vs Singapore Dollar"),
        ("EURCNH", "Forex (Exotic)", "EUR", "Euro", "CNH", "Offshore Chinese Yuan", "Euro vs Offshore Chinese Yuan"),
        ("EURSGD", "Forex (Exotic)", "EUR", "Euro", "SGD", "Singapore Dollar", "Euro vs Singapore Dollar"),
        ("GBPDKK", "Forex (Exotic)", "GBP", "British Pound", "DKK", "Danish Krone", "British Pound vs Danish Krone"),
        ("GBPTRY", "Forex (Exotic)", "GBP", "British Pound", "TRY", "Turkish Lira", "British Pound vs Turkish Lira"),
        ("NOKSEK", "Forex (Exotic)", "NOK", "Norwegian Krone", "SEK", "Swedish Krona", "Norwegian Krone vs Swedish Krona"),
        ("NZDSEK", "Forex (Exotic)", "NZD", "New Zealand Dollar", "SEK", "Swedish Krona", "New Zealand Dollar vs Swedish Krona"),
        ("GBPSEK", "Forex (Exotic)", "GBP", "British Pound", "SEK", "Swedish Krona", "British Pound vs Swedish Krona"),
        ("AUDDKK", "Forex (Exotic)", "AUD", "Australian Dollar", "DKK", "Danish Krone", "Australian Dollar vs Danish Krone"),
        ("AUDHUF", "Forex (Exotic)", "AUD", "Australian Dollar", "HUF", "Hungarian Forint", "Australian Dollar vs Hungarian Forint"),
        ("AUDNOK", "Forex (Exotic)", "AUD", "Australian Dollar", "NOK", "Norwegian Krone", "Australian Dollar vs Norwegian Krone"),
        ("AUDPLN", "Forex (Exotic)", "AUD", "Australian Dollar", "PLN", "Polish Zloty", "Australian Dollar vs Polish Zloty"),
        ("CADSGD", "Forex (Exotic)", "CAD", "Canadian Dollar", "SGD", "Singapore Dollar", "Canadian Dollar vs Singapore Dollar"),
        ("CHFDKK", "Forex (Exotic)", "CHF", "Swiss Franc", "DKK", "Danish Krone", "Swiss Franc vs Danish Krone"),
        ("CHFHUF", "Forex (Exotic)", "CHF", "Swiss Franc", "HUF", "Hungarian Forint", "Swiss Franc vs Hungarian Forint"),
        ("CHFNOK", "Forex (Exotic)", "CHF", "Swiss Franc", "NOK", "Norwegian Krone", "Swiss Franc vs Norwegian Krone"),
        ("CHFPLN", "Forex (Exotic)", "CHF", "Swiss Franc", "PLN", "Polish Zloty", "Swiss Franc vs Polish Zloty"),
        ("CHFSEK", "Forex (Exotic)", "CHF", "Swiss Franc", "SEK", "Swedish Krona", "Swiss Franc vs Swedish Krona"),
        ("CNHJPY", "Forex (Exotic)", "CNH", "Offshore Chinese Yuan", "JPY", "Japanese Yen", "Offshore Chinese Yuan vs Japanese Yen"),
        ("EURILS", "Forex (Exotic)", "EUR", "Euro", "ILS", "Israeli New Shekel", "Euro vs Israeli New Shekel"),
        ("GBPCNH", "Forex (Exotic)", "GBP", "British Pound", "CNH", "Offshore Chinese Yuan", "British Pound vs Offshore Chinese Yuan"),
        ("GBPHUF", "Forex (Exotic)", "GBP", "British Pound", "HUF", "Hungarian Forint", "British Pound vs Hungarian Forint"),
        ("MXNJPY", "Forex (Exotic)", "MXN", "Mexican Peso", "JPY", "Japanese Yen", "Mexican Peso vs Japanese Yen"),
        ("NZDCNH", "Forex (Exotic)", "NZD", "New Zealand Dollar", "CNH", "Offshore Chinese Yuan", "New Zealand Dollar vs Offshore Chinese Yuan"),
        ("NZDHUF", "Forex (Exotic)", "NZD", "New Zealand Dollar", "HUF", "Hungarian Forint", "New Zealand Dollar vs Hungarian Forint"),
        ("USDBRL", "Forex (Exotic)", "USD", "US Dollar", "BRL", "Brazilian Real", "US Dollar vs Brazilian Real"),
        ("USDCLP", "Forex (Exotic)", "USD", "US Dollar", "CLP", "Chilean Peso", "US Dollar vs Chilean Peso"),
        ("USDCOP", "Forex (Exotic)", "USD", "US Dollar", "COP", "Colombian Peso", "US Dollar vs Colombian Peso"),
        ("USDIDR", "Forex (Exotic)", "USD", "US Dollar", "IDR", "Indonesian Rupiah", "US Dollar vs Indonesian Rupiah"),
        ("USDINR", "Forex (Exotic)", "USD", "US Dollar", "INR", "Indian Rupee", "US Dollar vs Indian Rupee"),
        ("USDKRW", "Forex (Exotic)", "USD", "US Dollar", "KRW", "South Korean Won", "US Dollar vs South Korean Won"),
        ("USDRON", "Forex (Exotic)", "USD", "US Dollar", "RON", "Romanian Leu", "US Dollar vs Romanian Leu"),
        ("USDTWD", "Forex (Exotic)", "USD", "US Dollar", "TWD", "New Taiwan Dollar", "US Dollar vs New Taiwan Dollar"),
        ("ZARJPY", "Forex (Exotic)", "ZAR", "South African Rand", "JPY", "Japanese Yen", "South African Rand vs Japanese Yen"),
    ]
    index_data = [
        ("US500", "Index (AMER) Equity", "US500", "S&P 500", "USD", "US Dollar", "S&P 500 vs US Dollar"),
        ("US30", "Index (AMER) Equity", "US30", "Dow Jones Industrial Average", "USD", "US Dollar", "Dow Jones Industrial Average vs US Dollar"),
        ("NAS100", "Index (AMER) Equity", "NAS100", "Nasdaq 100", "USD", "US Dollar", "Nasdaq 100 vs US Dollar"),
        ("US2000", "Index (AMER) Equity", "US2000", "Russell 2000", "USD", "US Dollar", "Russell 2000 vs US Dollar"),
        ("US400", "Index (AMER) Equity", "US400", "S&P MidCap 400", "USD", "US Dollar", "S&P MidCap 400 vs US Dollar"),
        ("CA60", "Index (AMER) Equity", "CA60", "S&P/TSX 60", "CAD", "Canadian Dollar", "S&P/TSX 60 vs Canadian Dollar"),
        ("VIX", "Index (AMER) Equity", "VIX", "CBOE Volatility Index", "USD", "US Dollar", "CBOE Volatility Index vs US Dollar"),
        ("BRA60", "Index (AMER) Equity", "BRA60", "Bovespa Index", "BRL", "Brazilian Real", "Bovespa Index vs Brazilian Real"),
        ("MEX35", "Index (AMER) Equity", "MEX35", "IPC Index", "MXN", "Mexican Peso", "IPC Index vs Mexican Peso"),
        ("GER40", "Index (EMEA) Equity", "GER40", "DAX 40", "EUR", "Euro", "DAX 40 vs Euro"),
        ("FRA40", "Index (EMEA) Equity", "FRA40", "CAC 40", "EUR", "Euro", "CAC 40 vs Euro"),
        ("UK100", "Index (EMEA) Equity", "UK100", "FTSE 100", "GBP", "British Pound", "FTSE 100 vs British Pound"),
        ("STOXX50", "Index (EMEA) Equity", "STOXX50", "EURO STOXX 50", "EUR", "Euro", "EURO STOXX 50 vs Euro"),
        ("IT40", "Index (EMEA) Equity", "IT40", "FTSE MIB", "EUR", "Euro", "FTSE MIB vs Euro"),
        ("SPA35", "Index (EMEA) Equity", "SPA35", "IBEX 35", "EUR", "Euro", "IBEX 35 vs Euro"),
        ("SWI20", "Index (EMEA) Equity", "SWI20", "Swiss Market Index", "CHF", "Swiss Franc", "Swiss Market Index vs Swiss Franc"),
        ("NETH25", "Index (EMEA) Equity", "NETH25", "AEX Index", "EUR", "Euro", "AEX Index vs Euro"),
        ("SE30", "Index (EMEA) Equity", "SE30", "OMX Stockholm 30", "SEK", "Swedish Krona", "OMX Stockholm 30 vs Swedish Krona"),
        ("NOR25", "Index (EMEA) Equity", "NOR25", "OBX Index", "NOK", "Norwegian Krone", "OBX Index vs Norwegian Krone"),
        ("SA40", "Index (EMEA) Equity", "SA40", "FTSE/JSE Top 40", "ZAR", "South African Rand", "FTSE/JSE Top 40 vs South African Rand"),
        ("TECDE30", "Index (EMEA) Equity", "TECDE30", "TecDAX", "EUR", "Euro", "TecDAX vs Euro"),
        ("MIDDE60", "Index (EMEA) Equity", "MIDDE60", "MDAX", "EUR", "Euro", "MDAX vs Euro"),
        ("PL20", "Index (EMEA) Equity", "PL20", "WIG20", "PLN", "Polish Zloty", "WIG20 vs Polish Zloty"),
        ("JP225", "Index (APAC) Equity", "JP225", "Nikkei 225", "JPY", "Japanese Yen", "Nikkei 225 vs Japanese Yen"),
        ("AUS200", "Index (APAC) Equity", "AUS200", "S&P/ASX 200", "AUD", "Australian Dollar", "S&P/ASX 200 vs Australian Dollar"),
        ("HK50", "Index (APAC) Equity", "HK50", "Hang Seng Index", "HKD", "Hong Kong Dollar", "Hang Seng Index vs Hong Kong Dollar"),
        ("CHINAH", "Index (APAC) Equity", "CHINAH", "Hang Seng China Enterprises Index", "HKD", "Hong Kong Dollar", "Hang Seng China Enterprises Index vs Hong Kong Dollar"),
        ("CN50", "Index (APAC) Equity", "CN50", "FTSE China A50", "USD", "US Dollar", "FTSE China A50 vs US Dollar"),
        ("HSTECH", "Index (APAC) Equity", "HSTECH", "Hang Seng Tech Index", "HKD", "Hong Kong Dollar", "Hang Seng Tech Index vs Hong Kong Dollar"),
        ("SCI25", "Index (APAC) Equity", "SCI25", "MSCI Singapore Index", "SGD", "Singapore Dollar", "MSCI Singapore Index vs Singapore Dollar"),
        ("TWN", "Index (APAC) Equity", "TWN", "MSCI Taiwan Index", "USD", "US Dollar", "MSCI Taiwan Index vs US Dollar"),
        ("INDIA50", "Index (APAC) Equity", "INDIA50", "Nifty 50", "USD", "US Dollar", "Nifty 50 vs US Dollar"),
        ("USDX", "Index (AMER) Currency", "USD", "US Dollar Index", "INDEX", "Index Points", "US Dollar Index vs Index Points"),
        ("EURX", "Index (EMEA) Currency", "EUR", "Euro Index", "INDEX", "Index Points", "Euro Index vs Index Points"),
        ("JPYX", "Index (APAC) Currency", "JPY", "Japanese Yen Index", "INDEX", "Index Points", "Japanese Yen Index vs Index Points"),
        ("GBPX", "Index (EMEA) Currency", "GBP", "British Pound Index", "INDEX", "Index Points", "British Pound Index vs Index Points"),
        ("AUDX", "Index (APAC) Currency", "AUD", "Australian Dollar Index", "INDEX", "Index Points", "Australian Dollar Index vs Index Points"),
        ("CADX", "Index (AMER) Currency", "CAD", "Canadian Dollar Index", "INDEX", "Index Points", "Canadian Dollar Index vs Index Points"),
        ("CHFX", "Index (EMEA) Currency", "CHF", "Swiss Franc Index", "INDEX", "Index Points", "Swiss Franc Index vs Index Points"),
        ("NZDX", "Index (APAC) Currency", "NZD", "New Zealand Dollar Index", "INDEX", "Index Points", "New Zealand Dollar Index vs Index Points"),
    ]
    crypto_data = [
        ("BTCUSD", "Crypto (Major)", "BTC", "Bitcoin", "USD", "US Dollar", "Bitcoin vs US Dollar"),
        ("BTCEUR", "Crypto (Major)", "BTC", "Bitcoin", "EUR", "Euro", "Bitcoin vs Euro"),
        ("BTCGBP", "Crypto (Major)", "BTC", "Bitcoin", "GBP", "British Pound", "Bitcoin vs British Pound"),
        ("BTCAUD", "Crypto (Major)", "BTC", "Bitcoin", "AUD", "Australian Dollar", "Bitcoin vs Australian Dollar"),
        ("ETHUSD", "Crypto (Major)", "ETH", "Ethereum", "USD", "US Dollar", "Ethereum vs US Dollar"),
        ("ETHEUR", "Crypto (Major)", "ETH", "Ethereum", "EUR", "Euro", "Ethereum vs Euro"),
        ("ETHGBP", "Crypto (Major)", "ETH", "Ethereum", "GBP", "British Pound", "Ethereum vs British Pound"),
        ("ETHAUD", "Crypto (Major)", "ETH", "Ethereum", "AUD", "Australian Dollar", "Ethereum vs Australian Dollar"),
        ("SOLUSD", "Crypto (Minor)", "SOL", "Solana", "USD", "US Dollar", "Solana vs US Dollar"),
        ("ADAUSD", "Crypto (Minor)", "ADA", "Cardano", "USD", "US Dollar", "Cardano vs US Dollar"),
        ("DOTUSD", "Crypto (Minor)", "DOT", "Polkadot", "USD", "US Dollar", "Polkadot vs US Dollar"),
        ("AVAXUSD", "Crypto (Minor)", "AVAX", "Avalanche", "USD", "US Dollar", "Avalanche vs US Dollar"),
        ("XRPUSD", "Crypto (Minor)", "XRP", "Ripple", "USD", "US Dollar", "Ripple vs US Dollar"),
        ("LINKUSD", "Crypto (Minor)", "LINK", "Chainlink", "USD", "US Dollar", "Chainlink vs US Dollar"),
        ("LTCUSD", "Crypto (Minor)", "LTC", "Litecoin", "USD", "US Dollar", "Litecoin vs US Dollar"),
        ("BCHUSD", "Crypto (Minor)", "BCH", "Bitcoin Cash", "USD", "US Dollar", "Bitcoin Cash vs US Dollar"),
        ("XLMUSD", "Crypto (Minor)", "XLM", "Stellar", "USD", "US Dollar", "Stellar vs US Dollar"),
        ("UNIUSD", "Crypto (Minor)", "UNI", "Uniswap", "USD", "US Dollar", "Uniswap vs US Dollar"),
        ("BNBUSD", "Crypto (Minor)", "BNB", "Binance Coin", "USD", "US Dollar", "Binance Coin vs US Dollar"),
        ("TRXUSD", "Crypto (Minor)", "TRX", "Tron", "USD", "US Dollar", "Tron vs US Dollar"),
        ("TONUSD", "Crypto (Minor)", "TON", "Toncoin", "USD", "US Dollar", "Toncoin vs US Dollar"),
        ("MATICUSD", "Crypto (Minor)", "POL", "Polygon", "USD", "US Dollar", "Polygon vs US Dollar"),
        ("APTUSD", "Crypto (Minor)", "APT", "Aptos", "USD", "US Dollar", "Aptos vs US Dollar"),
        ("SUIUSD", "Crypto (Minor)", "SUI", "Sui", "USD", "US Dollar", "Sui vs US Dollar"),
        ("NEARUSD", "Crypto (Minor)", "NEAR", "NEAR Protocol", "USD", "US Dollar", "NEAR Protocol vs US Dollar"),
        ("RENDERUSD", "Crypto (Minor)", "RENDER", "Render Token", "USD", "US Dollar", "Render Token vs US Dollar"),
        ("FETUSD", "Crypto (Minor)", "FET", "Artificial Superintelligence Alliance", "USD", "US Dollar", "FET vs US Dollar"),
        ("HBARUSD", "Crypto (Minor)", "HBAR", "Hedera", "USD", "US Dollar", "Hedera vs US Dollar"),
        ("INJUSD", "Crypto (Minor)", "INJ", "Injective", "USD", "US Dollar", "Injective vs US Dollar"),
        ("AAVEUSD", "Crypto (Minor)", "AAVE", "Aave", "USD", "US Dollar", "Aave vs US Dollar"),
        ("JUPUSD", "Crypto (Minor)", "JUP", "Jupiter", "USD", "US Dollar", "Jupiter vs US Dollar"),
        ("ONDOUSD", "Crypto (Minor)", "ONDO", "Ondo", "USD", "US Dollar", "Ondo vs US Dollar"),
        ("DOGEUSD", "Crypto (Exotic)", "DOGE", "Dogecoin", "USD", "US Dollar", "Dogecoin vs US Dollar"),
        ("SHBUSD", "Crypto (Exotic)", "SHIB", "Shiba Inu", "USD", "US Dollar", "Shiba Inu vs US Dollar"),
        ("PEPUSD", "Crypto (Exotic)", "PEPE", "Pepe", "USD", "US Dollar", "Pepe vs US Dollar"),
        ("WIFUSD", "Crypto (Exotic)", "WIF", "dogwifhat", "USD", "US Dollar", "dogwifhat vs US Dollar"),
        ("BONKUSD", "Crypto (Exotic)", "BONK", "Bonk", "USD", "US Dollar", "Bonk vs US Dollar"),
        ("FLOKIUSD", "Crypto (Exotic)", "FLOKI", "Floki", "USD", "US Dollar", "Floki vs US Dollar"),
        ("TRUMPUSD", "Crypto (Exotic)", "TRUMP", "MAGA TRUMP", "USD", "US Dollar", "MAGA TRUMP vs US Dollar"),
        ("PAXGUSD", "Crypto (Exotic)", "PAXG", "Pax Gold", "USD", "US Dollar", "Pax Gold vs US Dollar"),
        ("XAUTUSD", "Crypto (Exotic)", "XAUT", "Tether Gold", "USD", "US Dollar", "Tether Gold vs US Dollar")
    ]
    metal_data = [
        ("XAUUSD", "Metal (Major)", "XAU", "Gold", "USD", "US Dollar", "Gold vs US Dollar"),
        ("XAUEUR", "Metal (Major)", "XAU", "Gold", "EUR", "Euro", "Gold vs Euro"),
        ("XAGUSD", "Metal (Major)", "XAG", "Silver", "USD", "US Dollar", "Silver vs US Dollar"),
        ("XAGEUR", "Metal (Major)", "XAG", "Silver", "EUR", "Euro", "Silver vs Euro"),
        ("XPTUSD", "Metal (Major)", "XPT", "Platinum", "USD", "US Dollar", "Platinum vs US Dollar"),
        ("XPDUSD", "Metal (Major)", "XPD", "Palladium", "USD", "US Dollar", "Palladium vs US Dollar"),
        ("XAUAUD", "Metal (Minor)", "XAU", "Gold", "AUD", "Australian Dollar", "Gold vs Australian Dollar"),
        ("XAUCHF", "Metal (Minor)", "XAU", "Gold", "CHF", "Swiss Franc", "Gold vs Swiss Franc"),
        ("XAUGBP", "Metal (Minor)", "XAU", "Gold", "GBP", "British Pound", "Gold vs British Pound"),
        ("XAUJPY", "Metal (Minor)", "XAU", "Gold", "JPY", "Japanese Yen", "Gold vs Japanese Yen"),
        ("XAUSGD", "Metal (Minor)", "XAU", "Gold", "SGD", "Singapore Dollar", "Gold vs Singapore Dollar"),
        ("XAUCNH", "Metal (Minor)", "XAU", "Gold", "CNH", "Offshore Chinese Yuan", "Gold vs Offshore Chinese Yuan"),
        ("XAUTHB", "Metal (Minor)", "XAU", "Gold", "THB", "Thai Baht", "Gold vs Thai Baht"),
        ("XAGAUD", "Metal (Minor)", "XAG", "Silver", "AUD", "Australian Dollar", "Silver vs Australian Dollar"),
        ("XAGSGD", "Metal (Minor)", "XAG", "Silver", "SGD", "Singapore Dollar", "Silver vs Singapore Dollar")
    ]
    energy_data = [
        ("XBRUSD", "Energy (Major)", "XBR", "Brent Crude Oil", "USD", "US Dollar", "Brent Crude Oil vs US Dollar"),
        ("XTIUSD", "Energy (Major)", "XTI", "WTI Crude Oil", "USD", "US Dollar", "WTI Crude Oil vs US Dollar"),
        ("XNGUSD", "Energy (Major)", "XNG", "Natural Gas", "USD", "US Dollar", "Natural Gas vs US Dollar"),
        ("XRBUSD", "Energy (Minor)", "XRB", "RBOB Gasoline", "USD", "US Dollar", "RBOB Gasoline vs US Dollar"),
        ("XHOUSD", "Energy (Minor)", "XHO", "Heating Oil", "USD", "US Dollar", "Heating Oil vs US Dollar")
    ]
    stock_all_data = []
    all_ticker_rows = []
    for uid, cat, base_asset, base_name, quote_asset, quote_name, desc in forex_data + index_data + crypto_data + metal_data + energy_data + stock_all_data:
        all_ticker_rows.append({
            TickerAPI.ID.UID: uid, TickerAPI.ID.Category: cat, TickerAPI.ID.BaseAsset: base_asset, TickerAPI.ID.BaseName: base_name,
            TickerAPI.ID.QuoteAsset: quote_asset, TickerAPI.ID.QuoteName: quote_name, TickerAPI.ID.Description: desc
        })
    UniverseAPI.push_tickers(db, pl.DataFrame(all_ticker_rows))
    providers = [f"{p.name} ({provider_map[p][1].name})" for p in Provider]
    contract_rows = []
    security_rows = []
    for uid, cat, _, _, _, _, _ in forex_data + index_data + crypto_data + metal_data + energy_data + stock_all_data:
        inst = TickerAPI.detect(uid)
        if inst == ContractType.Spot and "Forex" not in cat:
            inst = ContractType.CFD
        inst_name = inst.name
        for provider_uid in providers:
            contract_rows.append({ContractAPI.ID.Ticker: uid, ContractAPI.ID.Provider: provider_uid, ContractAPI.ID.Type: inst_name, ContractAPI.ID.Payoff: PayoffType.Trivial.name})
            security_rows.append({SecurityAPI.ID.Provider: provider_uid, SecurityAPI.ID.Category: cat, SecurityAPI.ID.Ticker: uid, SecurityAPI.ID.Contract: inst_name})
    UniverseAPI.push_contracts(db, pl.DataFrame(contract_rows))
    contracts_df = UniverseAPI.pull_contracts(db)
    contract_map = {}
    for row in contracts_df.iter_rows(named=True):
        contract_map[(row[ContractAPI.ID.Ticker], row[ContractAPI.ID.Provider])] = row[ContractAPI.ID.UID]
    for idx, row in enumerate(security_rows):
        key = (row[SecurityAPI.ID.Ticker], row[SecurityAPI.ID.Provider])
        if key in contract_map:
            security_rows[idx][SecurityAPI.ID.Contract] = contract_map[key]
    UniverseAPI.push_securities(db, pl.DataFrame(security_rows))
    timeframes = [
        "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M15", "M20", "M30", "M45",
        "H1", "H2", "H3", "H4", "H6", "H8", "H12",
        "D1", "D2", "D3",
        "W1", "MN1"
    ]
    UniverseAPI.push_timeframes(db, pl.DataFrame([{TimeframeAPI.ID.UID: tf} for tf in timeframes]))