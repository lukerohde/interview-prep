from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from .ai_helpers import call_openai
from http import HTTPStatus


class TextAIResponseViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    def create(self, request):
      
      developer_prompt = request.data.get('developer_prompt')
      user_prompt = request.data.get('user_prompt')
      
      if not developer_prompt or not user_prompt:
          return Response({'error': 'Both developer_prompt and user_prompt are required'}, status=HTTPStatus.UNPROCESSABLE_CONTENT)
      return Response({'response': call_openai(developer_prompt, user_prompt, user=request.user)}, status=HTTPStatus.CREATED)
