import json
import requests

import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 API 키와 시크릿 로드
TOSS_API_KEY = os.environ.get("TOSS_API_KEY")
TOSS_API_SECRET = os.environ.get("TOSS_API_SECRET")
BASE_URL = "https://openapi.tossinvest.com"

def get_access_token() -> str:
    if not TOSS_API_KEY or not TOSS_API_SECRET:
        raise ValueError("TOSS_API_KEY and TOSS_API_SECRET 환경변수가 설정되어 있어야 합니다.")
        
    url = f"{BASE_URL}/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": TOSS_API_KEY,
        "client_secret": TOSS_API_SECRET
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(url, data=payload, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    return data.get("access_token")

def get_account_seq(access_token: str) -> int:
    url = f"{BASE_URL}/api/v1/accounts"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    accounts_data = response.json()
    
    if "result" in accounts_data and isinstance(accounts_data["result"], list) and len(accounts_data["result"]) > 0:
        return accounts_data["result"][0].get("accountSeq")
    elif isinstance(accounts_data, list) and len(accounts_data) > 0:
        return accounts_data[0].get("accountSeq")
    elif "accountSeq" in accounts_data:
        return accounts_data["accountSeq"]
    
    raise ValueError(f"사용 가능한 계좌(accountSeq)를 찾을 수 없습니다. API 응답: {accounts_data}")

def get_portfolio_balance_and_return_rate_api() -> str:
    """내 포트폴리오 잔고 및 수익률을 조회합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/holdings"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq)
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        holdings_data = response.json()
        return json.dumps(holdings_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"Error: 포트폴리오 정보를 가져오는 중 오류가 발생했습니다. ({str(e)})"

def buy_stock_api(symbol: str, order_type: str, quantity: int, price: float = 0.0) -> str:
    """토스증권 API를 사용하여 주식을 매수합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/orders"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq),
            "Content-Type": "application/json"
        }
        
        payload = {
            "symbol": symbol,
            "side": "BUY",
            "orderType": order_type,
            "quantity": str(quantity)
        }
        if order_type == "LIMIT":
            if price <= 0:
                return "지정가(LIMIT) 매수 시 가격을 지정해야 합니다."
            payload["price"] = str(int(price)) if price == int(price) else str(price)
            
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            order_id = data.get("result", {}).get("orderId", "N/A")
            return f"[{symbol}] {quantity}주 매수 주문({order_type})이 접수되었습니다. (주문번호: {order_id})"
        else:
            return f"매수 주문 실패 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"매수 주문 중 오류 발생: {str(e)}"

def sell_stock_api(symbol: str, order_type: str, quantity: int, price: float = 0.0) -> str:
    """토스증권 API를 사용하여 주식을 매도합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/orders"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq),
            "Content-Type": "application/json"
        }
        
        payload = {
            "symbol": symbol,
            "side": "SELL",
            "orderType": order_type,
            "quantity": str(quantity)
        }
        if order_type == "LIMIT":
            if price <= 0:
                return "지정가(LIMIT) 매도 시 가격을 지정해야 합니다."
            payload["price"] = str(int(price)) if price == int(price) else str(price)
            
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            order_id = data.get("result", {}).get("orderId", "N/A")
            return f"[{symbol}] {quantity}주 매도 주문({order_type})이 접수되었습니다. (주문번호: {order_id})"
        else:
            return f"매도 주문 실패 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"매도 주문 중 오류 발생: {str(e)}"

def get_buying_power_api(currency: str = "KRW") -> str:
    """토스증권 API를 사용하여 계좌의 예수금을 조회합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/buying-power?currency={currency}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq)
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result = data.get("result", {})
            amount = result.get("cashBuyingPower", "N/A")
            return f"💰 현재 계좌의 예수금(주문 가능 금액)은 {amount} {currency} 입니다."
        else:
            return f"예수금 조회 실패 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"예수금 조회 중 오류 발생: {str(e)}"

def create_conditional_order_api(symbol: str, type_val: str, quantity: int, expire_date: str, first: dict, second: dict = None, order_type: str = "LIMIT") -> str:
    """조건주문을 생성합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/conditional-orders"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq),
            "Content-Type": "application/json"
        }
        
        payload = {
            "symbol": symbol,
            "type": type_val,
            "quantity": str(quantity),
            "orderType": order_type,
            "expireDate": expire_date,
            "first": first
        }
        if second:
            payload["second"] = second
            
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            order_id = data.get("result", {}).get("conditionalOrderId", "N/A")
            return f"[{symbol}] 조건주문이 성공적으로 접수되었습니다. (조건주문 식별자: {order_id})"
        else:
            return f"조건주문 생성 실패 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"조건주문 생성 중 오류 발생: {str(e)}"

def get_conditional_orders_api(status: str = "OPEN", symbol: str = None) -> str:
    """조건주문 목록을 조회합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/conditional-orders?status={status}"
        if symbol:
            url += f"&symbol={symbol}"
            
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq)
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return f"조건주문 조회 실패 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"조건주문 조회 중 오류 발생: {str(e)}"

def get_conditional_order_detail_api(conditional_order_id: str) -> str:
    """조건주문 상세를 조회합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/conditional-orders/{conditional_order_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq)
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return f"조건주문 상세 조회 실패 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"조건주문 상세 조회 중 오류 발생: {str(e)}"

def modify_conditional_order_api(conditional_order_id: str, type_val: str, quantity: int, expire_date: str, first: dict, second: dict = None, order_type: str = "LIMIT") -> str:
    """조건주문을 수정합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/conditional-orders/{conditional_order_id}/modify"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq),
            "Content-Type": "application/json"
        }
        
        payload = {
            "type": type_val,
            "quantity": str(quantity),
            "orderType": order_type,
            "expireDate": expire_date,
            "first": first
        }
        if second:
            payload["second"] = second
            
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            new_order_id = data.get("result", {}).get("conditionalOrderId", "N/A")
            return f"조건주문이 성공적으로 수정되었습니다. (새 조건주문 식별자: {new_order_id})"
        else:
            return f"조건주문 수정 실패 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"조건주문 수정 중 오류 발생: {str(e)}"

def cancel_conditional_order_api(conditional_order_id: str) -> str:
    """조건주문을 취소합니다."""
    try:
        access_token = get_access_token()
        account_seq = get_account_seq(access_token)
        
        url = f"{BASE_URL}/api/v1/conditional-orders/{conditional_order_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tossinvest-Account": str(account_seq)
        }
        
        response = requests.delete(url, headers=headers, timeout=10)
        if response.status_code == 204:
            return f"조건주문({conditional_order_id})이 성공적으로 취소되었습니다."
        else:
            return f"조건주문 취소 실패 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"조건주문 취소 중 오류 발생: {str(e)}"
