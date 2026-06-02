from accounts.models import MenuPermission


def user_menus(request):
    if not request.user.is_authenticated:
        return {'user_menus': []}
    if request.user.role == 'master':
        return {'user_menus': []}
    role = request.user.role
    if role == 'free':
        role = 'member'
    menus = MenuPermission.objects.filter(
        role=role,
        is_visible=True
    )
    return {'user_menus': menus}