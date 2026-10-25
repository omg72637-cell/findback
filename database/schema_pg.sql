-- FindBack 2.0 PostgreSQL Schema
-- Strictly enforces foreign keys, column constraints, and category allowlists.

-- 1. Admin Users Table (Stores individual admin credentials; passwords hashed with Werkzeug)
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin', 'desk_staff')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Ordinary Items Table (Allowlist-restricted public items only)
CREATE TABLE IF NOT EXISTS ordinary_items (
    id SERIAL PRIMARY KEY,
    report_type TEXT NOT NULL CHECK (report_type IN ('lost', 'found')),
    category TEXT NOT NULL CHECK (category IN (
        'Water Bottles & Mugs',
        'Notebooks, Binders & Textbooks',
        'Umbrellas',
        'Eyeglasses & Sunglasses',
        'Non-Electronic Stationery',
        'Outerwear, Jackets & Scarves',
        'General Bags & Backpacks (Non-Electronic)'
    )),
    description TEXT NOT NULL,
    campus_location TEXT NOT NULL,
    date_discovered TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'handover_pending', 'resolved')),
    contact_email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Confidential Electronics Table (Private reports; NEVER exposed to public queries)
CREATE TABLE IF NOT EXISTS private_electronics (
    id SERIAL PRIMARY KEY,
    tracking_code TEXT UNIQUE NOT NULL,
    report_type TEXT NOT NULL CHECK (report_type IN ('lost', 'found')),
    device_type TEXT NOT NULL CHECK (device_type IN ('phone', 'laptop', 'tablet', 'earbuds', 'charger', 'smartwatch')),
    brand TEXT NOT NULL,
    model_family TEXT,
    primary_color TEXT NOT NULL,
    campus_location TEXT NOT NULL,
    date_discovered TEXT NOT NULL,
    distinctive_clues TEXT NOT NULL,
    reporter_contact TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'lead_identified', 'disputed', 'resolved')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Match Leads Table (Generated candidate matches between private lost and found records)
CREATE TABLE IF NOT EXISTS match_leads (
    id SERIAL PRIMARY KEY,
    lost_report_id INTEGER NOT NULL REFERENCES private_electronics(id),
    found_report_id INTEGER NOT NULL REFERENCES private_electronics(id),
    match_score INTEGER NOT NULL CHECK (match_score >= 0 AND match_score <= 100),
    score_breakdown_json TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending_review' CHECK (review_status IN ('pending_review', 'investigating', 'disputed', 'approved', 'dismissed')),
    admin_notes TEXT,
    assigned_admin_id INTEGER REFERENCES admin_users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(lost_report_id, found_report_id)
);

-- 5. Handover Logs Table (Audit trail of verified custody releases)
CREATE TABLE IF NOT EXISTS handover_logs (
    id SERIAL PRIMARY KEY,
    item_type TEXT NOT NULL CHECK (item_type IN ('ordinary', 'electronics')),
    item_id INTEGER NOT NULL,
    match_id INTEGER REFERENCES match_leads(id),
    token_hash TEXT NOT NULL,
    token_expires_at TEXT NOT NULL,
    token_used_at TEXT,
    admin_id INTEGER NOT NULL REFERENCES admin_users(id),
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
