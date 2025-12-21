#!/usr/bin/env python3
from __future__ import annotations

"""
Manual test for the gemini-api-wrapper server API: only POST /api/new_chat.

Usage:
    python tests/test_manual_api_curl.py --base http://localhost:3000

Equivalent curl:
    curl -v -X POST http://localhost:3000/api/new_chat -H "Content-Type: application/json" -d '{"user_id": "manual_test", "message": "Hello new chat!"}'
"""
import argparse
import json
import sys
from typing import Optional

import requests


def post_json(url: str, body: dict, timeout: int = 30) -> requests.Response:
    headers = {"Content-Type": "application/json"}
    return requests.post(url, json=body, headers=headers, timeout=timeout)


def try_json(resp: requests.Response):
    try:
        return resp.json()
    except ValueError:
        return None




def test_new_chat(base: str) -> bool:
    url = base.rstrip('/') + '/api/new_chat'
    payload = {"user_id": "manual_test", "message": "Hello new chat!"}
    print(f"-> POST {url} payload={payload}")
    resp = post_json(url, payload)
    print(f"   status={resp.status_code}")
    body = try_json(resp)
    if body is not None:
        print("   json:", json.dumps(body, ensure_ascii=False, indent=2))
    else:
        print("   response:", resp.text)
    return resp.status_code == 200

def test_set_mode(base: str) -> bool:
    url = base.rstrip('/') + '/api/set_mode'
    payload = {"mode": "thinking"}
    print(f"-> POST {url} payload={payload}")
    resp = post_json(url, payload)
    print(f"   status={resp.status_code}")
    body = try_json(resp)
    if body is not None:
        print("   json:", json.dumps(body, ensure_ascii=False, indent=2))
    else:
        print("   response:", resp.text)
    return resp.status_code == 200

def test_ask(base: str) -> bool:
    url = base.rstrip('/') + '/api/ask'
    payload = {"prompt": "記事タイトルを考えてください"}
    print(f"-> POST {url} payload={payload}")
    resp = post_json(url, payload)
    print(f"   status={resp.status_code}")
    body = try_json(resp)
    if body is not None:
        print("   json:", json.dumps(body, ensure_ascii=False, indent=2))
    else:
        print("   response:", resp.text)
    return resp.status_code == 200


def test_press_image_icon(base: str) -> bool:
    url = base.rstrip('/') + '/api/press_image_icon'
    payload = {}
    print(f"-> POST {url} payload={payload}")
    resp = post_json(url, payload)
    print(f"   status={resp.status_code}")
    body = try_json(resp)
    if body is not None:
        print("   json:", json.dumps(body, ensure_ascii=False, indent=2))
    else:
        print("   response:", resp.text)
    return resp.status_code == 200


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', '-b', default='http://localhost:3000', help='Base URL of server')
    parser.add_argument('--test', '-t', default='new_chat', choices=['new_chat', 'set_mode', 'ask', 'press_image_icon', 'all'], help='Which endpoint to test')
    args = parser.parse_args()

    base = args.base
    test = args.test

    tests = {
        'new_chat': test_new_chat,
        'set_mode': test_set_mode,
        'ask': test_ask,
        'press_image_icon': test_press_image_icon,
    }

    if test == 'all':
        results = []
        for name, fn in tests.items():
            print(f'\n=== test: {name} ===')
            ok = fn(base)
            results.append(ok)
        print('\n=== RESULT ===')
        if all(results):
            print('All selected tests passed ✅')
            sys.exit(0)
        else:
            print('One or more tests failed ⚠️')
            sys.exit(2)
    else:
        print(f'\n=== test: {test} ===')
        ok = tests[test](base)
        print('\n=== RESULT ===')
        if ok:
            print(f'{test} test passed ✅')
            sys.exit(0)
        else:
            print(f'{test} test failed ⚠️')
            sys.exit(2)


if __name__ == '__main__':
    main()