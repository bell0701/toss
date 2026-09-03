import subprocess
import time
import os
import argparse
from datetime import datetime

def log_message(msg):
    now = datetime.now()
    timestamped_msg = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] [WATCHDOG] {msg}"
    print(timestamped_msg, flush=True)
    
    date_str = now.strftime('%Y%m%d')
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"watchdog_log_{date_str}.txt")
    
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(timestamped_msg + "\n")

def get_current_log_file():
    date_str = datetime.now().strftime('%Y%m%d')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), f"trading_log_{date_str}.txt")

def start_bot(symbol):
    log_message(f"auto_trader.py --symbol {symbol} 프로세스를 시작합니다.")
    return subprocess.Popen(["python", "auto_trader.py", "--symbol", symbol])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    
    symbol = args.symbol
    max_silent_seconds = 240  # 4분 이상 로그 갱신이 없으면 프리징으로 간주
    
    log_message(f"[{symbol}] 와치독 감시 프로그램을 시작합니다. (허용 응답 대기시간: {max_silent_seconds}초)")
    
    process = start_bot(symbol)
    
    while True:
        try:
            time.sleep(60)
            
            retcode = process.poll()
            if retcode is not None:
                if retcode == 0:
                    log_message(f"봇 프로세스가 정상적으로 종료되었습니다. (목표 달성 등) 와치독도 함께 종료합니다.")
                    break
                else:
                    log_message(f"봇 프로세스가 비정상 종료(코드 {retcode})되었습니다. 재시작합니다...")
                    process = start_bot(symbol)
                    continue
                
            # 로그 파일 갱신 시간 체크
            log_file = get_current_log_file()
            if os.path.exists(log_file):
                mtime = os.path.getmtime(log_file)
                silent_time = time.time() - mtime
                
                if silent_time > max_silent_seconds:
                    log_message(f"로그가 {int(silent_time)}초 동안 갱신되지 않았습니다. 프리징으로 간주하여 강제 종료 후 재시작합니다.")
                    try:
                        process.kill()
                        process.wait(timeout=5)
                    except:
                        pass
                    process = start_bot(symbol)
            
        except Exception as e:
            log_message(f"와치독 루프 에러: {e}")

if __name__ == "__main__":
    main()
