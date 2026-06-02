from accounts.models import MenuPermission


def user_menus(request):
    if not request.user.is_authenticated:
        return {'user_menus': []}
    if request.user.role == 'master':
        return {'user_menus': []}
    menus = MenuPermission.objects.filter(
        role=request.user.role,
        is_visible=True
    )
    return {'user_menus': menus}