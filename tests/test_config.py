import base64
import os
import tempfile
import unittest

import config
import streamer


class ConfigCookieTests(unittest.TestCase):
    def test_get_public_stream_url_uses_render_external_url(self):
        original_host = config.ICECAST_HOST
        original_port = config.ICECAST_PORT
        original_mount = config.ICECAST_MOUNT
        original_env = os.environ.get("RENDER_EXTERNAL_URL", "")
        os.environ["RENDER_EXTERNAL_URL"] = "https://example.onrender.com"
        config.ICECAST_HOST = "localhost"
        config.ICECAST_PORT = 8000
        config.ICECAST_MOUNT = "/radio"

        try:
            self.assertEqual(config.get_stream_url(), "https://example.onrender.com/radio")
        finally:
            if original_env:
                os.environ["RENDER_EXTERNAL_URL"] = original_env
            else:
                os.environ.pop("RENDER_EXTERNAL_URL", None)
            config.ICECAST_HOST = original_host
            config.ICECAST_PORT = original_port
            config.ICECAST_MOUNT = original_mount

    def test_build_yt_dlp_opts_does_not_force_cookiefile_by_default(self):
        cookie_file = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
                handle.write("# Netscape HTTP Cookie File\n")
                cookie_file = handle.name

            original = config.get_youtube_cookie_file
            config.get_youtube_cookie_file = lambda: cookie_file
            try:
                opts = streamer._build_yt_dlp_opts()
                self.assertNotIn("cookiefile", opts)
            finally:
                config.get_youtube_cookie_file = original
        finally:
            if cookie_file and os.path.exists(cookie_file):
                os.unlink(cookie_file)

    def test_get_youtube_cookie_file_skips_placeholder_cookie_text(self):
        placeholder = "# Netscape HTTP Cookie File\n# Example placeholder; replace this with real exported cookies from your browser.\n"

        original_b64 = config.YOUTUBE_COOKIES_B64
        original_file = config.YOUTUBE_COOKIES_FILE
        original_read = config._read_cookie_file
        cookie_file = None

        try:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
                handle.write(placeholder)
                cookie_file = handle.name

            def fake_read(path_str):
                if path_str == cookie_file:
                    return placeholder
                return None

            config.YOUTUBE_COOKIES_B64 = ""
            config.YOUTUBE_COOKIES_FILE = cookie_file
            config._read_cookie_file = fake_read
            self.assertIsNone(config.get_youtube_cookie_file())
        finally:
            if cookie_file and os.path.exists(cookie_file):
                os.unlink(cookie_file)
            config.YOUTUBE_COOKIES_B64 = original_b64
            config.YOUTUBE_COOKIES_FILE = original_file
            config._read_cookie_file = original_read

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
