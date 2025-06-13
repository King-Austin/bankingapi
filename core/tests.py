"""
Main test module for core app
Import all test modules from the tests folder
"""

# Import all test modules from the tests package
from .tests.test_models import *
from .tests.test_views import *
from .tests.test_serializers import *
from .tests.test_admin import *
from .tests.test_integration import *
from .tests.test_performance import *
