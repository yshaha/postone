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
    source_file = request.FILES.get('source_file')
    image_files = request.FILES.getlist('image_files')

    # 파일에서 텍스트 추출
    if source_file and not source_text:
        try:
            from .services.file_parser import extract_text
            source_text = extract_text(source_file)
        except Exception as e:
            return JsonResponse({'error': f'파일 읽기 오류: {str(e)}'}, status=400)

    if not all([content_type_id, channel_id, source_text]):
        return JsonResponse({'error': '필수 항목을 입력해 주세요.'}, status=400)

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

    try:
        cp = ChannelPrompt.objects.get(
            content_type_id=content_type_id,
            channel_id=channel_id,
            is_active=True
        )
    except ChannelPrompt.DoesNotExist:
        return JsonResponse({'error': '프롬프트 설정이 없습니다.'}, status=400)

    # 옵션 snippet 수집
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

    # 선택된 옵션 저장
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

    # 이미지 처리
    image_url = None
    if image_files or True:
        try:
            from .services.image import process_images
            channel = content_request.channel
            process_images(
                generation=content_request,
                uploaded_files=image_files,
                channel_type=channel.slug,
                title=result_text[:50],
                keyword=source_text[:20],
                tags=[],
                category='일반',
            )
            content_request.refresh_from_db()
            if content_request.thumbnail:
                image_url = content_request.thumbnail.url
            elif content_request.text_card:
                image_url = content_request.text_card.url
        except Exception:
            pass

    # 크레딧 차감
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

    return JsonResponse({
        'result': result_text,
        'image_url': image_url,
        'request_id': content_request.pk,
    })

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

@login_required
@require_POST
def generate_base_prompt(request):
    import json
    data = json.loads(request.body)
    content_type = data.get('content_type', '')
    channel = data.get('channel', '')

    prompt = f"""당신은 AI 콘텐츠 생성 시스템의 프롬프트 엔지니어입니다.
아래 조건에 맞는 최적화된 기본 프롬프트를 작성해 주세요.

- 콘텐츠 유형: {content_type}
- 채널: {channel}

이 프롬프트는 사용자가 소재를 입력하면 Claude가 해당 채널에 최적화된 콘텐츠를 생성하는 데 사용됩니다.
채널의 특성(글자수, 형식, 톤, 해시태그 등)을 반영한 구체적인 지시문을 작성해 주세요.
프롬프트만 출력하고 다른 설명은 하지 마세요."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        generated_prompt = message.content[0].text.strip()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'prompt': generated_prompt})


@login_required
@require_POST
def compare_prompts(request):
    import json
    data = json.loads(request.body)
    prompt_a = data.get('prompt_a', '')
    prompt_b = data.get('prompt_b', '')
    content_type = data.get('content_type', '')
    channel = data.get('channel', '')

    sample_source = f"{content_type} 관련 소재 예시입니다. 이것을 바탕으로 콘텐츠를 생성해 주세요."

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # 샘플 A 생성
        msg_a = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=500,
            messages=[{'role': 'user', 'content': prompt_a + f'\n\n---\n소재:\n{sample_source}'}]
        )
        sample_a = msg_a.content[0].text.strip()

        # 샘플 B 생성
        msg_b = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=500,
            messages=[{'role': 'user', 'content': prompt_b + f'\n\n---\n소재:\n{sample_source}'}]
        )
        sample_b = msg_b.content[0].text.strip()

        # AI 결합 프롬프트 생성 및 샘플
        combine_prompt = f"""아래 두 프롬프트의 장점을 결합해서 {channel} 채널의 {content_type} 콘텐츠 생성에 최적화된 하나의 프롬프트를 만들어 주세요.

프롬프트 A:
{prompt_a}

프롬프트 B:
{prompt_b}

결합된 최적화 프롬프트만 출력하세요."""

        msg_combined_prompt = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            messages=[{'role': 'user', 'content': combine_prompt}]
        )
        combined_prompt = msg_combined_prompt.content[0].text.strip()

        msg_combined = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=500,
            messages=[{'role': 'user', 'content': combined_prompt + f'\n\n---\n소재:\n{sample_source}'}]
        )
        sample_combined = msg_combined.content[0].text.strip()

        # 품질 점수 (글자수, 구조 등 간단한 휴리스틱)
        def score(text):
            s = min(100, len(text) // 3)
            return s

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({
        'sample_a': sample_a,
        'sample_b': sample_b,
        'sample_combined': sample_combined,
        'score_a': score(sample_a),
        'score_b': score(sample_b),
        'score_combined': score(sample_combined),
        'combined_prompt': combined_prompt,
    })


@login_required
@require_POST
def get_combined_prompt(request):
    import json
    data = json.loads(request.body)
    prompt_a = data.get('prompt_a', '')
    prompt_b = data.get('prompt_b', '')

    combine_prompt = f"""아래 두 프롬프트의 장점을 결합해서 최적화된 하나의 프롬프트를 만들어 주세요.

프롬프트 A:
{prompt_a}

프롬프트 B:
{prompt_b}

결합된 최적화 프롬프트만 출력하세요."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            messages=[{'role': 'user', 'content': combine_prompt}]
        )
        combined_prompt = message.content[0].text.strip()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'combined_prompt': combined_prompt})

@login_required
@require_POST
def channel_create(request):
    import json
    data = json.loads(request.body)
    try:
        Channel.objects.create(
            name=data.get('name', '').strip(),
            slug=data.get('slug', '').strip(),
            channel_type=data.get('channel_type', 'text'),
            description=data.get('description', '').strip(),
            order=int(data.get('order', 0)),
            is_auto_publish=data.get('is_auto_publish', False),
            is_active=data.get('is_active', True),
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def channel_edit(request, pk):
    import json
    data = json.loads(request.body)
    try:
        channel = Channel.objects.get(pk=pk)
        channel.name = data.get('name', '').strip()
        channel.slug = data.get('slug', '').strip()
        channel.channel_type = data.get('channel_type', 'text')
        channel.description = data.get('description', '').strip()
        channel.order = int(data.get('order', 0))
        channel.is_auto_publish = data.get('is_auto_publish', False)
        channel.is_active = data.get('is_active', True)
        channel.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def content_type_create(request):
    import json
    data = json.loads(request.body)
    try:
        ContentType.objects.create(
            name=data.get('name', '').strip(),
            description=data.get('description', '').strip(),
            is_active=data.get('is_active', True),
            created_by=request.user,
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def content_type_edit(request, pk):
    import json
    data = json.loads(request.body)
    try:
        ct = ContentType.objects.get(pk=pk)
        ct.name = data.get('name', '').strip()
        ct.description = data.get('description', '').strip()
        ct.is_active = data.get('is_active', True)
        ct.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@login_required
@require_POST
def user_delete(request, pk):
    from accounts.models import User
    from django.shortcuts import get_object_or_404
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '잘못된 요청입니다.'})
    target_user = get_object_or_404(User, pk=pk)
    if target_user == request.user:
        return JsonResponse({'success': False, 'error': '자기 자신은 삭제할 수 없습니다.'})
    target_user.delete()
    return JsonResponse({'success': True})


def user_edit(request, pk):
    import json
    from accounts.models import User
    data = json.loads(request.body)
    try:
        user = User.objects.get(pk=pk)
        user.first_name = data.get('first_name', '')
        user.email = data.get('email', '')
        user.company = data.get('company', '')
        user.phone = data.get('phone', '')
        user.role = data.get('role', 'member')
        user.is_active = data.get('is_active', True)
        user.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def user_credit_grant(request, pk):
    import json
    from accounts.models import User
    from credits.models import UserCredit, CreditTransaction
    data = json.loads(request.body)
    try:
        target_user = User.objects.get(pk=pk)
        amount = int(data.get('amount', 0))
        description = data.get('description', '관리자 직접 지급')
        if amount < 1:
            return JsonResponse({'error': '크레딧 수량을 확인해 주세요.'}, status=400)
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
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def option_group_create(request, channel_prompt_pk):
    import json
    from content.models import PromptOptionGroup
    data = json.loads(request.body)
    try:
        cp = ChannelPrompt.objects.get(pk=channel_prompt_pk)
        PromptOptionGroup.objects.create(
            channel_prompt=cp,
            name=data.get('name', '').strip(),
            label=data.get('label', '').strip(),
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def option_create(request, group_pk):
    import json
    from content.models import PromptOptionGroup, PromptOption
    data = json.loads(request.body)
    try:
        group = PromptOptionGroup.objects.get(pk=group_pk)
        PromptOption.objects.create(
            group=group,
            label=data.get('label', '').strip(),
            snippet=data.get('snippet', '').strip(),
            is_default=data.get('is_default', False),
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)  
    
@login_required
@require_POST
def menu_permission_toggle(request, pk):
    import json
    from accounts.models import MenuPermission
    data = json.loads(request.body)
    try:
        menu = MenuPermission.objects.get(pk=pk)
        menu.is_visible = data.get('is_visible', True)
        menu.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)  