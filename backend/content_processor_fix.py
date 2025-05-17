import os
import subprocess
import sys

def check_install_packages():
    """필요한 패키지가 설치되어 있는지 확인하고 없으면 설치"""
    required_packages = [
        'html2text',  # HTML을 마크다운으로 변환
        'readability-lxml',  # 콘텐츠 추출 향상 (선택 사항)
        'charset-normalizer',  # 인코딩 감지 개선
        'newspaper3k'  # 뉴스 기사 분석 (선택 사항)
    ]

    installed = []
    not_installed = []

    # 설치된 패키지 확인
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            installed.append(package)
        except ImportError:
            not_installed.append(package)

    # 누락된 패키지 설치
    if not_installed:
        print(f"다음 패키지를 설치합니다: {', '.join(not_installed)}")
        try:
            # pip를 사용하여 패키지 설치
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + not_installed)
            print("패키지 설치 완료!")
        except subprocess.CalledProcessError as e:
            print(f"패키지 설치 중 오류 발생: {e}")
            # requirements.txt에 추가
            add_to_requirements(not_installed)
            return False

    return True

def add_to_requirements(packages):
    """패키지를 requirements.txt에 추가"""
    req_path = os.path.join("requirements.txt")

    # 기존 requirements.txt 읽기
    existing_packages = []
    if os.path.exists(req_path):
        with open(req_path, 'r') as f:
            existing_packages = [line.strip() for line in f.readlines()]

    # 새 패키지 추가
    with open(req_path, 'a') as f:
        for package in packages:
            if package not in existing_packages and f"{package}==" not in existing_packages:
                f.write(f"{package}\n")

    print(f"패키지가 requirements.txt에 추가되었습니다. 'pip install -r requirements.txt'를 실행하여 설치하세요.")

if __name__ == "__main__":
    check_install_packages()
