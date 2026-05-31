-- Migration 002: Seed stock_info reference data
-- Date: 2026-05-31
-- Description: Populate initial stock_info with common Taiwan and US tickers

INSERT INTO stock_info (symbol, name, exchange, is_delisted, last_known_price, last_updated) VALUES
    -- Taiwan TWSE major stocks
    ('2330', '台積電',           'TWSE', FALSE, NULL, NULL),
    ('2317', '鴻海',             'TWSE', FALSE, NULL, NULL),
    ('2454', '聯發科',           'TWSE', FALSE, NULL, NULL),
    ('3008', '大立光',           'TWSE', FALSE, NULL, NULL),
    ('2308', '台達電',           'TWSE', FALSE, NULL, NULL),
    ('2412', '中華電',           'TWSE', FALSE, NULL, NULL),
    ('2891', '中信金',           'TWSE', FALSE, NULL, NULL),
    ('2881', '富邦金',           'TWSE', FALSE, NULL, NULL),
    ('2882', '國泰金',           'TWSE', FALSE, NULL, NULL),
    ('2892', '第一金',           'TWSE', FALSE, NULL, NULL),
    ('2002', '中鋼',             'TWSE', FALSE, NULL, NULL),
    ('1216', '統一',             'TWSE', FALSE, NULL, NULL),
    ('1707', '葡萄王',           'TWSE', FALSE, NULL, NULL),
    ('6505', '聯詠',             'TWSE', FALSE, NULL, NULL),
    ('2379', '瑞昱',             'TWSE', FALSE, NULL, NULL),
    ('3034', '聯詠',             'TWSE', FALSE, NULL, NULL),
    ('0050', '元大台灣50',       'TWSE', FALSE, NULL, NULL),
    ('0056', '元大高股息',       'TWSE', FALSE, NULL, NULL),
    ('00887', '街口中小型股',    'TPEx', FALSE, NULL, NULL),
    ('00881', '國泰5G',          'TPEx', FALSE, NULL, NULL),
    -- Taiwan OTC
    ('3105', '穩懋',             'TPEx', FALSE, NULL, NULL),
    ('3665', '天虹',             'TPEx', FALSE, NULL, NULL),
    -- US major stocks
    ('AAPL',  'Apple Inc.',              'NASDAQ', FALSE, NULL, NULL),
    ('MSFT',  'Microsoft Corp.',         'NASDAQ', FALSE, NULL, NULL),
    ('GOOGL', 'Alphabet Inc. Class A',   'NASDAQ', FALSE, NULL, NULL),
    ('GOOG',  'Alphabet Inc. Class C',   'NASDAQ', FALSE, NULL, NULL),
    ('AMZN',  'Amazon.com Inc.',         'NASDAQ', FALSE, NULL, NULL),
    ('NVDA',  'NVIDIA Corp.',            'NASDAQ', FALSE, NULL, NULL),
    ('META',  'Meta Platforms Inc.',      'NASDAQ', FALSE, NULL, NULL),
    ('TSLA',  'Tesla Inc.',              'NASDAQ', FALSE, NULL, NULL),
    ('BRK.B', 'Berkshire Hathaway B',    'NYSE',   FALSE, NULL, NULL),
    ('JPM',   'JPMorgan Chase & Co.',    'NYSE',   FALSE, NULL, NULL),
    ('V',     'Visa Inc.',               'NYSE',   FALSE, NULL, NULL),
    ('MA',    'Mastercard Inc.',         'NYSE',   FALSE, NULL, NULL),
    ('UNH',   'UnitedHealth Group',      'NYSE',   FALSE, NULL, NULL),
    ('HD',    'Home Depot Inc.',         'NYSE',   FALSE, NULL, NULL),
    ('PG',    'Procter & Gamble',        'NYSE',   FALSE, NULL, NULL),
    ('SPY',   'SPDR S&P 500 ETF',        'NYSE',   FALSE, NULL, NULL),
    ('QQQ',   'Invesco QQQ Trust',       'NASDAQ', FALSE, NULL, NULL),
    ('VTI',   'Vanguard Total Stock',    'NYSE',   FALSE, NULL, NULL),
    ('IWFG',  'iShares World FactSet',   'NYSE',   FALSE, NULL, NULL)
ON CONFLICT (symbol) DO UPDATE SET
    name          = EXCLUDED.name,
    exchange      = EXCLUDED.exchange,
    is_delisted   = EXCLUDED.is_delisted,
    last_updated  = NOW();