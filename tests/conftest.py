"""
Shared pytest configuration and fixtures for renewable energy pipeline tests.

This file makes all fixtures available to tests throughout the test suite.
"""

# Import all fixtures from the fixtures modules to make them available to pytest
from tests.fixtures.api_client import *
from tests.fixtures.openapi_loader import *
from tests.fixtures.storage_fixtures import *
from tests.fixtures.test_data import *
from tests.fixtures.uuid_helpers import *
