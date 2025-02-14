import os
import json
import yaml
import logging
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from pathlib import Path

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
            # Load configuration from YAML
            yaml_path = Path(__file__).parent.parent / 'voice-chat-prompt.yaml'
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)

            # Prepare session data from YAML config
            data = config['session']
            
            # Prepare our config data
            config_data = {
                'tools': config['tools'],
                'prompts': config['prompts']
            }

            logger.debug(f'Making request to {url}')
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            # Get OpenAI response and merge with our config
            response_data = response.json()
            logger.debug('Session response received')
            
            if 'client_secret' in response_data:
                # Merge OpenAI response with our config
                response_data.update(config_data)
                response_data['client_secret'] = response_data['client_secret']['value']
                return Response(response_data)
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
