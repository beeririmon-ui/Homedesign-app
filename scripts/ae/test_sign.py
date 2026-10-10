#!/usr/bin/env python3
"""Unit tests for the AliExpress signature and envelope handling. No network, no credentials.

The sample App Secret "helloworld", the sample parameters and the expected signatures are the worked examples
from the official "HTTP request sample" page (doc 1385 / 1366):
https://openservice.aliexpress.com/doc/doc.htm#/?docId=1385
They are test fixtures only; they are not real credentials.

Run:  python3 -I scripts/ae/test_sign.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client  # noqa: E402

SAMPLE_SECRET = "helloworld"


class SignTests(unittest.TestCase):
    def test_system_api_sample_from_docs(self):
        # doc 1385, Case 2: /auth/token/create, api path prefixed, sorted key+value, HMAC-SHA256, upper hex
        params = {"app_key": "12345678", "timestamp": "1517820392000", "sign_method": "sha256",
                  "code": "3_500102_JxZ05Ux3cnnSSUm6dCxYg6Q26"}
        self.assertEqual(client.sign(SAMPLE_SECRET, "/auth/token/create", params),
                         "35607762342831B6A417A0DED84B79C05FEFBF116969C48AD6DC00279A9F4D81")

    def test_business_api_sample_from_docs(self):
        # doc 1385, Case 1: business API, "method" is an ordinary sorted parameter, no path prefix.
        # (The doc's concatenated string uses method=aliexpress.logistics.redefining.getonlinelogisticsinfo.)
        params = {"access_token": "test", "aliexpress_category_id": "200135143", "app_key": "123456",
                  "method": "aliexpress.logistics.redefining.getonlinelogisticsinfo",
                  "sign_method": "sha256", "timestamp": "1517820392000"}
        self.assertEqual(client.sign(SAMPLE_SECRET, "", params),
                         "F7F7926B67316C9D1E8E15F7E66940ED3059B1638C497D77973F30046EFB5BBB")

    def test_sign_param_and_empty_values_are_skipped(self):
        base = {"app_key": "12345678", "timestamp": "1517820392000", "sign_method": "sha256",
                "code": "3_500102_JxZ05Ux3cnnSSUm6dCxYg6Q26"}
        with_noise = dict(base, sign="SHOULD_BE_IGNORED", empty="", none=None)
        self.assertEqual(client.sign(SAMPLE_SECRET, "/auth/token/create", with_noise),
                         client.sign(SAMPLE_SECRET, "/auth/token/create", base))

    def test_order_independent(self):
        a = {"b": "2", "a": "1", "foo_bar": "3", "foobar": "4"}
        b = dict(reversed(list(a.items())))
        self.assertEqual(client.sign(SAMPLE_SECRET, "", a), client.sign(SAMPLE_SECRET, "", b))
        self.assertEqual(len(client.sign(SAMPLE_SECRET, "", a)), 64)
        self.assertTrue(client.sign(SAMPLE_SECRET, "", a).isupper())

    def test_normalize_params(self):
        out = client.normalize_params({"n": 3, "b": True, "obj": {"quantity": 1, "shipToCountry": "IL"},
                                       "arr": ["IL"], "skip": None, "empty": ""})
        self.assertEqual(out, {"n": "3", "b": "true", "obj": '{"quantity":1,"shipToCountry":"IL"}', "arr": '["IL"]'})


class EnvelopeTests(unittest.TestCase):
    def test_unwrap_response_and_resp_result(self):
        d = {"aliexpress_ds_category_get_response": {"resp_result": {"resp_code": 200, "result": {"x": 1}}, "request_id": "r"}}
        self.assertEqual(client.unwrap(d), {"resp_code": 200, "result": {"x": 1}})
        flat = {"result": {}, "rsp_code": "200", "rsp_msg": "Call succeeds"}
        self.assertEqual(client.unwrap(flat), flat)

    def test_business_status(self):
        self.assertEqual(client.business_status({"rsp_code": "200", "rsp_msg": "ok"})[0], True)
        self.assertEqual(client.business_status({"rsp_code": 605, "rsp_msg": "ITEM_ID_NOT_FOUND"})[0], False)
        self.assertEqual(client.business_status({"code": "00", "msg": "ok", "data": {}})[0], True)
        self.assertEqual(client.business_status({"resp_code": 200})[0], True)
        self.assertEqual(client.business_status({"result": {"success": False, "msg": "DELIVERY_NOT_AVAILABLE_TO_YOUR_ADDRESS", "code": 400}}),
                         (False, 400, "DELIVERY_NOT_AVAILABLE_TO_YOUR_ADDRESS"))
        self.assertEqual(client.business_status({"result": {"ret": True, "code": "0", "data": {}}})[0], True)

    def test_gateway_error_detection(self):
        err = client.gateway_error({"type": "ISV", "code": "IncompleteSignature", "message": "bad sign", "request_id": "x"})
        self.assertIsNotNone(err)
        self.assertEqual(err.code, "IncompleteSignature")
        self.assertIn("IncompleteSignature", str(err))
        wrapped = client.gateway_error({"error_response": {"type": "ISP", "code": "ApiCallLimit", "msg": "Api access frequency exceeds the limit", "request_id": "y"}})
        self.assertTrue(client.is_flow_control(wrapped))
        # successful token response has code "0" + request_id: not an error
        self.assertIsNone(client.gateway_error({"code": "0", "request_id": "z", "access_token": "t", "expires_in": 86400}))
        # successful product.get has rsp_code + code "0": not an error
        self.assertIsNone(client.gateway_error({"result": {}, "code": "0", "rsp_code": "200", "rsp_msg": "Call succeeds", "request_id": "q"}))

    def test_extract_code(self):
        self.assertEqual(client.extract_code("https://127.0.0.1/callback?code=3_500102_abc&state=1"), "3_500102_abc")
        self.assertEqual(client.extract_code("code=3_500102_abc"), "3_500102_abc")
        self.assertEqual(client.extract_code("  3_500102_abc "), "3_500102_abc")

    def test_mask(self):
        self.assertEqual(client.mask("someone@example.com"), "so…ne@example.com")
        self.assertEqual(client.mask("2637908814"), "26…14")
        self.assertEqual(client.mask("ab"), "…")

    def test_authorize_url_shape(self):
        url = client.authorize_url(redirect_uri="https://127.0.0.1/callback", key="KEY")
        self.assertTrue(url.startswith("https://api-sg.aliexpress.com/oauth/authorize?"))
        self.assertIn("response_type=code", url)
        self.assertIn("force_auth=true", url)
        self.assertIn("redirect_uri=https%3A%2F%2F127.0.0.1%2Fcallback", url)
        self.assertIn("client_id=KEY", url)

    def test_token_record_uses_absolute_times_and_keeps_refresh_token(self):
        rec = client.token_record({"access_token": "A", "refresh_token": "R", "expires_in": 86400,
                                   "refresh_expires_in": 172800, "expire_time": 1711693026000,
                                   "refresh_token_valid_time": 1711779426000, "account": "u@x.com",
                                   "account_platform": "buyerApp"})
        self.assertEqual(rec["expires_at"], 1711693026)
        self.assertEqual(rec["refresh_expires_at"], 1711779426)
        rec2 = client.token_record({"access_token": "B", "expires_in": 86400}, previous=rec)
        self.assertEqual(rec2["refresh_token"], "R")
        self.assertEqual(rec2["refresh_expires_at"], 1711779426)


if __name__ == "__main__":
    unittest.main(verbosity=1)
