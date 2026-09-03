import sys
import os
import subprocess
from fastmcp import FastMCP
from toss_api import (
    get_portfolio_balance_and_return_rate_api,
    buy_stock_api,
    sell_stock_api,
    get_buying_power_api,
    create_conditional_order_api,
    get_conditional_orders_api,
    modify_conditional_order_api,
    cancel_conditional_order_api
)

# FastMCP 서버 초기화
mcp = FastMCP("TossInvest")

active_auto_traders = {}

@mcp.tool()
def get_portfolio_balance_and_return_rate() -> str:
    """내 포트폴리오 잔고 및 수익률을 조회합니다."""
    return get_portfolio_balance_and_return_rate_api()

@mcp.tool()
def create_conditional_order(symbol: str, type_val: str, quantity: int, expire_date: str, first: dict, second: dict = None, order_type: str = "LIMIT") -> str:
    """
    토스증권 API를 사용하여 조건주문을 생성합니다.
    :param symbol: 종목 코드 (예: 005930)
    :param type_val: 조건 타입 ('SINGLE', 'OCO', 'OTO')
    :param quantity: 주문 수량
    :param expire_date: 만료일 (YYYY-MM-DD 형식)
    :param first: 첫번째 조건 정보 (dict)
    :param second: 두번째 조건 정보 (dict, 선택)
    :param order_type: 주문 타입 (기본 'LIMIT')
    """
    return create_conditional_order_api(symbol, type_val, quantity, expire_date, first, second, order_type)

@mcp.tool()
def get_conditional_orders(status: str = "OPEN", symbol: str = None) -> str:
    """
    조건주문 목록을 조회합니다.
    :param status: 상태 ('OPEN' 또는 'CLOSED')
    :param symbol: 종목 코드 (선택)
    """
    return get_conditional_orders_api(status, symbol)

@mcp.tool()
def modify_conditional_order(conditional_order_id: str, type_val: str, quantity: int, expire_date: str, first: dict, second: dict = None, order_type: str = "LIMIT") -> str:
    """
    조건주문을 수정합니다.
    :param conditional_order_id: 조건주문 식별자
    :param type_val: 조건 타입 ('SINGLE', 'OCO', 'OTO')
    :param quantity: 주문 수량
    :param expire_date: 만료일 (YYYY-MM-DD 형식)
    :param first: 첫번째 조건 정보 (dict)
    :param second: 두번째 조건 정보 (dict, 선택)
    :param order_type: 주문 타입 (기본 'LIMIT')
    """
    return modify_conditional_order_api(conditional_order_id, type_val, quantity, expire_date, first, second, order_type)

@mcp.tool()
def cancel_conditional_order(conditional_order_id: str) -> str:
    """
    조건주문을 취소합니다.
    :param conditional_order_id: 취소할 조건주문 식별자
    """
    return cancel_conditional_order_api(conditional_order_id)

@mcp.tool()
def buy_stock(symbol: str, order_type: str, quantity: int, price: float = 0.0) -> str:
    """
    토스증권 API를 사용하여 주식을 매수합니다.
    :param symbol: 종목 코드 (예: 005930)
    :param order_type: 주문 타입 ('MARKET' 또는 'LIMIT')
    :param quantity: 매수 수량 (주)
    :param price: 지정가('LIMIT') 주문 시 매수 가격 (시장가인 경우 무시됨)
    """
    return buy_stock_api(symbol, order_type, quantity, price)

@mcp.tool()
def sell_stock(symbol: str, order_type: str, quantity: int, price: float = 0.0) -> str:
    """
    토스증권 API를 사용하여 주식을 매도합니다.
    :param symbol: 종목 코드 (예: 005930)
    :param order_type: 주문 타입 ('MARKET' 또는 'LIMIT')
    :param quantity: 매도 수량 (주)
    :param price: 지정가('LIMIT') 주문 시 매도 가격 (시장가인 경우 무시됨)
    """
    return sell_stock_api(symbol, order_type, quantity, price)

@mcp.tool()
def get_buying_power(currency: str = "KRW") -> str:
    """
    토스증권 API를 사용하여 계좌의 예수금(주문 가능 금액)을 조회합니다.
    :param currency: 통화 (기본값: 'KRW', 미국 주식의 경우 'USD' 입력)
    """
    return get_buying_power_api(currency)

@mcp.tool()
def start_auto_trader(symbol: str) -> str:
    """
    특정 종목에 대한 다단계 OCO 자동매매 봇을 실행합니다.
    :param symbol: 종목 코드
    """
    if symbol in active_auto_traders:
        if active_auto_traders[symbol].poll() is None:
            return f"이미 [{symbol}] 종목에 대한 자동매매 봇이 실행 중입니다."
    
    bot_path = os.path.join(os.path.dirname(__file__), "auto_trader.py")
    cmd = [sys.executable, bot_path, "--symbol", symbol]
    
    try:
        process = subprocess.Popen(cmd)
        active_auto_traders[symbol] = process
        return f"[{symbol}] 종목 다단계 OCO 자동매매 봇을 시작했습니다. (PID: {process.pid})"
    except Exception as e:
        return f"자동매매 봇 실행 중 오류: {str(e)}"

@mcp.tool()
def stop_auto_trader(symbol: str) -> str:
    """
    실행 중인 자동매매 봇을 중지합니다.
    :param symbol: 종목 코드
    """
    if symbol not in active_auto_traders:
        return f"[{symbol}] 종목에 대해 실행 중인 봇을 찾을 수 없습니다."
        
    process = active_auto_traders[symbol]
    if process.poll() is None:
        process.terminate()
        del active_auto_traders[symbol]
        return f"[{symbol}] 종목 봇(PID: {process.pid})을 종료했습니다. (조건주문 취소는 별도로 진행해야 할 수 있습니다)"
    else:
        del active_auto_traders[symbol]
        return f"[{symbol}] 종목 봇은 이미 종료된 상태입니다."

if __name__ == "__main__":
    # 서버 실행 (stdio 모드 등 기본 설정으로 실행됨)
    mcp.run()
