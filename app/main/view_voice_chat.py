import os
import json
import logging
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings

logger = logging.getLogger(__name__)

class SessionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        logger.debug('Session request received')
        
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            error_msg = "Invalid API key. Please set your OpenAI API key in Django settings."
            logger.error(error_msg)
            return Response({"error": error_msg}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            url = 'https://api.openai.com/v1/realtime/sessions'
            data = {
                'model': 'gpt-4o-mini-realtime-preview-2024-12-17',
                'modalities': ['text', 'audio'],
                'instructions': 'You are an english speaking japanese tutor. You use simple language. You help review flash cards, and help draft flash cards. You will also role play. And discuss japanese language matters as the user desires.  Keep everything you say terse, natural and conversational.',
                'voice': 'ballad',
                'input_audio_format': 'pcm16',
                'output_audio_format': 'pcm16',
                "input_audio_transcription": {
                   "model": "whisper-1",
                }, 
                'temperature': 0.8
            }

            logger.debug(f'Making request to {url}')
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            response_data = response.json()
            logger.debug('Session response received')
            
            if 'client_secret' in response_data:
                return Response({'client_secret': response_data['client_secret']['value']})
            else:
                return Response({"error": "No client secret in response"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except requests.exceptions.RequestException as e:
            if e.response:
                error_data = e.response.json()
                error_msg = error_data.get('error', str(error_data))
            else:
                error_msg = str(e)
            logger.error(f'Session error: {error_msg}')
            return Response({"error": error_msg}, 
                          status=e.response.status_code if e.response else status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f'Unexpected error: {str(e)}')
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
