import time
import json
import os
import sys
import argparse
from datetime import datetime, timedelta

from toss_api import (
    get_access_token,
    get_account_seq,
    BASE_URL,
    get_portfolio_balance_and_return_rate_api,
    get_conditional_order_detail_api,
    create_conditional_order_api,
    cancel_conditional_order_api,
    sell_stock_api,
    get_conditional_orders_api
)

def log_message(msg):
    now = datetime.now()
    timestamped_msg = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(timestamped_msg, flush=True)
    
    # 일자별 로그 파일명 생성 (예: trading_log_20231024.txt)
    date_str = now.strftime('%Y%m%d')
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"trading_log_{date_str}.txt")
    
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(timestamped_msg + "\n")

def get_holding_info(symbol: str):
    log_message(f"[{symbol}] 계좌 보유 종목 정보 조회 요청...")
    data_str = get_portfolio_balance_and_return_rate_api()
    if data_str.startswith("Error"):
        log_message(f"[{symbol}] 포트폴리오 API 호출 오류: {data_str}")
        return None, None
    try:
        data = json.loads(data_str)
        items = data.get("result", {}).get("items", []) if "result" in data else data.get("items", [])
        for item in items:
            if item.get("symbol") == symbol:
                avg_price = float(item.get("averagePurchasePrice", 0))
                qty = int(float(item.get("quantity", 0)))
                log_message(f"[{symbol}] 보유 정보 조회 완료 - 평단가: {avg_price}, 수량: {qty}")
                return avg_price, qty
        log_message(f"[{symbol}] 보유 종목 목록에 해당 심볼({symbol})이 존재하지 않습니다.")
        return None, 0
    except Exception as e:
        log_message(f"[{symbol}] 보유 종목 조회 데이터 파싱 중 오류 발생: {e}\n응답데이터: {data_str}")
        return None, None

def get_kr_tick_size(price: float) -> int:
    if price < 2000:
        return 1
    elif price < 5000:
        return 5
    elif price < 20000:
        return 10
    elif price < 50000:
        return 50
    elif price < 200000:
        return 100
    elif price < 500000:
        return 500
    else:
        return 1000

def calculate_price(base_price: float, rate: float, market: str) -> float:
    target = base_price * (1 + rate)
    if market == "KR":
        tick = get_kr_tick_size(target)
        return float(round(target / tick) * tick)
    else:
        return round(target, 2)

def get_market(symbol: str) -> str:
    return "KR" if symbol.isdigit() else "US"

def get_expire_date() -> str:
    return (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

def register_stage_order(symbol: str, stage: int, avg_price: float, current_qty: int) -> str:
    market = get_market(symbol)
    
    if stage == 1:
        tp_rate = 0.03
        sl_rate = -0.03
        sell_qty = max(1, int(current_qty * 0.3))
    elif stage == 2:
        tp_rate = 0.06
        sl_rate = 0.00
        sell_qty = max(1, int(current_qty * 0.5))
    elif stage == 3:
        tp_rate = 0.09
        sl_rate = 0.03
        sell_qty = current_qty
    elif stage == -2:
        tp_rate = 0.03
        sl_rate = -0.06
        sell_qty = max(1, int(current_qty * 0.5))
    elif stage == -3:
        tp_rate = 0.03
        sl_rate = -0.09
        sell_qty = current_qty
    else:
        return None

    if sell_qty <= 0:
        log_message(f"[{symbol}] 매도할 수량이 없습니다 (잔고: {current_qty}). 봇을 종료합니다.")
        return None

    tp_price = calculate_price(avg_price, tp_rate, market)
    sl_price = calculate_price(avg_price, sl_rate, market)
    
    first = {
        "orderSide": "SELL",
        "triggerPrice": str(tp_price),
        "orderPrice": str(tp_price)
    }
    
    second = {
        "orderSide": "SELL",
        "triggerPrice": str(sl_price),
        "orderPrice": str(sl_price)
    }
    
    expire_date = get_expire_date()
    
    log_message(f"[{symbol}] Stage {stage} OCO 주문 등록 시도: 익절 감시가 {tp_price}, 손절 감시가 {sl_price}, 수량 {sell_qty}")
    
    res = create_conditional_order_api(
        symbol=symbol,
        type_val="OCO",
        quantity=sell_qty,
        expire_date=expire_date,
        first=first,
        second=second,
        order_type="LIMIT"
    )
    
    log_message(f"[{symbol}] API 응답: {res}")
    
    if "조건주문 식별자:" in res:
        order_id = res.split("조건주문 식별자: ")[1].strip(")")
        return order_id, None
    
    return None, res

def load_state(symbol: str) -> dict:
    state_file = f"auto_trader_state_{symbol}.json"
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return {}

def save_state(symbol: str, state: dict):
    state_file = f"auto_trader_state_{symbol}.json"
    with open(state_file, "w") as f:
        json.dump(state, f)

def attempt_register_with_fallback(symbol: str, target_stage: int, avg_price: float, current_qty: int, state: dict) -> bool:
    stages_to_try = []
    if target_stage == 1:
        stages_to_try = [1, -2, -3]
    elif target_stage == -2:
        stages_to_try = [-2, -3]
    elif target_stage == -3:
        stages_to_try = [-3]
    else:
        stages_to_try = [target_stage]
        
    for stg in stages_to_try:
        time.sleep(2) # API Rate Limit 방지
        order_id, err = register_stage_order(symbol, stg, avg_price, current_qty)
        if order_id:
            state["stage"] = stg
            state["order_id"] = order_id
            save_state(symbol, state)
            return True
        elif err and ("OCO" in err or "400" in err or "429" in err):
            log_message(f"[{symbol}] Stage {stg} 등록 실패 (주가 이탈 또는 오류: {err}). 다음 단계 시도...")
            continue
        elif err and "422" in err and "duplicate" in err:
            log_message(f"[{symbol}] 이미 설정된 조건주문이 존재하여 오류(422) 발생. 기존 주문을 모두 취소하고 다시 시도합니다...")
            res_json = get_conditional_orders_api(status="OPEN", symbol=symbol)
            if not res_json.startswith("Error"):
                try:
                    orders = json.loads(res_json).get("result", {}).get("conditionalOrders", [])
                    for order in orders:
                        c_id = order.get("conditionalOrderId")
                        if c_id:
                            cancel_conditional_order_api(c_id)
                            log_message(f"[{symbol}] 중복 조건주문({c_id}) 강제 취소 완료.")
                except Exception as e:
                    log_message(f"[{symbol}] 기존 조건주문 취소 중 오류: {e}")
            time.sleep(2)
            # 재시도 로직을 위해 다시 시도해야 하지만 for루프의 stg는 넘어감. 따라서 이 stg를 다시 시도해야함.
            # 하지만 간단하게 다음 루프나 재시작을 유도하기 위해 return False를 해서 와치독이 재시작하게 하거나 
            # 혹은 while 안에서 해결해야 함. 와치독 재시작 유도:
            import sys
            sys.exit(1)
        else:
            log_message(f"[{symbol}] 통신 오류 또는 알 수 없는 오류 발생({err}). 시장가 손절 없이 봇을 일시 정지(코드 1)합니다.")
            import sys
            sys.exit(1)
            
    if target_stage in [1, -2, -3]:
        log_message(f"[{symbol}] -9% 조건(Stage -3)까지 모두 실패. 현재가가 이미 너무 낮습니다. 전량 시장가 손절 진행!")
        res = sell_stock_api(symbol, "MARKET", current_qty)
        log_message(f"[{symbol}] 시장가 손절 결과: {res}")
        state["order_id"] = None
        save_state(symbol, state)
        return False
        
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    
    symbol = args.symbol
    log_message(f"[{symbol}] 다단계 OCO 자동매매 봇 시작")
    
    state = load_state(symbol)
    
    if "stage" not in state or not state.get("order_id"):
        # 봇 최초 시작 또는 재시작 시 주문이 없는 경우
        avg_price, qty = get_holding_info(symbol)
        if avg_price is None:
            log_message(f"[{symbol}] API 통신 오류로 잔고를 조회할 수 없어 봇을 일시 정지(코드 1)합니다. 와치독이 재시작할 것입니다.")
            import sys
            sys.exit(1)
        if qty <= 0:
            log_message(f"[{symbol}] 보유 주식이 없어 봇을 종료합니다.")
            return
            
        state["stage"] = 1
        state["avg_price"] = avg_price
        
        success = attempt_register_with_fallback(symbol, 1, avg_price, qty, state)
        if not success:
            log_message(f"[{symbol}] 초기 주문 등록 및 시장가 손절 처리 완료로 봇을 종료합니다.")
            return

    while True:
        try:
            state = load_state(symbol)
            order_id = state.get("order_id")
            stage = state.get("stage", 1)
            avg_price = state.get("avg_price")
            
            if not order_id:
                break
                
            res = get_conditional_order_detail_api(order_id)
            if res.startswith("Error") or "조회 실패" in res or "오류 발생" in res:
                log_message(f"[{symbol}] 조건주문({order_id}) 상세 조회 실패: {res}")
            else:
                try:
                    order_data = json.loads(res)
                    if "result" in order_data:
                        order_data = order_data["result"]
                except json.JSONDecodeError as e:
                    log_message(f"[{symbol}] API 응답 JSON 파싱 실패 (일시적 오류 가능성): {e} / 원본: {res}")
                    continue
                    
                status = order_data.get("status")
                first_status = (order_data.get("first") or {}).get("status", "N/A")
                second_status = (order_data.get("second") or {}).get("status", "N/A")
                
                log_message(f"[{symbol}] 1분 주기 상태 확인 - 주문번호: {order_id}, 현재단계: Stage {stage}, 전체상태: {status}, 익절조건상태: {first_status}, 손절조건상태: {second_status}")
                
                if status in ["COMPLETED", "EXPIRED", "CANCELED"]:
                    log_message(f"[{symbol}] OCO 주문({order_id}) 상태 변경 감지: {status}")
                    
                    if status == "COMPLETED":
                        first_status = order_data.get("first", {}).get("status")
                        second_status = order_data.get("second", {}).get("status")
                        
                        log_message(f"[{symbol}] 상세 상태 - 익절 감시: {first_status}, 손절 감시: {second_status}")
                        
                        if first_status in ["ORDERED", "COMPLETED"]:
                            log_message(f"[{symbol}] [!] Stage {stage} 익절 달성!")
                            
                            next_stage = None
                            if stage == 1:
                                next_stage = 2
                            elif stage == 2:
                                next_stage = 3
                                
                            if next_stage is None:
                                log_message(f"[{symbol}] 익절 후 더 이상 진행할 단계가 없습니다. 봇을 종료합니다.")
                                state["order_id"] = None
                                save_state(symbol, state)
                                break
                            
                            # 다음 단계 주문 등록
                            time.sleep(5) # 체결 후 잔고 반영 대기
                            _, qty = get_holding_info(symbol)
                            if qty > 0:
                                success = attempt_register_with_fallback(symbol, next_stage, avg_price, qty, state)
                                if not success:
                                    break
                            else:
                                break
                        elif second_status in ["ORDERED", "COMPLETED"]:
                            log_message(f"[{symbol}] [!] Stage {stage} 손절 조건 발동!")
                            
                            next_stage = None
                            if stage == 1:
                                next_stage = -2
                            elif stage == -2:
                                next_stage = -3
                                
                            if next_stage is None:
                                log_message(f"[{symbol}] 손절 후 더 이상 진행할 단계가 없습니다. 봇을 종료합니다.")
                                state["order_id"] = None
                                save_state(symbol, state)
                                break
                                
                            # 다음 단계 주문 등록
                            time.sleep(5)
                            _, qty = get_holding_info(symbol)
                            if qty > 0:
                                success = attempt_register_with_fallback(symbol, next_stage, avg_price, qty, state)
                                if not success:
                                    break
                            else:
                                break
                        else:
                            log_message(f"[{symbol}] 알 수 없는 체결 상태. 봇 종료.")
                            break
                    else:
                        log_message(f"[{symbol}] 조건주문 취소 또는 만료. 봇 종료.")
                        state["order_id"] = None
                        save_state(symbol, state)
                        break
                        
        except Exception as e:
            log_message(f"[{symbol}] 감시 루프 오류: {e}")
            
        time.sleep(60) # 1분마다 폴링

if __name__ == "__main__":
    main()
