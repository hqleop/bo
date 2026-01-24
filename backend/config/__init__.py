"""
Project package init.

We use PyMySQL as MySQL driver (pure Python) to avoid native build deps on Windows.
"""

import pymysql

pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.__version__ = "2.2.1"
pymysql.install_as_MySQLdb()