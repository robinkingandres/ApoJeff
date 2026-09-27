from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0004_appointment_additional_names'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patient',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='patient',
            name='contact_number',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AlterField(
            model_name='patient',
            name='age',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(120)]),
        ),
        migrations.AlterField(
            model_name='patient',
            name='gender',
            field=models.CharField(blank=True, choices=[('female', 'Female'), ('male', 'Male'), ('other', 'Other'), ('prefer_not', 'Prefer not to say')], max_length=20),
        ),
    ]
