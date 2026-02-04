CREATE TABLE IF NOT EXISTS ads_dabo_daily_sales (
  sale_date DATE NOT NULL,
  product_alias_code VARCHAR(80) NOT NULL,
  dabo_sales_qty INT NOT NULL DEFAULT 0,
  dabo_order_count INT NOT NULL DEFAULT 0,
  dabo_revenue DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (sale_date, product_alias_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS log_dabo_import (
  id BIGINT NOT NULL AUTO_INCREMENT,
  file_name VARCHAR(255) NOT NULL,
  file_path VARCHAR(500) NULL,
  records_total INT NOT NULL DEFAULT 0,
  records_after_filter INT NOT NULL DEFAULT 0,
  records_inserted INT NOT NULL DEFAULT 0,
  sku_match_rate DECIMAL(5,4) NULL,
  status VARCHAR(20) NOT NULL,
  message VARCHAR(1000) NULL,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_log_dabo_import_created_at (created_at),
  KEY idx_log_dabo_import_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
