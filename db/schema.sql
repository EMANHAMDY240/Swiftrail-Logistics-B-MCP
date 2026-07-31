CREATE TABLE employees (
    id     INT PRIMARY KEY AUTO_INCREMENT,
    name   VARCHAR(100) NOT NULL,
    email  VARCHAR(150) NOT NULL UNIQUE,
    role   ENUM('sales_rep', 'finance_manager') NOT NULL
);

CREATE TABLE customers (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    name          VARCHAR(150) NOT NULL,
    credit_limit  DECIMAL(12,2) NOT NULL CHECK (credit_limit >= 0),
    balance_due   DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (balance_due >= 0),
    credit_status ENUM('good', 'hold') NOT NULL DEFAULT 'good'
);

CREATE TABLE shipments (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    customer_id   INT NOT NULL,
    origin        VARCHAR(100) NOT NULL,
    destination   VARCHAR(100) NOT NULL,
    railcar_id    VARCHAR(50),
    base_rate     DECIMAL(12,2) NOT NULL CHECK (base_rate > 0),
    final_rate    DECIMAL(12,2),
    status        ENUM('pending','blocked','released','in_transit','delivered') NOT NULL DEFAULT 'pending',
    requested_by  INT NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (requested_by) REFERENCES employees(id)
);

CREATE TABLE invoices (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    customer_id   INT NOT NULL,
    shipment_id   INT UNIQUE,
    amount        DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    due_date      DATE NOT NULL,
    paid_status   ENUM('unpaid','paid','overdue') NOT NULL DEFAULT 'unpaid',
    days_overdue  INT NOT NULL DEFAULT 0 CHECK (days_overdue >= 0),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (shipment_id) REFERENCES shipments(id)
);

CREATE TABLE credit_holds (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    customer_id   INT NOT NULL,
    reason        VARCHAR(255) NOT NULL,
    severity      ENUM('minor','severe') NOT NULL,
    status        ENUM('active','released') NOT NULL DEFAULT 'active',
    placed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_by   INT,
    released_at   TIMESTAMP NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (released_by) REFERENCES employees(id)
);

CREATE TABLE rate_exceptions (
    id             INT PRIMARY KEY AUTO_INCREMENT,
    shipment_id    INT NOT NULL,
    requested_by   INT NOT NULL,
    discount_pct   DECIMAL(5,2) NOT NULL CHECK (discount_pct > 0 AND discount_pct <= 50),
    justification  TEXT NOT NULL CHECK (CHAR_LENGTH(justification) >= 20),
    status         ENUM('pending','auto_approved','approved','rejected') NOT NULL DEFAULT 'pending',
    approved_by    INT,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at    TIMESTAMP NULL,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id),
    FOREIGN KEY (requested_by) REFERENCES employees(id),
    FOREIGN KEY (approved_by) REFERENCES employees(id)
);