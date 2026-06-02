from django.core.management.base import BaseCommand
from accounts.models import MenuPermission


class Command(BaseCommand):
    help = '기본 메뉴 권한 초기화'

    def handle(self, *args, **kwargs):
        menus = [
            # admin 메뉴
            {'role': 'admin', 'menu_key': 'dashboard', 'menu_label': '대시보드', 'icon': 'bi-speedometer2', 'order': 1},
            {'role': 'admin', 'menu_key': 'generate', 'menu_label': '콘텐츠 생성', 'icon': 'bi-magic', 'order': 2},
            {'role': 'admin', 'menu_key': 'history', 'menu_label': '생성 이력', 'icon': 'bi-clock-history', 'order': 3},
            {'role': 'admin', 'menu_key': 'stats', 'menu_label': '생성 통계', 'icon': 'bi-bar-chart', 'order': 4},
            {'role': 'admin', 'menu_key': 'user_list', 'menu_label': '회원 관리', 'icon': 'bi-people', 'order': 5},
            {'role': 'admin', 'menu_key': 'credit_list', 'menu_label': '크레딧 관리', 'icon': 'bi-coin', 'order': 6},
            {'role': 'admin', 'menu_key': 'prompt_list', 'menu_label': '프롬프트 관리', 'icon': 'bi-sliders', 'order': 7},
            {'role': 'admin', 'menu_key': 'credit_charge', 'menu_label': '크레딧 충전', 'icon': 'bi-plus-circle', 'order': 8},
            {'role': 'admin', 'menu_key': 'profile', 'menu_label': '내 정보', 'icon': 'bi-person', 'order': 9},

            # member 메뉴
            {'role': 'member', 'menu_key': 'dashboard', 'menu_label': '대시보드', 'icon': 'bi-speedometer2', 'order': 1},
            {'role': 'member', 'menu_key': 'generate', 'menu_label': '콘텐츠 생성', 'icon': 'bi-magic', 'order': 2},
            {'role': 'member', 'menu_key': 'history', 'menu_label': '생성 이력', 'icon': 'bi-clock-history', 'order': 3},
            {'role': 'member', 'menu_key': 'credit_charge', 'menu_label': '크레딧 충전', 'icon': 'bi-plus-circle', 'order': 4},
            {'role': 'member', 'menu_key': 'credit_list', 'menu_label': '크레딧 내역', 'icon': 'bi-coin', 'order': 5},
            {'role': 'member', 'menu_key': 'profile', 'menu_label': '내 정보', 'icon': 'bi-person', 'order': 6},
        ]

        for menu in menus:
            MenuPermission.objects.get_or_create(
                role=menu['role'],
                menu_key=menu['menu_key'],
                defaults={
                    'menu_label': menu['menu_label'],
                    'icon': menu['icon'],
                    'order': menu['order'],
                    'is_visible': True,
                }
            )
        self.stdout.write(self.style.SUCCESS('기본 메뉴 권한이 초기화됐습니다.'))