import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os



template_dir = os.path.abspath('templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'sua_chave_secreta_aqui_mude_isso'  # Troque por algo seguro

print(">>> PASTA DE TEMPLATES:", app.template_folder)
print(">>> ARQUIVOS NESSA PASTA:", os.listdir(app.template_folder))

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Função para conectar ao banco
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

# Criar tabelas se não existirem
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabela de usuários (admin)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Tabela de pedidos de orçamento
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT,
            tipo_site TEXT,
            mensagem TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'novo'
        )
    ''')
    
    # Tabela de feedbacks de clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_cliente TEXT NOT NULL,
            feedback TEXT NOT NULL,
            estrelas INTEGER,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aprovado BOOLEAN DEFAULT 0
        )
    ''')
    
    # Tabela de projetos (portfólio)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            imagem_url TEXT,
            link TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de posts do blog
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            conteudo TEXT,
            autor TEXT,
            data_publicacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # Criar usuário admin padrão se não existir (você pode mudar depois)
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed = generate_password_hash('Rafael@2024')
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", ('admin', hashed))
        conn.commit()
    
    conn.close()

init_db()

# Modelo de usuário para o Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'])
    return None

# Rota para login do admin
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'])
            login_user(user_obj)
            return redirect(url_for('admin_painel'))
        else:
            flash('Usuário ou senha inválidos')
    return render_template('admin_login.html')

# Rota para logout
@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

# Painel principal do admin
@app.route('/admin')
@login_required
def admin_painel():
    conn = get_db()
    total_pedidos = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    total_feedbacks = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
    total_projetos = conn.execute("SELECT COUNT(*) FROM projetos").fetchone()[0]
    total_blog = conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0]
    conn.close()
    return render_template('admin_painel.html', 
                           total_pedidos=total_pedidos,
                           total_feedbacks=total_feedbacks,
                           total_projetos=total_projetos,
                           total_blog=total_blog)

# Listar pedidos
@app.route('/admin/pedidos')
@login_required
def admin_pedidos():
    conn = get_db()
    pedidos = conn.execute("SELECT * FROM pedidos ORDER BY data DESC").fetchall()
    conn.close()
    return render_template('admin_pedidos.html', pedidos=pedidos)

# Marcar pedido como respondido (exemplo)
@app.route('/admin/pedidos/responder/<int:id>')
@login_required
def responder_pedido(id):
    conn = get_db()
    conn.execute("UPDATE pedidos SET status = 'respondido' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_pedidos'))

# Listar feedbacks
@app.route('/admin/feedbacks')
@login_required
def admin_feedbacks():
    conn = get_db()
    feedbacks = conn.execute("SELECT * FROM feedbacks ORDER BY data DESC").fetchall()
    conn.close()
    return render_template('admin_feedbacks.html', feedbacks=feedbacks)

# Aprovar feedback para aparecer no site
@app.route('/admin/feedbacks/aprovar/<int:id>')
@login_required
def aprovar_feedback(id):
    conn = get_db()
    conn.execute("UPDATE feedbacks SET aprovado = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_feedbacks'))

# Listar projetos
@app.route('/admin/projetos')
@login_required
def admin_projetos():
    conn = get_db()
    projetos = conn.execute("SELECT * FROM projetos ORDER BY data_criacao DESC").fetchall()
    conn.close()
    return render_template('admin_projetos.html', projetos=projetos)

# Adicionar projeto
@app.route('/admin/projetos/novo', methods=['GET', 'POST'])
@login_required
def novo_projeto():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        imagem_url = request.form['imagem_url']
        link = request.form['link']
        conn = get_db()
        conn.execute('''
            INSERT INTO projetos (titulo, descricao, imagem_url, link)
            VALUES (?, ?, ?, ?)
        ''', (titulo, descricao, imagem_url, link))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_projetos'))
    return render_template('admin_projeto_form.html')

# Excluir projeto
@app.route('/admin/projetos/excluir/<int:id>')
@login_required
def excluir_projeto(id):
    conn = get_db()
    conn.execute("DELETE FROM projetos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_projetos'))

# Listar blog posts
@app.route('/admin/blog')
@login_required
def admin_blog():
    conn = get_db()
    posts = conn.execute("SELECT * FROM blog_posts ORDER BY data_publicacao DESC").fetchall()
    conn.close()
    return render_template('admin_blog.html', posts=posts)

# Adicionar post no blog
@app.route('/admin/blog/novo', methods=['GET', 'POST'])
@login_required
def novo_post():
    if request.method == 'POST':
        titulo = request.form['titulo']
        conteudo = request.form['conteudo']
        autor = request.form.get('autor', 'Rafael')
        conn = get_db()
        conn.execute('''
            INSERT INTO blog_posts (titulo, conteudo, autor)
            VALUES (?, ?, ?)
        ''', (titulo, conteudo, autor))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_blog'))
    return render_template('admin_post_form.html')

# Excluir post
@app.route('/admin/blog/excluir/<int:id>')
@login_required
def excluir_post(id):
    conn = get_db()
    conn.execute("DELETE FROM blog_posts WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_blog'))

# --- ROTAS PÚBLICAS (seu site) ---

# Rota para receber pedidos do formulário de orçamento (via POST)
@app.route('/api/pedido', methods=['POST'])
def receber_pedido():
    data = request.form
    nome = data.get('nome')
    email = data.get('email')
    telefone = data.get('telefone')
    tipo_site = data.get('tipo_site')
    mensagem = data.get('mensagem')
    
    if not nome or not email:
        return "Nome e e-mail são obrigatórios", 400
    
    conn = get_db()
    conn.execute('''
        INSERT INTO pedidos (nome, email, telefone, tipo_site, mensagem)
        VALUES (?, ?, ?, ?, ?)
    ''', (nome, email, telefone, tipo_site, mensagem))
    conn.commit()
    conn.close()
    
    return "Pedido recebido com sucesso! Em breve entraremos em contato."

# Rota para receber feedback de cliente (via POST)
@app.route('/api/feedback', methods=['POST'])
def receber_feedback():
    data = request.form
    nome = data.get('nome')
    feedback = data.get('feedback')
    estrelas = data.get('estrelas', 5)
    
    if not nome or not feedback:
        return "Nome e feedback são obrigatórios", 400
    
    conn = get_db()
    conn.execute('''
        INSERT INTO feedbacks (nome_cliente, feedback, estrelas, aprovado)
        VALUES (?, ?, ?, ?)
    ''', (nome, feedback, estrelas, 0))  # 0 = não aprovado ainda
    conn.commit()
    conn.close()
    
    return "Feedback enviado! Obrigado."

# Rota para listar feedbacks aprovados (para exibir no site)
@app.route('/api/feedbacks-aprovados')
def feedbacks_aprovados():
    conn = get_db()
    feedbacks = conn.execute("SELECT nome_cliente, feedback, estrelas FROM feedbacks WHERE aprovado = 1 ORDER BY data DESC").fetchall()
    conn.close()
    return {'feedbacks': [dict(f) for f in feedbacks]}

# Rota para listar projetos (para exibir no site)
@app.route('/api/projetos')
def listar_projetos():
    conn = get_db()
    projetos = conn.execute("SELECT titulo, descricao, imagem_url, link FROM projetos ORDER BY data_criacao DESC").fetchall()
    conn.close()
    return {'projetos': [dict(p) for p in projetos]}

# Rota para listar posts do blog
@app.route('/api/blog')
def listar_blog():
    conn = get_db()
    posts = conn.execute("SELECT titulo, conteudo, autor, data_publicacao FROM blog_posts ORDER BY data_publicacao DESC").fetchall()
    conn.close()
    return {'posts': [dict(p) for p in posts]}

# Rota principal do seu site (front-end) - se quiser servir o index.html pelo Flask
@app.route('/')
def index():
    return render_template('index.html')  # Coloque seu index.html dentro de templates

if __name__ == '__main__':
    app.run(debug=True)