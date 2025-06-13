"""
Test runner configuration and utilities for the banking application
"""
import os
import sys
from django.test.utils import get_runner
from django.conf import settings
from django.core.management import execute_from_command_line


class CustomTestRunner:
    """Custom test runner with additional setup and reporting"""
    
    def __init__(self):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bankingapi.settings')
        
    def run_tests(self, test_labels=None, verbosity=1):
        """Run the test suite"""
        if test_labels is None:
            test_labels = ['core']
        
        # Setup Django
        import django
        django.setup()
        
        # Get Django's test runner
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=verbosity, interactive=True)
        
        # Run tests
        failures = test_runner.run_tests(test_labels)
        
        if failures:
            sys.exit(bool(failures))
        
        return failures


def run_specific_tests():
    """Run specific test categories"""
    
    test_categories = {
        'models': ['core.tests.test_models'],
        'views': ['core.tests.test_views'],
        'serializers': ['core.tests.test_serializers'],
        'admin': ['core.tests.test_admin'],
        'integration': ['core.tests.test_integration'],
        'performance': ['core.tests.test_performance'],
        'all': ['core']
    }
    
    print("Available test categories:")
    for category, tests in test_categories.items():
        print(f"  {category}: {', '.join(tests)}")
    
    category = input("\nEnter test category to run (default: all): ").strip() or 'all'
    
    if category not in test_categories:
        print(f"Invalid category. Available: {list(test_categories.keys())}")
        return
    
    verbosity = input("Enter verbosity level (0-3, default: 2): ").strip() or '2'
    try:
        verbosity = int(verbosity)
    except ValueError:
        verbosity = 2
    
    runner = CustomTestRunner()
    runner.run_tests(test_categories[category], verbosity=verbosity)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        run_specific_tests()
    else:
        # Default: run all tests
        runner = CustomTestRunner()
        runner.run_tests()
