from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint('auth', __name__)

USUARIO_CORRETO = 'interadmin'
SENHA_CORRETA = 'Intervet2025'

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        senha = request.form['password']

        if usuario == USUARIO_CORRETO and senha == SENHA_CORRETA:
            session['usuario'] = usuario
            destino = session.pop('destino', 'home')
            return redirect(url_for(destino))
        else:
            flash('Usuário ou senha incorretos', 'erro')
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Sessão encerrada com sucesso!', 'sucesso')
    return redirect(url_for('home'))
