from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import CustomUser
from .serializers import UserSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def create_initial_users(request):
    """
    Create initial admin and worker users
    """
    # Create admin user
    admin_user, created = CustomUser.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@inventory.com',
            'user_type': 'admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
    
    # Create worker user
    worker_user, created = CustomUser.objects.get_or_create(
        username='worker',
        defaults={
            'email': 'worker@inventory.com',
            'user_type': 'worker',
            'is_staff': False,
            'is_superuser': False
        }
    )
    if created:
        worker_user.set_password('worker123')
        worker_user.save()
    
    return Response({
        'message': 'Initial users created successfully',
        'admin': {'username': 'admin', 'password': 'admin123'},
        'worker': {'username': 'worker', 'password': 'worker123'}
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })
    else:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    return Response(UserSerializer(request.user).data)