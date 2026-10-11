#!/usr/bin/env python3
"""Unit tests for the supplier options mapping (scripts/sourcing/options.py) and the AliExpress / CJ adapters.
No network, no credentials, no repo writes (cards are written to a temporary directory).

Run:  python3 -I scripts/sourcing/test_options.py
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "ae"))
import options  # noqa: E402
import cj_source  # noqa: E402
import ds  # noqa: E402


def ae_sku(sku_id, price, props, stock=10):
    return {"sku_id": sku_id, "offer_sale_price": str(price), "sku_price": str(price), "currency_code": "USD", "sku_available_stock": stock,
            "ae_sku_property_dtos": [{"sku_property_name": n, "property_value_definition_name": v, "sku_property_value": "x",
                                      "sku_image": img} for n, v, img in props]}


class MappingTests(unittest.TestCase):
    def test_aliexpress_axes_values_and_default(self):
        # the seller's "Color" holds sizes and "Size" holds colour temperatures: the values decide the axis
        skus = [ae_sku("1", 51.94, [("Lampshade Color", "16cm", "https://a/1.jpg"), ("Size", "Warm White 3000K", None)]),
                ae_sku("2", 60.10, [("Lampshade Color", "23cm", "https://a/2.jpg"), ("Size", "Warm White 3000K", None)]),
                ae_sku("3", 51.94, [("Lampshade Color", "16cm", "https://a/1.jpg"), ("Size", "Cold White 6000K", None)]),
                ae_sku("4", 99.00, [("Lampshade Color", "Contact us", None), ("Size", "Cold White 6000K", None)])]
        o, note = ds.ae_options({"result": {"ae_item_sku_info_dtos": skus}}, "1", {"1": {"amount": 1.99, "currency": "USD", "days": "6-15"}})
        self.assertEqual([a["id"] for a in o["axes"]], ["size", "other"])
        self.assertEqual([v["label_he"] for v in o["axes"][0]["values"]], ['16 ס"מ', '23 ס"מ'])
        self.assertEqual(o["axes"][1]["name_he"], "גוון אור")
        self.assertEqual({s["id"] for s in o["skus"]}, {"1", "2", "3"})  # "Contact us" is not a product
        self.assertIn("dropped 1", note)
        d = next(s for s in o["skus"] if s["id"] == "1")
        self.assertTrue(d["in_room"])
        self.assertEqual(d["shipping_il"]["amount"], 1.99)
        self.assertEqual(d["image"], "https://a/1.jpg")
        self.assertFalse(any(s["in_room"] for s in o["skus"] if s["id"] != "1"))
        self.assertEqual(options.validate(o), ([], []))

    def test_colors_sizes_order_and_hebrew(self):
        rows = [{"id": str(i), "props": [("Color", c, None), ("Size", s, None)], "price": p, "currency": "USD"}
                for i, (c, s, p) in enumerate([("Light Camel", "60X60cm", 14), ("Beige", "45X45cm", 11), ("Beige", "30X50cm", 10),
                                               ("Light Camel", "45X45cm", 11)])]
        o, _ = options.from_variants(rows, "1")
        color, size = o["axes"]
        self.assertEqual(color["id"], "color")
        self.assertEqual([v["label_he"] for v in color["values"]], ["קאמל בהיר", "בז'"])
        self.assertTrue(all(options.HEX.match(v["hex"]) for v in color["values"]))
        self.assertEqual([v["id"] for v in size["values"]], ["30x50", "45x45", "60x60"])  # numeric order
        self.assertEqual(o["default_sku"], "1")

    def test_single_value_axes_ship_from_and_plug_are_not_choices(self):
        rows = [{"id": "a", "props": [("Ships From", "China", None), ("Plug", "EU", None), ("Color", "Tulle", None), ("Size", "S", None)], "price": 5},
                {"id": "b", "props": [("Ships From", "China", None), ("Plug", "EU", None), ("Color", "Tulle", None), ("Size", "L", None)], "price": 6},
                {"id": "c", "props": [("Ships From", "Spain", None), ("Plug", "EU", None), ("Color", "Tulle", None), ("Size", "L", None)], "price": 9},
                {"id": "d", "props": [("Ships From", "China", None), ("Plug", "US", None), ("Color", "Tulle", None), ("Size", "L", None)], "price": 5}]
        o, _ = options.from_variants(rows, "a")
        self.assertEqual([a["id"] for a in o["axes"]], ["size"])
        self.assertEqual([s["id"] for s in o["skus"]], ["a", "b"])

    def test_no_options_for_a_single_sku_or_an_unknown_default(self):
        one = [{"id": "a", "props": [("Color", "Black", None)], "price": 5}]
        self.assertEqual(options.from_variants(one, "a")[0], None)
        two = one + [{"id": "b", "props": [("Color", "White", None)], "price": 5}]
        o, why = options.from_variants(two, "zzz")
        self.assertIsNone(o)
        self.assertIn("not in the supplier's SKU list", why)

    def test_cj_keys_split_from_the_right_and_default_variant(self):
        payload = {"pid": "P1", "variants": [
            {"vid": "2605300823551604611", "variantSku": "CJX01-A", "variantKey": "Off-White-L", "variantSellPrice": 3.5, "variantImage": "https://c/1.jpg"},
            {"vid": "2605300823551604612", "variantSku": "CJX01-B", "variantKey": "Off-White-S", "variantSellPrice": 2.5},
            {"vid": "2605300823551604613", "variantSku": "CJX01-C", "variantKey": "Black-L", "variantSellPrice": 3.5}]}
        parts, names = cj_source.split_keys(payload)
        self.assertEqual(parts[0], ["Off-White", "L"])
        card = {"id": "x", "supplier": {"sku": "CJX01"}, "price": {"cost": 2.5}, "notes": "recommended vid 2605300823551604612 ('Off-White-S'), $2.5"}
        self.assertEqual(cj_source.default_variant(card, payload), ("CJX01-B", "notes vid"))
        o, _ = cj_source.cj_options(card, payload, "x", "P1")
        self.assertEqual([a["id"] for a in o["axes"]], ["color", "size"])
        self.assertEqual(o["default_sku"], "CJX01-B")
        self.assertEqual(options.validate(o, card)[0], [])


class ValidateAndWriteTests(unittest.TestCase):
    def good(self):
        return {"axes": [{"id": "color", "name_he": "צבע", "values": [{"id": "beige", "label_he": "בז'", "hex": "#D9CBB3"},
                                                                     {"id": "white", "label_he": "לבן"}]}],
                "skus": [{"id": "1", "values": {"color": "beige"}, "price": {"amount": 4, "currency": "USD"}, "in_room": True},
                         {"id": "2", "values": {"color": "white"}, "price": {"amount": 4.5, "currency": "USD"}}],
                "default_sku": "1", "source": "api"}

    def test_validate_catches_typos_and_broken_references(self):
        self.assertEqual(options.validate(self.good())[0], [])
        bad = self.good()
        bad["axes"][0]["id"] = "colour"
        bad["skus"][1]["values"] = {"color": "ivory"}
        bad["skus"][1]["prise"] = 1
        bad["default_sku"] = "9"
        errs = options.validate(bad)[0]
        for needle in ("axes[0].id", "unknown key 'prise'", "options.default_sku", "no such axis"):
            self.assertTrue(any(needle in e for e in errs), (needle, errs))

    def test_write_splices_and_keeps_existing_options(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "card.json")
            text = '{\n  "id": "x",\n  "price": { "cost": 4, "currency": "USD" },\n  "status": "candidate",\n  "notes": null\n}'
            with open(p, "w") as f:
                f.write(text)
            self.assertEqual(options.write_options(p, self.good()), "written")
            with open(p) as f:
                new = f.read()
            self.assertIn('"price": { "cost": 4, "currency": "USD" },', new)  # the rest of the file is untouched
            self.assertLess(new.index('"options"'), new.index('"status"'))
            self.assertEqual(json.loads(new)["options"], self.good())
            other = self.good()
            other["default_sku"] = "2"
            other["skus"][0]["in_room"], other["skus"][1]["in_room"] = False, True
            self.assertEqual(options.write_options(p, other), "kept")  # curated options are never overwritten
            self.assertEqual(options.write_options(p, other, force=True), "written")
            manual = dict(self.good(), source="manual")
            self.assertEqual(options.write_options(p, manual, force=True), "written")
            self.assertEqual(options.write_options(p, self.good(), force=True), "kept")  # manual stays even with force


if __name__ == "__main__":
    unittest.main(verbosity=2)
