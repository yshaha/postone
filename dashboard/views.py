from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from content.models import ContentRequest, ContentType, Channel, ChannelPrompt
from credits.models import UserCredit, CreditTransaction, CreditPackage


def get_user_menus(user):
    from accounts.models import MenuPermission
    if user.role in ['master']:
        return []
    return MenuPermission.objects.filter(role=user.role, is_visible=True)


@login_required
def index(request):
    today = timezone.now().date()
    total_requests = ContentRequest.objects.filter(user=request.user).count()
    today_requests = ContentRequest.objects.filter(
        user=request.user, created_at__date=today
    ).count()
    try:
        my_credits = request.user.credit.balance
    except:
        my_credits = 0
    from accounts.models import User
    total_users = User.objects.count() if request.user.is_admin else 0
    recent_requests = ContentRequest.objects.filter(
        user=request.user
    ).select_related('content_type', 'channel')[:5]
    return render(request, 'dashboard/index.html', {
        'stats': {
            'total_requests': total_requests,
            'today_requests': today_requests,
            'my_credits': my_credits,
            'total_users': total_users,
        },
        'recent_requests': recent_requests,
    })


# 콘텐츠 유형
@login_required
def content_type_list(request):
    content_types = ContentType.objects.all()
    return render(request, 'dashboard/content_type_list.html', {'content_types': content_types})


@login_required
def content_type_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        if name:
            ContentType.objects.create(
                name=name, description=description,
                is_active=is_active, created_by=request.user
            )
            messages.success(request, f'"{name}" 유형이 추가됐습니다.')
            return redirect('dashboard:content_type_list')
    class DummyForm:
        def __getattr__(self, name):
            class F:
                def value(self): return ''
            f = F()
            if name == 'is_active':
                f.value = lambda: True
            return f
    return render(request, 'dashboard/content_type_form.html', {
        'form': DummyForm(), 'title': '새 콘텐츠 유형'
    })


@login_required
def content_type_edit(request, pk):
    ct = get_object_or_404(ContentType, pk=pk)
    if request.method == 'POST':
        ct.name = request.POST.get('name', '').strip()
        ct.description = request.POST.get('description', '').strip()
        ct.is_active = request.POST.get('is_active') == 'on'
        ct.save()
        messages.success(request, '수정됐습니다.')
        return redirect('dashboard:content_type_list')
    class FormProxy:
        def __getattr__(self, name):
            class F:
                pass
            f = F()
            f.value = lambda: getattr(ct, name, '')
            return f
    return render(request, 'dashboard/content_type_form.html', {
        'form': FormProxy(), 'title': f'"{ct.name}" 수정', 'content_type': ct
    })


@login_required
def content_type_detail(request, pk):
    ct = get_object_or_404(ContentType, pk=pk)
    channel_prompts = ct.channel_prompts.select_related('channel').prefetch_related('option_groups')
    return render(request, 'dashboard/content_type_detail.html', {
        'content_type': ct, 'channel_prompts': channel_prompts
    })


@login_required
def content_type_delete(request, pk):
    ct = get_object_or_404(ContentType, pk=pk)
    if request.method == 'POST':
        ct.delete()
        messages.success(request, '삭제됐습니다.')
        return redirect('dashboard:content_type_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': ct, 'back_url': 'dashboard:content_type_list'
    })


# 채널 프롬프트
@login_required
def channel_prompt_create(request, content_type_pk):
    ct = get_object_or_404(ContentType, pk=content_type_pk)
    channels = Channel.objects.filter(is_active=True)
    if request.method == 'POST':
        channel_id = request.POST.get('channel')
        base_prompt = request.POST.get('base_prompt', '').strip()
        channel = get_object_or_404(Channel, pk=channel_id)
        ChannelPrompt.objects.create(
            content_type=ct, channel=channel,
            base_prompt=base_prompt, updated_by=request.user
        )
        messages.success(request, f'{channel.name} 채널 프롬프트가 추가됐습니다.')
        return redirect('dashboard:content_type_detail', pk=ct.pk)
    return render(request, 'dashboard/channel_prompt_form.html', {
        'content_type': ct, 'channels': channels, 'title': '채널 프롬프트 추가'
    })


@login_required
def channel_prompt_edit(request, pk):
    cp = get_object_or_404(ChannelPrompt, pk=pk)
    if request.method == 'POST':
        cp.base_prompt = request.POST.get('base_prompt', '').strip()
        cp.is_active = request.POST.get('is_active') == 'on'
        cp.updated_by = request.user
        cp.save()
        messages.success(request, '프롬프트가 수정됐습니다.')
        return redirect('dashboard:content_type_detail', pk=cp.content_type.pk)
    return render(request, 'dashboard/channel_prompt_form.html', {
        'channel_prompt': cp, 'content_type': cp.content_type,
        'title': f'{cp.channel.name} 프롬프트 수정'
    })


# 채널
@login_required
def channel_list(request):
    channels = Channel.objects.all()
    return render(request, 'dashboard/channel_list.html', {'channels': channels})


@login_required
def channel_create(request):
    if request.method == 'POST':
        Channel.objects.create(
            name=request.POST.get('name', '').strip(),
            slug=request.POST.get('slug', '').strip(),
            channel_type=request.POST.get('channel_type'),
            description=request.POST.get('description', '').strip(),
            order=int(request.POST.get('order', 0)),
            is_auto_publish=request.POST.get('is_auto_publish') == 'on',
            is_active=request.POST.get('is_active') == 'on',
        )
        messages.success(request, '채널이 추가됐습니다.')
        return redirect('dashboard:channel_list')
    return render(request, 'dashboard/channel_form.html', {
        'title': '채널 추가', 'channel': None
    })


@login_required
def channel_edit(request, pk):
    channel = get_object_or_404(Channel, pk=pk)
    if request.method == 'POST':
        channel.name = request.POST.get('name', '').strip()
        channel.slug = request.POST.get('slug', '').strip()
        channel.channel_type = request.POST.get('channel_type')
        channel.description = request.POST.get('description', '').strip()
        channel.order = int(request.POST.get('order', 0))
        channel.is_auto_publish = request.POST.get('is_auto_publish') == 'on'
        channel.is_active = request.POST.get('is_active') == 'on'
        channel.save()
        messages.success(request, '채널이 수정됐습니다.')
        return redirect('dashboard:channel_list')
    return render(request, 'dashboard/channel_form.html', {
        'title': f'"{channel.name}" 수정', 'channel': channel
    })


@login_required
def channel_delete(request, pk):
    channel = get_object_or_404(Channel, pk=pk)
    if request.method == 'POST':
        channel.delete()
        messages.success(request, '채널이 삭제됐습니다.')
        return redirect('dashboard:channel_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': channel, 'back_url': 'dashboard:channel_list'
    })


# 회원
@login_required
def user_list(request):
    from accounts.models import User
    users = User.objects.all()
    return render(request, 'dashboard/user_list.html', {'users': users})


@login_required
def user_create(request):
    if request.method == 'POST':
        from accounts.models import User
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        if username and password:
            user = User.objects.create_user(
                username=username,
                password=password,
                email=request.POST.get('email', ''),
                first_name=request.POST.get('first_name', ''),
                company=request.POST.get('company', ''),
                phone=request.POST.get('phone', ''),
                role=request.POST.get('role', 'member'),
            )
            UserCredit.objects.create(user=user, balance=0)
            messages.success(request, f'"{username}" 회원이 추가됐습니다.')
            return redirect('dashboard:user_list')
    return render(request, 'dashboard/user_form.html', {'title': '회원 추가'})


@login_required
def user_detail(request, pk):
    from accounts.models import User
    target_user = get_object_or_404(User, pk=pk)
    transactions = CreditTransaction.objects.filter(user=target_user)[:10]
    return render(request, 'dashboard/user_detail.html', {
        'target_user': target_user,
        'transactions': transactions,
    })


@login_required
def user_edit(request, pk):
    from accounts.models import User
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', '')
        target_user.email = request.POST.get('email', '')
        target_user.company = request.POST.get('company', '')
        target_user.phone = request.POST.get('phone', '')
        target_user.role = request.POST.get('role', 'member')
        target_user.is_active = request.POST.get('is_active') == 'on'
        target_user.save()
        messages.success(request, '회원 정보가 수정됐습니다.')
    return redirect('dashboard:user_detail', pk=pk)


@login_required
def user_credit_grant(request, pk):
    from accounts.models import User
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        amount = int(request.POST.get('amount', 0))
        description = request.POST.get('description', '관리자 지급')
        if amount > 0:
            credit, _ = UserCredit.objects.get_or_create(user=target_user)
            credit.balance += amount
            credit.save()
            CreditTransaction.objects.create(
                user=target_user,
                transaction_type='admin_grant',
                amount=amount,
                balance_after=credit.balance,
                description=description,
            )
            messages.success(request, f'{amount}개 크레딧이 지급됐습니다.')
    return redirect('dashboard:user_detail', pk=pk)


# 크레딧
@login_required
def credit_list(request):
    transactions = CreditTransaction.objects.filter(user=request.user)
    try:
        uc = request.user.credit
        balance = uc.balance
        free_used = uc.free_used_this_month
    except:
        balance = 0
        free_used = 0
    total_charged = sum(t.amount for t in transactions if t.amount > 0)
    total_used = abs(sum(t.amount for t in transactions if t.amount < 0))
    return render(request, 'dashboard/credit_list.html', {
        'transactions': transactions,
        'balance': balance,
        'free_used': free_used,
        'total_charged': total_charged,
        'total_used': total_used,
    })


@login_required
def credit_charge(request):
    packages = CreditPackage.objects.filter(is_active=True)
    try:
        balance = request.user.credit.balance
    except:
        balance = 0
    if request.method == 'POST':
        package_id = request.POST.get('package_id')
        pkg = get_object_or_404(CreditPackage, pk=package_id)
        credit, _ = UserCredit.objects.get_or_create(user=request.user)
        credit.balance += pkg.credits
        credit.save()
        CreditTransaction.objects.create(
            user=request.user,
            transaction_type='charge',
            amount=pkg.credits,
            balance_after=credit.balance,
            description=f'{pkg.name} 충전',
        )
        messages.success(request, f'{pkg.credits}개 크레딧이 충전됐습니다.')
        return redirect('dashboard:credit_list')
    return render(request, 'dashboard/credit_charge.html', {
        'packages': packages,
        'balance': balance,
    })


# 콘텐츠 생성
@login_required
def generate(request):
    content_types = ContentType.objects.filter(is_active=True)
    return render(request, 'dashboard/generate.html', {'content_types': content_types})


# 이력
@login_required
def history(request):
    requests = ContentRequest.objects.filter(
        user=request.user
    ).select_related('content_type', 'channel').order_by('-created_at')
    return render(request, 'dashboard/history.html', {'requests': requests})


@login_required
def request_detail(request, pk):
    req = get_object_or_404(ContentRequest, pk=pk, user=request.user)
    return render(request, 'dashboard/request_detail.html', {'req': req})


# 통계
@login_required
def stats(request):
    from django.db.models import Count, Sum
    from datetime import timedelta

    today = timezone.now().date()
    period = request.GET.get('period', '30')
    days = int(period)
    start_date = today - timedelta(days=days)

    qs = ContentRequest.objects.all() if request.user.is_admin else ContentRequest.objects.filter(user=request.user)

    total = qs.count()
    period_count = qs.filter(created_at__date__gte=start_date).count()
    this_month = qs.filter(
        created_at__year=today.year,
        created_at__month=today.month
    ).count()
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month_end = today.replace(day=1)
    last_month = qs.filter(
        created_at__date__gte=last_month_start,
        created_at__date__lt=last_month_end
    ).count()

    total_credits_used = qs.aggregate(t=Sum('credit_used'))['t'] or 0

    channel_stats = qs.filter(
        created_at__date__gte=start_date
    ).values('channel__name').annotate(count=Count('id')).order_by('-count')[:5]

    type_stats = qs.filter(
        created_at__date__gte=start_date
    ).values('content_type__name').annotate(count=Count('id')).order_by('-count')[:5]

    daily_stats = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        count = qs.filter(created_at__date=d).count()
        daily_stats.append({'date': d.strftime('%m/%d'), 'count': count})

    top_channel = channel_stats[0]['channel__name'] if channel_stats else None
    top_type = type_stats[0]['content_type__name'] if type_stats else None
    diff = this_month - last_month

    return render(request, 'dashboard/stats.html', {
        'stats': {
            'total': total,
            'period_count': period_count,
            'this_month': this_month,
            'total_credits_used': total_credits_used,
        },
        'channel_stats': channel_stats,
        'type_stats': type_stats,
        'daily_stats': daily_stats,
        'period': period,
        'insight': {
            'top_channel': top_channel,
            'top_type': top_type,
            'diff': diff,
        },
    })


# 프롬프트 옵션
@login_required
def menu_permission(request):
    from accounts.models import MenuPermission
    admin_menus = MenuPermission.objects.filter(role='admin')
    member_menus = MenuPermission.objects.filter(role='member')
    return render(request, 'dashboard/menu_permission.html', {
        'admin_menus': admin_menus,
        'member_menus': member_menus,
    })


@login_required
def prompt_list(request):
    content_types = ContentType.objects.prefetch_related(
        'channel_prompts__channel',
        'channel_prompts__option_groups'
    ).all()
    return render(request, 'dashboard/prompt_list.html', {
        'content_types': content_types,
    })


@login_required
def prompt_option_manage(request, channel_prompt_pk):
    from content.models import PromptOptionGroup
    cp = get_object_or_404(ChannelPrompt, pk=channel_prompt_pk)
    option_groups = cp.option_groups.prefetch_related('options').all()
    selected_group = None
    group_pk = request.GET.get('group')
    if group_pk:
        selected_group = get_object_or_404(PromptOptionGroup, pk=group_pk)
    return render(request, 'dashboard/prompt_option_form.html', {
        'channel_prompt': cp,
        'option_groups': option_groups,
        'selected_group': selected_group,
    })


@login_required
def option_group_create(request, channel_prompt_pk):
    from content.models import PromptOptionGroup
    cp = get_object_or_404(ChannelPrompt, pk=channel_prompt_pk)
    if request.method == 'POST':
        PromptOptionGroup.objects.create(
            channel_prompt=cp,
            name=request.POST.get('name', '').strip(),
            label=request.POST.get('label', '').strip(),
        )
        messages.success(request, '옵션 그룹이 추가됐습니다.')
    return redirect('dashboard:prompt_option_manage', channel_prompt_pk=cp.pk)


@login_required
def option_group_delete(request, pk):
    from content.models import PromptOptionGroup
    group = get_object_or_404(PromptOptionGroup, pk=pk)
    cp_pk = group.channel_prompt.pk
    if request.method == 'POST':
        group.delete()
        messages.success(request, '옵션 그룹이 삭제됐습니다.')
    url = reverse('dashboard:prompt_option_manage', kwargs={'channel_prompt_pk': cp_pk})
    return redirect(url)


@login_required
def option_create(request, group_pk):
    from content.models import PromptOptionGroup, PromptOption
    group = get_object_or_404(PromptOptionGroup, pk=group_pk)
    if request.method == 'POST':
        PromptOption.objects.create(
            group=group,
            label=request.POST.get('label', '').strip(),
            snippet=request.POST.get('snippet', '').strip(),
            is_default=request.POST.get('is_default') == 'on',
        )
        messages.success(request, '옵션이 추가됐습니다.')
    url = reverse('dashboard:prompt_option_manage', kwargs={'channel_prompt_pk': group.channel_prompt.pk})
    return redirect(f"{url}?group={group.pk}")


@login_required
def option_delete(request, pk):
    from content.models import PromptOption
    opt = get_object_or_404(PromptOption, pk=pk)
    group = opt.group
    cp_pk = group.channel_prompt.pk
    opt.delete()
    messages.success(request, '옵션이 삭제됐습니다.')
    url = reverse('dashboard:prompt_option_manage', kwargs={'channel_prompt_pk': cp_pk})
    return redirect(f"{url}?group={group.pk}")