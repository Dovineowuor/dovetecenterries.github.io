from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Profile
from .helpers import *
from django.contrib.auth import authenticate, login


class LoginView(APIView):

    def post(self, request):
        response = {}
        response['status'] = 500
        response['message'] = 'Something went wrong'
        try:
            data = request.data

            if data.get('email') is None:
                response['message'] = 'key email not found'
                raise Exception('key email not found')

            if data.get('password') is None:
                response['message'] = 'key password not found'
                raise Exception('key password not found')

            check_user = User.objects.filter(
                email=data.get('email')).first()

            if check_user is None:
                response['message'] = 'invalid email, user not found'
                raise Exception('invalid email not found')

            if not Profile.objects.filter(user=check_user).first().is_verified:
                response['message'] = 'your profile is not verified'
                raise Exception('profile not verified')

            user_obj = authenticate(email=data.get('email'),
                                  password=data.get('password'))
            if user_obj:
                login(request, user_obj)
                response['status'] = 200
                response['message'] = 'Welcome'
            else:
                response['message'] = 'invalid password'
                raise Exception('invalid password')


        except Exception as e:
            print(e)

        return Response(response)


class RegisterView(APIView):

    def post(self, request):
        response = {'status': 500, 'message': 'Something went wrong'}
        try:
            data = request.data

            # Validate required fields
            required_fields = ['email', 'password', 'first_name', 'last_name']
            for field in required_fields:
                if not data.get(field):
                    response['message'] = f'key {field} not found'
                    raise Exception(f'key {field} not found')

            # Check if email already exists
            if User.objects.filter(email=data.get('email')).exists():
                response['message'] = 'Email already taken'
                raise Exception('Email already taken')

            user_obj = User.objects.create_user(
                email=data.get('email'),
                password=data.get('password'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name')
            )
            token = generate_random_string(20)
            # set verified user
            Profile.objects.create(user=user_obj, token=token,
                                   is_verified=True)
            # send_mail_to_user(token , data.get('username'))
            response['message'] = 'User created '
            response['status'] = 200
        except Exception as e:
            print(e)

        return Response(response)
