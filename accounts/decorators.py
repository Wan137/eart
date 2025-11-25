from django.contrib.auth.decorators import user_passes_test

def artist_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and getattr(u, "role", "") == "artist")(view_func)

