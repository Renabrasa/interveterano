from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps

auth_bp = Blueprint('auth', __name__)

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('username')
        senha = request.form.get('password')

        if usuario == 'interadmin' and senha == 'Intervet2025':
            session['usuario'] = 'interadmin'
            session['logado'] = True
            flash('Login realizado com sucesso!', 'sucesso')
            return redirect(url_for('home'))  # ou redirecionar para uma página protegida
        else:
            flash('Usuário ou senha inválidos.', 'erro')
            return redirect(url_for('auth.login'))
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.pop('logado', None)
    session.pop('usuario', None)  # ✅ Removendo também o usuário
    flash('Logout realizado com sucesso!', 'sucesso')
    return redirect(url_for('home'))

# Decorador para rotas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logado'):
            session['proxima_url'] = request.path
            flash('Você precisa estar logado para acessar esta página.', 'erro')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
