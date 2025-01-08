from django.apps import AppConfig

class UserleaderAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'userleader_app'

    def ready(self):
        import userleader_app.signals
