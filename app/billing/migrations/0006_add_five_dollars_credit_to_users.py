from decimal import Decimal
from django.db import migrations, transaction

def add_five_dollars_credit(apps, schema_editor):
    BillingProfile = apps.get_model('billing', 'BillingProfile')
    Transaction = apps.get_model('billing', 'Transaction')

    with transaction.atomic():
        for billing_profile in BillingProfile.objects.all():
            # Update total credits
            billing_profile.total_credits += Decimal('5.00')
            billing_profile.save()

            # Create promotion transaction
            Transaction.objects.create(
                billing_profile=billing_profile,
                amount=Decimal('5.00'),
                transaction_type='promotion',
                description='$5 credit promotion'
            )

def reverse_five_dollars_credit(apps, schema_editor):
    # We can't reliably reverse this operation since credits may have been spent
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0005_seed_token_costs'),
    ]

    operations = [
        migrations.RunPython(
            add_five_dollars_credit,
            reverse_five_dollars_credit
        ),
    ]
