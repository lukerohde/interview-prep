from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import json

from billing.models import BillingProfile, BillingSettingItem

@login_required
@require_POST
def add_token_usage(request):
    """
    Add token usage for the current user's session and return updated cost and balance.
    Requires authentication and CSRF token.
    
    Expected POST data:
    {
        "model_name": "gpt-4o-mini-realtime-preview",
        "input_tokens": 100,
        "input_tokens_cached": 50,
        "output_tokens": 200
    }
    
    Returns:
    {
        "status": "success",
        "cost": 0.123,  # Cost for this usage
        "balance": 99.877,  # Updated account balance
        "message": "Token usage added successfully"
    }
    """
    try:
        data = json.loads(request.body)
        model_name = data.get('model_name')
        input_tokens = int(data.get('input_tokens', 0))
        input_tokens_cached = int(data.get('input_tokens_cached', 0))
        output_tokens = int(data.get('output_tokens', 0))
        
        # Get or create billing profile for the current user
        billing_profile = request.user.billing_profile
        
        # Add token usage and get cost and updated balance
        cost, balance = billing_profile.add_token_usage(
            model_name=model_name,
            input_tokens=input_tokens,
            input_tokens_cached=input_tokens_cached,
            output_tokens=output_tokens
        )    
        
        return JsonResponse({
            'status': 'success',
            'cost': float(cost),
            'balance': float(balance),
            'message': 'Token usage added successfully'
        })
    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    except BillingSettingItem.DoesNotExist as e:
        return JsonResponse({
                'status': 'error',
                'message': f'Token cost not found for model: {model_name}'
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred'
        }, status=500)


