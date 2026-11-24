import os
import unittest
from unittest.mock import patch

from dashboard.database import _get_db_config


class DatabaseConfigTest(unittest.TestCase):
    def test_local_target_uses_local_url_instead_of_neon_url(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "DB_TARGET": "local",
                    "LOCAL_DATABASE_URL": "postgresql://local.example/app",
                    "DATABASE_URL": "postgresql://neon.example/app",
                },
                clear=True,
            ),
            patch("dashboard.database._get_secret_value", return_value=None),
        ):
            config = _get_db_config()

        self.assertEqual(
            config["database_url"],
            "postgresql+psycopg2://local.example/app",
        )

    def test_auto_target_keeps_neon_url_precedence(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "LOCAL_DATABASE_URL": "postgresql://local.example/app",
                    "DATABASE_URL": "postgresql://neon.example/app",
                },
                clear=True,
            ),
            patch("dashboard.database._get_secret_value", return_value=None),
        ):
            config = _get_db_config()

        self.assertEqual(
            config["database_url"],
            "postgresql+psycopg2://neon.example/app",
        )

    def test_rejects_unknown_database_target(self) -> None:
        with (
            patch.dict(os.environ, {"DB_TARGET": "other"}, clear=True),
            patch("dashboard.database._get_secret_value", return_value=None),
            self.assertRaisesRegex(ValueError, "DB_TARGET"),
        ):
            _get_db_config()


if __name__ == "__main__":
    unittest.main()
