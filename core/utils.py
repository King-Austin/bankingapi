import functools
from rest_framework.request import Request
import json

def verbose_logging(func):
    """A decorator to log request and response details for debugging."""
    @functools.wraps(func)
    def wrapper_verbose_logging(*args, **kwargs):
        # The request object is typically the first or second argument in DRF views
        request = None
        if args:
            # For function-based views, request is often the first argument
            if isinstance(args[0], Request):
                request = args[0]
            # For class-based views, `self` is the first argument, request is the second
            elif len(args) > 1 and isinstance(args[1], Request):
                request = args[1]

        print("\n" + "="*60)
        if request:
            print(f"BANKING_API_DEBUG: ==> Request: {request.method} {request.path}")
            try:
                # Pretty print JSON body if possible
                body = json.dumps(request.data, indent=2)
                print(f"BANKING_API_DEBUG: ==> Body:\n{body}")
            except Exception:
                print(f"BANKING_API_DEBUG: ==> Body: {request.data}")
        else:
            # Fallback if request object can't be found
            print(f"BANKING_API_DEBUG: ==> Calling function: {func.__name__}")

        try:
            # Execute the actual view function
            response = func(*args, **kwargs)
            
            print(f"BANKING_API_DEBUG: <== Response Status: {response.status_code}")
            try:
                # Pretty print JSON response data if possible
                response_data = json.dumps(response.data, indent=2)
                print(f"BANKING_API_DEBUG: <== Response Data:\n{response_data}")
            except Exception:
                 print(f"BANKING_API_DEBUG: <== Response Data: {getattr(response, 'data', 'No data attribute')}")
            
            print("="*60 + "\n")
            return response
        except Exception as e:
            print(f"BANKING_API_DEBUG: !!! ERROR in {func.__name__}: {e}")
            print("="*60 + "\n")
            # Re-raise the exception to ensure normal error handling proceeds
            raise
            
    return wrapper_verbose_logging
