from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

from app.models.schemas import AppConfig, Exchange, ExchangeCredentialValidationResult


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _result(
    exchange: Exchange,
    state: str,
    message: str,
    *,
    can_trade: bool | None = None,
) -> ExchangeCredentialValidationResult:
    return ExchangeCredentialValidationResult(
        exchange=exchange,
        state=state,
        checked_at=utcnow(),
        can_trade=can_trade,
        message=message,
    )


def _extract_error_message(payload: object, fallback: str) -> str:
    if isinstance(payload, dict):
        nested_error = payload.get("error")
        if isinstance(nested_error, dict):
            if isinstance(nested_error.get("message"), str):
                return nested_error["message"]
            if isinstance(nested_error.get("reason"), str):
                return nested_error["reason"]
        if isinstance(payload.get("message"), str):
            return payload["message"]
        if isinstance(payload.get("msg"), str):
            return payload["msg"]
        if isinstance(payload.get("code"), str):
            return payload["code"]
    return fallback


async def _validate_binance(api_key: str, api_secret: str) -> ExchangeCredentialValidationResult:
    if not api_key or not api_secret:
        return _result(Exchange.BINANCE, "missing", "Chave e secret ausentes.")

    params = {
        "recvWindow": 5000,
        "timestamp": int(time.time() * 1000),
    }
    query = urlencode(params)
    signature = hmac.new(api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()

    async with httpx.AsyncClient(base_url="https://api.binance.com", timeout=httpx.Timeout(15.0)) as client:
        response = await client.get(
            "/api/v3/account",
            params={**params, "signature": signature},
            headers={"X-MBX-APIKEY": api_key},
        )

    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = None

    if response.status_code == 200 and isinstance(payload, dict):
        can_trade = bool(payload.get("canTrade"))
        permissions = payload.get("permissions") or []
        if can_trade:
            return _result(
                Exchange.BINANCE,
                "valid",
                f"Conta autenticada. Permissões: {', '.join(permissions) if permissions else 'não informadas'}.",
                can_trade=True,
            )
        return _result(
            Exchange.BINANCE,
            "no_trading_permission",
            "Credencial válida, mas a conta não possui permissão de trading.",
            can_trade=False,
        )

    return _result(
        Exchange.BINANCE,
        "invalid",
        _extract_error_message(payload, "Falha ao autenticar na Binance."),
        can_trade=False,
    )


def _novadax_signature(path: str, api_secret: str, timestamp: str, params: dict[str, object] | None = None) -> str:
    params = params or {}
    sorted_query = urlencode(sorted((key, str(value)) for key, value in params.items()))
    sign_str = f"GET\n{path}\n{sorted_query}\n{timestamp}"
    return hmac.new(api_secret.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256).hexdigest()


async def _novadax_signed_get(
    client: httpx.AsyncClient,
    *,
    path: str,
    api_key: str,
    api_secret: str,
    params: dict[str, object] | None = None,
) -> tuple[httpx.Response, object]:
    timestamp = str(int(time.time() * 1000))
    response = await client.get(
        path,
        params=params,
        headers={
            "X-Nova-Access-Key": api_key,
            "X-Nova-Signature": _novadax_signature(path, api_secret, timestamp, params),
            "X-Nova-Timestamp": timestamp,
        },
    )
    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = None
    return response, payload


async def _validate_novadax(api_key: str, api_secret: str) -> ExchangeCredentialValidationResult:
    if not api_key or not api_secret:
        return _result(Exchange.NOVADAX, "missing", "Chave e secret ausentes.")

    async with httpx.AsyncClient(base_url="https://api.novadax.com", timeout=httpx.Timeout(15.0)) as client:
        balance_response, balance_payload = await _novadax_signed_get(
            client,
            path="/v1/account/getBalance",
            api_key=api_key,
            api_secret=api_secret,
        )

        if balance_response.status_code != 200 or not isinstance(balance_payload, dict) or balance_payload.get("code") != "A10000":
            return _result(
                Exchange.NOVADAX,
                "invalid",
                _extract_error_message(balance_payload, "Falha ao autenticar na NovaDAX."),
                can_trade=False,
            )

        orders_response, orders_payload = await _novadax_signed_get(
            client,
            path="/v1/orders/list",
            api_key=api_key,
            api_secret=api_secret,
            params={"limit": 1},
        )

    if orders_response.status_code == 200 and isinstance(orders_payload, dict) and orders_payload.get("code") == "A10000":
        return _result(
            Exchange.NOVADAX,
            "valid",
            "Credencial autenticada e endpoint privado de ordens respondeu com sucesso.",
            can_trade=True,
        )

    if orders_response.status_code in {401, 403}:
        return _result(
            Exchange.NOVADAX,
            "no_trading_permission",
            _extract_error_message(
                orders_payload,
                "Credencial autenticada no saldo, mas sem permissão suficiente no endpoint privado de ordens.",
            ),
            can_trade=False,
        )

    return _result(
        Exchange.NOVADAX,
        "error",
        _extract_error_message(orders_payload, "Não foi possível confirmar a permissão de trading na NovaDAX."),
        can_trade=None,
    )


async def _mercado_bitcoin_bearer_token(api_key: str, api_secret: str) -> tuple[str | None, str | None]:
    async with httpx.AsyncClient(base_url="https://api.mercadobitcoin.net", timeout=httpx.Timeout(15.0)) as client:
        response = await client.post(
            "/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "scope": "global",
                "client_id": api_key,
                "client_secret": api_secret,
            },
        )

    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = None

    if response.status_code != 200 or not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
        return None, _extract_error_message(payload, "Falha ao obter token OAuth2 do Mercado Bitcoin.")
    return payload["access_token"], None


async def _validate_mercado_bitcoin(api_key: str, api_secret: str) -> ExchangeCredentialValidationResult:
    if not api_key or not api_secret:
        return _result(Exchange.MERCADO_BITCOIN, "missing", "Chave e secret ausentes.")

    access_token, token_error = await _mercado_bitcoin_bearer_token(api_key, api_secret)
    if access_token is None:
        return _result(Exchange.MERCADO_BITCOIN, "invalid", token_error or "Token OAuth2 inválido.", can_trade=False)

    async with httpx.AsyncClient(base_url="https://api.mercadobitcoin.net", timeout=httpx.Timeout(15.0)) as client:
        accounts_response = await client.get(
            "/api/v4/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            accounts_payload = accounts_response.json()
        except json.JSONDecodeError:
            accounts_payload = None

        if accounts_response.status_code != 200 or not isinstance(accounts_payload, list) or not accounts_payload:
            return _result(
                Exchange.MERCADO_BITCOIN,
                "invalid",
                _extract_error_message(accounts_payload, "Falha ao listar contas do Mercado Bitcoin."),
                can_trade=False,
            )

        account_id = accounts_payload[0].get("id")
        orders_response = await client.get(
            f"/api/v4/accounts/{account_id}/orders",
            params={"size": 1},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            orders_payload = orders_response.json()
        except json.JSONDecodeError:
            orders_payload = None

    if orders_response.status_code == 200:
        return _result(
            Exchange.MERCADO_BITCOIN,
            "valid",
            "Credencial autenticada e endpoint privado de ordens respondeu com sucesso.",
            can_trade=True,
        )

    if orders_response.status_code == 403:
        return _result(
            Exchange.MERCADO_BITCOIN,
            "no_trading_permission",
            _extract_error_message(
                orders_payload,
                "Credencial autenticada, mas sem permissão suficiente para acessar recursos de trading.",
            ),
            can_trade=False,
        )

    return _result(
        Exchange.MERCADO_BITCOIN,
        "error",
        _extract_error_message(orders_payload, "Não foi possível confirmar a permissão de trading no Mercado Bitcoin."),
        can_trade=None,
    )


async def validate_exchange_credentials(config: AppConfig) -> list[ExchangeCredentialValidationResult]:
    novadax = await _validate_novadax(config.novadax_api_key, config.novadax_api_secret)
    mercado_bitcoin = await _validate_mercado_bitcoin(config.mb_api_key, config.mb_api_secret)
    binance = await _validate_binance(config.binance_api_key, config.binance_api_secret)
    return [novadax, mercado_bitcoin, binance]