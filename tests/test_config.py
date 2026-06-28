import base64
import os
import unittest

import config


class ConfigCookieTests(unittest.TestCase):
    def test_get_youtube_cookie_file_decodes_base64(self):
        cookie_text = "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t0\tfoo\tbar\n"
        encoded = base64.b64encode(cookie_text.encode("utf-8")).decode("ascii")

        original = config.YOUTUBE_COOKIES_B64
        config.YOUTUBE_COOKIES_B64 = encoded
        cookie_file = None

        try:
            cookie_file = config.get_youtube_cookie_file()
            self.assertTrue(cookie_file)
            self.assertTrue(os.path.exists(cookie_file))
            with open(cookie_file, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), cookie_text)
        finally:
            if cookie_file and os.path.exists(cookie_file):
                os.unlink(cookie_file)
            config.YOUTUBE_COOKIES_B64 = original

    def test_get_youtube_cookie_file_accepts_raw_cookie_text(self):
        cookie_text = "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t0\tfoo\tbar\n"

        original_b64 = config.YOUTUBE_COOKIES_B64
        original_file = config.YOUTUBE_COOKIES_FILE
        config.YOUTUBE_COOKIES_B64 = cookie_text
        config.YOUTUBE_COOKIES_FILE = ""
        cookie_file = None

        try:
            cookie_file = config.get_youtube_cookie_file()
            self.assertTrue(cookie_file)
            self.assertTrue(os.path.exists(cookie_file))
            with open(cookie_file, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), cookie_text)
        finally:
            if cookie_file and os.path.exists(cookie_file):
                os.unlink(cookie_file)
            config.YOUTUBE_COOKIES_B64 = original_b64
            config.YOUTUBE_COOKIES_FILE = original_file


if __name__ == "__main__":
    unittest.main()
