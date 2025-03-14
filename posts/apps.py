from django.apps import AppConfig


class PostsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'posts'

    # def ready(self):
    #     from social_network.custom_admin import customize_admin_site
    #     customize_admin_site()