@echo off
echo === Setup do ambiente Python ===
cd /d %~dp0

python -m venv venv
call venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
    copy ..\\.env.example .env
    echo .env criado a partir do .env.example — configure suas chaves!
)

echo.
echo Pronto. Para rodar: python run.py
