PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    image_url TEXT,
    stock INTEGER NOT NULL DEFAULT 100,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    flower_type TEXT,
    bouquet_size TEXT,
    color_theme TEXT,
    card_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id, flower_type, bouquet_size, color_theme, card_message),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_amount REAL NOT NULL CHECK (total_amount >= 0),
    payment_method TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    delivery_address TEXT NOT NULL,
    delivery_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'Confirmed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    flower_type TEXT,
    bouquet_size TEXT,
    color_theme TEXT,
    card_message TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS special_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    person_name TEXT NOT NULL,
    event_date DATE NOT NULL,
    preferred_flower_package INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (preferred_flower_package) REFERENCES products(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    discount_percent REAL NOT NULL CHECK (discount_percent >= 0 AND discount_percent <= 100),
    product_id INTEGER,
    offer_link TEXT,
    expiry_date DATE NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

INSERT OR IGNORE INTO products (id, name, category, description, price, image_url, stock) VALUES
(1, 'Rose Romance Bouquet', 'Romantic', 'Red roses with baby''s breath and satin wrap.', 49.99, 'https://images.unsplash.com/photo-1519378058457-4c29a0a2efac?auto=format&fit=crop&w=1200&q=60', 50),
(2, 'Sunshine Tulip Basket', 'Birthday', 'Bright tulips arranged in a woven basket.', 39.50, 'https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=1200&q=60', 70),
(3, 'Pure White Lilies', 'Wedding', 'Elegant white lily bouquet for special moments.', 59.00, 'https://images.unsplash.com/photo-1468327768560-75b778cbb551?auto=format&fit=crop&w=1200&q=60', 40),
(4, 'Mixed Celebration Box', 'Anniversary', 'A colorful blend of seasonal flowers with custom card.', 45.75, 'https://images.unsplash.com/photo-1470509037663-253afd7f0f51?auto=format&fit=crop&w=1200&q=60', 60);
