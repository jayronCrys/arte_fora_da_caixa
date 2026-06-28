import random
import string
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app
)
from flask_mail import Message
from src.app import mail                       # Flask-Mail
from src.controller.users.user_default import (
    check_user, reset_user_password, database
)

from . import forg_pass_bp

# ─── Envio de e‑mail com o código ────────────────────────────────────────
def send_reset_email(email, code):
    """Envia o código de verificação para o e‑mail informado."""
    try:
        msg = Message(
            subject="Redefinição de senha",
            recipients=[email],
            body=f"Seu código de verificação é: {code}\n\nEste código expira em 15 minutos."
        )
        mail.send(msg)
        current_app.logger.info(f"Código enviado para {email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar e‑mail: {e}")
        return False

# ─── Rota: solicitar redefinição ──────────────────────────────────────────
@forg_pass_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('reset_password.html')

    identifier = request.form.get('identifier', '').strip()
    if not identifier:
        flash('Informe seu nome ou e‑mail.')
        return redirect(url_for('forgot_password.forgot_password'))

    # Determina se é e‑mail (contém @) ou nome
    if '@' in identifier:
        user = check_user(identifier, column='email')
    else:
        user = check_user(identifier, column='name')

    if not user:
        flash('Usuário não encontrado.')
        return redirect(url_for('auth.login'))

    user_id = user.get('id')
    user_email = user.get('email')

    # Caso 1: sem e‑mail → redefinição direta
    if not user_email:
        session['reset_user_id'] = str(user_id)
        session['direct_reset'] = True
        flash('Sua conta não possui e‑mail. Redefina sua senha agora.')
        return redirect(url_for('forgot_password.reset_password'))

    # Caso 2: com e‑mail → enviar código
    code = ''.join(random.choices(string.digits, k=6))
    session['reset_code'] = code
    session['reset_user_id'] = str(user_id)
    session['reset_code_expires'] = (datetime.utcnow() + timedelta(minutes=15)).timestamp()

    if not send_reset_email(user_email, code):
        flash('Erro ao enviar o código. Tente novamente mais tarde.')
        return redirect(url_for('forgot_password.forgot_password'))

    flash('Um código de verificação foi enviado para seu e‑mail.')
    return redirect(url_for('forgot_password.verify_code'))

# ─── Rota: verificar código ─────────────────────────────────────────────
@forg_pass_bp.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if 'reset_user_id' not in session or 'reset_code' not in session:
        flash('Sessão inválida. Recomece o processo.')
        return redirect(url_for('forgot_password.forgot_password'))

    if request.method == 'GET':
        return render_template('verify_code.html')

    submitted_code = request.form.get('code', '').strip()
    if not submitted_code:
        flash('Informe o código recebido.')
        return redirect(url_for('forgot_password.verify_code'))

    stored_code = session.get('reset_code')
    expires = session.get('reset_code_expires')

    if submitted_code != stored_code:
        flash('Código inválido.')
        return redirect(url_for('forgot_password.verify_code'))

    if expires and datetime.utcnow().timestamp() > expires:
        flash('O código expirou. Solicite um novo.')
        # Limpa dados da verificação
        session.pop('reset_code', None)
        session.pop('reset_code_expires', None)
        session.pop('reset_user_id', None)
        return redirect(url_for('forgot_password.forgot_password'))

    # Código válido
    session['code_verified'] = True
    session.pop('reset_code', None)
    session.pop('reset_code_expires', None)
    return redirect(url_for('forgot_password.reset_password'))

# ─── Rota: redefinir senha ──────────────────────────────────────────────
@forg_pass_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    user_id = session.get('reset_user_id')
    if not user_id or not (session.get('direct_reset') or session.get('code_verified')):
        flash('Acesso não autorizado. Inicie o processo novamente.')
        return redirect(url_for('forgot_password.forgot_password'))

    if request.method == 'GET':
        return render_template('reset_password.html')

    new_pass = request.form.get('new_password', '').strip()
    confirm_pass = request.form.get('confirm_password', '').strip()

    if not new_pass or not confirm_pass:
        flash('Preencha todos os campos.')
        return redirect(url_for('forgot_password.reset_password'))
    if new_pass != confirm_pass:
        flash('As senhas não coincidem.')
        return redirect(url_for('forgot_password.reset_password'))

    # Validação de força da senha (igual à do Create_Account)
    if ' ' in new_pass or len(new_pass) < 8:
        flash('A senha deve ter no mínimo 8 caracteres e não pode conter espaços.')
        return redirect(url_for('forgot_password.reset_password'))
    if not (any(c.isdigit() for c in new_pass) and
            any(c.isalpha() for c in new_pass) and
            any(c.islower() for c in new_pass) and
            any(c.isupper() for c in new_pass)):
        flash('A senha deve conter letras maiúsculas, minúsculas e números.')
        return redirect(url_for('forgot_password.reset_password'))

    success = reset_user_password(user_id, new_pass)
    if success:
        session.clear()
        flash('Senha redefinida com sucesso! Faça login com a nova senha.')
        return redirect(url_for('auth.login'))
    else:
        flash('Erro ao redefinir a senha. Tente novamente.')
        return redirect(url_for('forgot_password.reset_password'))