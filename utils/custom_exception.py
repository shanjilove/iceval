from rest_framework.views import exception_handler
from rest_framework.views import Response
from rest_framework import status


class SxopeException(Exception):
    def __init__(self, error_code, error_message):
        self.error_code = error_code
        self.error_message = error_message

    def __str__(self):
        return f"[Error Code: {self.error_code}] {self.error_message}"

    @staticmethod
    def custom_exception_handler(exc, context):
        response = exception_handler(exc, context)
        for index, value in enumerate(response.data):
            if index == 0:
                key = value
                value = response.data[key]

                if isinstance(value, str):
                    message = value
                else:
                    message = key + value[0]

        if response is None:
            print('1234 = %s - %s - %s' % (context['view'], context['request'].method, exc))
            return Response({
                'message': 'failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR, exception=True)

        else:
            print('123 = %s - %s - %s' % (context['view'], context['request'].method, exc))
            return Response({
                'message': message,
            }, status=response.status_code, exception=True)



