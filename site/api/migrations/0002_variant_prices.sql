-- Supplier options (studio rules ג, 2026-10-11, "כל האפשרויות של הספק בדף המוצר"): every SKU of a product is a variant
-- with its own price, cost and shipping. Additive: NULL in a new column = the product's value (products without options
-- keep one variant, '<product id>:default', that leaves them NULL).
ALTER TABLE product_variants ADD COLUMN option_label_he TEXT;                 -- "בז', 45×45 ס"מ"; NULL without options
ALTER TABLE product_variants ADD COLUMN retail_agorot INTEGER CHECK (retail_agorot IS NULL OR retail_agorot > 0);
ALTER TABLE product_variants ADD COLUMN unit_retail_agorot INTEGER CHECK (unit_retail_agorot IS NULL OR unit_retail_agorot > 0);
ALTER TABLE product_variants ADD COLUMN price_provisional INTEGER;
ALTER TABLE product_variants ADD COLUMN unit_price_estimated INTEGER;
ALTER TABLE product_variants ADD COLUMN cost_usd_cents INTEGER CHECK (cost_usd_cents IS NULL OR cost_usd_cents >= 0);
ALTER TABLE product_variants ADD COLUMN shipping_usd_cents INTEGER CHECK (shipping_usd_cents IS NULL OR shipping_usd_cents >= 0);
ALTER TABLE product_variants ADD COLUMN in_room INTEGER NOT NULL DEFAULT 0;   -- the option the room shows (default_sku)
