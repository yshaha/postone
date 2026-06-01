import json
import anthropic
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Channel, ChannelPrompt, PromptOption, ContentRequest
from credits.models import UserCredit, CreditTransaction


@login_required
@require_GET
def channel_list(request):
    content_type_id = request.GET.get('content_type')
    if not content_type_id:
        return JsonResponse({'channels': []})

    prompt_channel_ids = ChannelPrompt.objects.filter(
        content_type_id=content_type_id,
        is_active=True
    ).values_list('channel_id', flat=True)

    channels = Channel.objects.filter(
        id__in=prompt_channel_ids, is_active=True
    )
    return JsonResponse({
        'channels': [{'id': ch.id, 'name': ch.name} for ch in channels]
    })


@login_required
@require_GET
def option_list(request):
    content_type_id = request.GET.get('content_type')
    channel_id = request.GET.get('channel')

    try:
        cp = ChannelPrompt.objects.get(
            content_type_id=content_type_id,
            channel_id=channel_id,
            is_active=True
        )
    except ChannelPrompt.DoesNotExist:
        return JsonResponse({'groups': []})

    groups = []
    for group in cp.option_groups.prefetch_related('options').all():
        groups.append({
            'id': group.id,
            'label': group.label,
            'options': [
                {
                    'id': opt.id,
                    'label': opt.label,
                    'is_default': opt.is_default,
                }
                for opt in group.options.all()
            ]
        })
    return JsonResponse({'groups': groups})


@login_required
@require_POST
def generate(request):
    content_type_id = request.POST.get('content_type')
    channel_id = request.POST.get('channel')
    source_text = request.POST.get('source_text', '').strip()

    if not all([content_type_id, channel_id, source_text]):
        return JsonResponse({'error': '필수 항목을 입력해 주세요.'}, status=400)

    # 크레딧 확인
    user = request.user
    try:
        uc = user.credit
    except UserCredit.DoesNotExist:
        uc = UserCredit.objects.create(user=user, balance=0)

    is_free = user.is_admin
    if not is_free:
        if uc.free_used_this_month < settings.FREE_MONTHLY_LIMIT:
            is_free = True
        elif uc.balance < 1:
            return JsonResponse({'error': '크레딧이 부족합니다.'}, status=400)

    # 프롬프트 구성
    try:
        cp = ChannelPrompt.objects.get(
            content_type_id=content_type_id,
            channel_id=channel_id,
            is_active=True
        )
    except ChannelPrompt.DoesNotExist:
        return JsonResponse({'error': '프롬프트 설정이 없습니다.'}, status=400)

    # 선택된 옵션 snippet 수집
    option_snippets = []
    for key, value in request.POST.items():
        if key.startswith('option_'):
            try:
                opt = PromptOption.objects.get(pk=value)
                option_snippets.append(opt.snippet)
            except PromptOption.DoesNotExist:
                pass

    # 최종 프롬프트 조합
    final_prompt = cp.base_prompt
    if option_snippets:
        final_prompt += '\n\n' + '\n'.join(option_snippets)
    final_prompt += f'\n\n---\n소재:\n{source_text}'

    # Claude API 호출
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=2000,
            messages=[{'role': 'user', 'content': final_prompt}]
        )
        result_text = message.content[0].text
    except Exception as e:
        return JsonResponse({'error': f'생성 중 오류: {str(e)}'}, status=500)

    # 크레딧 차감
    selected_options = {}
    for key, value in request.POST.items():
        if key.startswith('option_'):
            selected_options[key] = value

    content_request = ContentRequest.objects.create(
        user=user,
        content_type_id=content_type_id,
        channel_id=channel_id,
        source_text=source_text,
        selected_options=selected_options,
        result_text=result_text,
        status='done',
        credit_used=0 if is_free else 1,
    )

    if is_free:
        if not user.is_admin:
            uc.free_used_this_month += 1
            uc.save()
        CreditTransaction.objects.create(
            user=user,
            transaction_type='free',
            amount=0,
            balance_after=uc.balance,
            description='무료 생성',
            related_request=content_request,
        )
    else:
        uc.balance -= 1
        uc.save()
        CreditTransaction.objects.create(
            user=user,
            transaction_type='use',
            amount=-1,
            balance_after=uc.balance,
            description='콘텐츠 생성',
            related_request=content_request,
        )

    return JsonResponse({'result': result_text})

@login_required
@require_GET
def request_detail(request, pk):
    from django.shortcuts import get_object_or_404
    req = get_object_or_404(ContentRequest, pk=pk, user=request.user)
    return JsonResponse({
        'source_text': req.source_text,
        'result_text': req.result_text,
        'status': req.status,
    })

@login_required
@require_POST
def generate_snippet(request):
    import json
    data = json.loads(request.body)
    channel = data.get('channel', '')
    content_type = data.get('content_type', '')
    group_label = data.get('group_label', '')
    option_label = data.get('option_label', '')

    prompt = f"""당신은 AI 콘텐츠 생성 시스템의 프롬프트 엔지니어입니다.
아래 조건에 맞는 프롬프트 snippet을 작성해 주세요.

- 채널: {channel}
- 콘텐츠 유형: {content_type}
- 옵션 그룹: {group_label}
- 옵션명: {option_label}

이 snippet은 기본 프롬프트 뒤에 추가되어 Claude에게 전달됩니다.
"{option_label}" 스타일로 콘텐츠를 생성하도록 지시하는 간결한 문장으로 작성해 주세요.
snippet만 출력하고 다른 설명은 하지 마세요."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=300,
            messages=[{'role': 'user', 'content': prompt}]
        )
        snippet = message.content[0].text.strip()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'snippet': snippet})