from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    # def ready(self):
    #     from social_network.custom_admin import customize_admin_site
    #     customize_admin_site()