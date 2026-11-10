-- S11, fixes from QA S6–S7 (qa/reports/2026-11-10-site-track-qa-s6-s7.md):
--   ת8: the line in the cart, the checkout, the order and the invoice is the base name without a colour · the Hebrew
--       option labels (manager's rule). The variant carries its line's base name; NULL keeps the product's name.
--   ת9: a part of a set of distinct SKUs (a print of a triptych other than the set's) is never sold on its own: the
--       server answers 422 for it, and for a single piece of such a set (its unit price is NULL).
--   ת11: a line whose product stopped being sold is removed from the cart, and the cart says so ("פריט אחד כבר לא זמין
--       והוסר"): the count of such lines, kept for the cart's life.
ALTER TABLE product_variants ADD COLUMN line_name_he TEXT;
ALTER TABLE product_variants ADD COLUMN set_part INTEGER NOT NULL DEFAULT 0 CHECK (set_part IN (0, 1));
ALTER TABLE carts ADD COLUMN removed_lines INTEGER NOT NULL DEFAULT 0 CHECK (removed_lines >= 0);
