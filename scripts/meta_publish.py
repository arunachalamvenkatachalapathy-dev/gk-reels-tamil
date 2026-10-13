"""Dedicated Tamil Meta consumers. No credential logging or automatic retries."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Supported version verified against Meta's version table on 2026-10-14.
GRAPH = 'https://graph.facebook.com/v26.0'
PAGE_ID = '1443299385526347'
APP_ID = '2309390193185830'
IG_USERNAME = 'gk_snippets_tamil'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RuntimeError('Authenticated Meta request cannot redirect')

AUTH_HTTP = urllib.request.build_opener(NoRedirect)


def secret(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise RuntimeError('Missing repository secret: ' + name)
    return value


def graph(method, path, token, values=None):
    values = values or {}
    url = GRAPH + '/' + path
    data = None
    if method == 'GET':
        url += '?' + urllib.parse.urlencode(values)
    else:
        data = urllib.parse.urlencode(values).encode()
    request = urllib.request.Request(url, data=data, method=method,
        headers={'Authorization': 'Bearer ' + token})
    try:
        with AUTH_HTTP.open(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Never include a URL, request, token, or untrusted API error body.
        raise RuntimeError('Meta API request failed: HTTP ' + str(error.code)) from None
    except Exception:
        raise RuntimeError('Meta API transport or response failure') from None


def preflight():
    token = secret('IG_ACCESS_TOKEN')
    page = secret('FB_PAGE_ID')
    ig = secret('IG_USER_ID')
    if page != PAGE_ID or not ig.isdigit():
        raise RuntimeError('Tamil Meta destination configuration mismatch')
    debug = graph('GET', 'debug_token', token, {'input_token': token}).get('data', {})
    required = {'pages_show_list', 'pages_read_engagement', 'pages_manage_posts',
                'instagram_basic', 'instagram_content_publish'}
    if (not debug.get('is_valid') or str(debug.get('app_id')) != APP_ID
            or debug.get('type') != 'PAGE' or str(debug.get('profile_id')) != PAGE_ID
            or not required.issubset(set(debug.get('scopes', [])))):
        raise RuntimeError('Dedicated Tamil Page token identity or scopes not verified')
    for field in ('expires_at', 'data_access_expires_at'):
        expiry = debug.get(field)
        if expiry is None or (expiry != 0 and expiry <= time.time() + 900):
            raise RuntimeError('Tamil token expiry not safe for this publication')
    identity = graph('GET', 'me', token, {'fields': 'id,instagram_business_account'})
    linked = identity.get('instagram_business_account', {}).get('id')
    if str(identity.get('id')) != PAGE_ID or str(linked) != ig:
        raise RuntimeError('Token Page identity or Instagram linkage mismatch')
    account = graph('GET', ig, token, {'fields': 'id,username'})
    if str(account.get('id')) != ig or account.get('username') != IG_USERNAME:
        raise RuntimeError('Existing Tamil Instagram account identity mismatch')
    limit = graph('GET', ig + '/content_publishing_limit', token,
                  {'fields': 'quota_usage,config'}).get('data', [])
    if not limit or limit[0].get('quota_usage', 100) >= 100:
        raise RuntimeError('Instagram publishing quota not available')
    return {'page_id': page, 'instagram_id': ig, 'instagram_username': IG_USERNAME,
            'app_id': APP_ID, 'graph_version': 'v26.0'}


def public_video(url, expected_hash):
    if not url.startswith('https://'):
        raise ValueError('Instagram requires an approved public HTTPS video URL')
    try:
        # No cookies or Authorization headers. The approved URL stays unchanged.
        request = urllib.request.Request(url, headers={'User-Agent':
            'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'})
        with urllib.request.urlopen(request, timeout=90) as response:
            if not response.geturl().startswith('https://'):
                raise ValueError('Non-HTTPS video redirect')
            content = response.read()
        if hashlib.sha256(content).hexdigest() != expected_hash:
            raise ValueError('Public video hash mismatch or hosting returned a login/HTML page')
    except ValueError:
        raise
    except Exception:
        raise RuntimeError('Public video URL could not be verified anonymously') from None
    return content


def publish_reel(video_url, caption, checkpoint):
    if len(caption) > 2200:
        raise ValueError('Instagram caption exceeds 2200 characters')
    token, ig = secret('IG_ACCESS_TOKEN'), secret('IG_USER_ID')
    container = graph('POST', ig + '/media', token,
        {'media_type': 'REELS', 'video_url': video_url, 'caption': caption}).get('id')
    if not container:
        raise RuntimeError('Instagram container receipt missing')
    checkpoint({'container_id': str(container), 'phase': 'processing'})
    for attempt in range(5):
        code = graph('GET', str(container), token, {'fields': 'status_code'}).get('status_code')
        if code == 'FINISHED':
            break
        if code in ('ERROR', 'EXPIRED', 'PUBLISHED'):
            raise RuntimeError('Instagram container requires reconciliation: ' + code)
        if attempt < 4:
            time.sleep(60)
    else:
        raise TimeoutError('Instagram container processing timed out')
    checkpoint({'phase': 'publishing'})
    media_id = graph('POST', ig + '/media_publish', token,
                     {'creation_id': container}).get('id')
    if not media_id:
        raise RuntimeError('Instagram publication receipt missing')
    # Persist the confirmed ID before any optional permalink read can fail.
    receipt = {'id': str(media_id), 'container_id': str(container), 'status': 'published'}
    checkpoint(receipt)
    try:
        permalink = graph('GET', str(media_id), token, {'fields': 'permalink'}).get('permalink')
        if permalink:
            receipt['url'] = permalink
    except Exception:
        pass
    return receipt


def publish_facebook_reel(video_path, title, description, checkpoint):
    page, token = secret('FB_PAGE_ID'), secret('IG_ACCESS_TOKEN')
    if page != PAGE_ID:
        raise RuntimeError('Wrong Tamil Facebook Page')
    start = graph('POST', page + '/video_reels', token, {'upload_phase': 'start'})
    video_id, upload_url = start.get('video_id'), start.get('upload_url', '')
    if not video_id:
        raise RuntimeError('Facebook upload session receipt missing')
    checkpoint({'id': str(video_id), 'phase': 'uploading'})
    parsed = urllib.parse.urlparse(upload_url)
    if parsed.scheme != 'https' or parsed.hostname != 'rupload.facebook.com':
        raise RuntimeError('Facebook returned an unexpected binary upload host')
    content = Path(video_path).read_bytes()
    request = urllib.request.Request(upload_url, data=content, method='POST', headers={
        'Authorization': 'OAuth ' + token, 'offset': '0', 'file_size': str(len(content)),
        'Content-Type': 'application/octet-stream'})
    try:
        with AUTH_HTTP.open(request, timeout=120) as response:
            uploaded = json.load(response)
    except Exception:
        raise RuntimeError('Facebook binary upload response uncertain') from None
    if uploaded.get('success') is not True:
        raise RuntimeError('Facebook binary upload not confirmed')
    checkpoint({'phase': 'publishing'})
    finish = graph('POST', page + '/video_reels', token, {'upload_phase': 'finish',
        'video_id': video_id, 'video_state': 'PUBLISHED', 'description': description,
        'title': title})
    if finish.get('success') is not True:
        raise RuntimeError('Facebook publication acceptance not confirmed')
    checkpoint({'phase': 'accepted'})
    for attempt in range(5):
        status = graph('GET', str(video_id), token, {'fields': 'status'}).get('status', {})
        if status.get('publishing_phase', {}).get('status') == 'complete':
            receipt = {'id': str(video_id), 'status': 'published'}
            checkpoint(receipt)
            try:
                link = graph('GET', str(video_id), token, {'fields': 'permalink_url'}).get('permalink_url')
                if link:
                    receipt['url'] = link
            except Exception:
                pass
            return receipt
        if status.get('video_status') == 'error':
            raise RuntimeError('Facebook processing failed; reconciliation required')
        if attempt < 4:
            time.sleep(60)
    raise TimeoutError('Facebook publication not yet confirmed; reconcile before retry')
