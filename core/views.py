from rest_framework import status, viewsets, permissions, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import (
    User, BankAccount, Transaction, Beneficiary, Card, 
    AccountType, TransactionCategory, AuditLog
)
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer, LoginSerializer,
    BankAccountSerializer, TransactionSerializer, TransferSerializer,
    BeneficiarySerializer, CardSerializer, ChangePasswordSerializer,
    AccountTypeSerializer, TransactionCategorySerializer,
    SetTransactionPINSerializer, VerifyTransactionPINSerializer
)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Simple health check endpoint to verify backend is running
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'message': 'Banking API is running'
    }, status=status.HTTP_200_OK)


def log_request_details(view_func):
    """
    A decorator to print verbose details about incoming requests for debugging.
    """
    def wrapper(self, request, *args, **kwargs):
        print("\n" + "="*50)
        print(f"[{timezone.now().isoformat()}]")
        print(f"Request Path: {request.path}")
        print(f"Request Method: {request.method}")
        
        # Log authenticated user
        if request.user and request.user.is_authenticated:
            print(f"Authenticated User: {request.user.username}")
        else:
            print("Authenticated User: Anonymous")
            
        # Log request headers
        print("Headers:")
        for header, value in request.headers.items():
            # Avoid printing sensitive headers like Authorization if needed
            if header in ['Content-Length', 'Content-Type', 'User-Agent', 'Accept']:
                 print(f"  {header}: {value}")

        # Log request body (payload)
        if request.data:
            print("Request Body:")
            # Pretty print JSON if possible
            try:
                import json
                print(json.dumps(request.data, indent=2))
            except:
                print(request.data)
        else:
            print("Request Body: Empty")
        
        print("="*50 + "\n")
        
        return view_func(self, request, *args, **kwargs)
    return wrapper


class AuthViewSet(viewsets.GenericViewSet):
    """
    Authentication related endpoints
    """
    permission_classes = [permissions.AllowAny] # Allow any for middleware

    @log_request_details
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens for the new user
            refresh = RefreshToken.for_user(user)
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action_type='REGISTER',
                description='User registered successfully.',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @log_request_details
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def set_pin(self, request):
        """
        Set or change the user's transaction PIN.
        """
        serializer = SetTransactionPINSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            AuditLog.objects.create(
                user=request.user,
                action_type='PIN_SET',
                description='Transaction PIN was set or changed.',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({'message': 'Transaction PIN set successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @log_request_details
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def verify_pin(self, request):
        """
        Verify the user's transaction PIN.
        """
        serializer = VerifyTransactionPINSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            if serializer.verify():
                return Response({'message': 'PIN verified successfully.'}, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid PIN'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @log_request_details
    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user) # This is for session-based auth, can be kept or removed
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action_type='LOGIN',
                description='User logged in',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @log_request_details
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated]) # Requires auth
    def logout(self, request):
        if request.user.is_authenticated:
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='LOGOUT',
                description='User logged out',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            # Blacklist the refresh token to log the user out
            try:
                refresh_token = request.data["refresh"]
                token = RefreshToken(refresh_token)
                token.blacklist()
                logout(request) # Also clear session
                return Response(status=status.HTTP_25_NO_CONTENT)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
                
        return Response({'error': 'User not authenticated'}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User profile management
    """
    permission_classes = [permissions.IsAuthenticated] # Default to authenticated

    @log_request_details
    @action(detail=False, methods=['get'])
    def profile(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @log_request_details
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='ACCOUNT_UPDATE',
                description='Profile updated',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @log_request_details
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='PASSWORD_CHANGE',
                description='Password changed',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BankAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Bank account management
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    @log_request_details
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        account = self.get_object()
        transactions = Transaction.objects.filter(account=account)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @log_request_details
    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        account = self.get_object()
        return Response({
            'account_number': account.account_number,
            'balance': account.balance,
            'available_balance': account.available_balance
        })


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows transactions to be viewed.
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the transactions
        for the currently authenticated user.
        """
        user = self.request.user
        return Transaction.objects.filter(account__user=user).order_by('-created_at')

    @log_request_details
    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """
        Handle fund transfers between user's own accounts or to other users.
        PIN verification is handled by the serializer.
        """
        serializer = TransferSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                result = serializer.save()
                
                # Create audit log for the successful transfer
                AuditLog.objects.create(
                    user=request.user,
                    action_type='TRANSFER',
                    description=f"Transfer of {serializer.validated_data['amount']} from {serializer.validated_data['from_account_obj'].account_number} to {serializer.validated_data['to_account_obj'].account_number}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return Response(result, status=status.HTTP_200_OK)
            except serializers.ValidationError as e:
                return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                # Generic error for unexpected issues during the transaction save
                return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BeneficiaryViewSet(viewsets.ModelViewSet):
    """
    Beneficiary management
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BeneficiarySerializer

    def get_queryset(self):
        return Beneficiary.objects.filter(user=self.request.user)

    @log_request_details
    def create(self, request, *args, **kwargs):
        print("Creating beneficiary...")
        return super().create(request, *args, **kwargs)

    @log_request_details
    def update(self, request, *args, **kwargs):
        print("Updating beneficiary...")
        return super().update(request, *args, **kwargs)

    @log_request_details
    def destroy(self, request, *args, **kwargs):
        print("Deleting beneficiary...")
        return super().destroy(request, *args, **kwargs)


class CardViewSet(viewsets.ModelViewSet):
    """
    Card management
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CardSerializer

    def get_queryset(self):
        return Card.objects.filter(account__user=self.request.user)

    @log_request_details
    def perform_create(self, serializer):
        # This is a simplified example. In a real app, you'd integrate with a payment gateway
        # to get a card token and would not handle raw card numbers.
        account_id = self.request.data.get('account')
        try:
            primary_account = BankAccount.objects.get(user=self.request.user, is_primary=True)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("User does not have a primary account to link the card to.")
            
        # Simplified: Assume last four digits are provided directly for this example
        last_four = self.request.data.get('last_four_digits', '0000')

        serializer.save(account=primary_account, last_four_digits=last_four)
        
        AuditLog.objects.create(
            user=self.request.user,
            action_type='CARD_ADDED',
            description=f"Card ending in {last_four} was added.",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        card_last_four = instance.last_four_digits
        instance.delete()
        AuditLog.objects.create(
            user=self.request.user,
            action_type='CARD_REMOVED',
            description=f"Card ending in {card_last_four} was removed.",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class UserProfileViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    @log_request_details
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get the profile of the currently authenticated user.
        """
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    @log_request_details
    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """
        Update the profile of the currently authenticated user.
        """
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            AuditLog.objects.create(
                user=user,
                action_type='PROFILE_UPDATE',
                description='User profile was updated.',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @log_request_details
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        Change the password of the currently authenticated user.
        """
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            AuditLog.objects.create(
                user=request.user,
                action_type='PASSWORD_CHANGE',
                description='User changed their password.',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a list of available account types.
    """
    queryset = AccountType.objects.filter(is_active=True)
    serializer_class = AccountTypeSerializer
    permission_classes = [permissions.AllowAny] # Publicly viewable


class TransactionCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a list of available transaction categories.
    """
    queryset = TransactionCategory.objects.all()
    serializer_class = TransactionCategorySerializer
    permission_classes = [permissions.IsAuthenticated] # Only for logged-in users
