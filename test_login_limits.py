import unittest

from backend.login_limits import (
    LOGIN_WINDOW_SECONDS,
    MAX_LOGIN_ATTEMPTS,
    _reset_attempts_for_tests,
    consume_login_attempt,
)


class LoginLimitTests(unittest.TestCase):
    def setUp(self):
        _reset_attempts_for_tests()

    def tearDown(self):
        _reset_attempts_for_tests()

    def test_limits_by_email_and_ip(self):
        for attempt in range(MAX_LOGIN_ATTEMPTS):
            self.assertIsNone(
                consume_login_attempt("user@example.com", "192.0.2.1", now=attempt)
            )

        self.assertGreater(
            consume_login_attempt("user@example.com", "192.0.2.1", now=20), 0
        )
        self.assertGreater(
            consume_login_attempt("other@example.com", "192.0.2.1", now=20), 0
        )

    def test_attempts_expire_after_window(self):
        for attempt in range(MAX_LOGIN_ATTEMPTS):
            consume_login_attempt("user@example.com", "192.0.2.1", now=attempt)

        self.assertIsNone(
            consume_login_attempt(
                "user@example.com",
                "192.0.2.1",
                now=MAX_LOGIN_ATTEMPTS + LOGIN_WINDOW_SECONDS,
            )
        )


if __name__ == "__main__":
    unittest.main()
